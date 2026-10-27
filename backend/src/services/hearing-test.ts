import { dbAll, dbGet, dbRun } from '../db';

export interface TrialInput {
  sessionId: string;
  ear: 'LEFT' | 'RIGHT';
  frequency: number;
  soundLevel: number;
  trialNumber: number;
  duration: number;
  response: number; // 1 = YES, 0 = NO
  responseTime: number;
}

export interface NextTrialInfo {
  ear: 'LEFT' | 'RIGHT';
  frequency: number;
  soundLevel: number;
  trialNumber: number;
  isCatchTrial: boolean;
  testComplete: boolean;
}

const FREQUENCIES = [250, 500, 1000, 2000, 4000, 8000];

/**
 * Determines the next ear and frequency that haven't been completed yet.
 */
export async function getNextTrial(sessionId: string): Promise<NextTrialInfo> {
  const session = await dbGet('SELECT * FROM sessions WHERE id = ?', [sessionId]);
  if (!session) {
    throw new Error('Session not found');
  }

  // 1. Get completed Left Ear thresholds
  const leftThresholds = await dbAll('SELECT frequency FROM thresholds WHERE session_id = ? AND ear = "LEFT"', [sessionId]);
  const completedLeftFreqs = leftThresholds.map((t) => t.frequency);

  let currentEar: 'LEFT' | 'RIGHT' = 'LEFT';
  let targetFreq = -1;

  // Find first incomplete left ear frequency
  for (const freq of FREQUENCIES) {
    if (!completedLeftFreqs.includes(freq)) {
      targetFreq = freq;
      break;
    }
  }

  if (targetFreq === -1) {
    // Left ear complete, check right ear
    const rightThresholds = await dbAll('SELECT frequency FROM thresholds WHERE session_id = ? AND ear = "RIGHT"', [sessionId]);
    const completedRightFreqs = rightThresholds.map((t) => t.frequency);

    currentEar = 'RIGHT';
    for (const freq of FREQUENCIES) {
      if (!completedRightFreqs.includes(freq)) {
        targetFreq = freq;
        break;
      }
    }
  }

  // If all frequencies for both ears are complete
  if (targetFreq === -1) {
    return {
      ear: 'RIGHT',
      frequency: 8000,
      soundLevel: 0,
      trialNumber: 0,
      isCatchTrial: false,
      testComplete: true,
    };
  }

  // Get current trial number (how many total pure tone thresholds have been saved)
  const savedLeftCount = completedLeftFreqs.length;
  const savedRightCount = currentEar === 'RIGHT' 
    ? (await dbAll('SELECT frequency FROM thresholds WHERE session_id = ? AND ear = "RIGHT"', [sessionId])).length 
    : 0;
  const savedThresholdsCount = savedLeftCount + savedRightCount;

  // Update session current_ear state
  await dbRun('UPDATE sessions SET current_ear = ?, left_status = ?, right_status = ? WHERE id = ?', [
    currentEar,
    completedLeftFreqs.length === FREQUENCIES.length ? 'Complete' : 'In Progress',
    currentEar === 'RIGHT' ? 'In Progress' : 'Not tested',
    sessionId
  ]);

  return {
    ear: currentEar,
    frequency: targetFreq,
    soundLevel: 0.16, // Initial level 2 (2/12 = 0.16666...)
    trialNumber: savedThresholdsCount + 1,
    isCatchTrial: false,
    testComplete: false,
  };
}
