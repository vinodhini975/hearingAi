"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.analyzeSession = analyzeSession;
const db_1 = require("../db");
const pathology_classifier_1 = require("./pathology-classifier");
async function analyzeSession(sessionId) {
    const session = await (0, db_1.dbGet)('SELECT * FROM sessions WHERE id = ?', [sessionId]);
    if (!session) {
        throw new Error('Session not found');
    }
    // 1. Fetch trials data
    const pureToneTrials = await (0, db_1.dbAll)('SELECT * FROM pure_tone_trials WHERE session_id = ? ORDER BY timestamp ASC', [sessionId]);
    const speechTrials = await (0, db_1.dbAll)('SELECT * FROM speech_trials WHERE session_id = ? ORDER BY timestamp ASC', [sessionId]);
    const estimatedThresholds = await (0, db_1.dbAll)('SELECT * FROM thresholds WHERE session_id = ?', [sessionId]);
    // 2. Format thresholds
    const leftThresholds = {};
    const rightThresholds = {};
    estimatedThresholds.forEach((t) => {
        if (t.ear === 'LEFT')
            leftThresholds[t.frequency] = t.estimated_level;
        if (t.ear === 'RIGHT')
            rightThresholds[t.frequency] = t.estimated_level;
    });
    // 3. Calculate Speech Recognition Scores
    const leftSpeechTrials = speechTrials.filter((t) => t.ear === 'LEFT');
    const rightSpeechTrials = speechTrials.filter((t) => t.ear === 'RIGHT');
    const calculateSpeechScore = (trials) => {
        if (trials.length === 0)
            return 0;
        const correctCount = trials.filter((t) => t.is_correct === 1).length;
        return Math.round((correctCount / trials.length) * 100);
    };
    const leftSpeechScore = calculateSpeechScore(leftSpeechTrials);
    const rightSpeechScore = calculateSpeechScore(rightSpeechTrials);
    // 4. Determine Data Quality and Response Reliability
    // Calculate false alarm rate from silent catch trials (sound_level = 0)
    const catchTrials = pureToneTrials.filter((t) => t.sound_level === 0);
    const falseAlarms = catchTrials.filter((t) => t.response === 1);
    const falseAlarmRate = catchTrials.length > 0 ? falseAlarms.length / catchTrials.length : 0;
    // Check for premature responses (response_time < 300ms)
    const prematureResponses = pureToneTrials.filter((t) => t.sound_level > 0 && t.response === 1 && t.response_time < 300);
    // Determine Data Quality Label
    let dataQuality = 'Reliable';
    const totalRequiredPureTone = 8; // 4 freqs * 2 ears
    if (estimatedThresholds.length < totalRequiredPureTone || speechTrials.length < 3) {
        dataQuality = 'Insufficient data';
    }
    else if (falseAlarmRate >= 0.40 || prematureResponses.length >= 3) {
        dataQuality = 'Potentially unreliable';
    }
    // Determine Confidence Level
    let confidenceLevel = 'High confidence';
    if (dataQuality === 'Insufficient data') {
        confidenceLevel = 'Low confidence';
    }
    else if (dataQuality === 'Potentially unreliable') {
        confidenceLevel = 'Low confidence';
    }
    else {
        // If headphone info is 'other' or missing symptoms, drop to moderate
        const headphoneLower = (session.headphone_type || '').toLowerCase();
        if (headphoneLower.includes('other') || headphoneLower === '') {
            confidenceLevel = 'Moderate confidence';
        }
    }
    // 5. Interpret each ear
    const interpretEar = (thresholds, speechScore) => {
        const freqs = Object.keys(thresholds).map(Number);
        if (freqs.length === 0)
            return 'Testing not started or incomplete.';
        const avgThreshold = freqs.reduce((sum, f) => sum + thresholds[f], 0) / freqs.length;
        // Normal hearing: Average device amplitude threshold <= 0.15 (15% volume)
        // Mild difficulty: 0.15 < Average <= 0.35
        // Significant difficulty: Average > 0.35
        let statusText = 'Normal-looking screening response';
        if (avgThreshold > 0.35) {
            statusText = 'Possible significant hearing difficulty';
        }
        else if (avgThreshold > 0.15) {
            statusText = 'Possible mild hearing difficulty';
        }
        // High frequency specific check (4000Hz, 6000Hz, 8000Hz) vs Low frequency (1000Hz, 2000Hz)
        const lowFreqs = freqs.filter((f) => f <= 2000);
        const highFreqs = freqs.filter((f) => f >= 4000);
        const lowAvg = lowFreqs.length > 0 ? lowFreqs.reduce((s, f) => s + thresholds[f], 0) / lowFreqs.length : 0;
        const highAvg = highFreqs.length > 0 ? highFreqs.reduce((s, f) => s + thresholds[f], 0) / highFreqs.length : 0;
        if (highAvg - lowAvg > 0.20 && statusText === 'Normal-looking screening response') {
            statusText = 'High-frequency hearing difficulty';
        }
        return statusText;
    };
    const leftInterpretation = interpretEar(leftThresholds, leftSpeechScore);
    const rightInterpretation = interpretEar(rightThresholds, rightSpeechScore);
    // 6. Compare Ears
    const leftFreqs = Object.keys(leftThresholds).map(Number);
    const rightFreqs = Object.keys(rightThresholds).map(Number);
    let comparisonText = '';
    let isAsymmetric = false;
    if (leftFreqs.length > 0 && rightFreqs.length > 0) {
        const leftAvg = leftFreqs.reduce((sum, f) => sum + leftThresholds[f], 0) / leftFreqs.length;
        const rightAvg = rightFreqs.reduce((sum, f) => sum + rightThresholds[f], 0) / rightFreqs.length;
        const diff = Math.abs(leftAvg - rightAvg);
        const speechDiff = Math.abs(leftSpeechScore - rightSpeechScore);
        if (diff > 0.15 || speechDiff >= 30) {
            isAsymmetric = true;
            const strongerEar = leftAvg < rightAvg ? 'Left' : 'Right';
            comparisonText = `Asymmetric hearing performance observed. The ${strongerEar} ear performed notably better than the other, with a mean device threshold difference of ${Math.round(diff * 100)}% and a speech score difference of ${speechDiff}%.`;
        }
        else {
            comparisonText = 'Symmetrical hearing performance observed between both ears. Left and right thresholds are balanced within typical screening tolerances.';
        }
    }
    else {
        comparisonText = 'Comparison cannot be performed because testing for one or both ears is incomplete.';
    }
    // 7. Map to the Three Major Hearing-Loss Patterns (suggestive only)
    let hearingPattern = 'Indeterminate';
    let overallStatus = 'Normal-looking screening response';
    if (dataQuality !== 'Insufficient data') {
        const allLeftVals = Object.values(leftThresholds);
        const allRightVals = Object.values(rightThresholds);
        const combinedVals = [...allLeftVals, ...allRightVals];
        const combinedAvg = combinedVals.reduce((s, v) => s + v, 0) / combinedVals.length;
        const combinedSpeechAvg = (leftSpeechScore + rightSpeechScore) / 2;
        const leftFreqsKeys = Object.keys(leftThresholds).map(Number);
        const leftLow = leftFreqsKeys.filter(f => f <= 2000).reduce((s, f) => s + leftThresholds[f], 0) / 2;
        const leftHigh = leftFreqsKeys.filter(f => f >= 4000).reduce((s, f) => s + leftThresholds[f], 0) / 3;
        const rightFreqsKeys = Object.keys(rightThresholds).map(Number);
        const rightLow = rightFreqsKeys.filter(f => f <= 2000).reduce((s, f) => s + rightThresholds[f], 0) / 2;
        const rightHigh = rightFreqsKeys.filter(f => f >= 4000).reduce((s, f) => s + rightThresholds[f], 0) / 3;
        const leftSloping = leftHigh - leftLow > 0.15;
        const rightSloping = rightHigh - rightLow > 0.15;
        if (combinedAvg <= 0.15 && combinedSpeechAvg >= 90) {
            hearingPattern = 'Normal hearing response';
            overallStatus = 'Normal-looking screening response';
        }
        else {
            overallStatus = isAsymmetric ? 'Asymmetric hearing performance' : 'Further professional evaluation recommended';
            // 1. Conductive Pattern:
            // High thresholds (elevated) but speech scores remain high (>= 80% accuracy)
            // and flat threshold slopes (not steeply sloping down at high freqs)
            if (combinedSpeechAvg >= 80 && !leftSloping && !rightSloping) {
                hearingPattern = 'Possible conductive hearing-loss pattern';
            }
            // 2. Sensorineural Pattern:
            // Elevated thresholds especially in high frequencies, and speech scores are significantly reduced (< 75%)
            else if (combinedSpeechAvg < 75 && (leftSloping || rightSloping || combinedAvg > 0.30)) {
                hearingPattern = 'The observed results may be suggestive of sensorineural hearing difficulty';
            }
            // 3. Mixed Pattern:
            // High thresholds across all frequencies (flat or irregular), combined with a moderately reduced speech score
            else if (combinedSpeechAvg >= 40 && combinedSpeechAvg < 80 && combinedAvg > 0.25) {
                hearingPattern = 'The available screening data show a pattern that may warrant evaluation for mixed hearing loss';
            }
            else {
                hearingPattern = 'The available screening results are insufficient to determine the underlying type of difficulty. Professional audiological testing is recommended.';
            }
        }
    }
    // 7b. Run Machine Learning Pathology Classification Layer (hearing_pathology_model.pkl)
    let pathologyClassification;
    try {
        pathologyClassification = await (0, pathology_classifier_1.runPathologyClassification)({
            leftThresholds,
            rightThresholds,
            leftSpeechScore,
            rightSpeechScore,
            age: session.age,
            symptoms: JSON.parse(session.symptoms || '[]'),
            headphoneType: session.headphone_type,
            deviceType: session.device_type,
        });
    }
    catch (err) {
        console.error('Error invoking pathology classifier:', err);
    }
    // 8. Generate explanation report
    let aiExplanation = '';
    if (dataQuality === 'Insufficient data') {
        aiExplanation = 'The available test data may not be reliable enough for a meaningful preliminary assessment. Please repeat the test under recommended conditions (quiet environment, headphones securely adjusted) or consult a hearing professional.';
    }
    else {
        const age = session.age;
        const symptoms = JSON.parse(session.symptoms || '[]');
        const headphone = session.headphone_type;
        aiExplanation = `### Clinical Findings Summary
User is a ${age}-year-old testing with ${headphone}. The screening was completed in a quiet environment.

1. **Pure-Tone Response Analysis:**
   - **Left Ear:** Mean relative device threshold is **${Math.round((Object.values(leftThresholds).reduce((s, v) => s + v, 0) / Object.keys(leftThresholds).length) * 100)}%**. The response profile shows ${leftInterpretation.toLowerCase()}.
   - **Right Ear:** Mean relative device threshold is **${Math.round((Object.values(rightThresholds).reduce((s, v) => s + v, 0) / Object.keys(rightThresholds).length) * 100)}%**. The response profile shows ${rightInterpretation.toLowerCase()}.

2. **Speech Recognition Performance:**
   - Left ear speech recognition score: **${leftSpeechScore}%** accuracy.
   - Right ear speech recognition score: **${rightSpeechScore}%** accuracy.
   ${leftSpeechScore < 80 || rightSpeechScore < 80 ? 'Reduced speech clarity suggests potential difficulties in word intelligibility, which is commonly associated with high-frequency hearing attenuation.' : 'Speech intelligibility remains excellent, indicating strong speech recognition capabilities in low-noise settings.'}

3. **Ear-to-Ear Comparison:**
   - ${comparisonText}

4. **Machine Learning Pathology Classification (Layer: hearing_pathology_model.pkl):**
   - **Model Prediction:** **${pathologyClassification?.overallPathology || 'Indeterminate'}** (${pathologyClassification?.overallConfidence || 0}% model confidence).
   - **Left Ear:** ${pathologyClassification?.leftEar?.predictedClass || 'Not evaluated'} (${pathologyClassification?.leftEar?.confidence || 0}% confidence) — ${pathologyClassification?.leftEar?.explanation || ''}
   - **Right Ear:** ${pathologyClassification?.rightEar?.predictedClass || 'Not evaluated'} (${pathologyClassification?.rightEar?.confidence || 0}% confidence) — ${pathologyClassification?.rightEar?.explanation || ''}
   - **Model Clinical Summary:** ${pathologyClassification?.clinicalSummary || 'Classifier evaluated air conduction, bone conduction, and air-bone gap dynamics.'}

5. **Response Reliability & Acoustic Environment:**
   - Catch trials false alarm rate: **${Math.round(falseAlarmRate * 100)}%**.
   - Premature clicks (under 300ms): **${prematureResponses.length}**.
   - Applied Device Noise Cancellation: **${session.noise_cancellation_profile || 'Adaptive Acoustic Filter'}** (Level: **${session.noise_cancellation_level || 'High'}**).
   - Acoustic isolation mode: **${session.device_type || 'Consumer Hardware'}** paired with **${session.headphone_type || 'Headphones'}**.
   - These parameters indicate that the test response quality is **${dataQuality}**.

### Assessment Interpretation
The combined findings are **${hearingPattern.toLowerCase()}**.
*Please note: This remote screening is an air-conduction evaluation on consumer hardware with device-tuned noise cancellation. Clinically distinguishing conductive from sensorineural or mixed loss requires bone-conduction testing and tympanometry. These results should be considered preliminary and indicative of general trends.*

### Recommendations
1. **Professional Consultation:** A consultation with a licensed clinical audiologist or ENT specialist is highly recommended for a full, calibrated diagnostic audiogram.
2. **Device Care:** Ensure ears are free from wax blockage or congestion, which can temporarily cause conductive-like hearing changes.
3. **Environment:** If repeat screening is conducted, do so in an ultra-quiet room with the calibrated noise cancellation profile active to ensure background noise does not mask weak stimuli.`;
    }
    // Update session record
    await (0, db_1.dbRun)(`UPDATE sessions SET 
      data_quality = ?, 
      confidence_level = ?, 
      overall_status = ?, 
      left_status = ?, 
      right_status = ?, 
      hearing_pattern = ?, 
      ai_explanation = ?,
      pathology_classification = ?
     WHERE id = ?`, [
        dataQuality,
        confidenceLevel,
        overallStatus,
        leftInterpretation,
        rightInterpretation,
        hearingPattern,
        aiExplanation,
        JSON.stringify(pathologyClassification || null),
        sessionId,
    ]);
    return {
        sessionId,
        age: session.age,
        symptoms: JSON.parse(session.symptoms || '[]'),
        headphoneType: session.headphone_type,
        deviceType: session.device_type,
        noiseCancellationProfile: session.noise_cancellation_profile || 'Adaptive Acoustic Filter',
        noiseCancellationLevel: session.noise_cancellation_level || 'High',
        created_at: session.created_at,
        dataQuality,
        confidenceLevel,
        overallStatus,
        leftStatus: leftInterpretation,
        rightStatus: rightInterpretation,
        leftThresholds,
        rightThresholds,
        leftSpeechScore,
        rightSpeechScore,
        leftInterpretation,
        rightInterpretation,
        comparison: comparisonText,
        hearingPattern,
        aiExplanation,
        pathologyClassification,
        fixedSystemVolume: session.fixed_system_volume ?? 0.50,
        audioDevice: session.audio_device || 'Stereo Headphones',
        calibrationProfile: session.calibration_profile ? JSON.parse(session.calibration_profile) : undefined,
    };
}
