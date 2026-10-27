import React, { useState, useEffect, useRef } from 'react';
import { Mic, Volume2, ShieldAlert, CheckCircle, AlertTriangle, Laptop, Monitor, Smartphone, Tablet, ShieldCheck, Sliders } from 'lucide-react';
import { getNoiseCancellationConfig, buildAudioNoiseFilter, type NoiseCancellationConfig } from '../utils/noiseCancellation';

interface AudioCheckProps {
  onSuccess: (micGranted: boolean) => void;
  onBack: () => void;
  deviceType?: string;
  headphoneType?: string;
}

export const AudioCheck: React.FC<AudioCheckProps> = ({ 
  onSuccess, 
  onBack, 
  deviceType = 'Laptop', 
  headphoneType = 'Over-ear headphones' 
}) => {
  const [micState, setMicState] = useState<'prompt' | 'granted' | 'denied'>('prompt');
  const [noiseLevel, setNoiseLevel] = useState<number>(0);
  const [isPlayingTestTone, setIsPlayingTestTone] = useState<boolean>(false);
  const [testTonePlayed, setTestTonePlayed] = useState<boolean>(false);
  const [audioContextSupported, setAudioContextSupported] = useState<boolean>(true);
  const [noiseCancellationEnabled, setNoiseCancellationEnabled] = useState<boolean>(true);

  const audioContextRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const filteredOutputRef = useRef<AudioNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const ncConfig: NoiseCancellationConfig = getNoiseCancellationConfig(deviceType, headphoneType);

  // Check Web Audio API support
  useEffect(() => {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) {
      setAudioContextSupported(false);
    }
  }, []);

  // Handle request microphone access and start analyser with device-specific noise cancellation
  const requestMicrophone = async () => {
    try {
      // Apply device-tailored MediaTrackConstraints
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: ncConfig.mediaTrackConstraints
      });
      micStreamRef.current = stream;
      setMicState('granted');

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioContextClass();
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // Build hardware-tuned DSP noise filter chain
      const dspChain = buildAudioNoiseFilter(ctx, source, ncConfig);
      filteredOutputRef.current = dspChain.outputNode;

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      // Connect filtered or raw based on state
      if (noiseCancellationEnabled) {
        dspChain.outputNode.connect(analyser);
      } else {
        source.connect(analyser);
      }

      const bufferLength = analyser.fftSize;
      const dataArray = new Uint8Array(bufferLength);
      const frequencyArray = new Uint8Array(analyser.frequencyBinCount);

      const checkNoise = () => {
        if (!analyserRef.current) return;
        
        // Draw Waveform to Canvas
        const canvas = canvasRef.current;
        if (canvas) {
          const ctx2 = canvas.getContext('2d');
          if (ctx2) {
            analyserRef.current.getByteTimeDomainData(dataArray);
            
            // Clear screen
            ctx2.fillStyle = '#F1F4F2';
            ctx2.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw clean baseline
            ctx2.strokeStyle = '#DDE5E1';
            ctx2.lineWidth = 1;
            ctx2.beginPath();
            ctx2.moveTo(0, canvas.height / 2);
            ctx2.lineTo(canvas.width, canvas.height / 2);
            ctx2.stroke();

            // Draw wave line (deep teal if active filter, muted if bypassed)
            ctx2.lineWidth = 1.8;
            ctx2.strokeStyle = '#176B68';
            ctx2.beginPath();

            const sliceWidth = canvas.width / bufferLength;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
              const v = dataArray[i] / 128.0;
              const y = (v * canvas.height) / 2;

              if (i === 0) {
                ctx2.moveTo(x, y);
              } else {
                ctx2.lineTo(x, y);
              }
              x += sliceWidth;
            }

            ctx2.lineTo(canvas.width, canvas.height / 2);
            ctx2.stroke();
          }
        }

        // Calculate average frequency noise level
        analyserRef.current.getByteFrequencyData(frequencyArray);
        const avg = frequencyArray.reduce((sum, val) => sum + val, 0) / frequencyArray.length;
        setNoiseLevel(Math.min(100, Math.round((avg / 128) * 100)));

        animationFrameRef.current = requestAnimationFrame(checkNoise);
      };

      checkNoise();
    } catch (err) {
      console.warn('Microphone access denied:', err);
      setMicState('denied');
    }
  };

  // Switch between filtered DSP output and raw microphone feed
  const toggleNoiseCancellation = () => {
    const nextState = !noiseCancellationEnabled;
    setNoiseCancellationEnabled(nextState);

    if (analyserRef.current && sourceNodeRef.current && filteredOutputRef.current) {
      try {
        sourceNodeRef.current.disconnect();
        filteredOutputRef.current.disconnect();

        if (nextState) {
          filteredOutputRef.current.connect(analyserRef.current);
        } else {
          sourceNodeRef.current.connect(analyserRef.current);
        }
      } catch (e) {
        console.warn('Error toggling audio node chain:', e);
      }
    }
  };

  // Clean up mic streams
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // Play stereo test sound (chime in Left, then chime in Right)
  const playStereoTest = async () => {
    if (isPlayingTestTone) return;

    try {
      setIsPlayingTestTone(true);
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioContextClass();

      // 1. Play Left Chime
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      const panner1 = ctx.createStereoPanner();

      osc1.type = 'sine';
      osc1.frequency.value = 800; // 800Hz chime
      panner1.pan.value = -1.0; // Hard left

      osc1.connect(gain1);
      gain1.connect(panner1);
      panner1.connect(ctx.destination);

      gain1.gain.setValueAtTime(0, ctx.currentTime);
      gain1.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 0.1);
      gain1.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.2);

      osc1.start();
      osc1.stop(ctx.currentTime + 1.2);

      // 2. Play Right Chime after 1.5s delay
      setTimeout(() => {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        const panner2 = ctx.createStereoPanner();

        osc2.type = 'sine';
        osc2.frequency.value = 1200; // 1200Hz chime
        panner2.pan.value = 1.0; // Hard right

        osc2.connect(gain2);
        gain2.connect(panner2);
        panner2.connect(ctx.destination);

        gain2.gain.setValueAtTime(0, ctx.currentTime);
        gain2.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 0.1);
        gain2.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.2);

        osc2.start();
        osc2.stop(ctx.currentTime + 1.2);

        setTimeout(() => {
          setIsPlayingTestTone(false);
          setTestTonePlayed(true);
        }, 1200);
      }, 1500);

    } catch (err) {
      console.error('Error playing test tone:', err);
      setIsPlayingTestTone(false);
    }
  };

  const handleProceed = () => {
    onSuccess(micState === 'granted');
  };

  const isEnvironmentTooLoud = noiseLevel > 30;

  const renderDeviceIcon = () => {
    const dev = deviceType.toLowerCase();
    if (dev.includes('laptop')) return <Laptop className="w-4 h-4 text-[#176B68]" />;
    if (dev.includes('desktop')) return <Monitor className="w-4 h-4 text-[#176B68]" />;
    if (dev.includes('phone') || dev.includes('smart')) return <Smartphone className="w-4 h-4 text-[#176B68]" />;
    return <Tablet className="w-4 h-4 text-[#176B68]" />;
  };

  return (
    <div className="max-w-xl mx-auto py-6 px-4 animate-fadeIn">
      <div className="card-premium p-8 bg-white space-y-6">
        
        <h2 className="text-2xl font-bold text-[#1C2421] text-center tracking-tight">
          System verification & calibration
        </h2>
        <p className="text-[#66716D] text-xs text-center leading-relaxed mb-4">
          Audio parameters and noise cancellation profiles are adapted to your detected device hardware.
        </p>

        {!audioContextSupported && (
          <div className="bg-[#C65A5A]/10 border border-[#C65A5A]/20 p-4 rounded-xl flex gap-3 text-xs text-[#C65A5A] text-left">
            <ShieldAlert className="w-5 h-5 shrink-0" />
            <div>
              <strong>Audio API unsupported:</strong> Your browser does not support the HTML5 Audio interface. Please use Chrome, Safari, or Microsoft Edge.
            </div>
          </div>
        )}

        {/* Device-Specific Noise Cancellation Profile Card */}
        <div className="border border-[#176B68]/30 rounded-xl p-4.5 bg-[#E6F2F0]/40 text-left space-y-3">
          <div className="flex justify-between items-start gap-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-white border border-[#176B68]/30 flex items-center justify-center">
                {renderDeviceIcon()}
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#176B68] block">
                  Hardware Profile: {deviceType}
                </span>
                <h4 className="text-xs font-bold text-[#1C2421]">
                  {ncConfig.profileName}
                </h4>
              </div>
            </div>
            <span className="bg-[#176B68] text-white text-[9px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider font-mono shrink-0">
              {ncConfig.aggression} ANC
            </span>
          </div>

          <p className="text-[11px] text-[#4A5551] leading-relaxed">
            {ncConfig.details}
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-[#176B68]/15 text-[10px] font-mono text-[#556360]">
            <div className="bg-white/70 p-1.5 rounded border border-[#DDE5E1]">
              <span className="text-[#66716D] block text-[8px] uppercase">Rumble Cutoff</span>
              <span className="font-bold text-[#1C2421]">{ncConfig.highPassFreq} Hz</span>
            </div>
            <div className="bg-white/70 p-1.5 rounded border border-[#DDE5E1]">
              <span className="text-[#66716D] block text-[8px] uppercase">Mains Notch</span>
              <span className="font-bold text-[#1C2421]">{ncConfig.notchFreq} Hz</span>
            </div>
            <div className="bg-white/70 p-1.5 rounded border border-[#DDE5E1]">
              <span className="text-[#66716D] block text-[8px] uppercase">Attenuation</span>
              <span className="font-bold text-[#176B68]">~{ncConfig.expectedAttenuationDb} dB</span>
            </div>
            <div className="bg-white/70 p-1.5 rounded border border-[#DDE5E1]">
              <span className="text-[#66716D] block text-[8px] uppercase">Ear Seal</span>
              <span className="font-bold text-[#1C2421]">~{ncConfig.passiveSealDb} dB</span>
            </div>
          </div>
        </div>

        {/* 1. Mic check section with real-time noise cancellation */}
        <div className="border border-[#DDE5E1] rounded-xl p-5 space-y-4 bg-[#F1F4F2]/30 text-left">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#E6F2F0] flex items-center justify-center border border-[#DDE5E1]">
                <Mic className="w-4.5 h-4.5 text-[#176B68]" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-[#1C2421] uppercase tracking-wide font-mono">Microphone calibration</h4>
                <p className="text-[11px] text-[#66716D]">Calibrated with device noise suppression filters</p>
              </div>
            </div>
            {micState === 'granted' ? (
              <span className="bg-[#3A8065]/10 text-[#3A8065] border border-[#3A8065]/20 text-[9px] px-2.5 py-1 rounded-full font-bold uppercase font-mono tracking-wider">
                Access active
              </span>
            ) : micState === 'denied' ? (
              <span className="bg-[#C65A5A]/10 text-[#C65A5A] border border-[#C65A5A]/20 text-[9px] px-2.5 py-1 rounded-full font-bold uppercase font-mono tracking-wider">
                Access blocked
              </span>
            ) : (
              <button
                onClick={requestMicrophone}
                className="bg-white hover:bg-[#F1F4F2] text-[#176B68] text-[10px] px-4 py-2 rounded-lg font-bold border border-[#DDE5E1] transition cursor-pointer uppercase tracking-wider font-sans"
              >
                Allow access
              </button>
            )}
          </div>

          {/* Oscilloscope Canvas Visualizer if microphone is active */}
          {micState === 'granted' && (
            <div className="space-y-3 pt-3 border-t border-[#DDE5E1]">
              <div className="flex justify-between items-center text-[11px]">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#176B68]" />
                  <span className="font-semibold text-[#1C2421]">Noise Cancellation Filter:</span>
                  <span className={noiseCancellationEnabled ? 'text-[#176B68] font-bold' : 'text-[#66716D]'}>
                    {noiseCancellationEnabled ? 'Active (Suppressed)' : 'Bypassed (Raw Mic)'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={toggleNoiseCancellation}
                  className="flex items-center gap-1 text-[10px] bg-white border border-[#DDE5E1] px-2.5 py-1 rounded font-medium hover:bg-[#F1F4F2] transition text-[#176B68]"
                >
                  <Sliders className="w-3 h-3" />
                  <span>Toggle filter</span>
                </button>
              </div>

              <div className="w-full h-16 rounded-lg overflow-hidden border border-[#DDE5E1] bg-[#F1F4F2] relative">
                <canvas ref={canvasRef} width="400" height="64" className="w-full h-full" />
                <span className="absolute bottom-1 right-2 text-[8px] font-mono text-[#66716D]/70 bg-white/60 px-1.5 py-0.5 rounded">
                  {noiseCancellationEnabled ? `${deviceType} Filter On` : 'Raw Feed'}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-[#66716D]">Calibrated noise floor:</span>
                <span className={`font-bold uppercase tracking-wider ${isEnvironmentTooLoud ? 'text-[#C65A5A]' : 'text-[#3A8065]'}`}>
                  {isEnvironmentTooLoud ? `High noise (${noiseLevel}%)` : `Ideal environment (${noiseLevel}%)`}
                </span>
              </div>

              {isEnvironmentTooLoud && (
                <div className="flex gap-2 items-center text-[10px] text-[#B68132] bg-[#B68132]/5 p-2.5 rounded-lg border border-[#B68132]/10">
                  <AlertTriangle className="w-4.5 h-4.5 shrink-0 text-[#B68132]" />
                  <span>Ambient room noise exceeds recommended screening threshold. Move away from open windows or loud appliances.</span>
                </div>
              )}
            </div>
          )}

          {micState === 'denied' && (
            <div className="flex gap-2 items-start text-[10px] text-[#C65A5A] bg-[#C65A5A]/5 p-3.5 rounded-lg border border-[#C65A5A]/10">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                Microphone denied. Voice screening will be simulated using keyboard inputs.
              </span>
            </div>
          )}
        </div>

        {/* 2. Audio playback check section */}
        <div className="border border-[#DDE5E1] rounded-xl p-5 space-y-3 bg-[#F1F4F2]/30 text-left">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#E6F2F0] flex items-center justify-center border border-[#DDE5E1]">
                <Volume2 className="w-4.5 h-4.5 text-[#176B68]" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-[#1C2421] uppercase tracking-wide font-mono">Channel isolation</h4>
                <p className="text-[11px] text-[#66716D]">Calibrates separate left and right playback</p>
              </div>
            </div>
            <button
              onClick={playStereoTest}
              disabled={isPlayingTestTone}
              className={`flex items-center gap-1.5 text-[10px] px-4 py-2 rounded-lg font-bold border transition cursor-pointer uppercase tracking-wider font-sans ${
                isPlayingTestTone
                  ? 'bg-[#F1F4F2] text-[#66716D] border-[#DDE5E1]'
                  : 'bg-white hover:bg-[#F1F4F2] text-[#176B68] border-[#DDE5E1]'
              }`}
            >
              <span>{isPlayingTestTone ? 'Playing...' : 'Test Left/Right'}</span>
            </button>
          </div>

          {isPlayingTestTone && (
            <div className="text-center py-2 text-[10px] font-mono font-bold text-[#176B68] animate-pulse">
              [Emitting test tones: Left ear chime, followed by Right ear]
            </div>
          )}

          {testTonePlayed && !isPlayingTestTone && (
            <div className="flex gap-2 items-center text-[10px] text-[#3A8065] bg-[#3A8065]/5 p-2.5 rounded-lg border border-[#3A8065]/10">
              <CheckCircle className="w-4 h-4 shrink-0 text-[#3A8065]" />
              <span>Channel chime check complete. Make sure you heard distinct sounds in each ear.</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={onBack}
            className="flex-1 py-3 bg-white hover:bg-[#F1F4F2] text-[#66716D] border border-[#DDE5E1] rounded-xl font-bold transition text-xs uppercase tracking-wider cursor-pointer"
          >
            Go Back
          </button>
          <button
            onClick={handleProceed}
            className="flex-1 py-3 bg-[#176B68] hover:bg-[#125754] text-white rounded-xl font-bold transition duration-200 text-xs uppercase tracking-wider cursor-pointer border border-[#176B68]"
          >
            Start Hearing Test
          </button>
        </div>
      </div>
    </div>
  );
};
