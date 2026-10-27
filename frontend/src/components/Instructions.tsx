import React from 'react';
import { Volume2, HelpCircle, CheckCircle, Info } from 'lucide-react';

interface InstructionsProps {
  onProceed: () => void;
}

export const Instructions: React.FC<InstructionsProps> = ({ onProceed }) => {
  return (
    <div className="max-w-xl mx-auto py-6 px-4 animate-fadeIn">
      <div className="card-premium p-8 bg-white space-y-6">
        
        <h2 className="text-2xl font-bold text-[#1C2421] text-center tracking-tight">
          Screening protocols
        </h2>
        <p className="text-[#66716D] text-xs text-center leading-relaxed">
          Please review these clinical rules carefully to ensure the accuracy and reproducibility of your thresholds.
        </p>

        {/* Bullet Instructions */}
        <div className="space-y-4 pt-2 text-left">
          <div className="flex gap-3">
            <div className="bg-[#E6F2F0] w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border border-[#DDE5E1]">
              <CheckCircle className="w-4.5 h-4.5 text-[#176B68]" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-[#1C2421] uppercase tracking-wide font-mono">Acoustic shielding</h4>
              <p className="text-xs text-[#66716D] leading-relaxed mt-0.5 font-sans">
                Isolate your testing location from external noise. Secure your headphones correctly (verify Left and Right transducer channels align).
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="bg-[#E6F2F0] w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border border-[#DDE5E1]">
              <Volume2 className="w-4.5 h-4.5 text-[#176B68]" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-[#1C2421] uppercase tracking-wide font-mono">Binaural separation</h4>
              <p className="text-xs text-[#66716D] leading-relaxed mt-0.5 font-sans">
                Maintain headphone positioning continuously. Stimuli are programmatically panned to isolate individual ear channels.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="bg-[#E6F2F0] w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border border-[#DDE5E1]">
              <HelpCircle className="w-4.5 h-4.5 text-[#176B68]" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-[#1C2421] uppercase tracking-wide font-mono">Intensity calibration</h4>
              <p className="text-xs text-[#66716D] leading-relaxed mt-0.5 font-sans">
                Adjust the volume slider until the tone is just barely detectable (the absolute threshold). Avoid guessing; base adjustments on clear sensory detection.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="bg-[#E6F2F0] w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border border-[#DDE5E1]">
              <Info className="w-4.5 h-4.5 text-[#176B68]" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-[#1C2421] uppercase tracking-wide font-mono">Screening flow</h4>
              <p className="text-xs text-[#66716D] leading-relaxed mt-0.5 font-sans">
                Testing sequence executes Left Ear pure-tones (4 hidden bands), Right Ear pure-tones (4 hidden bands), followed by Speech Accuracy tests.
              </p>
            </div>
          </div>
        </div>

        {/* Calibration Advisory Alert */}
        <div className="bg-[#E6F2F0]/60 border border-[#DDE5E1] p-4 rounded-xl text-xs text-[#176B68] leading-relaxed text-left font-sans">
          <strong>Calibration advisory:</strong> Set your device master hardware volume to approximately 50-60% before initiating tone emissions.
        </div>

        {/* Proceed Button */}
        <button
          onClick={onProceed}
          className="w-full py-3.5 bg-[#176B68] hover:bg-[#125754] text-white rounded-xl font-bold transition text-xs uppercase tracking-wider cursor-pointer font-sans border border-[#176B68]"
        >
          Proceed to audio & mic check
        </button>
      </div>
    </div>
  );
};
