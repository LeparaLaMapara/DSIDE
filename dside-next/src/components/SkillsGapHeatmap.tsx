'use client';

import { useState } from 'react';
import { cn, interpolateColor, formatNumber } from '@/lib/utils';
import { SA_PROVINCES, SECTORS } from '@/lib/utils';
import type { SkillsGapCell } from '@/types';
import { X } from 'lucide-react';

interface SkillsGapHeatmapProps {
  data: SkillsGapCell[];
  maxGap?: number;
}

export default function SkillsGapHeatmap({ data, maxGap }: SkillsGapHeatmapProps) {
  const [selectedCell, setSelectedCell] = useState<SkillsGapCell | null>(null);

  // Build a lookup map for quick access
  const cellMap = new Map<string, SkillsGapCell>();
  data.forEach((cell) => {
    cellMap.set(`${cell.province}|${cell.sector}`, cell);
  });

  // Calculate the max gap for color scaling
  const computedMaxGap = maxGap || Math.max(...data.map((d) => Math.abs(d.gap)), 1);

  function getCellColor(gap: number): string {
    if (gap === 0) return '#e2e8f0'; // neutral gray
    if (gap > 0) {
      // Demand > Supply: red (gap = bad, needs workers)
      const t = Math.min(gap / computedMaxGap, 1);
      return interpolateColor(0.5 + t * 0.5);
    } else {
      // Supply > Demand: green (oversupplied)
      const t = Math.min(Math.abs(gap) / computedMaxGap, 1);
      return interpolateColor(0.5 - t * 0.5);
    }
  }

  return (
    <div className="space-y-4">
      {/* Heatmap grid */}
      <div className="overflow-x-auto scrollbar-thin">
        <div className="min-w-[800px]">
          {/* Header row */}
          <div className="grid" style={{ gridTemplateColumns: `160px repeat(${SECTORS.length}, 1fr)` }}>
            <div className="p-2 text-xs font-medium text-slate-500" />
            {SECTORS.map((sector) => (
              <div
                key={sector}
                className="p-2 text-xs font-medium text-slate-700 dark:text-slate-300 text-center"
              >
                {sector}
              </div>
            ))}
          </div>

          {/* Data rows */}
          {SA_PROVINCES.map((province) => (
            <div
              key={province}
              className="grid"
              style={{ gridTemplateColumns: `160px repeat(${SECTORS.length}, 1fr)` }}
            >
              <div className="p-2 text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center">
                {province}
              </div>
              {SECTORS.map((sector) => {
                const cell = cellMap.get(`${province}|${sector}`);
                const gap = cell?.gap ?? 0;
                const bgColor = getCellColor(gap);
                const isSelected =
                  selectedCell?.province === province && selectedCell?.sector === sector;

                return (
                  <button
                    key={`${province}-${sector}`}
                    className={cn(
                      'p-2 text-xs font-semibold text-center border border-white/50 rounded-sm transition-all duration-150 cursor-pointer',
                      'hover:ring-2 hover:ring-accent/40 hover:z-10',
                      isSelected && 'ring-2 ring-accent z-10'
                    )}
                    style={{ backgroundColor: bgColor, color: Math.abs(gap) > computedMaxGap * 0.5 ? '#fff' : '#1e293b' }}
                    onClick={() => setSelectedCell(cell || null)}
                    aria-label={`${province}, ${sector}: gap of ${gap}`}
                  >
                    {gap > 0 ? `+${formatNumber(gap)}` : formatNumber(gap)}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Color legend */}
      <div className="flex items-center justify-center gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm" style={{ backgroundColor: interpolateColor(0) }} />
          <span>Oversupplied</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm bg-slate-200" />
          <span>Balanced</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm" style={{ backgroundColor: interpolateColor(1) }} />
          <span>Large gap</span>
        </div>
      </div>

      {/* Detail panel */}
      {selectedCell && (
        <div className="stat-card animate-fade-in relative">
          <button
            onClick={() => setSelectedCell(null)}
            className="absolute top-3 right-3 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
            aria-label="Close detail panel"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {selectedCell.province} - {selectedCell.sector}
          </h3>
          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <p className="text-xs text-slate-500">Demand</p>
              <p className="text-lg font-bold text-accent">{formatNumber(selectedCell.demand)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Supply</p>
              <p className="text-lg font-bold text-primary">{formatNumber(selectedCell.supply)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Net Gap</p>
              <p className={cn('text-lg font-bold', selectedCell.gap > 0 ? 'text-danger' : 'text-primary')}>
                {selectedCell.gap > 0 ? '+' : ''}{formatNumber(selectedCell.gap)}
              </p>
            </div>
          </div>
          {selectedCell.top_occupations.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-slate-500 mb-1">Top Occupations in Demand</p>
              <div className="flex flex-wrap gap-1.5">
                {selectedCell.top_occupations.map((occ) => (
                  <span key={occ} className="badge badge-accent">{occ}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
