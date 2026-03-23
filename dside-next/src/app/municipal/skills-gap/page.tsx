'use client';

import { useEffect, useState, useCallback } from 'react';
import { createBrowserClient } from '@/lib/supabase';
import { cn, formatNumber, formatPercent, formatCurrency, SA_PROVINCES, SECTORS } from '@/lib/utils';
import type { SkillsGapCell, TrainingProgram } from '@/types';
import SkillsGapHeatmap from '@/components/SkillsGapHeatmap';
import {
  Zap,
  AlertTriangle,
  Target,
  Loader2,
  GraduationCap,
  TrendingUp,
  Clock,
} from 'lucide-react';

interface SkillsGapSummary {
  biggest_opportunity: { province: string; sector: string; gap: number } | null;
  most_oversupplied: { province: string; sector: string; surplus: number } | null;
  quickest_win: { sector: string; avg_training_months: number; employment_rate: number } | null;
}

export default function SkillsGapPage() {
  const [heatmapData, setHeatmapData] = useState<SkillsGapCell[]>([]);
  const [trainingAlignment, setTrainingAlignment] = useState<TrainingProgram[]>([]);
  const [summary, setSummary] = useState<SkillsGapSummary>({
    biggest_opportunity: null,
    most_oversupplied: null,
    quickest_win: null,
  });
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const supabase = createBrowserClient();

      // Fetch skills gap data aggregated by province and sector
      const { data: skillsData } = await supabase
        .from('skills_gaps')
        .select('*')
        .order('province')
        .order('sector');

      // Aggregate into cells: group by province + sector
      const cellMap = new Map<string, SkillsGapCell>();

      (skillsData || []).forEach((sg: Record<string, unknown>) => {
        const key = `${sg.province}|${sg.sector}`;
        const existing = cellMap.get(key);
        if (existing) {
          existing.demand += (sg.demand_count as number) || 0;
          existing.supply += (sg.supply_count as number) || 0;
          existing.gap += (sg.gap as number) || 0;
          if ((sg.occupation as string) && existing.top_occupations.length < 3) {
            existing.top_occupations.push(sg.occupation as string);
          }
        } else {
          cellMap.set(key, {
            province: sg.province as string,
            sector: sg.sector as string,
            demand: (sg.demand_count as number) || 0,
            supply: (sg.supply_count as number) || 0,
            gap: (sg.gap as number) || 0,
            top_occupations: (sg.occupation as string) ? [sg.occupation as string] : [],
          });
        }
      });

      const cells = Array.from(cellMap.values());
      setHeatmapData(cells);

      // Compute summary stats
      const positiveCells = cells.filter((c) => c.gap > 0);
      const negativeCells = cells.filter((c) => c.gap < 0);

      const biggestOpp = positiveCells.sort((a, b) => b.gap - a.gap)[0] || null;
      const mostOverSup = negativeCells.sort((a, b) => a.gap - b.gap)[0] || null;

      setSummary({
        biggest_opportunity: biggestOpp
          ? { province: biggestOpp.province, sector: biggestOpp.sector, gap: biggestOpp.gap }
          : null,
        most_oversupplied: mostOverSup
          ? { province: mostOverSup.province, sector: mostOverSup.sector, surplus: Math.abs(mostOverSup.gap) }
          : null,
        quickest_win: null, // Will be computed from training data
      });

      // Fetch training programs for alignment table
      const { data: trainingData } = await supabase
        .from('training_programs')
        .select('*')
        .order('employment_rate', { ascending: false })
        .limit(20);

      const programs = (trainingData || []) as TrainingProgram[];
      setTrainingAlignment(programs);

      // Find quickest win
      if (programs.length > 0) {
        // Group by sector, find shortest average duration with highest employment rate
        const sectorStats = new Map<string, { totalMonths: number; totalEmployment: number; count: number }>();
        programs.forEach((p) => {
          const existing = sectorStats.get(p.sector) || { totalMonths: 0, totalEmployment: 0, count: 0 };
          existing.totalMonths += p.duration_months;
          existing.totalEmployment += p.employment_rate;
          existing.count += 1;
          sectorStats.set(p.sector, existing);
        });

        let quickestWin: { sector: string; avg_training_months: number; employment_rate: number } | null = null;
        let bestScore = 0;

        sectorStats.forEach((stats, sector) => {
          const avgMonths = stats.totalMonths / stats.count;
          const avgEmployment = stats.totalEmployment / stats.count;
          // Score = employment rate / duration (higher is better)
          const score = avgEmployment / Math.max(avgMonths, 1);
          if (score > bestScore) {
            bestScore = score;
            quickestWin = { sector, avg_training_months: Math.round(avgMonths), employment_rate: avgEmployment };
          }
        });

        setSummary((prev) => ({ ...prev, quickest_win: quickestWin }));
      }
    } catch (err) {
      console.error('Error fetching skills gap data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="skeleton h-10 w-64 rounded" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-32 rounded-xl" />
          ))}
        </div>
        <div className="skeleton h-96 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Skills Gap Analysis
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Mapping the gap between labour demand and skills supply across South Africa&apos;s provinces and sectors.
          Red cells indicate large unmet demand; green cells indicate adequate or excess supply.
        </p>
      </div>

      {/* Summary panel */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Biggest Opportunity */}
        <div className="stat-card border-l-4 border-l-primary">
          <div className="flex items-center gap-2 text-primary mb-2">
            <Target className="w-5 h-5" />
            <h3 className="text-sm font-semibold">Biggest Opportunity</h3>
          </div>
          {summary.biggest_opportunity ? (
            <>
              <p className="text-lg font-bold text-slate-900 dark:text-slate-100">
                {summary.biggest_opportunity.sector}
              </p>
              <p className="text-sm text-slate-500">
                in {summary.biggest_opportunity.province}
              </p>
              <p className="text-xs text-primary mt-1">
                Gap: {formatNumber(summary.biggest_opportunity.gap)} positions
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-400">No data available</p>
          )}
        </div>

        {/* Most Oversupplied */}
        <div className="stat-card border-l-4 border-l-secondary">
          <div className="flex items-center gap-2 text-secondary-700 mb-2">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="text-sm font-semibold">Most Oversupplied</h3>
          </div>
          {summary.most_oversupplied ? (
            <>
              <p className="text-lg font-bold text-slate-900 dark:text-slate-100">
                {summary.most_oversupplied.sector}
              </p>
              <p className="text-sm text-slate-500">
                in {summary.most_oversupplied.province}
              </p>
              <p className="text-xs text-secondary-700 mt-1">
                Surplus: {formatNumber(summary.most_oversupplied.surplus)} workers
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-400">No data available</p>
          )}
        </div>

        {/* Quickest Win */}
        <div className="stat-card border-l-4 border-l-accent">
          <div className="flex items-center gap-2 text-accent mb-2">
            <Zap className="w-5 h-5" />
            <h3 className="text-sm font-semibold">Quickest Win</h3>
          </div>
          {summary.quickest_win ? (
            <>
              <p className="text-lg font-bold text-slate-900 dark:text-slate-100">
                {summary.quickest_win.sector}
              </p>
              <p className="text-sm text-slate-500">
                Avg. {summary.quickest_win.avg_training_months} months training
              </p>
              <p className="text-xs text-accent mt-1">
                {summary.quickest_win.employment_rate.toFixed(0)}% employment rate after training
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-400">No data available</p>
          )}
        </div>
      </div>

      {/* Heatmap */}
      <div className="stat-card">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Province &times; Sector Skills Gap Matrix
        </h2>
        <p className="text-xs text-slate-400 mb-4">
          Positive values indicate unmet demand (skills shortage). Negative values indicate oversupply. Click a cell for details.
        </p>
        {heatmapData.length > 0 ? (
          <SkillsGapHeatmap data={heatmapData} />
        ) : (
          <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
            No skills gap data available. Data will appear once the ingestion pipeline has run.
          </div>
        )}
      </div>

      {/* Training alignment table */}
      {trainingAlignment.length > 0 && (
        <div className="stat-card">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2 mb-4">
            <GraduationCap className="w-5 h-5 text-accent" />
            Training Program Alignment
          </h2>
          <p className="text-xs text-slate-400 mb-4">
            Training programs matched to the highest-demand sectors. Sorted by post-training employment rate.
          </p>
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-sm" role="table" aria-label="Training programs aligned to skills gaps">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Program
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Sector
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Duration
                    </span>
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Cost
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      Employment Rate
                    </span>
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Province
                  </th>
                </tr>
              </thead>
              <tbody>
                {trainingAlignment.map((tp) => (
                  <tr
                    key={tp.id}
                    className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-900 dark:text-slate-100">
                          {tp.name}
                        </p>
                        <p className="text-xs text-slate-500">{tp.provider}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="badge badge-accent">{tp.sector}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                      {tp.duration_months} months
                    </td>
                    <td className="px-4 py-3">
                      {tp.is_free ? (
                        <span className="badge badge-primary font-semibold">FREE</span>
                      ) : (
                        <span className="text-slate-600 dark:text-slate-400">
                          {formatCurrency(tp.cost)}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 max-w-16 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className={cn(
                              'h-full rounded-full transition-all',
                              tp.employment_rate > 70
                                ? 'bg-primary'
                                : tp.employment_rate > 40
                                  ? 'bg-secondary'
                                  : 'bg-danger'
                            )}
                            style={{ width: `${Math.min(tp.employment_rate, 100)}%` }}
                          />
                        </div>
                        <span
                          className={cn(
                            'text-xs font-semibold w-10 text-right',
                            tp.employment_rate > 70
                              ? 'text-primary'
                              : tp.employment_rate > 40
                                ? 'text-secondary-700'
                                : 'text-danger'
                          )}
                        >
                          {tp.employment_rate.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {tp.province}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
