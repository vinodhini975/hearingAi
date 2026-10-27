/**
 * Audiometric Threshold Search Engine
 *
 * Implements a standardized ascending-descending staircase procedure
 * (modified Hughson-Westlake method):
 * 1. For each frequency (250, 500, 1000, 2000, 4000, 8000 Hz):
 *    - Start at predefined stimulus intensity (e.g. Level 5, moderate-low).
 *    - Play pure tone at fixed system volume.
 *    - Participant indicates Heard / Not Heard.
 *    - If Heard -> decrease intensity by 2 steps.
 *    - If Not Heard -> increase intensity by 1 step.
 *    - Continue until threshold criterion (2 affirmations at lowest heard level on ascent,
 *      or minimum 3 reversals) is established.
 * 2. Left ear tested through all 6 frequencies, followed by Right ear.
 * 3. Records every trial and produces structured final output.
 */

import {
  AUDIOMETRY_FREQUENCIES,
  type AudiometryFrequency,
  INTENSITY_LEVELS,
  type StimulusIntensityLevel,
  DEFAULT_STAIRCASE_PROTOCOL,
  type StaircaseProtocolConfig,
} from './audiometryConfig';
import { type CalibrationProfile, getCalibrationProfile } from './calibration';

export interface TrialRecord {
  trialIndex: number;
  frequency: AudiometryFrequency;
  ear: 'LEFT' | 'RIGHT';
  levelIndex: number;
  softwareLevel: number;
  stimulusLevel: number;
  relativeIntensity: number;
  response: 'heard' | 'not_heard';
  responseTimeMs: number;
  timestamp: string;
}

export interface PureToneThresholdResult {
  leftEar: { [freq: number]: number }; // Maps frequency -> relativeIntensity (0.0 to 1.0)
  rightEar: { [freq: number]: number };
  leftSoftwareLevels: { [freq: number]: number }; // Maps frequency -> software level (1 to 12)
  rightSoftwareLevels: { [freq: number]: number };
  audioDevice: string;
  fixedSystemVolume: number;
  calibrationProfile: CalibrationProfile;
  testTimestamp: string;
  allTrials: TrialRecord[];
}

export interface SearchState {
  currentEar: 'LEFT' | 'RIGHT';
  freqIndex: number;
  currentFrequency: AudiometryFrequency;
  currentLevelIndex: number;
  currentStimulus: StimulusIntensityLevel;
  stepNumber: number; // 1 to 12 (6 freqs * 2 ears)
  isComplete: boolean;
  leftThresholds: { [freq: number]: number };
  rightThresholds: { [freq: number]: number };
  leftSoftwareLevels: { [freq: number]: number };
  rightSoftwareLevels: { [freq: number]: number };
  trials: TrialRecord[];
}

export class ThresholdSearchManager {
  private config: StaircaseProtocolConfig;
  private currentEar: 'LEFT' | 'RIGHT' = 'LEFT';
  private freqIndex: number = 0;
  private currentLevelIndex: number;
  private trials: TrialRecord[] = [];
  private leftThresholds: { [freq: number]: number } = {};
  private rightThresholds: { [freq: number]: number } = {};
  private leftSoftwareLevels: { [freq: number]: number } = {};
  private rightSoftwareLevels: { [freq: number]: number } = {};

  // Tracking for current frequency staircase
  private freqResponses: { levelIndex: number; response: 'heard' | 'not_heard' }[] = [];
  private heardLevelsMap: { [levelIndex: number]: number } = {}; // counts how many times heard at level

  constructor(config: StaircaseProtocolConfig = DEFAULT_STAIRCASE_PROTOCOL) {
    this.config = config;
    this.currentLevelIndex = config.initialLevelIndex;
  }

  public getState(): SearchState {
    const currentFrequency = AUDIOMETRY_FREQUENCIES[this.freqIndex];
    const isComplete = this.currentEar === 'RIGHT' && this.freqIndex >= AUDIOMETRY_FREQUENCIES.length;
    const stepNumber = this.currentEar === 'LEFT' 
      ? this.freqIndex + 1 
      : 6 + Math.min(this.freqIndex + 1, 6);

    return {
      currentEar: this.currentEar,
      freqIndex: this.freqIndex,
      currentFrequency: currentFrequency || 8000,
      currentLevelIndex: this.currentLevelIndex,
      currentStimulus: INTENSITY_LEVELS[this.currentLevelIndex] || INTENSITY_LEVELS[4],
      stepNumber,
      isComplete,
      leftThresholds: { ...this.leftThresholds },
      rightThresholds: { ...this.rightThresholds },
      leftSoftwareLevels: { ...this.leftSoftwareLevels },
      rightSoftwareLevels: { ...this.rightSoftwareLevels },
      trials: [...this.trials],
    };
  }

  /**
   * Process participant's response: 'heard' or 'not_heard'
   * Returns updated SearchState.
   */
  public registerResponse(response: 'heard' | 'not_heard', responseTimeMs: number = 0): SearchState {
    const curFreq = AUDIOMETRY_FREQUENCIES[this.freqIndex];
    const curStim = INTENSITY_LEVELS[this.currentLevelIndex];

    // 1. Record trial
    const trial: TrialRecord = {
      trialIndex: this.trials.length + 1,
      frequency: curFreq,
      ear: this.currentEar,
      levelIndex: this.currentLevelIndex,
      softwareLevel: curStim.softwareLevel,
      stimulusLevel: curStim.stimulusLevel,
      relativeIntensity: curStim.relativeIntensity,
      response,
      responseTimeMs,
      timestamp: new Date().toISOString(),
    };
    this.trials.push(trial);
    this.freqResponses.push({ levelIndex: this.currentLevelIndex, response });

    if (response === 'heard') {
      this.heardLevelsMap[this.currentLevelIndex] = (this.heardLevelsMap[this.currentLevelIndex] || 0) + 1;
    }

    // 2. Evaluate if threshold criterion for this frequency has been met
    const thresholdReached = this.checkThresholdCriterion();

    if (thresholdReached) {
      // Record threshold for this frequency
      const thresholdIntensity = curStim.relativeIntensity;
      const thresholdSoftwareLevel = curStim.softwareLevel;

      if (this.currentEar === 'LEFT') {
        this.leftThresholds[curFreq] = thresholdIntensity;
        this.leftSoftwareLevels[curFreq] = thresholdSoftwareLevel;
      } else {
        this.rightThresholds[curFreq] = thresholdIntensity;
        this.rightSoftwareLevels[curFreq] = thresholdSoftwareLevel;
      }

      // Advance to next frequency or next ear
      this.advanceToNextFrequency();
    } else {
      // Adaptive Staircase Adjustment:
      if (response === 'heard') {
        // Drop by 2 levels (or to minimum level 0)
        this.currentLevelIndex = Math.max(0, this.currentLevelIndex - this.config.stepDownOnHeard);
      } else {
        // Ascend by 1 level (or up to maximum level 11)
        this.currentLevelIndex = Math.min(INTENSITY_LEVELS.length - 1, this.currentLevelIndex + this.config.stepUpOnNotHeard);
      }
    }

    return this.getState();
  }

  /**
   * Threshold criterion:
   * 1. If at lowest level (0) and heard twice -> confirmed at 0.
   * 2. If at highest level (11) and not heard twice -> confirmed at 11.
   * 3. If a level was heard 2 or more times on ascending or bracketing trials.
   * 4. If at least 5 trials completed for this frequency, pick the lowest heard level.
   */
  private checkThresholdCriterion(): boolean {
    const trialsForFreq = this.freqResponses.length;

    // Min 3 trials required per frequency to establish genuine threshold
    if (trialsForFreq < 3) return false;

    // Condition 1: Lowest level heard twice
    if (this.heardLevelsMap[0] >= 2) return true;

    // Condition 2: Max level reached and still not heard twice
    const notHeardAtMax = this.freqResponses.filter((r) => r.levelIndex === INTENSITY_LEVELS.length - 1 && r.response === 'not_heard').length;
    if (notHeardAtMax >= 2) return true;

    // Condition 3: A level has been confirmed with 2 positive responses
    const heardLevels = Object.keys(this.heardLevelsMap).map(Number).sort((a, b) => a - b);
    for (const lvl of heardLevels) {
      if (this.heardLevelsMap[lvl] >= this.config.minConfirmations) {
        // If confirmed, set currentLevelIndex to this lowest confirmed level
        this.currentLevelIndex = lvl;
        return true;
      }
    }

    // Condition 4: Max trials limit per frequency (6 trials) to prevent patient fatigue
    if (trialsForFreq >= 6) {
      if (heardLevels.length > 0) {
        this.currentLevelIndex = heardLevels[0]; // Lowest level participant heard
      }
      return true;
    }

    return false;
  }

  private advanceToNextFrequency(): void {
    this.freqResponses = [];
    this.heardLevelsMap = {};
    this.freqIndex++;

    if (this.freqIndex >= AUDIOMETRY_FREQUENCIES.length) {
      if (this.currentEar === 'LEFT') {
        // Finished Left Ear -> Move to Right Ear
        this.currentEar = 'RIGHT';
        this.freqIndex = 0;
        this.currentLevelIndex = this.config.initialLevelIndex;
      } else {
        // Finished Right Ear -> Test Complete!
      }
    } else {
      // Next frequency starts at initial moderate level (e.g. Level 5)
      this.currentLevelIndex = this.config.initialLevelIndex;
    }
  }

  public getFinalResult(
    audioDevice: string = 'Default Stereo Headphones',
    deviceType: string = 'Laptop',
    headphoneType: string = 'Over-ear headphones'
  ): PureToneThresholdResult {
    return {
      leftEar: { ...this.leftThresholds },
      rightEar: { ...this.rightThresholds },
      leftSoftwareLevels: { ...this.leftSoftwareLevels },
      rightSoftwareLevels: { ...this.rightSoftwareLevels },
      audioDevice,
      fixedSystemVolume: this.config.fixedReferenceOsVolume,
      calibrationProfile: getCalibrationProfile(deviceType, headphoneType),
      testTimestamp: new Date().toISOString(),
      allTrials: [...this.trials],
    };
  }
}
