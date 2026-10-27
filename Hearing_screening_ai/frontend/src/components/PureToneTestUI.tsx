import React from 'react';
import type { Ear } from '../types/test';

interface Props {
    currentEar: Ear;
    countdown: number;
    isPlayingAudio: boolean;
    showResponseButtons: boolean;
    onStartTrial: () => void;
    onSubmitResponse: (heard: boolean) => void;
}

export const PureToneTestUI: React.FC<Props> = ({
    currentEar,
    countdown,
    isPlayingAudio,
    showResponseButtons,
    onStartTrial,
    onSubmitResponse,
}) => {
    return (
        <div className="max-w-md mx-auto my-8 p-8 bg-white rounded-2xl shadow-xl border border-slate-100 text-center">
            <div className="inline-block px-4 py-1.5 mb-6 bg-blue-50 text-blue-700 font-semibold text-xs rounded-full uppercase tracking-wider">
                Testing {currentEar === 'LEFT' ? 'Left Ear' : 'Right Ear'}
            </div>

            {!showResponseButtons ? (
                <div className="space-y-6">
                    <h3 className="text-xl font-bold text-slate-800">Listen carefully</h3>
                    <div className="text-8xl font-black text-blue-600 my-8 tracking-tighter font-mono">
                        {countdown}
                    </div>
                    {!isPlayingAudio && countdown === 10 && (
                        <button
                            onClick={onStartTrial}
                            className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition shadow-md cursor-pointer"
                        >
                            Begin Trial
                        </button>
                    )}
                </div>
            ) : (
                <div className="space-y-6">
                    <h3 className="text-xl font-bold text-slate-800 mb-6">
                        Did you hear the sound?
                    </h3>
                    <div className="space-y-3">
                        <button
                            onClick={() => onSubmitResponse(true)}
                            className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm rounded-xl shadow-md transition cursor-pointer"
                        >
                            YES, I HEARD IT
                        </button>
                        <button
                            onClick={() => onSubmitResponse(false)}
                            className="w-full py-4 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-sm rounded-xl transition cursor-pointer"
                        >
                            NO, I DID NOT HEAR IT
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};