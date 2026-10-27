import { useState, useEffect } from 'react';
import { useTestStateMachine } from './hooks/useTestStateMachine';
import { PureToneTestUI } from './components/PureToneTestUI';
import { predictHearingPattern } from './services/apiService';
import type { PredictionResponse } from './services/apiService';

export default function App() {
    const {
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
    } = useTestStateMachine();

    const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
    const [loadingAi, setLoadingAi] = useState<boolean>(false);

    useEffect(() => {
        if (stage === 'COMPLETE' && responses.length > 0 && !prediction) {
            setLoadingAi(true);

            const getThreshold = (ear: 'LEFT' | 'RIGHT', freq: number) => {
                const match = responses.find((r) => r.ear === ear && r.frequency === freq);
                return match && match.heard ? 15.0 : 45.0;
            };

            const payload = {
                L_1000: getThreshold('LEFT', 1000),
                L_2000: getThreshold('LEFT', 2000),
                L_4000: getThreshold('LEFT', 4000),
                L_6000: getThreshold('LEFT', 6000),
                L_8000: getThreshold('LEFT', 8000),
                R_1000: getThreshold('RIGHT', 1000),
                R_2000: getThreshold('RIGHT', 2000),
                R_4000: getThreshold('RIGHT', 4000),
                R_6000: getThreshold('RIGHT', 6000),
                R_8000: getThreshold('RIGHT', 8000),
            };

            predictHearingPattern(payload)
                .then((data) => {
                    setPrediction(data);
                    setLoadingAi(false);
                })
                .catch((err) => {
                    console.error('API Error:', err);
                    setLoadingAi(false);
                });
        }
    }, [stage, responses, prediction]);

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4 font-sans">
            <header className="mb-8 text-center">
                <h1 className="text-2xl font-bold text-slate-800">
                    AI Hearing Screening Assessment
                </h1>
                <p className="text-sm text-slate-500 mt-1">
                    Research-Oriented Remote Diagnostic Tool
                </p>
            </header>

            {stage === 'INSTRUCTIONS' && (
                <div className="max-w-md bg-white p-8 rounded-2xl shadow-lg border border-slate-100 text-center">
                    <h2 className="text-xl font-bold text-slate-800 mb-3">Test Instructions</h2>
                    <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                        Put on your headphones. The <strong>Left Ear</strong> will be tested first, followed by the <strong>Right Ear</strong>.
                    </p>
                    <button
                        onClick={() => setStage('PURE_TONE_TEST')}
                        className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition cursor-pointer shadow-md"
                    >
                        Start Left Ear Test
                    </button>
                </div>
            )}

            {stage === 'PURE_TONE_TEST' && (
                <PureToneTestUI
                    currentEar={currentEar}
                    countdown={countdown}
                    isPlayingAudio={isPlayingAudio}
                    showResponseButtons={showResponseButtons}
                    onStartTrial={startTrial}
                    onSubmitResponse={submitResponse}
                />
            )}

            {stage === 'EAR_TRANSITION' && (
                <div className="max-w-md bg-white p-8 rounded-2xl shadow-lg border border-slate-100 text-center">
                    <div className="text-4xl mb-3">✅</div>
                    <h2 className="text-xl font-bold text-slate-800 mb-2">Left Ear Complete</h2>
                    <p className="text-sm text-slate-600 mb-6">
                        We will now test your <strong>Right Ear</strong>.
                    </p>
                    <button
                        onClick={proceedToRightEar}
                        className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition cursor-pointer shadow-md"
                    >
                        Start Right Ear Test
                    </button>
                </div>
            )}

            {stage === 'COMPLETE' && (
                <div className="max-w-lg w-full bg-white p-8 rounded-2xl shadow-lg border border-slate-100 text-left">
                    <h2 className="text-xl font-bold text-slate-800 mb-2 text-center">
                        Assessment Results
                    </h2>

                    {loadingAi ? (
                        <div className="text-center py-8 text-blue-600 font-semibold animate-pulse">
                            Running AI Pattern Analysis...
                        </div>
                    ) : prediction ? (
                        <div className="space-y-4">
                            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
                                <span className="text-xs font-bold text-blue-600 uppercase tracking-wider block mb-1">
                                    AI Screening Result
                                </span>
                                <div className="text-lg font-bold text-slate-800">
                                    {prediction.predicted_pattern}
                                </div>
                                <div className="text-xs text-slate-500 mt-1">
                                    Model Confidence: <strong>{prediction.confidence_percentage}%</strong>
                                </div>
                            </div>

                            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 leading-relaxed">
                                <strong>Medical Disclaimer:</strong> Remote screening only. Not a medical diagnosis.
                            </div>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    );
}