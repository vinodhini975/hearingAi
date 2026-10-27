import React from 'react';
import { Headphones, Mic, Volume2, ShieldAlert } from 'lucide-react';

interface LandingPageProps {
  onStart: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onStart }) => {
  return (
    <div className="flex flex-col items-center justify-center max-w-3xl mx-auto py-8 px-4 animate-fadeIn">
      {/* Brand Badge */}
      <div className="flex items-center gap-2 mb-4 bg-[#E6F2F0] px-4 py-1.5 rounded-full border border-[#DDE5E1]">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#176B68]">
          Clinical Screening Portal
        </span>
      </div>

      {/* Hero Headings */}
      <h1 className="text-3xl md:text-4xl font-extrabold text-center text-[#1C2421] leading-tight mb-4 tracking-tight">
        Remote hearing screening and preliminary assessment
      </h1>
      
      <p className="text-[#66716D] text-center max-w-xl text-sm md:text-base mb-10 leading-relaxed font-normal">
        A clinical-grade, self-administered audio screening dashboard designed to record air-conduction thresholds and speech intelligibility using consumer hardware.
      </p>

      {/* Grid Requirements */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mb-10">
        
        {/* Card 1: Headphones */}
        <div className="card-premium p-6 flex flex-col justify-between text-left">
          <div>
            <div className="bg-[#E6F2F0] w-10 h-10 rounded-lg flex items-center justify-center mb-4">
              <Headphones className="w-5 h-5 text-[#176B68]" />
            </div>
            <h3 className="font-bold text-[#1C2421] text-sm mb-2">Stereo headphones</h3>
            <p className="text-xs text-[#66716D] leading-relaxed">
              Standard over-ear headphones or in-ear earphones with working left and right channels are required for spatial ear testing.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#DDE5E1] text-[9px] text-[#66716D] font-mono">
            Requires dual channels
          </div>
        </div>

        {/* Card 2: Quiet Room */}
        <div className="card-premium p-6 flex flex-col justify-between text-left">
          <div>
            <div className="bg-[#E6F2F0] w-10 h-10 rounded-lg flex items-center justify-center mb-4">
              <Volume2 className="w-5 h-5 text-[#176B68]" />
            </div>
            <h3 className="font-bold text-[#1C2421] text-sm mb-2">Quiet environment</h3>
            <p className="text-xs text-[#66716D] leading-relaxed">
              Background noise can mask soft assessment tones. Please find a quiet space away from household noise and fans.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#DDE5E1] text-[9px] text-[#66716D] font-mono">
            Low ambient noise
          </div>
        </div>

        {/* Card 3: Mic Check */}
        <div className="card-premium p-6 flex flex-col justify-between text-left">
          <div>
            <div className="bg-[#E6F2F0] w-10 h-10 rounded-lg flex items-center justify-center mb-4">
              <Mic className="w-5 h-5 text-[#176B68]" />
            </div>
            <h3 className="font-bold text-[#1C2421] text-sm mb-2">Microphone</h3>
            <p className="text-xs text-[#66716D] leading-relaxed">
              A working microphone is used to repeat back played words during the speech recognition section of the screening.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#DDE5E1] text-[9px] text-[#66716D] font-mono">
            Voice speech input
          </div>
        </div>
      </div>

      {/* Clinical Disclaimer Board */}
      <div className="w-full card-premium p-6 mb-8 text-sm leading-relaxed text-[#66716D] relative text-left bg-white">
        <div className="flex items-center gap-2 text-[#C65A5A] mb-3 font-bold text-xs uppercase tracking-wider">
          <ShieldAlert className="w-4 h-4 text-[#C65A5A]" />
          <span>Research and screening notice</span>
        </div>
        <p className="text-xs text-[#1C2421] mb-2 leading-relaxed">
          This platform is an uncalibrated remote screening tool and does not replace a professional audiologist or ENT examination.
        </p>
        <p className="text-xs text-[#66716D] leading-relaxed">
          Your threshold estimates depend on your headphone frequency response and ambient noise levels. If you have sudden hearing changes, fluid discharge, or persistent ringing, please seek immediate consultation with a qualified medical professional.
        </p>
      </div>

      {/* Start Button */}
      <button
        onClick={onStart}
        className="px-8 py-3.5 bg-[#176B68] hover:bg-[#125754] text-white rounded-xl font-bold transition duration-200 uppercase tracking-wider text-xs flex items-center gap-2 cursor-pointer shadow-sm"
      >
        <span>Get started</span>
      </button>
    </div>
  );
};
