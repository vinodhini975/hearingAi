import { useState } from 'react';
import { ShieldAlert, Volume2, ShieldCheck } from 'lucide-react';
import { LandingPage } from './components/LandingPage';
import { UserInfo } from './components/UserInfo';
import { Instructions } from './components/Instructions';
import { AudioCheck } from './components/AudioCheck';
import { PureToneTest } from './components/PureToneTest';
import { SpeechTest } from './components/SpeechTest';
import { ReportDashboard } from './components/ReportDashboard';
import { getNoiseCancellationConfig } from './utils/noiseCancellation';

type ScreeningStage = 
  | 'landing' 
  | 'demographics' 
  | 'instructions' 
  | 'audio-check' 
  | 'pure-tone' 
  | 'speech' 
  | 'report';

interface UserParameters {
  age: number;
  symptoms: string[];
  headphoneType: string;
  deviceType: string;
}

export default function App() {
  const [stage, setStage] = useState<ScreeningStage>('landing');
  const [sessionId, setSessionId] = useState<string>('');
  const [userParams, setUserParams] = useState<UserParameters | null>(null);

  // Demographics Submission
  const handleDemographicsSubmit = async (data: UserParameters) => {
    try {
      setUserParams(data);
      const ncConfig = getNoiseCancellationConfig(data.deviceType, data.headphoneType);

      const res = await fetch('http://localhost:5000/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          age: data.age,
          symptoms: data.symptoms,
          headphoneType: data.headphoneType,
          deviceType: data.deviceType,
          noiseCancellationProfile: ncConfig.profileName,
          noiseCancellationLevel: ncConfig.aggression,
        })
      });

      const body = await res.json();
      if (body.sessionId) {
        setSessionId(body.sessionId);
        setStage('instructions');
      } else {
        alert('Failed to initialize session. Please check connection to backend.');
      }
    } catch (err) {
      console.error('API Error initializing session:', err);
      alert('Cannot connect to the screening backend. Please make sure the backend server is running on port 5000.');
    }
  };

  const handleAudioCheckSuccess = (_granted: boolean) => {
    setStage('pure-tone');
  };

  const handleRestart = () => {
    setSessionId('');
    setUserParams(null);
    setStage('landing');
  };

  return (
    <div className="min-h-screen bg-[#F7F8F6] text-[#1C2421] flex flex-col justify-between font-sans selection:bg-[#176B68] selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-[#DDE5E1] bg-white/80 backdrop-blur sticky top-0 z-50 non-printable">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Volume2 className="w-5.5 h-5.5 text-[#176B68]" />
            <div>
              <span className="font-bold text-[#1c2421] text-sm tracking-tight block">Auditory Screening Portal</span>
              <span className="text-[10px] text-[#66716D] tracking-wide block">Remote Hearing Assessment</span>
            </div>
          </div>
          {sessionId && userParams && (
            <div className="flex items-center gap-2">
              <div className="hidden sm:flex items-center gap-1.5 text-[10px] bg-[#E6F2F0] border border-[#176B68]/30 text-[#176B68] px-3 py-1 rounded-lg font-medium">
                <ShieldCheck className="w-3.5 h-3.5 text-[#176B68]" />
                <span>Noise Filtering: {getNoiseCancellationConfig(userParams.deviceType, userParams.headphoneType).shortDescription}</span>
              </div>
              <div className="text-[10px] bg-[#F1F4F2] border border-[#DDE5E1] text-[#66716D] px-3 py-1 rounded-lg font-mono">
                Session ID: {sessionId.substring(0, 8)}...
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-6 py-10 flex flex-col justify-center">
        {stage === 'landing' && (
          <LandingPage onStart={() => setStage('demographics')} />
        )}
        
        {stage === 'demographics' && (
          <UserInfo onSubmit={handleDemographicsSubmit} />
        )}

        {stage === 'instructions' && (
          <Instructions onProceed={() => setStage('audio-check')} />
        )}

        {stage === 'audio-check' && (
          <AudioCheck 
            onSuccess={handleAudioCheckSuccess} 
            onBack={() => setStage('demographics')} 
            deviceType={userParams?.deviceType}
            headphoneType={userParams?.headphoneType}
          />
        )}

        {stage === 'pure-tone' && (
          <PureToneTest 
            sessionId={sessionId} 
            onComplete={() => setStage('speech')} 
            onStop={handleRestart}
            deviceType={userParams?.deviceType}
            headphoneType={userParams?.headphoneType}
          />
        )}

        {stage === 'speech' && (
          <SpeechTest 
            sessionId={sessionId} 
            onComplete={() => setStage('report')} 
            onStop={handleRestart}
            deviceType={userParams?.deviceType}
            headphoneType={userParams?.headphoneType}
          />
        )}

        {stage === 'report' && (
          <ReportDashboard 
            sessionId={sessionId} 
            onRestart={handleRestart} 
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#DDE5E1] py-6 bg-[#F1F4F2]/50 text-center text-[10px] text-[#66716D] non-printable space-y-1">
        <p>© 2026 Remote Hearing Assessment Portal. For research and screening purposes only.</p>
        <p className="flex items-center justify-center gap-1">
          <ShieldAlert className="w-3.5 h-3.5 text-[#66716D]" />
          <span>This screening is not a replacement for a clinical audiology diagnosis.</span>
        </p>
      </footer>
    </div>
  );
}
