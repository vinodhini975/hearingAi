import React, { useState, useEffect } from 'react';
import { AudiogramChart } from './AudiogramChart';
import { 
  FileText, ShieldAlert, AlertTriangle, 
  Download, RefreshCw, Layers, ShieldCheck,
  Cpu, Sparkles
} from 'lucide-react';

interface ReportDashboardProps {
  sessionId: string;
  onRestart: () => void;
}

export interface PathologyEarReport {
  predictedClass: 'Normal' | 'Sensorineural' | 'Conductive' | 'Mixed';
  confidence: number;
  probabilities: { [className: string]: number };
  metrics: {
    meanAcDbHl: number;
    meanBcDbHl: number;
    meanAirBoneGap: number;
    speechScore: number;
  };
  thresholds: {
    ac: { [freq: number]: number };
    bc: { [freq: number]: number };
    abg: { [freq: number]: number };
  };
  explanation: string;
}

export interface PathologyClassificationReport {
  success: boolean;
  overallPathology: string;
  overallConfidence: number;
  clinicalSummary: string;
  leftEar: PathologyEarReport | null;
  rightEar: PathologyEarReport | null;
  modelMetadata: {
    modelName: string;
    modelFile: string;
    classes: string[];
    featureCount: number;
    status: string;
  };
}

interface ReportData {
  sessionId: string;
  age: number;
  symptoms: string[];
  headphoneType: string;
  deviceType: string;
  created_at: string;
  dataQuality: 'Reliable' | 'Potentially unreliable' | 'Insufficient data';
  confidenceLevel: 'High confidence' | 'Moderate confidence' | 'Low confidence';
  overallStatus: string;
  leftStatus: string;
  rightStatus: string;
  leftThresholds: { [freq: number]: number };
  rightThresholds: { [freq: number]: number };
  leftSpeechScore: number;
  rightSpeechScore: number;
  leftInterpretation: string;
  rightInterpretation: string;
  comparison: string;
  hearingPattern: string;
  aiExplanation: string;
  noiseCancellationProfile?: string;
  noiseCancellationLevel?: string;
  pathologyClassification?: PathologyClassificationReport;
  fixedSystemVolume?: number;
  audioDevice?: string;
  calibrationProfile?: any;
}

export const ReportDashboard: React.FC<ReportDashboardProps> = ({ sessionId, onRestart }) => {
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchReport();
  }, [sessionId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      const res = await fetch(`http://localhost:5000/api/sessions/${sessionId}/report`);
      if (!res.ok) {
        throw new Error('Failed to generate report.');
      }
      const data: ReportData = await res.json();
      setReport(data);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching report:', err);
      setError('Failed to load assessment report. Please ensure the backend is running.');
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-[#66716D]">
        <RefreshCw className="w-8 h-8 text-[#176B68] animate-spin mb-4" />
        <span className="text-xs font-semibold">Running analysis layer...</span>
        <span className="text-[10px] text-slate-500 mt-1">Aggregating pure-tone thresholds and speech clarity statistics</span>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-md mx-auto py-8 px-4 text-center">
        <div className="card-premium p-8 bg-white border-[#C65A5A]/20 space-y-4">
          <AlertTriangle className="w-10 h-10 text-[#C65A5A] mx-auto animate-pulse" />
          <h3 className="text-sm font-bold text-[#1C2421] uppercase tracking-wider">Report load error</h3>
          <p className="text-xs text-[#66716D] leading-relaxed">{error}</p>
          <button
            onClick={fetchReport}
            className="w-full py-3 bg-[#F1F4F2] hover:bg-[#DDE5E1] border border-[#DDE5E1] text-[#176B68] rounded-xl text-xs font-bold transition cursor-pointer uppercase tracking-wider"
          >
            Retry analysis
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 space-y-8 animate-fadeIn printable-report text-left">
      
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-[#DDE5E1] pb-5 non-printable">
        <div className="flex items-center gap-3">
          <div className="bg-[#E6F2F0] w-10 h-10 rounded-xl flex items-center justify-center border border-[#DDE5E1]">
            <FileText className="w-5 h-5 text-[#176B68]" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-[#1C2421]">Hearing screening results</h2>
            <p className="text-xs text-[#66716D]">Session ID: {report.sessionId.substring(0, 18)}...</p>
          </div>
        </div>
        <div className="flex gap-2.5 w-full sm:w-auto">
          <button
            onClick={handlePrint}
            className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-5 py-2.5 bg-white hover:bg-[#F1F4F2] border border-[#DDE5E1] rounded-xl text-xs font-bold text-[#1C2421] transition cursor-pointer"
          >
            <Download className="w-4 h-4 text-[#176B68]" />
            <span>Save PDF / Print</span>
          </button>
          <button
            onClick={onRestart}
            className="flex-1 sm:flex-none px-6 py-2.5 bg-[#176B68] hover:bg-[#125754] text-white rounded-xl font-bold shadow-sm transition duration-200 text-xs uppercase tracking-wider cursor-pointer border border-[#176B68]"
          >
            New screening
          </button>
        </div>
      </div>

      {/* Grid: Information Summary & Screening completed status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Demographics Card */}
        <div className="card-premium p-6 bg-white space-y-4">
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-[#66716D] border-b border-[#DDE5E1] pb-2">
            Patient & session parameters
          </h3>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between border-b border-[#F1F4F2] pb-1.5">
              <span className="text-[#66716D]">Age:</span>
              <span className="text-[#1C2421] font-bold">{report.age} years</span>
            </div>
            <div className="flex justify-between border-b border-[#F1F4F2] pb-1.5">
              <span className="text-[#66716D]">Transducer:</span>
              <span className="text-[#1C2421] font-bold truncate max-w-[150px]">{report.headphoneType}</span>
            </div>
            <div className="flex justify-between border-b border-[#F1F4F2] pb-1.5">
              <span className="text-[#66716D]">Device:</span>
              <span className="text-[#1C2421] font-bold truncate max-w-[150px]">{report.deviceType || 'Web Client'}</span>
            </div>
            <div className="flex justify-between border-b border-[#F1F4F2] pb-1.5">
              <span className="text-[#66716D]">System Volume:</span>
              <span className="text-[#176B68] font-bold">Fixed {Math.round((report.fixedSystemVolume ?? 0.5) * 100)}%</span>
            </div>
            <div className="flex flex-col border-b border-[#F1F4F2] pb-1.5">
              <div className="flex justify-between items-center mb-0.5">
                <span className="text-[#66716D] flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#176B68]" />
                  <span>Noise Cancellation:</span>
                </span>
                <span className="bg-[#E6F2F0] text-[#176B68] text-[9px] px-2 py-0.2 rounded font-bold uppercase">
                  {report.noiseCancellationLevel || 'High'}
                </span>
              </div>
              <span className="text-[#1C2421] font-bold text-[11px] leading-tight pl-4.5">
                {report.noiseCancellationProfile || 'Adaptive Acoustic Filter'}
              </span>
            </div>
            <div>
              <span className="text-[#66716D] block mb-1">Symptoms reported:</span>
              <div className="flex flex-wrap gap-1 mt-0.5">
                {report.symptoms.length > 0 ? (
                  report.symptoms.map((sym, idx) => (
                    <span key={idx} className="bg-[#F1F4F2] px-2.5 py-0.5 rounded border border-[#DDE5E1] text-[#1C2421] text-[10px]">
                      {sym}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-400 italic">[None reported]</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Screening Completed Card */}
        <div className="card-premium p-6 bg-white md:col-span-2 space-y-4 relative">
          <div className="flex justify-between items-center border-b border-[#DDE5E1] pb-2">
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-[#66716D]">
              Overall screening status
            </h3>
            <span className="bg-[#3A8065]/10 text-[#3A8065] border border-[#3A8065]/20 text-[9px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider font-mono">
              Screening completed
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-1 text-xs">
            <div className="space-y-3">
              <div>
                <span className="text-[#66716D] text-[10px] font-bold uppercase tracking-wider block">Estimated status</span>
                <span className="text-[#1C2421] font-extrabold text-sm block mt-1 uppercase tracking-wide">{report.overallStatus}</span>
              </div>
              <div>
                <span className="text-[#66716D] text-[10px] font-bold uppercase tracking-wider block">Suggested pattern</span>
                <span className="text-[#176B68] font-extrabold text-sm block mt-1 uppercase tracking-wide">{report.hearingPattern}</span>
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <span className="text-[#66716D] text-[10px] font-bold uppercase tracking-wider block">Diagnostic confidence</span>
                <span className="text-[#1C2421] font-extrabold text-sm block mt-1 uppercase tracking-wide">{report.confidenceLevel}</span>
              </div>
              <div>
                <span className="text-[#66716D] text-[10px] font-bold uppercase tracking-wider block">Data validation</span>
                <span className="text-[#66716D] text-[11px] block mt-1">
                  Response consistency check: {report.dataQuality === 'Reliable' ? 'Passed' : 'Flags detected'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Machine Learning Pathology Classification Layer (hearing_pathology_model.pkl) */}
      {report.pathologyClassification && (
        <div className="card-premium p-6 bg-white space-y-6 border border-[#176B68]/30 shadow-sm relative overflow-hidden">
          {/* Subtle decorative background gradient */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-[#E6F2F0]/40 to-transparent pointer-events-none rounded-full -mr-20 -mt-20" />

          {/* Section Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#DDE5E1] pb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#E6F2F0] border border-[#176B68]/30 flex items-center justify-center text-[#176B68]">
                <Cpu className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-[#1C2421]">
                    AI Pathology Classification Layer
                  </h3>
                  <span className="bg-[#176B68]/10 text-[#176B68] text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border border-[#176B68]/20">
                    hearing_pathology_model.pkl
                  </span>
                </div>
                <p className="text-[11px] text-[#66716D] mt-0.5">
                  Multi-class Random Forest model evaluating air conduction, bone conduction, and air-bone gap dynamics across octaves.
                </p>
              </div>
            </div>

            {/* Overall Model Result Pill */}
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <div className="bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl px-3 py-1.5 text-right">
                <span className="text-[9px] uppercase tracking-wider font-bold text-[#66716D] block">
                  Model Output
                </span>
                <span className="text-xs font-extrabold text-[#176B68] tracking-wide block">
                  {report.pathologyClassification.overallPathology}
                </span>
              </div>
              <div className="bg-[#E6F2F0] border border-[#176B68]/30 rounded-xl px-2.5 py-1.5 text-center">
                <span className="text-[9px] uppercase tracking-wider font-bold text-[#176B68] block">
                  Confidence
                </span>
                <span className="text-xs font-mono font-black text-[#176B68] block">
                  {report.pathologyClassification.overallConfidence}%
                </span>
              </div>
            </div>
          </div>

          {/* Clinical Model Summary Banner */}
          <div className="bg-[#F7F8F6]/80 border border-[#DDE5E1] rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-[#1C2421]">
            <Sparkles className="w-4 h-4 text-[#176B68] shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong className="font-semibold text-[#1C2421]">Classification Rationale: </strong>
              <span className="text-[#66716D]">{report.pathologyClassification.clinicalSummary}</span>
            </div>
          </div>

          {/* Ear-Level Pathology Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Ear Classification Card */}
            {report.pathologyClassification.leftEar ? (
              <div className="border border-[#176B68]/20 rounded-xl p-4 bg-gradient-to-b from-[#E6F2F0]/20 to-transparent space-y-4">
                <div className="flex items-center justify-between border-b border-[#DDE5E1] pb-2">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#176B68]" />
                    <span className="text-xs font-bold text-[#1C2421]">Left Ear Classification</span>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    report.pathologyClassification.leftEar.predictedClass === 'Normal'
                      ? 'bg-[#E6F2F0] text-[#176B68] border-[#176B68]/30'
                      : report.pathologyClassification.leftEar.predictedClass === 'Conductive'
                      ? 'bg-[#FFF9EB] text-[#B87A14] border-[#B87A14]/30'
                      : report.pathologyClassification.leftEar.predictedClass === 'Sensorineural'
                      ? 'bg-[#FDF2F2] text-[#C65A5A] border-[#C65A5A]/30'
                      : 'bg-[#F5F0FF] text-[#7E42D6] border-[#7E42D6]/30'
                  }`}>
                    {report.pathologyClassification.leftEar.predictedClass} ({report.pathologyClassification.leftEar.confidence}%)
                  </span>
                </div>

                {/* Audiological Feature Derivations */}
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Mean AC</span>
                    <span className="text-xs font-bold text-[#1C2421]">
                      {report.pathologyClassification.leftEar.metrics.meanAcDbHl} <span className="text-[8px] font-normal text-slate-400">dB</span>
                    </span>
                  </div>
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Est. BC</span>
                    <span className="text-xs font-bold text-[#1C2421]">
                      {report.pathologyClassification.leftEar.metrics.meanBcDbHl} <span className="text-[8px] font-normal text-slate-400">dB</span>
                    </span>
                  </div>
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Air-Bone Gap</span>
                    <span className="text-xs font-bold text-[#1C2421]">
                      {report.pathologyClassification.leftEar.metrics.meanAirBoneGap} <span className="text-[8px] font-normal text-slate-400">dB</span>
                    </span>
                  </div>
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Speech</span>
                    <span className="text-xs font-bold text-[#176B68]">
                      {report.pathologyClassification.leftEar.metrics.speechScore}%
                    </span>
                  </div>
                </div>

                {/* Class Probabilities Distribution */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#66716D] block">
                    Class Probability Distribution
                  </span>
                  {(['Normal', 'Sensorineural', 'Conductive', 'Mixed'] as const).map((cls) => {
                    const prob = report.pathologyClassification?.leftEar?.probabilities[cls] || 0;
                    const isWinner = report.pathologyClassification?.leftEar?.predictedClass === cls;
                    return (
                      <div key={cls} className="space-y-0.5">
                        <div className="flex justify-between text-[10px]">
                          <span className={isWinner ? 'font-bold text-[#1C2421]' : 'text-[#66716D]'}>
                            {cls}
                          </span>
                          <span className="font-mono text-[10px] text-[#66716D]">
                            {prob}%
                          </span>
                        </div>
                        <div className="w-full bg-[#F1F4F2] h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 rounded-full ${
                              cls === 'Normal'
                                ? 'bg-[#176B68]'
                                : cls === 'Conductive'
                                ? 'bg-[#D9822B]'
                                : cls === 'Sensorineural'
                                ? 'bg-[#C65A5A]'
                                : 'bg-[#7E42D6]'
                            }`}
                            style={{ width: `${Math.max(prob, 2)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Ear Explanation */}
                <p className="text-[11px] text-[#66716D] leading-relaxed border-t border-[#DDE5E1] pt-2">
                  {report.pathologyClassification.leftEar.explanation}
                </p>
              </div>
            ) : (
              <div className="border border-[#DDE5E1] rounded-xl p-4 text-center text-xs text-[#66716D]">
                Left ear data not available.
              </div>
            )}

            {/* Right Ear Classification Card */}
            {report.pathologyClassification.rightEar ? (
              <div className="border border-[#C65A5A]/20 rounded-xl p-4 bg-gradient-to-b from-[#C65A5A]/5 to-transparent space-y-4">
                <div className="flex items-center justify-between border-b border-[#DDE5E1] pb-2">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#C65A5A]" />
                    <span className="text-xs font-bold text-[#1C2421]">Right Ear Classification</span>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    report.pathologyClassification.rightEar.predictedClass === 'Normal'
                      ? 'bg-[#E6F2F0] text-[#176B68] border-[#176B68]/30'
                      : report.pathologyClassification.rightEar.predictedClass === 'Conductive'
                      ? 'bg-[#FFF9EB] text-[#B87A14] border-[#B87A14]/30'
                      : report.pathologyClassification.rightEar.predictedClass === 'Sensorineural'
                      ? 'bg-[#FDF2F2] text-[#C65A5A] border-[#C65A5A]/30'
                      : 'bg-[#F5F0FF] text-[#7E42D6] border-[#7E42D6]/30'
                  }`}>
                    {report.pathologyClassification.rightEar.predictedClass} ({report.pathologyClassification.rightEar.confidence}%)
                  </span>
                </div>

                {/* Audiological Feature Derivations */}
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Mean AC</span>
                    <span className="text-xs font-bold text-[#1C2421]">
                      {report.pathologyClassification.rightEar.metrics.meanAcDbHl} <span className="text-[8px] font-normal text-slate-400">dB</span>
                    </span>
                  </div>
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Est. BC</span>
                    <span className="text-xs font-bold text-[#1C2421]">
                      {report.pathologyClassification.rightEar.metrics.meanBcDbHl} <span className="text-[8px] font-normal text-slate-400">dB</span>
                    </span>
                  </div>
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Air-Bone Gap</span>
                    <span className="text-xs font-bold text-[#1C2421]">
                      {report.pathologyClassification.rightEar.metrics.meanAirBoneGap} <span className="text-[8px] font-normal text-slate-400">dB</span>
                    </span>
                  </div>
                  <div className="bg-white border border-[#DDE5E1] rounded-lg p-2">
                    <span className="text-[9px] text-[#66716D] block font-mono">Speech</span>
                    <span className="text-xs font-bold text-[#C65A5A]">
                      {report.pathologyClassification.rightEar.metrics.speechScore}%
                    </span>
                  </div>
                </div>

                {/* Class Probabilities Distribution */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#66716D] block">
                    Class Probability Distribution
                  </span>
                  {(['Normal', 'Sensorineural', 'Conductive', 'Mixed'] as const).map((cls) => {
                    const prob = report.pathologyClassification?.rightEar?.probabilities[cls] || 0;
                    const isWinner = report.pathologyClassification?.rightEar?.predictedClass === cls;
                    return (
                      <div key={cls} className="space-y-0.5">
                        <div className="flex justify-between text-[10px]">
                          <span className={isWinner ? 'font-bold text-[#1C2421]' : 'text-[#66716D]'}>
                            {cls}
                          </span>
                          <span className="font-mono text-[10px] text-[#66716D]">
                            {prob}%
                          </span>
                        </div>
                        <div className="w-full bg-[#F1F4F2] h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 rounded-full ${
                              cls === 'Normal'
                                ? 'bg-[#176B68]'
                                : cls === 'Conductive'
                                ? 'bg-[#D9822B]'
                                : cls === 'Sensorineural'
                                ? 'bg-[#C65A5A]'
                                : 'bg-[#7E42D6]'
                            }`}
                            style={{ width: `${Math.max(prob, 2)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Ear Explanation */}
                <p className="text-[11px] text-[#66716D] leading-relaxed border-t border-[#DDE5E1] pt-2">
                  {report.pathologyClassification.rightEar.explanation}
                </p>
              </div>
            ) : (
              <div className="border border-[#DDE5E1] rounded-xl p-4 text-center text-xs text-[#66716D]">
                Right ear data not available.
              </div>
            )}
          </div>

          {/* Model Specs Sub-Footer */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-[#DDE5E1] text-[10px] font-mono text-[#66716D]">
            <span>Model: {report.pathologyClassification.modelMetadata.modelName} (18 Features)</span>
            <span>Formula: Air-Bone Gap = AC - BC</span>
            <span>Classes: Normal • Sensorineural • Conductive • Mixed</span>
          </div>
        </div>
      )}

      {/* Grid: Audiogram Graph & Detail Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        
        {/* Custom SVG Audiogram Chart */}
        <div className="card-premium p-6 bg-white">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[#66716D] border-b border-[#DDE5E1] pb-2 mb-4">
            Air-conduction audiogram
          </h3>
          
          <div className="flex gap-4 mb-4 text-[10px] font-mono justify-center">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#176B68]" />
              <span className="text-[#1C2421] font-bold">Left ear (O)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#C65A5A]" />
              <span className="text-[#1C2421] font-bold">Right ear (X)</span>
            </div>
          </div>

          <AudiogramChart leftThresholds={report.leftThresholds} rightThresholds={report.rightThresholds} />
        </div>

        {/* Tabular Freq-wise threshold and speech comparison */}
        <div className="card-premium p-6 bg-white space-y-6">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[#66716D] border-b border-[#DDE5E1] pb-2">
            Threshold measurements summary
          </h3>

          <div className="space-y-5">
            {/* Table */}
            <div className="overflow-x-auto border border-[#DDE5E1] rounded-xl bg-[#F7F8F6]/30">
              <table className="w-full text-left text-xs font-sans">
                <thead>
                  <tr className="bg-[#F1F4F2]/50 text-[#66716D] border-b border-[#DDE5E1] text-[9px] font-bold uppercase tracking-wider">
                    <th className="px-4 py-2.5">Frequency</th>
                    <th className="px-4 py-2.5 text-[#176B68] font-bold">Left ear</th>
                    <th className="px-4 py-2.5 text-[#C65A5A] font-bold">Right ear</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#DDE5E1] text-[#1C2421] font-medium">
                  {[250, 500, 1000, 2000, 4000, 8000].map((freq) => (
                    <tr key={freq} className="hover:bg-[#F7F8F6]/40">
                      <td className="px-4 py-3 font-bold text-[#66716D]">{freq} Hz</td>
                      <td className="px-4 py-3 text-[#176B68]">
                        {report.leftThresholds[freq] !== undefined 
                          ? `Stimulus ${Math.round(report.leftThresholds[freq] * 100)}% (Lvl ${Math.max(1, Math.round(report.leftThresholds[freq] * 12))})` 
                          : 'Not tested'}
                      </td>
                      <td className="px-4 py-3 text-[#C65A5A]">
                        {report.rightThresholds[freq] !== undefined 
                          ? `Stimulus ${Math.round(report.rightThresholds[freq] * 100)}% (Lvl ${Math.max(1, Math.round(report.rightThresholds[freq] * 12))})` 
                          : 'Not tested'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Speech metrics summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-[#DDE5E1] pt-4">
              
              {/* Left Speech */}
              <div className="bg-[#F7F8F6]/40 p-4 rounded-xl border border-[#DDE5E1] flex items-center gap-4">
                <div className="w-11 h-11 rounded-full border border-[#176B68]/20 bg-[#E6F2F0] flex items-center justify-center shrink-0">
                  <span className="text-[#176B68] font-extrabold text-xs font-mono">{report.leftSpeechScore}%</span>
                </div>
                <div>
                  <span className="text-[#66716D] text-[9px] font-bold uppercase tracking-wider block">Left speech accuracy</span>
                  <span className="text-[10px] text-[#1C2421] font-semibold block mt-0.5 truncate max-w-[140px]">{report.leftInterpretation}</span>
                </div>
              </div>

              {/* Right Speech */}
              <div className="bg-[#F7F8F6]/40 p-4 rounded-xl border border-[#DDE5E1] flex items-center gap-4">
                <div className="w-11 h-11 rounded-full border border-[#C65A5A]/20 bg-[#C65A5A]/5 flex items-center justify-center shrink-0">
                  <span className="text-[#C65A5A] font-extrabold text-xs font-mono">{report.rightSpeechScore}%</span>
                </div>
                <div>
                  <span className="text-[#66716D] text-[9px] font-bold uppercase tracking-wider block">Right speech accuracy</span>
                  <span className="text-[10px] text-[#1C2421] font-semibold block mt-0.5 truncate max-w-[140px]">{report.rightInterpretation}</span>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

      {/* Structured Ear-to-Ear Comparison */}
      <div className="card-premium p-6 bg-white space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[#66716D] border-b border-[#DDE5E1] pb-2">
          Left vs. right ear comparison
        </h3>
        <p className="text-xs text-[#1C2421] leading-relaxed font-sans font-light">
          {report.comparison}
        </p>
      </div>

      {/* Rich AI Explanation & Interpretations */}
      <div className="card-premium p-6 bg-white space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[#66716D] border-b border-[#DDE5E1] pb-2 flex items-center gap-1.5">
          <Layers className="w-4 h-4 text-[#176B68]" />
          <span>Full narrative analysis report</span>
        </h3>
        
        {/* Markdown-style custom viewer */}
        <div className="text-xs text-[#1C2421] space-y-4 leading-relaxed whitespace-pre-line font-sans font-light">
          {report.aiExplanation}
        </div>
      </div>

      {/* Screening Interpretation Alert Card */}
      <div className="bg-[#E6F2F0] border border-[#DDE5E1] p-5 rounded-2xl flex gap-3 text-xs leading-relaxed text-[#66716D]">
        <ShieldAlert className="w-5 h-5 text-[#176B68] shrink-0 mt-0.5" />
        <div>
          <strong className="text-[#1C2421] font-bold block mb-1">Screening interpretation:</strong>
          This screening provides an estimated hearing profile based on the responses recorded during the test. It is not a diagnostic hearing examination. Consumer headphones are uncalibrated and actual ear thresholds may vary. For a comprehensive audiological diagnosis or treatment recommendation, please consult a certified audiologist or ENT doctor.
        </div>
      </div>
    </div>
  );
};
