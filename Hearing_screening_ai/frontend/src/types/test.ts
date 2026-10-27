export type Ear = 'LEFT' | 'RIGHT';
export type TestStage = 'INSTRUCTIONS' | 'PURE_TONE_TEST' | 'EAR_TRANSITION' | 'COMPLETE';

export interface TestTrial {
    trialNumber: number;
    ear: Ear;
    frequency: number;
    soundLevel: number;
}

export interface UserResponse {
    trialNumber: number;
    ear: Ear;
    frequency: number;
    soundLevel: number;
    heard: boolean;
    responseTimeMs: number;
    timestamp: number;
}