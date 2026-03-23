'use client';

import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts';
import { getScoreColor } from '@/lib/utils';

interface GaugeChartProps {
  value: number;
  label: string;
  maxValue?: number;
}

export default function GaugeChart({ value, label, maxValue = 100 }: GaugeChartProps) {
  const percentage = Math.round((value / maxValue) * 100);
  const color = getScoreColor(percentage);

  const data = [
    {
      name: label,
      value: percentage,
      fill: color,
    },
  ];

  return (
    <div className="gauge-container" role="img" aria-label={`${label}: ${percentage}%`}>
      <div className="relative w-32 h-32 sm:w-36 sm:h-36">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="70%"
            outerRadius="90%"
            barSize={10}
            data={data}
            startAngle={210}
            endAngle={-30}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            <RadialBar
              background={{ fill: '#e2e8f0' }}
              dataKey="value"
              cornerRadius={5}
              angleAxisId={0}
            />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold" style={{ color }}>
            {percentage}%
          </span>
        </div>
      </div>
      <span className="mt-2 text-sm font-medium text-slate-600 dark:text-slate-400 text-center">
        {label}
      </span>
    </div>
  );
}
