"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getNextSpeechTrial = getNextSpeechTrial;
exports.calculateSimilarity = calculateSimilarity;
const db_1 = require("../db");
// Harvard phonetically balanced words or simple spondee words
const LEFT_EAR_WORDS = ['baseball', 'sunset'];
const RIGHT_EAR_WORDS = ['playground'];
/**
 * Returns the next speech trial details or complete status
 */
async function getNextSpeechTrial(sessionId) {
    const session = await (0, db_1.dbGet)('SELECT * FROM sessions WHERE id = ?', [sessionId]);
    if (!session) {
        throw new Error('Session not found');
    }
    // Get completed speech trials
    const trials = await (0, db_1.dbAll)('SELECT * FROM speech_trials WHERE session_id = ? ORDER BY timestamp ASC', [sessionId]);
    const leftCompleted = trials.filter((t) => t.ear === 'LEFT').map((t) => t.target_word);
    const rightCompleted = trials.filter((t) => t.ear === 'RIGHT').map((t) => t.target_word);
    const globalTrialNumber = leftCompleted.length + rightCompleted.length + 1;
    // 1. Test Left Ear First
    for (let i = 0; i < LEFT_EAR_WORDS.length; i++) {
        const word = LEFT_EAR_WORDS[i];
        if (!leftCompleted.includes(word)) {
            return {
                ear: 'LEFT',
                targetWord: word,
                trialNumber: globalTrialNumber,
                testComplete: false,
            };
        }
    }
    // 2. Test Right Ear Second
    for (let i = 0; i < RIGHT_EAR_WORDS.length; i++) {
        const word = RIGHT_EAR_WORDS[i];
        if (!rightCompleted.includes(word)) {
            return {
                ear: 'RIGHT',
                targetWord: word,
                trialNumber: globalTrialNumber,
                testComplete: false,
            };
        }
    }
    // Both ears complete
    return {
        ear: 'RIGHT',
        targetWord: '',
        trialNumber: 0,
        testComplete: true,
    };
}
/**
 * Computes the similarity score between the target word and the user's spoken response.
 * Uses a normalized Levenshtein Distance for comparison.
 */
function calculateSimilarity(wordA, wordB) {
    const s1 = wordA.toLowerCase().trim();
    const s2 = wordB.toLowerCase().trim();
    if (s1 === s2)
        return 100.0;
    if (!s1 || !s2)
        return 0.0;
    // Track Levenshtein distance
    const costs = [];
    for (let i = 0; i <= s1.length; i++) {
        let lastValue = i;
        for (let j = 0; j <= s2.length; j++) {
            if (i === 0) {
                costs[j] = j;
            }
            else {
                if (j > 0) {
                    let newValue = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
                        newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    }
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
        }
        if (i > 0)
            costs[s2.length] = lastValue;
    }
    const distance = costs[s2.length];
    const maxLength = Math.max(s1.length, s2.length);
    const similarity = ((maxLength - distance) / maxLength) * 100;
    return Math.round(similarity * 10) / 10;
}
