import React, { useState, useEffect, useRef } from 'react';
import { 
  Volume2, ShieldAlert, ArrowRight, RotateCcw, 
  Headphones, CheckCircle2, AlertTriangle, Lock
} from 'lucide-react';
import { getNoiseCancellationConfig } from '../utils/noiseCancellation';
import { audioEngine } from '../services/audiometry/audioEngine';
import { 
  ThresholdSearchManager, 
  type SearchState, 
  type PureToneThresholdResult 
} from '../services/audiometry/thresholdSearch';
import { CLINICAL_SCREENING_DISCLAIMER } from '../services/audiometry/calibration';
import { DEFAULT_STAIRCASE_PROTOCOL } from '../services/audiometry/audiometryConfig';

interface PureToneTestProps {
  sessionId: string;
  onComplete: () => void;
  onStop: () => void;
  deviceType?: string;
  headphoneType?: string;
}

type TestPhase = 'setup' | 'testing' | 'submitting' | 'error';

export const PureToneTest: React.FC<PureToneTestProps> = ({
  sessionId,
  onComplete,
  onStop,
  deviceType = 'Laptop',
  headphoneType = 'Over-ear headphones',
}) => {
  const ncConfig = getNoiseCancellationConfig(deviceType, headphoneType);

  // Test Phase: 'setup' -> 'testing' -> 'submitting'
  const [phase, setPhase] = useState<TestPhase>('setup');
  const [detectedAudioDevice, setDetectedAudioDevice] = useState<string>('Detecting audio hardware...');
  const [isTonePlaying, setIsTonePlaying] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Threshold search manager instance
  const searchManagerRef = useRef<ThresholdSearchManager | null>(null);
  const [searchState, setSearchState] = useState<SearchState | null>(null);
  const toneStartTimeRef = useRef<number>(0);

  // 1. Detect audio output device on mount
  useEffect(() => {
    let isMounted = true;
    audioEngine.detectAudioOutputDevice().then((dev) => {
      if (isMounted) {
        setDetectedAudioDevice(dev.deviceName);
      }
    });

    return () => {
      isMounted = false;
      audioEngine.stopTone();
    };
  }, []);

  // 2. Start test handler
  const handleStartTest = () => {
    const manager = new ThresholdSearchManager(DEFAULT_STAIRCASE_PROTOCOL);
    searchManagerRef.current = manager;
    const initial = manager.getState();
    setSearchState(initial);
    setPhase('testing');

    // Trigger first tone presentation after short UI transition
    setTimeout(() => {
      presentStimulus(initial);
    }, 600);
  };

  // 3. Stimulus presentation
  const presentStimulus = async (state: SearchState) => {
    setIsTonePlaying(true);
    toneStartTimeRef.current = Date.now();

    try {
      await audioEngine.playTone({
        frequency: state.currentFrequency,
        ear: state.currentEar,
        stimulusLevel: state.currentStimulus.stimulusLevel,
        durationMs: DEFAULT_STAIRCASE_PROTOCOL.toneDurationMs,
        rampMs: DEFAULT_STAIRCASE_PROTOCOL.rampDurationMs,
      });
    } catch (err) {
      console.error('Audio playback error:', err);
    } finally {
      setIsTonePlaying(false);
    }
  };

  // 4. Replay stimulus handler
  const handleReplayStimulus = () => {
    if (!searchState || isTonePlaying) return;
    presentStimulus(searchState);
  };

  // 5. Handle participant response (Heard / Not Heard)
  const handleResponse = async (response: 'heard' | 'not_heard') => {
    if (!searchManagerRef.current || !searchState || isTonePlaying) return;

    const responseTimeMs = Date.now() - toneStartTimeRef.current;
    const updatedState = searchManagerRef.current.registerResponse(response, responseTimeMs);
    setSearchState(updatedState);

    if (updatedState.isComplete) {
      // All 6 frequencies for Left & Right ears completed!
      await finalizeTest();
    } else {
      // Present next stimulus in staircase or next frequency
      setTimeout(() => {
        presentStimulus(updatedState);
      }, 500);
    }
  };

  // 6. Finalize and submit structured dataset
  const finalizeTest = async () => {
    if (!searchManagerRef.current) return;
    setPhase('submitting');

    const result: PureToneThresholdResult = searchManagerRef.current.getFinalResult(
      detectedAudioDevice,
      deviceType,
      headphoneType
    );

    try {
      const res = await fetch(`http://localhost:5000/api/sessions/${sessionId}/pure-tone/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(result),
      });

      if (!res.ok) {
        throw new Error('Failed to submit pure-tone dataset.');
      }

      onComplete();
    } catch (err: any) {
      console.error('Error submitting completed test:', err);
      setErrorMessage(err.message || 'Network error submitting test results. Please try again.');
      setPhase('error');
    }
  };

  // Stop test handler
  const handleStopTest = () => {
    if (window.confirm('Are you sure you want to stop the test? Your current progress will be lost.')) {
      audioEngine.stopTone();
      onStop();
    }
  };

  // ==========================================
  // SCREEN 1: Pre-Test Setup & Calibration Screen
  // ==========================================
  if (phase === 'setup') {
    return (
      <div className="max-w-xl mx-auto py-6 px-4 animate-fadeIn text-left">
        <div className="card-premium p-8 bg-white space-y-6">
          
          {/* Header */}
          <div className="border-b border-[#DDE5E1] pb-4 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-[#176B68] font-mono">
                Controlled Audiometric Protocol
              </span>
              <h2 className="text-xl font-bold text-[#1C2421] mt-0.5">
                Pure-Tone Hearing Test Setup
              </h2>
            </div>
            <div className="w-10 h-10 rounded-xl bg-[#E6F2F0] border border-[#176B68]/30 flex items-center justify-center text-[#176B68]">
              <Headphones className="w-5 h-5" />
            </div>
          </div>

          {/* Test Overview & Dataset Frequencies */}
          <div className="bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl p-4 space-y-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#66716D] block">
              Dataset Test Frequencies (6 Octaves per Ear)
            </span>
            <div className="flex flex-wrap gap-2 pt-1 font-mono text-xs">
              {[250, 500, 1000, 2000, 4000, 8000].map((f) => (
                <span
                  key={f}
                  className="bg-white px-2.5 py-1 rounded-lg border border-[#DDE5E1] text-[#1C2421] font-semibold"
                >
                  {f} Hz
                </span>
              ))}
            </div>
            <p className="text-[11px] text-[#66716D] pt-1">
              Frequencies are tested sequentially: Left ear (250 → 8000 Hz), then Right ear (250 → 8000 Hz).
            </p>
          </div>

          {/* Fixed System Volume Lock Instruction */}
          <div className="border border-[#176B68]/30 bg-[#E6F2F0]/50 rounded-xl p-4 space-y-2.5">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#176B68] shrink-0" />
              <h4 className="text-xs font-bold text-[#1C2421] uppercase tracking-wide">
                Mandatory System Volume Calibration: 50%
              </h4>
            </div>
            <p className="text-xs text-[#1C2421] leading-relaxed">
              Please manually set your computer / phone media volume to <strong>50%</strong> now.
              Throughout the test, <strong>do NOT adjust your device volume buttons</strong>.
            </p>
            <div className="bg-white/80 border border-[#176B68]/20 rounded-lg p-2.5 text-[11px] text-[#66716D] flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-[#176B68] shrink-0 mt-0.5" />
              <span>
                <strong>System Volume vs. Tone Intensity:</strong> Browser security prohibits websites from directly
                locking the master OS volume slider. The application controls the sound stimulus intensity
                independently in software while your device volume remains fixed at 50%.
              </span>
            </div>
          </div>

          {/* Connected Device & Acoustic Filter */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl p-3.5 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#66716D] block">
                Audio Output Device
              </span>
              <span className="font-semibold text-[#1C2421] block truncate" title={detectedAudioDevice}>
                {detectedAudioDevice}
              </span>
            </div>
            <div className="bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl p-3.5 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#66716D] block">
                Acoustic Seal & Isolation
              </span>
              <span className="font-semibold text-[#176B68] block truncate">
                {ncConfig.shortDescription} (~{ncConfig.passiveSealDb}dB)
              </span>
            </div>
          </div>

          {/* Headphone Instructions */}
          <div className="space-y-1.5 text-xs text-[#66716D]">
            <span className="font-bold text-[#1C2421] block">Headphone Checklist:</span>
            <ul className="list-disc pl-5 space-y-1">
              <li>Wear stereo headphones with Left (L) and Right (R) in the correct ears.</li>
              <li>Sit in a quiet room with minimal background noise.</li>
              <li>You will hear a series of brief tones. Simply indicate if you heard the sound or not.</li>
            </ul>
          </div>

          {/* Clinical Disclaimer */}
          <div className="border border-[#DDE5E1] rounded-xl p-3 bg-white text-[11px] text-[#66716D] flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-[#C65A5A] shrink-0 mt-0.5" />
            <span className="leading-relaxed">
              <strong>Clinical Notice:</strong> {CLINICAL_SCREENING_DISCLAIMER}
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleStopTest}
              className="py-3 px-4 rounded-xl border border-[#DDE5E1] text-xs font-bold text-[#66716D] hover:bg-[#F1F4F2] transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleStartTest}
              className="flex-1 py-3 px-6 rounded-xl bg-[#176B68] hover:bg-[#125754] text-white text-xs font-bold uppercase tracking-wider transition shadow-sm cursor-pointer flex items-center justify-center gap-2"
            >
              <span>Start Pure-Tone Test</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </div>
      </div>
    );
  }

  // ==========================================
  // SCREEN 3: Submitting State
  // ==========================================
  if (phase === 'submitting') {
    return (
      <div className="max-w-md mx-auto py-12 px-4 text-center space-y-4">
        <div className="w-10 h-10 border-3 border-[#176B68]/20 border-t-[#176B68] rounded-full animate-spin mx-auto" />
        <h3 className="text-sm font-bold text-[#1C2421] uppercase tracking-wider">
          Recording Threshold Dataset...
        </h3>
        <p className="text-xs text-[#66716D]">
          Structuring 12 pure-tone octave thresholds and compiling trials for ML analysis.
        </p>
      </div>
    );
  }

  // ==========================================
  // SCREEN 4: Error State
  // ==========================================
  if (phase === 'error') {
    return (
      <div className="max-w-md mx-auto py-8 px-4 text-center">
        <div className="card-premium p-8 bg-white border-[#C65A5A]/30 space-y-4">
          <AlertTriangle className="w-10 h-10 text-[#C65A5A] mx-auto animate-pulse" />
          <h3 className="text-sm font-bold text-[#1C2421]">Transmission Error</h3>
          <p className="text-xs text-[#66716D] leading-relaxed">{errorMessage}</p>
          <button
            onClick={finalizeTest}
            className="w-full py-3 bg-[#176B68] text-white rounded-xl text-xs font-bold uppercase tracking-wider transition cursor-pointer"
          >
            Retry Submission
          </button>
        </div>
      </div>
    );
  }

  // ==========================================
  // SCREEN 2: Active Controlled Audiometric Test Screen
  // (Hidden frequency & stimulus numbers, pure interaction)
  // ==========================================
  const currentEarLabel = searchState?.currentEar === 'LEFT' ? 'Left Ear' : 'Right Ear';
  const progressPercent = ((searchState?.stepNumber || 1) / 12) * 100;

  return (
    <div className="max-w-md mx-auto py-6 px-4 animate-fadeIn text-center">
      <div className="card-premium p-8 bg-white flex flex-col items-center justify-between min-h-[480px] space-y-6">

        {/* Progress & Ear Badge */}
        <div className="w-full space-y-2 text-left">
          <div className="flex justify-between items-center text-[10px] text-[#66716D] font-bold uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${searchState?.currentEar === 'LEFT' ? 'bg-[#176B68]' : 'bg-[#C65A5A]'}`} />
              <strong className="text-[#1C2421]">{currentEarLabel}</strong>
            </span>
            <span className="font-mono">Step {searchState?.stepNumber || 1} of 12</span>
          </div>
          <div className="w-full bg-[#F1F4F2] h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ease-out ${
                searchState?.currentEar === 'LEFT' ? 'bg-[#176B68]' : 'bg-[#C65A5A]'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Fixed System Volume Status Pill */}
        <div className="w-full bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl px-3 py-1.5 flex items-center justify-between text-[11px] text-[#66716D]">
          <span className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-[#176B68]" />
            <span>System Volume: <strong>Fixed 50%</strong></span>
          </span>
          <span className="font-mono text-[9px] bg-white px-2 py-0.5 rounded border border-[#DDE5E1] text-[#176B68] font-bold uppercase">
            Stimulus Controlled
          </span>
        </div>

        {/* Tone Presentation / Listening Cue Card */}
        <div className="w-full py-6 flex flex-col items-center justify-center space-y-4">
          {/* Animated acoustic pulse circle */}
          <div className="relative flex items-center justify-center">
            {isTonePlaying && (
              <div className="absolute w-24 h-24 rounded-full bg-[#176B68]/10 animate-ping" />
            )}
            <div
              className={`w-20 h-20 rounded-full flex items-center justify-center border transition-all duration-300 ${
                isTonePlaying
                  ? 'bg-[#E6F2F0] border-[#176B68] scale-105 shadow-md shadow-[#176B68]/20'
                  : 'bg-[#F7F8F6] border-[#DDE5E1]'
              }`}
            >
              <Volume2
                className={`w-8 h-8 transition-colors duration-300 ${
                  isTonePlaying ? 'text-[#176B68] animate-pulse' : 'text-[#66716D]'
                }`}
              />
            </div>
          </div>

          <div>
            <h3 className="text-lg font-bold text-[#1C2421]">
              {isTonePlaying ? 'Playing sound tone...' : 'Did you hear the sound?'}
            </h3>
            <p className="text-xs text-[#66716D] mt-1 max-w-[280px] mx-auto leading-relaxed">
              {isTonePlaying
                ? 'Listen carefully in your ' + currentEarLabel.toLowerCase() + '.'
                : 'Click "I Heard It" if you heard the tone, even faintly, or "Did Not Hear".'}
            </p>
          </div>
        </div>

        {/* Primary Interaction Buttons (Heard / Not Heard) */}
        <div className="w-full space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => handleResponse('heard')}
              disabled={isTonePlaying}
              className={`py-3.5 px-4 rounded-xl text-xs font-bold uppercase tracking-wider transition shadow-sm flex items-center justify-center gap-2 ${
                isTonePlaying
                  ? 'bg-[#F1F4F2] text-[#66716D] cursor-not-allowed border border-[#DDE5E1]'
                  : 'bg-[#176B68] hover:bg-[#125754] text-white cursor-pointer active:scale-98'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>I Heard It</span>
            </button>

            <button
              onClick={() => handleResponse('not_heard')}
              disabled={isTonePlaying}
              className={`py-3.5 px-4 rounded-xl text-xs font-bold uppercase tracking-wider transition border flex items-center justify-center gap-2 ${
                isTonePlaying
                  ? 'bg-[#F1F4F2] text-[#66716D] border-[#DDE5E1] cursor-not-allowed'
                  : 'bg-white hover:bg-[#F7F8F6] border-[#DDE5E1] text-[#1C2421] cursor-pointer active:scale-98'
              }`}
            >
              <span>Did Not Hear</span>
            </button>
          </div>

          {/* Replay Tone Option */}
          <div className="flex justify-between items-center pt-2">
            <button
              onClick={handleReplayStimulus}
              disabled={isTonePlaying}
              className="text-[11px] text-[#66716D] hover:text-[#176B68] flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Replay tone</span>
            </button>

            <button
              onClick={handleStopTest}
              className="text-[11px] text-[#66716D] hover:text-[#C65A5A] transition cursor-pointer"
            >
              Cancel test
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
