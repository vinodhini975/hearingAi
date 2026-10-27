import { useState, useCallback, useRef } from 'react';
import type { Ear, TestStage, TestTrial, UserResponse } from '../types/test';
import { audioEngine } from '../services/audioEngine';



const FREQUENCIES = [1000, 2000, 4000, 6000, 8000];

export const useTestStateMachine = () => {
    const [stage, setStage] = useState<TestStage>('INSTRUCTIONS');
    const [currentEar, setCurrentEar] = useState<Ear>('LEFT');
    const [frequencyIndex, setFrequencyIndex] = useState<number>(0);
    const [trialCount, setTrialCount] = useState<number>(1);

    const [countdown, setCountdown] = useState<number>(10);
    const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
    const [showResponseButtons, setShowResponseButtons] = useState<boolean>(false);

    const [responses, setResponses] = useState<UserResponse[]>([]);
    const trialStartTimeRef = useRef<number>(0);

    const currentTrial: TestTrial = {
        trialNumber: trialCount,
        ear: currentEar,
        frequency: FREQUENCIES[frequencyIndex],
        soundLevel: 0.1,
    };

    const startTrial = useCallback(async () => {
        setShowResponseButtons(false);
        setCountdown(10);
        setIsPlayingAudio(true);
        trialStartTimeRef.current = Date.now();

        // Play tone for 10 seconds
        audioEngine.playPureTone(currentTrial.frequency, currentTrial.soundLevel, currentTrial.ear, 10000);

        const interval = setInterval(() => {
            setCountdown((prev) => {
                if (prev <= 1) {
                    clearInterval(interval);
                    setIsPlayingAudio(false);
                    setShowResponseButtons(true);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
    }, [currentTrial]);

    const submitResponse = useCallback((heard: boolean) => {
        const responseTimeMs = Date.now() - trialStartTimeRef.current;

        const record: UserResponse = {
            ...currentTrial,
            heard,
            responseTimeMs,
            timestamp: Date.now(),
        };

        setResponses((prev) => [...prev, record]);

        if (frequencyIndex < FREQUENCIES.length - 1) {
            setFrequencyIndex((prev) => prev + 1);
            setTrialCount((prev) => prev + 1);
            setCountdown(10);
            setShowResponseButtons(false);
        } else if (currentEar === 'LEFT') {
            setCurrentEar('RIGHT');
            setFrequencyIndex(0);
            setTrialCount((prev) => prev + 1);
            setStage('EAR_TRANSITION');
        } else {
            setStage('COMPLETE');
        }
    }, [currentTrial, frequencyIndex, currentEar]);

    const proceedToRightEar = useCallback(() => {
        setStage('PURE_TONE_TEST');
        setCountdown(10);
        setShowResponseButtons(false);
    }, []);

    return {
        stage,
        setStage,
        currentEar,
        countdown,
        isPlayingAudio,
        showResponseButtons,
        responses,
        startTrial,
        submitResponse,
        proceedToRightEar,
    };
};