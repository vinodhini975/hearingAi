import express from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import { dbRun, dbGet } from './db';
import { getNextTrial } from './services/hearing-test';
import { getNextSpeechTrial, calculateSimilarity } from './services/speech-test';
import { analyzeSession } from './services/analysis';

const app = express();
const port = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Logger middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date() });
});

// 1. Create a screening session
app.post('/api/sessions', async (req, res) => {
  try {
    const { age, symptoms, headphoneType, deviceType, noiseCancellationProfile, noiseCancellationLevel } = req.body;

    if (!age || typeof age !== 'number') {
      return res.status(400).json({ error: 'Valid age is required.' });
    }

    const sessionId = uuidv4();
    const symptomsJson = JSON.stringify(symptoms || []);

    // Derive profile based on device if not explicitly provided
    let derivedProfile = noiseCancellationProfile;
    if (!derivedProfile) {
      const dev = (deviceType || '').toLowerCase();
      if (dev.includes('laptop')) {
        derivedProfile = 'Laptop Acoustic Shield (Fan & Rumble Suppression)';
      } else if (dev.includes('desktop')) {
        derivedProfile = 'Desktop Acoustic Isolator (Echo & Room Noise Suppression)';
      } else if (dev.includes('smart') || dev.includes('phone') || dev.includes('mobile')) {
        derivedProfile = 'Mobile Speech Clarity & Wind Shield';
      } else if (dev.includes('tablet')) {
        derivedProfile = 'Tablet Adaptive Soundstage Filter';
      } else {
        derivedProfile = 'Universal Active Acoustic Filter';
      }
    }

    const derivedLevel = noiseCancellationLevel || 'High';

    await dbRun(
      `INSERT INTO sessions (id, age, symptoms, headphone_type, device_type, noise_cancellation_profile, noise_cancellation_level) 
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [sessionId, age, symptomsJson, headphoneType || 'Other', deviceType || 'Unknown', derivedProfile, derivedLevel]
    );

    console.log(`Created session ${sessionId} for age ${age} with noise cancellation: ${derivedProfile}`);
    res.status(201).json({ sessionId, noiseCancellationProfile: derivedProfile });
  } catch (error) {
    console.error('Error creating session:', error);
    res.status(500).json({ error: 'Failed to create session.' });
  }
});

// 2. Fetch session details
app.get('/api/sessions/:id', async (req, res) => {
  try {
    const session = await dbGet('SELECT * FROM sessions WHERE id = ?', [req.params.id]);
    if (!session) {
      return res.status(404).json({ error: 'Session not found.' });
    }

    res.json({
      id: session.id,
      age: session.age,
      symptoms: JSON.parse(session.symptoms || '[]'),
      headphoneType: session.headphone_type,
      deviceType: session.device_type,
      noiseCancellationProfile: session.noise_cancellation_profile,
      noiseCancellationLevel: session.noise_cancellation_level,
      created_at: session.created_at,
    });
  } catch (error) {
    console.error('Error fetching session:', error);
    res.status(500).json({ error: 'Failed to fetch session.' });
  }
});

// 3. Get next pure-tone trial details
app.get('/api/sessions/:id/trials/next-pure-tone', async (req, res) => {
  try {
    const sessionId = req.params.id;
    const nextTrial = await getNextTrial(sessionId);
    res.json(nextTrial);
  } catch (error: any) {
    console.error('Error calculating next trial:', error);
    res.status(500).json({ error: error.message || 'Failed to determine next trial.' });
  }
});

// 4. Submit pure-tone trial result
app.post('/api/sessions/:id/trials/pure-tone', async (req, res) => {
  try {
    const sessionId = req.params.id;
    const { ear, frequency, soundLevel, trialNumber, duration, response, responseTime } = req.body;

    // Validation
    if (
      !ear ||
      !['LEFT', 'RIGHT'].includes(ear) ||
      typeof frequency !== 'number' ||
      typeof soundLevel !== 'number' ||
      typeof trialNumber !== 'number' ||
      ![0, 1].includes(response) ||
      typeof responseTime !== 'number'
    ) {
      return res.status(400).json({ error: 'Invalid trial parameters.' });
    }

    await dbRun(
      `INSERT INTO pure_tone_trials (session_id, ear, frequency, sound_level, trial_number, duration, response, response_time) 
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [sessionId, ear, frequency, soundLevel, trialNumber, duration || 10000, response, responseTime]
    );

    // Save threshold directly from user's confirmed slider value
    await dbRun(
      `INSERT OR REPLACE INTO thresholds (session_id, ear, frequency, estimated_level) 
       VALUES (?, ?, ?, ?)`,
      [sessionId, ear, frequency, soundLevel]
    );

    console.log(`Recorded threshold for ${sessionId} - Ear: ${ear}, Freq: ${frequency}Hz, Level: ${soundLevel}`);

    // Calculate the next trial parameters dynamically
    const nextTrial = await getNextTrial(sessionId);
    res.status(201).json(nextTrial);
  } catch (error) {
    console.error('Error recording pure-tone trial:', error);
    res.status(500).json({ error: 'Failed to record trial.' });
  }
});

// 4b. Complete entire pure-tone test with structured dataset
app.post('/api/sessions/:id/pure-tone/complete', async (req, res) => {
  try {
    const sessionId = req.params.id;
    const { leftEar, rightEar, audioDevice, fixedSystemVolume, calibrationProfile, allTrials } = req.body;

    // Save left ear thresholds
    if (leftEar && typeof leftEar === 'object') {
      for (const [freq, level] of Object.entries(leftEar)) {
        await dbRun(
          `INSERT OR REPLACE INTO thresholds (session_id, ear, frequency, estimated_level) VALUES (?, 'LEFT', ?, ?)`,
          [sessionId, Number(freq), Number(level)]
        );
      }
    }

    // Save right ear thresholds
    if (rightEar && typeof rightEar === 'object') {
      for (const [freq, level] of Object.entries(rightEar)) {
        await dbRun(
          `INSERT OR REPLACE INTO thresholds (session_id, ear, frequency, estimated_level) VALUES (?, 'RIGHT', ?, ?)`,
          [sessionId, Number(freq), Number(level)]
        );
      }
    }

    // Save individual trials if provided
    if (Array.isArray(allTrials)) {
      for (const t of allTrials) {
        await dbRun(
          `INSERT INTO pure_tone_trials (session_id, ear, frequency, sound_level, trial_number, duration, response, response_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            sessionId,
            t.ear,
            t.frequency,
            t.relativeIntensity ?? t.stimulusLevel ?? 0,
            t.trialIndex ?? 1,
            1400,
            t.response === 'heard' ? 1 : 0,
            t.responseTimeMs ?? 0,
          ]
        );
      }
    }

    // Update session metadata
    await dbRun(
      `UPDATE sessions SET 
         fixed_system_volume = ?, 
         audio_device = ?, 
         calibration_profile = ?,
         current_stage = 'speech'
       WHERE id = ?`,
      [
        fixedSystemVolume || 0.50,
        audioDevice || 'Stereo Headphones',
        JSON.stringify(calibrationProfile || {}),
        sessionId,
      ]
    );

    console.log(`Successfully completed pure-tone screening for session ${sessionId} across 6 frequencies.`);
    res.status(200).json({ success: true, message: 'Pure tone test results successfully saved.' });
  } catch (error: any) {
    console.error('Error completing pure tone test:', error);
    res.status(500).json({ error: error.message || 'Failed to save completed pure tone test.' });
  }
});

// 5. Get next speech trial word
app.get('/api/sessions/:id/trials/next-speech', async (req, res) => {
  try {
    const sessionId = req.params.id;
    const nextSpeech = await getNextSpeechTrial(sessionId);
    res.json(nextSpeech);
  } catch (error: any) {
    console.error('Error calculating next speech word:', error);
    res.status(500).json({ error: error.message || 'Failed to determine next speech word.' });
  }
});

// 6. Submit speech trial result
app.post('/api/sessions/:id/trials/speech', async (req, res) => {
  try {
    const sessionId = req.params.id;
    const { ear, targetWord, userResponse, recordingQuality } = req.body;

    if (!ear || !['LEFT', 'RIGHT'].includes(ear) || !targetWord || typeof userResponse !== 'string') {
      return res.status(400).json({ error: 'Invalid speech trial parameters.' });
    }

    // Process phonetic similarity score
    const similarity = calculateSimilarity(targetWord, userResponse);
    const isCorrect = similarity >= 80.0 ? 1 : 0;
    const finalQuality = recordingQuality || 'Good';

    await dbRun(
      `INSERT INTO speech_trials (session_id, ear, target_word, user_response, similarity_score, is_correct, recording_quality) 
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [sessionId, ear, targetWord, userResponse, similarity, isCorrect, finalQuality]
    );

    console.log(`Recorded speech trial for ${sessionId} - Ear: ${ear}, Target: ${targetWord}, Heard: "${userResponse}", Similarity: ${similarity}%, Correct: ${isCorrect}`);

    const nextSpeech = await getNextSpeechTrial(sessionId);
    res.status(201).json({
      similarity,
      isCorrect: isCorrect === 1,
      ...nextSpeech
    });
  } catch (error) {
    console.error('Error recording speech trial:', error);
    res.status(500).json({ error: 'Failed to record speech trial.' });
  }
});

// 7. Get final reports & AI analysis
app.get('/api/sessions/:id/report', async (req, res) => {
  try {
    const sessionId = req.params.id;
    const report = await analyzeSession(sessionId);
    res.json(report);
  } catch (error: any) {
    console.error('Error generating report:', error);
    res.status(500).json({ error: error.message || 'Failed to generate screening report.' });
  }
});

// Start Express server
app.listen(port, () => {
  console.log(`Hearing Screening API running on http://localhost:${port}`);
});
