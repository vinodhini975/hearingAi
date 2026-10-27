const API_BASE_URL = 'http://127.0.0.1:8000';

export interface HearingThresholds {
    L_1000: number;
    L_2000: number;
    L_4000: number;
    L_6000: number;
    L_8000: number;
    R_1000: number;
    R_2000: number;
    R_4000: number;
    R_6000: number;
    R_8000: number;
}

export interface PredictionResponse {
    predicted_pattern: string;
    confidence_percentage: number;
    status: string;
}

export const predictHearingPattern = async (
    thresholds: HearingThresholds
): Promise<PredictionResponse> => {
    const response = await fetch(`${API_BASE_URL}/predict`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(thresholds),
    });

    if (!response.ok) {
        throw new Error('Failed to reach AI assessment backend');
    }

    return response.json();
};