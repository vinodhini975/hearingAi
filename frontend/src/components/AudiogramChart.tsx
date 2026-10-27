import React from 'react';

interface AudiogramChartProps {
  leftThresholds: { [freq: number]: number };
  rightThresholds: { [freq: number]: number };
}

const FREQUENCIES = [250, 500, 1000, 2000, 4000, 8000];

export const AudiogramChart: React.FC<AudiogramChartProps> = ({ leftThresholds, rightThresholds }) => {
  // Chart dimensions
  const width = 540;
  const height = 350;
  const paddingLeft = 55;
  const paddingRight = 30;
  const paddingTop = 40;
  const paddingBottom = 45;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  // X coordinate mapping (even spacing for frequencies)
  const getX = (freq: number) => {
    const index = FREQUENCIES.indexOf(freq);
    if (index === -1) return paddingLeft;
    return paddingLeft + (index / (FREQUENCIES.length - 1)) * chartWidth;
  };

  // Y coordinate mapping (0% is at the top, 100% is at the bottom)
  const getY = (level: number) => {
    const clampedLevel = Math.max(0, Math.min(1, level));
    return paddingTop + clampedLevel * chartHeight;
  };

  // Generate path lines
  const getPathData = (thresholds: { [freq: number]: number }) => {
    const points = FREQUENCIES.filter(f => thresholds[f] !== undefined).map(f => ({
      x: getX(f),
      y: getY(thresholds[f])
    }));

    if (points.length < 2) return '';
    return points.reduce((path, p, i) => {
      return i === 0 ? `M ${p.x} ${p.y}` : `${path} L ${p.x} ${p.y}`;
    }, '');
  };

  const leftPath = getPathData(leftThresholds);
  const rightPath = getPathData(rightThresholds);

  return (
    <div className="flex flex-col items-center w-full bg-white select-none">
      <div className="w-full relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto text-[#66716D]">
          {/* Grid Background (Clean warm grey) */}
          <rect
            x={paddingLeft}
            y={paddingTop}
            width={chartWidth}
            height={chartHeight}
            fill="#F7F8F6"
            stroke="#DDE5E1"
            strokeWidth="1.5"
          />

          {/* Horizontal Grid Lines & Y-Axis Labels (0% to 100% stimulus intensity in 10% steps) */}
          {Array.from({ length: 11 }).map((_, i) => {
            const pct = i * 10;
            const y = getY(pct / 100);
            return (
              <g key={`y-grid-${i}`}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={width - paddingRight}
                  y2={y}
                  stroke="#DDE5E1"
                  strokeWidth="0.75"
                  strokeDasharray="2,2"
                />
                <text
                  x={paddingLeft - 10}
                  y={y + 3.5}
                  textAnchor="end"
                  className="text-[9px] font-medium fill-[#66716D]"
                >
                  {pct}%
                </text>
              </g>
            );
          })}

          {/* Vertical Grid Lines & X-Axis Labels */}
          {FREQUENCIES.map((freq, i) => {
            const x = getX(freq);
            return (
              <g key={`x-grid-${i}`}>
                <line
                  x1={x}
                  y1={paddingTop}
                  x2={x}
                  y2={height - paddingBottom}
                  stroke="#DDE5E1"
                  strokeWidth="1"
                />
                <text
                  x={x}
                  y={height - paddingBottom + 16}
                  textAnchor="middle"
                  className="text-[10px] font-semibold fill-[#66716D]"
                >
                  {freq >= 1000 ? `${freq / 1000}k` : freq} Hz
                </text>
              </g>
            );
          })}

          {/* Y-Axis Title */}
          <text
            transform={`rotate(-90 ${paddingLeft - 40} ${paddingTop + chartHeight / 2})`}
            x={paddingLeft - 40}
            y={paddingTop + chartHeight / 2}
            textAnchor="middle"
            className="text-[8.5px] font-bold tracking-wider fill-[#66716D] uppercase"
          >
            Software Stimulus Intensity Level (%)
          </text>

          {/* X-Axis Title */}
          <text
            x={paddingLeft + chartWidth / 2}
            y={height - 8}
            textAnchor="middle"
            className="text-[9px] font-bold tracking-wider fill-[#66716D] uppercase"
          >
            Frequency (Hz)
          </text>

          {/* Right Ear Line & Symbols (Red Circle O) */}
          {rightPath && (
            <>
              <path
                d={rightPath}
                fill="none"
                stroke="#C65A5A"
                strokeWidth="2.5"
              />
              {FREQUENCIES.filter(f => rightThresholds[f] !== undefined).map(f => {
                const cx = getX(f);
                const cy = getY(rightThresholds[f]);
                return (
                  <circle
                    key={`right-point-${f}`}
                    cx={cx}
                    cy={cy}
                    r="4.5"
                    fill="none"
                    stroke="#C65A5A"
                    strokeWidth="2.5"
                    className="cursor-pointer"
                  >
                    <title>{`Right Ear: ${f} Hz @ ${Math.round(rightThresholds[f] * 100)}%`}</title>
                  </circle>
                );
              })}
            </>
          )}

          {/* Left Ear Line & Symbols (Blue/Teal Cross X) */}
          {leftPath && (
            <>
              <path
                d={leftPath}
                fill="none"
                stroke="#176B68"
                strokeWidth="2.5"
                strokeDasharray="4,4"
              />
              {FREQUENCIES.filter(f => leftThresholds[f] !== undefined).map(f => {
                const cx = getX(f);
                const cy = getY(leftThresholds[f]);
                return (
                  <g key={`left-point-${f}`} className="cursor-pointer">
                    <title>{`Left Ear: ${f} Hz @ ${Math.round(leftThresholds[f] * 100)}%`}</title>
                    <line x1={cx - 4.5} y1={cy - 4.5} x2={cx + 4.5} y2={cy + 4.5} stroke="#176B68" strokeWidth="2.5" />
                    <line x1={cx + 4.5} y1={cy - 4.5} x2={cx - 4.5} y2={cy + 4.5} stroke="#176B68" strokeWidth="2.5" />
                  </g>
                );
              })}
            </>
          )}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex gap-6 mt-3 text-xs font-semibold">
        <div className="flex items-center gap-2 text-[#C65A5A]">
          <svg width="14" height="14" className="inline-block">
            <line x1="0" y1="7" x2="14" y2="7" stroke="#C65A5A" strokeWidth="2" />
            <circle cx="7" cy="7" r="3.5" fill="none" stroke="#C65A5A" strokeWidth="2" />
          </svg>
          <span className="font-sans text-[#66716D]">Right Ear (Solid red circle)</span>
        </div>
        <div className="flex items-center gap-2 text-[#176B68]">
          <svg width="14" height="14" className="inline-block">
            <line x1="0" y1="7" x2="14" y2="7" stroke="#176B68" strokeWidth="2" strokeDasharray="3,2" />
            <line x1="4" y1="4" x2="10" y2="10" stroke="#176B68" strokeWidth="2" />
            <line x1="10" y1="4" x2="4" y2="10" stroke="#176B68" strokeWidth="2" />
          </svg>
          <span className="font-sans text-[#66716D]">Left Ear (Dashed teal cross)</span>
        </div>
      </div>
    </div>
  );
};
