/**
 * Audiometry Central Configuration
 *
 * Defines the 6 standard audiometric test frequencies matching the dataset:
 * 250 Hz, 500 Hz, 1000 Hz, 2000 Hz, 4000 Hz, 8000 Hz.
 *
 * Configures stimulus levels (relative software amplitudes) independently
 * from the operating system volume.
 */

export const AUDIOMETRY_FREQUENCIES = [250, 500, 1000, 2000, 4000, 8000] as const;
export type AudiometryFrequency = typeof AUDIOMETRY_FREQUENCIES[number];

export interface StimulusIntensityLevel {
  levelIndex: number;
  softwareLevel: number;        // Discrete level 1 to 12
  stimulusLevel: number;        // Amplitude gain passed to GainNode (0.001 to 0.40)
  relativeIntensity: number;    // Normalized scale 0.0 to 1.0 for ML / thresholds
  stepDbEquivalent: number;     // Relative step change for staircase (e.g. ~5 dB relative step)
  label: string;
}

/**
 * Centralized configurable stimulus intensity scale.
 * Note: These are software stimulus amplitudes, NOT clinical dB HL.
 * The system volume remains FIXED while these software gains modulate the tone.
 */
export const INTENSITY_LEVELS: StimulusIntensityLevel[] = [
  { levelIndex: 0,  softwareLevel: 1,  stimulusLevel: 0.0015, relativeIntensity: 0.083, stepDbEquivalent: 5,  label: 'Stimulus Level 1 (Faint)' },
  { levelIndex: 1,  softwareLevel: 2,  stimulusLevel: 0.0035, relativeIntensity: 0.166, stepDbEquivalent: 10, label: 'Stimulus Level 2 (Soft)' },
  { levelIndex: 2,  softwareLevel: 3,  stimulusLevel: 0.0070, relativeIntensity: 0.250, stepDbEquivalent: 15, label: 'Stimulus Level 3' },
  { levelIndex: 3,  softwareLevel: 4,  stimulusLevel: 0.0140, relativeIntensity: 0.333, stepDbEquivalent: 20, label: 'Stimulus Level 4' },
  { levelIndex: 4,  softwareLevel: 5,  stimulusLevel: 0.0250, relativeIntensity: 0.416, stepDbEquivalent: 25, label: 'Stimulus Level 5 (Moderate-Low)' },
  { levelIndex: 5,  softwareLevel: 6,  stimulusLevel: 0.0450, relativeIntensity: 0.500, stepDbEquivalent: 30, label: 'Stimulus Level 6 (Moderate)' },
  { levelIndex: 6,  softwareLevel: 7,  stimulusLevel: 0.0800, relativeIntensity: 0.583, stepDbEquivalent: 35, label: 'Stimulus Level 7' },
  { levelIndex: 7,  softwareLevel: 8,  stimulusLevel: 0.1300, relativeIntensity: 0.666, stepDbEquivalent: 40, label: 'Stimulus Level 8 (Clear)' },
  { levelIndex: 8,  softwareLevel: 9,  stimulusLevel: 0.1900, relativeIntensity: 0.750, stepDbEquivalent: 45, label: 'Stimulus Level 9' },
  { levelIndex: 9,  softwareLevel: 10, stimulusLevel: 0.2600, relativeIntensity: 0.833, stepDbEquivalent: 50, label: 'Stimulus Level 10 (Loud)' },
  { levelIndex: 10, softwareLevel: 11, stimulusLevel: 0.3300, relativeIntensity: 0.916, stepDbEquivalent: 55, label: 'Stimulus Level 11' },
  { levelIndex: 11, softwareLevel: 12, stimulusLevel: 0.4000, relativeIntensity: 1.000, stepDbEquivalent: 60, label: 'Stimulus Level 12 (Max Stimulus)' },
];

export interface StaircaseProtocolConfig {
  initialLevelIndex: number;    // Starting stimulus intensity index (default Level 5 = index 4)
  stepDownOnHeard: number;      // Reduce intensity by 2 levels on "heard" (Hughson-Westlake 10 dB down)
  stepUpOnNotHeard: number;     // Increase intensity by 1 level on "not heard" (Hughson-Westlake 5 dB up)
  minConfirmations: number;     // Affirmations required at minimum heard level to establish threshold
  toneDurationMs: number;       // Duration of stimulus presentation
  rampDurationMs: number;       // Attack / decay ramp to eliminate transient clicks
  fixedReferenceOsVolume: number; // Constant reference OS volume recommended (50%)
}

export const DEFAULT_STAIRCASE_PROTOCOL: StaircaseProtocolConfig = {
  initialLevelIndex: 4,         // Level 5 (moderate stimulus)
  stepDownOnHeard: 2,           // -2 levels (~10 dB equivalent drop)
  stepUpOnNotHeard: 1,          // +1 level (~5 dB equivalent ascent)
  minConfirmations: 2,          // 2 positive responses at lowest level establishes threshold
  toneDurationMs: 1400,         // 1.4 second tone pulse
  rampDurationMs: 40,           // 40ms smooth cosine envelope
  fixedReferenceOsVolume: 0.50, // 50% constant system volume
};
