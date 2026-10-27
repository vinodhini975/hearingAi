import React, { useState, useEffect, useRef } from 'react';
import { Mic, Volume2, StopCircle, RefreshCw, AlertCircle, ShieldCheck } from 'lucide-react';
import { getNoiseCancellationConfig } from '../utils/noiseCancellation';

interface SpeechTestProps {
  sessionId: string;
  onComplete: () => void;
  onStop: () => void;
  deviceType?: string;
  headphoneType?: string;
}

interface NextSpeechResponse {
  ear: 'LEFT' | 'RIGHT';
  targetWord: string;
  testComplete: boolean;
  trialNumber: number;
  similarity?: number;
  isCorrect?: boolean;
}

export const SpeechTest: React.FC<SpeechTestProps> = ({ 
  sessionId, 
  onComplete, 
  onStop,
  deviceType = 'Laptop',
  headphoneType = 'Over-ear headphones'
}) => {
  const ncConfig = getNoiseCancellationConfig(deviceType, headphoneType);
  const [currentTrial, setCurrentTrial] = useState<NextSpeechResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [testPhase, setTestPhase] = useState<'listening' | 'recording' | 'submitting'>('listening');
  const [countdown, setCountdown] = useState<number>(5);
  const [transcript, setTranscript] = useState<string>('');
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [speechSupported, setSpeechSupported] = useState<boolean>(true);
  const [errorText, setErrorText] = useState<string>('');

  const timerRef = useRef<any>(null);
  const recognitionRef = useRef<any>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const handleStopTest = () => {
    if (window.confirm('Are you sure you want to stop the test? Your current progress will be reset.')) {
      if (recognitionRef.current) recognitionRef.current.abort();
      onStop();
    }
  };

  useEffect(() => {
    fetchNextSpeech();

    // Check browser speech recognition support
    const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionClass) {
      setSpeechSupported(false);
    } else {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
        setErrorText('');
      };

      recognition.onresult = (event: any) => {
        const resultText = event.results[0][0].transcript;
        setTranscript(resultText);
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'no-speech') {
          setErrorText('No speech detected. Please speak louder or adjust mic.');
        } else {
          setErrorText(`Error: ${event.error}. Please try typing.`);
        }
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recognitionRef.current) recognitionRef.current.abort();
    };
  }, []);

  const fetchNextSpeech = async () => {
    try {
      setLoading(true);
      const res = await fetch(`http://localhost:5000/api/sessions/${sessionId}/trials/next-speech`);
      const data: NextSpeechResponse = await res.json();

      if (data.testComplete) {
        onComplete();
        return;
      }

      setCurrentTrial(data);
      setLoading(false);
      setTestPhase('listening');
      setCountdown(5);
      setTranscript('');
      setErrorText('');

      // Play audio stimulus word and start timer
      playSpeechWord(data.targetWord, data.ear);
      startTimer();
    } catch (err) {
      console.error('Error fetching next speech trial:', err);
    }
  };

  const startTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    let secondsLeft = 5;
    timerRef.current = setInterval(() => {
      secondsLeft--;
      setCountdown(secondsLeft);
      if (secondsLeft <= 0) {
        if (timerRef.current) clearInterval(timerRef.current);
        setTestPhase('recording');
      }
    }, 1000);
  };

  // Play word with panning using Google Translate TTS
  const playSpeechWord = async (word: string, ear: 'LEFT' | 'RIGHT') => {
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioContextClass();
      audioCtxRef.current = ctx;

      const ttsUrl = `https://translate.google.com/translate_tts?ie=UTF-8&tl=en&client=tw-ob&q=${encodeURIComponent(word)}`;
      
      const response = await fetch(ttsUrl);
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

      const source = ctx.createBufferSource();
      const panner = ctx.createStereoPanner();
      const gain = ctx.createGain();

      source.buffer = audioBuffer;
      panner.pan.value = ear === 'LEFT' ? -1.0 : 1.0;
      gain.gain.value = 0.5; // Comfortable volume

      source.connect(gain);
      gain.connect(panner);
      panner.connect(ctx.destination);

      source.start(0);
    } catch (err) {
      console.warn('Network TTS panner failed, falling back to local speech synthesis:', err);
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(word);
        utterance.lang = 'en-US';
        utterance.rate = 0.8;
        window.speechSynthesis.speak(utterance);
      }
    }
  };

  const startRecording = () => {
    if (recognitionRef.current) {
      setTranscript('');
      setErrorText('');
      try {
        recognitionRef.current.start();
      } catch (err) {
        recognitionRef.current.stop();
        setTimeout(() => recognitionRef.current.start(), 200);
      }
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const submitResponse = async () => {
    if (!currentTrial || !transcript.trim()) return;

    setTestPhase('submitting');
    try {
      const res = await fetch(`http://localhost:5000/api/sessions/${sessionId}/trials/speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ear: currentTrial.ear,
          targetWord: currentTrial.targetWord,
          userResponse: transcript.trim(),
          recordingQuality: errorText ? 'Poor' : 'Good',
          noiseCancellationProfile: ncConfig.profileName
        })
      });

      const nextData: NextSpeechResponse = await res.json();

      if (nextData.testComplete) {
        onComplete();
        return;
      }

      setCurrentTrial(nextData);
      setTestPhase('listening');
      setCountdown(5);
      setTranscript('');
      setErrorText('');
      playSpeechWord(nextData.targetWord, nextData.ear);
      startTimer();
    } catch (err) {
      console.error('Error submitting speech trial response:', err);
      setTestPhase('recording');
    }
  };

  if (loading || !currentTrial) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] text-[#66716D]">
        <div className="w-8 h-8 border-3 border-[#176B68]/20 border-t-[#176B68] rounded-full animate-spin mb-4" />
        <span className="text-xs font-mono">Preparing speech assessment...</span>
      </div>
    );
  }

  // Progress percentage (speech test has 3 trials)
  const progressPercent = (currentTrial.trialNumber / 3) * 100;

  return (
    <div className="max-w-md mx-auto py-6 px-4 animate-fadeIn">
      <div className="card-premium p-8 bg-white flex flex-col items-center text-center space-y-7 min-h-[460px] justify-between">
        
        {/* Stage Header */}
        <div className="w-full text-left space-y-2">
          <div className="flex justify-between items-center text-[10px] text-[#66716D] font-bold uppercase tracking-wider">
            <span>Speech recognition</span>
            <span>Word trial: {currentTrial.trialNumber} of 3</span>
          </div>
          <div className="w-full bg-[#F1F4F2] h-1 rounded-full overflow-hidden">
            <div 
              className="bg-[#176B68] h-full transition-all duration-300 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Device-Specific Noise Cancellation Banner */}
        <div className="w-full bg-[#E6F2F0]/70 border border-[#176B68]/20 rounded-xl px-3.5 py-2 flex items-center justify-between text-[11px] text-[#176B68]">
          <div className="flex items-center gap-1.5 font-medium">
            <ShieldCheck className="w-4 h-4 text-[#176B68] shrink-0" />
            <span className="font-semibold text-[#1C2421]">ANC Active: {ncConfig.shortDescription}</span>
          </div>
          <span className="font-mono text-[9px] bg-white px-2 py-0.5 rounded border border-[#176B68]/20 text-[#176B68] font-bold">
            ~{ncConfig.expectedAttenuationDb}dB reduction
          </span>
        </div>

        {testPhase === 'listening' ? (
          /* Listening Screen */
          <div className="flex flex-col items-center space-y-6 my-auto">
            <h3 className="text-lg font-bold text-[#1C2421]">
              Listen carefully
            </h3>
            
            {/* Elegant Muted Countdown Circle */}
            <div className="relative w-32 h-32 flex items-center justify-center rounded-full bg-[#F1F4F2] border border-[#DDE5E1]">
              <div className="flex flex-col items-center justify-center">
                <span className="text-4xl font-extrabold text-[#1c2421] tracking-tight">{countdown}</span>
                <span className="text-[9px] uppercase font-bold text-[#66716D] tracking-widest mt-0.5">Seconds</span>
              </div>
            </div>
            
            <p className="text-xs text-[#66716D] flex items-center gap-1.5 justify-center">
              <Volume2 className="w-4 h-4 text-[#176B68]" />
              <span>A word was played in your {currentTrial.ear.toLowerCase()} ear.</span>
            </p>
          </div>
        ) : testPhase === 'recording' ? (
          /* Speech Input Screen */
          <div className="flex flex-col items-center space-y-6 my-auto w-full">
            <h3 className="text-lg font-bold text-[#1C2421]">
              Repeat the word
            </h3>

            {/* Muted Voice Wave Simulator */}
            <div className="w-full flex items-center justify-center gap-1.5 h-10 bg-[#F1F4F2]/50 rounded-xl border border-[#DDE5E1] px-4">
              {isRecording ? (
                <>
                  <div className="w-0.5 bg-[#176B68] rounded-full h-3 animate-bar-1 origin-bottom" />
                  <div className="w-0.5 bg-[#176B68] rounded-full h-5 animate-bar-2 origin-bottom" />
                  <div className="w-0.5 bg-[#176B68] rounded-full h-6 animate-bar-3 origin-bottom" />
                  <div className="w-0.5 bg-[#176B68] rounded-full h-4 animate-bar-2 origin-bottom" />
                  <div className="w-0.5 bg-[#176B68] rounded-full h-2 animate-bar-1 origin-bottom" />
                </>
              ) : (
                <span className="text-[9px] text-[#66716D] font-medium tracking-wide uppercase">[Voice input idle]</span>
              )}
            </div>

            {/* Mic Action Circle */}
            <div className="flex flex-col items-center space-y-3">
              {isRecording ? (
                <button
                  onClick={stopRecording}
                  className="w-16 h-16 bg-[#C65A5A] hover:bg-[#b54a4a] text-white rounded-full flex items-center justify-center transition cursor-pointer shadow-sm border-4 border-[#F7F8F6]"
                >
                  <StopCircle className="w-7 h-7" />
                </button>
              ) : (
                <button
                  onClick={startRecording}
                  className="w-16 h-16 bg-[#176B68] hover:bg-[#125754] text-white rounded-full flex items-center justify-center transition cursor-pointer shadow-sm border-4 border-[#F7F8F6]"
                >
                  <Mic className="w-7 h-7" />
                </button>
              )}
              <span className="text-[10px] font-bold text-[#66716D] tracking-wide">
                {isRecording ? 'Listening... Speak now' : 'Click microphone to speak'}
              </span>
            </div>

            {/* Transcript text box / input fallback */}
            <div className="w-full space-y-3">
              {!speechSupported ? (
                <div className="space-y-2">
                  <p className="text-[10px] text-[#B68132] flex items-center gap-1 bg-[#B68132]/5 p-2 rounded-lg border border-[#B68132]/10">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>Your browser does not support speech recognition. Please type the word.</span>
                  </p>
                  <input
                    type="text"
                    placeholder="Type the word you heard..."
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    className="w-full text-center bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl px-4 py-3 text-[#1C2421] focus:outline-none focus:border-[#176B68] text-sm transition"
                  />
                </div>
              ) : (
                <div className="w-full min-h-[50px] bg-[#F1F4F2]/30 border border-[#DDE5E1] rounded-xl flex items-center justify-center p-3 text-[#1C2421] font-semibold text-sm italic">
                  {transcript ? `"${transcript}"` : <span className="text-slate-400 text-[10px] font-normal not-italic tracking-wider uppercase">[reception queue empty]</span>}
                </div>
              )}

              {errorText && (
                <p className="text-[10px] text-[#C65A5A] font-semibold flex items-center gap-1 justify-center">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{errorText}</span>
                </p>
              )}
            </div>

            {/* Submit button */}
            <button
              onClick={submitResponse}
              disabled={!transcript.trim()}
              className={`w-full py-3.5 rounded-xl font-bold transition text-xs uppercase tracking-wider cursor-pointer border ${
                transcript.trim()
                  ? 'bg-[#176B68] hover:bg-[#125754] text-white border-[#176B68] shadow-sm'
                  : 'bg-[#F1F4F2] text-slate-400 border-[#DDE5E1] cursor-not-allowed'
              }`}
            >
              Submit response
            </button>
          </div>
        ) : (
          /* Submitting screen */
          <div className="flex flex-col items-center justify-center min-h-[220px] text-[#66716D]">
            <RefreshCw className="w-8 h-8 text-[#176B68] animate-spin mb-4" />
            <span className="text-[10px] uppercase tracking-widest font-bold">Comparing response...</span>
          </div>
        )}

        {/* Disclaimer footer */}
        <div className="text-[9px] text-[#66716D] border-t border-[#DDE5E1] pt-3 w-full">
          Speak clearly and repeat the word exactly as it was played.
        </div>

        {/* Stop Test Section */}
        <div className="w-full border-t border-[#DDE5E1] pt-3 flex justify-center">
          <button
            onClick={handleStopTest}
            className="text-[10px] font-bold uppercase tracking-wider text-[#66716D] hover:text-[#C65A5A] hover:underline transition cursor-pointer flex items-center gap-1"
          >
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Stop and cancel test</span>
          </button>
        </div>
      </div>
    </div>
  );
};
