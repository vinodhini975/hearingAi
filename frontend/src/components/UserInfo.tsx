import React, { useState } from 'react';
import { User, ClipboardList, Laptop, Headphones } from 'lucide-react';

interface UserInfoProps {
  onSubmit: (data: {
    age: number;
    symptoms: string[];
    headphoneType: string;
    deviceType: string;
  }) => void;
}

const HEADPHONE_TYPES = [
  'Over-ear headphones',
  'On-ear headphones',
  'In-ear earphones',
  'TWS earbuds',
  'Other'
];

const DEVICE_TYPES = [
  'Laptop',
  'Desktop',
  'Smartphone',
  'Tablet'
];

const SYMPTOM_OPTIONS = [
  { id: 'muffled', label: 'Muffled speech or sounds' },
  { id: 'pain', label: 'Ear pain, fullness, or pressure' },
  { id: 'fullness', label: 'Sensation of fluid inside the ear' },
  { id: 'none', label: 'No significant symptoms (Routine screening)' }
];

export const UserInfo: React.FC<UserInfoProps> = ({ onSubmit }) => {
  const [age, setAge] = useState<string>('');
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [customSymptom, setCustomSymptom] = useState<string>('');
  const [headphoneType, setHeadphoneType] = useState<string>('');
  const [deviceType, setDeviceType] = useState<string>('');
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  const handleSymptomToggle = (label: string) => {
    if (label === 'No significant symptoms (Routine screening)') {
      setSelectedSymptoms([label]);
      return;
    }

    let updated = [...selectedSymptoms].filter(
      (s) => s !== 'No significant symptoms (Routine screening)'
    );

    if (updated.includes(label)) {
      updated = updated.filter((s) => s !== label);
    } else {
      updated.push(label);
    }
    setSelectedSymptoms(updated);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: { [key: string]: string } = {};

    const numAge = parseInt(age, 10);
    if (!age || isNaN(numAge) || numAge <= 0 || numAge > 125) {
      newErrors.age = 'Please enter a valid age (1 - 120).';
    }

    if (!headphoneType) {
      newErrors.headphone = 'Please select your headphone/earphone type.';
    }

    if (!deviceType) {
      newErrors.device = 'Please select your device type.';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    const finalSymptoms = [...selectedSymptoms];
    if (customSymptom.trim()) {
      finalSymptoms.push(customSymptom.trim());
    }
    if (finalSymptoms.length === 0) {
      finalSymptoms.push('No significant symptoms (Routine screening)');
    }

    onSubmit({
      age: numAge,
      symptoms: finalSymptoms,
      headphoneType,
      deviceType
    });
  };

  return (
    <div className="max-w-xl mx-auto py-6 px-4 animate-fadeIn">
      <div className="card-premium p-8 bg-white">
        
        <h2 className="text-2xl font-bold text-[#1C2421] text-center tracking-tight mb-1">
          Patient details
        </h2>
        <p className="text-[#66716D] text-xs text-center mb-8 leading-relaxed">
          Please fill out these simple parameters. All parameters remain local to your session.
        </p>

        <form onSubmit={handleFormSubmit} className="space-y-6">
          {/* Age Section */}
          <div className="space-y-2 text-left">
            <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#66716D]">
              <User className="w-4 h-4 text-[#176B68]" />
              <span>Age (years)</span>
            </label>
            <input
              type="number"
              placeholder="e.g. 35"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="w-full bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl px-4 py-3 text-[#1C2421] focus:outline-none focus:border-[#176B68] transition text-sm"
            />
            {errors.age && <p className="text-xs text-[#C65A5A] font-semibold">{errors.age}</p>}
          </div>

          {/* Symptoms Section */}
          <div className="space-y-3 text-left">
            <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#66716D]">
              <ClipboardList className="w-4 h-4 text-[#176B68]" />
              <span>Current hearing-related symptoms</span>
            </label>
            <div className="grid grid-cols-1 gap-2.5">
              {SYMPTOM_OPTIONS.map((opt) => {
                const isSelected = selectedSymptoms.includes(opt.label);
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleSymptomToggle(opt.label)}
                    className={`flex items-center text-left px-4 py-3 rounded-xl border text-xs font-medium transition cursor-pointer ${
                      isSelected
                        ? 'bg-[#E6F2F0] border-[#176B68] text-[#176B68]'
                        : 'bg-[#F7F8F6] border-[#DDE5E1] text-[#66716D] hover:border-[#176B68]/40'
                    }`}
                  >
                    <span>{opt.label}</span>
                  </button>
                );
              })}
            </div>
            {/* Custom symptom write-in */}
            <input
              type="text"
              placeholder="Other symptoms (optional)"
              value={customSymptom}
              onChange={(e) => setCustomSymptom(e.target.value)}
              className="w-full bg-[#F7F8F6] border border-[#DDE5E1] rounded-xl px-4 py-3 text-xs text-[#1C2421] focus:outline-none focus:border-[#176B68] transition"
            />
          </div>

          {/* Headphones Section */}
          <div className="space-y-3 text-left">
            <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#66716D]">
              <Headphones className="w-4 h-4 text-[#176B68]" />
              <span>Headphone or earphone type</span>
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              {HEADPHONE_TYPES.map((type) => {
                const isSelected = headphoneType === type;
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setHeadphoneType(type)}
                    className={`px-3 py-2.5 rounded-xl border text-xs font-medium text-center transition cursor-pointer ${
                      isSelected
                        ? 'bg-[#E6F2F0] border-[#176B68] text-[#176B68]'
                        : 'bg-[#F7F8F6] border-[#DDE5E1] text-[#66716D] hover:border-[#176B68]/40'
                    }`}
                  >
                    {type}
                  </button>
                );
              })}
            </div>
            {errors.headphone && <p className="text-xs text-[#C65A5A] font-semibold">{errors.headphone}</p>}
          </div>

          {/* Device Section */}
          <div className="space-y-3 text-left">
            <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#66716D]">
              <Laptop className="w-4 h-4 text-[#176B68]" />
              <span>Device being used</span>
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              {DEVICE_TYPES.map((type) => {
                const isSelected = deviceType === type;
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setDeviceType(type)}
                    className={`px-3 py-2.5 rounded-xl border text-xs font-medium text-center transition cursor-pointer ${
                      isSelected
                        ? 'bg-[#E6F2F0] border-[#176B68] text-[#176B68]'
                        : 'bg-[#F7F8F6] border-[#DDE5E1] text-[#66716D] hover:border-[#176B68]/40'
                    }`}
                  >
                    {type}
                  </button>
                );
              })}
            </div>
            {errors.device && <p className="text-xs text-[#C65A5A] font-semibold">{errors.device}</p>}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="w-full py-4 mt-2 bg-[#176B68] hover:bg-[#125754] text-white rounded-xl font-bold transition text-xs uppercase tracking-wider cursor-pointer"
          >
            Continue to instructions
          </button>
        </form>
      </div>
    </div>
  );
};
