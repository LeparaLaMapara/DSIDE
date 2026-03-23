'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface SeriesConfig {
  key: string;
  label: string;
  color: string;
  dashed?: boolean;
}

interface TrendChartProps {
  data: Record<string, unknown>[];
  series: SeriesConfig[];
  xKey: string;
  xLabel?: string;
  yLabel?: string;
  height?: number;
  yDomain?: [number, number];
  formatY?: (value: number) => string;
}

export default function TrendChart({
  data,
  series,
  xKey,
  xLabel,
  yLabel,
  height = 300,
  yDomain,
  formatY,
}: TrendChartProps) {
  return (
    <div className="chart-container" role="img" aria-label={`Trend chart showing ${series.map(s => s.label).join(', ')}`}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12 }}
            label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -5, fontSize: 12 } : undefined}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            domain={yDomain}
            tickFormatter={formatY}
            label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 12 } : undefined}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgb(var(--card))',
              border: '1px solid rgb(var(--border))',
              borderRadius: '8px',
              fontSize: '13px',
            }}
            formatter={(value: number, name: string) => {
              const label = series.find(s => s.key === name)?.label || name;
              const formatted = formatY ? formatY(value) : `${value.toFixed(1)}%`;
              return [formatted, label];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px' }}
            formatter={(value: string) => {
              const s = series.find(s => s.key === value);
              return s?.label || value;
            }}
          />
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dashed ? '5 5' : undefined}
              dot={{ r: 3, strokeWidth: 2 }}
              activeDot={{ r: 5, strokeWidth: 2 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
