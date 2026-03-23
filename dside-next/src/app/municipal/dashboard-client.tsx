'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { cn, formatPercent } from '@/lib/utils';
import type { MunicipalityWithStats, ProvinceSummary } from '@/types';
import { ArrowUpDown, ChevronRight, Map as MapIcon } from 'lucide-react';

// Dynamic import for Leaflet (SSR incompatible)
const MunicipalMap = dynamic(() => import('@/components/MunicipalMap'), {
  ssr: false,
  loading: () => (
    <div className="map-container flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-500 mt-3">Loading map...</p>
      </div>
    </div>
  ),
});

type ColorMetric = 'unemployment' | 'service_delivery' | 'neet';
type SortKey = 'province' | 'avg_unemployment_rate' | 'avg_service_delivery_score' | 'municipality_count';

interface DashboardClientProps {
  municipalities: MunicipalityWithStats[];
  provinceSummaries: ProvinceSummary[];
}

export default function MunicipalDashboardClient({
  municipalities,
  provinceSummaries,
}: DashboardClientProps) {
  const router = useRouter();
  const [colorMetric, setColorMetric] = useState<ColorMetric>('unemployment');
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('province');
  const [sortAsc, setSortAsc] = useState(true);

  const handleMunicipalityClick = useCallback(
    (munCode: string) => {
      router.push(`/municipal/scorecard?mun_code=${munCode}`);
    },
    [router]
  );

  const handleProvinceClick = (province: string) => {
    setSelectedProvince((prev) => (prev === province ? null : province));
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sortedProvinces = [...provinceSummaries].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    return sortAsc
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number);
  });

  const trendIcon = (trend: string) => {
    if (trend === 'up') return <span className="text-danger text-xs font-medium">Worsening</span>;
    if (trend === 'down') return <span className="text-primary text-xs font-medium">Improving</span>;
    return <span className="text-secondary-700 text-xs font-medium">Stable</span>;
  };

  return (
    <div className="space-y-6">
      {/* Map section */}
      <div className="stat-card p-0 overflow-hidden">
        {/* Map controls */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <MapIcon className="w-4 h-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Municipality Map
            </span>
            {selectedProvince && (
              <button
                onClick={() => setSelectedProvince(null)}
                className="badge badge-accent text-xs cursor-pointer hover:opacity-80"
              >
                {selectedProvince} &times;
              </button>
            )}
          </div>
          <div className="flex gap-1">
            {(['unemployment', 'service_delivery', 'neet'] as ColorMetric[]).map((metric) => (
              <button
                key={metric}
                onClick={() => setColorMetric(metric)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                  colorMetric === metric
                    ? 'bg-accent text-white'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'
                )}
              >
                {metric === 'unemployment'
                  ? 'Unemployment'
                  : metric === 'service_delivery'
                    ? 'Service Delivery'
                    : 'NEET Rate'}
              </button>
            ))}
          </div>
        </div>

        <div className="relative">
          <MunicipalMap
            municipalities={municipalities}
            colorMetric={colorMetric}
            selectedProvince={selectedProvince}
            onMunicipalityClick={handleMunicipalityClick}
          />
        </div>
      </div>

      {/* Province breakdown table */}
      <div className="stat-card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Province Breakdown
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Click a row to filter the map to that province.
          </p>
        </div>
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full text-sm" role="table" aria-label="Province breakdown of unemployment and service delivery">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <SortableHeader
                  label="Province"
                  sortKey="province"
                  currentSort={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <SortableHeader
                  label="Avg. Youth Unemployment"
                  sortKey="avg_unemployment_rate"
                  currentSort={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <SortableHeader
                  label="Avg. Service Delivery"
                  sortKey="avg_service_delivery_score"
                  currentSort={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <SortableHeader
                  label="Municipalities"
                  sortKey="municipality_count"
                  currentSort={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Trend
                </th>
                <th className="px-4 py-3 w-8" />
              </tr>
            </thead>
            <tbody>
              {sortedProvinces.map((prov) => (
                <tr
                  key={prov.province}
                  onClick={() => handleProvinceClick(prov.province)}
                  className={cn(
                    'border-b border-slate-100 dark:border-slate-700/50 cursor-pointer transition-colors',
                    selectedProvince === prov.province
                      ? 'bg-accent/5'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800/30'
                  )}
                >
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                    {prov.province}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'font-semibold',
                        prov.avg_unemployment_rate > 40
                          ? 'text-danger'
                          : prov.avg_unemployment_rate > 25
                            ? 'text-secondary-700'
                            : 'text-primary'
                      )}
                    >
                      {formatPercent(prov.avg_unemployment_rate)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 max-w-24 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${Math.min(prov.avg_service_delivery_score, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400 w-12 text-right">
                        {prov.avg_service_delivery_score.toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                    {prov.municipality_count}
                  </td>
                  <td className="px-4 py-3">{trendIcon(prov.trend)}</td>
                  <td className="px-4 py-3">
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SortableHeader({
  label,
  sortKey,
  currentSort,
  asc,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  currentSort: SortKey;
  asc: boolean;
  onClick: (key: SortKey) => void;
}) {
  const isActive = currentSort === sortKey;
  return (
    <th className="px-4 py-3 text-left">
      <button
        onClick={() => onClick(sortKey)}
        className="flex items-center gap-1 text-xs font-medium text-slate-500 uppercase tracking-wider hover:text-slate-700 dark:hover:text-slate-300"
      >
        {label}
        <ArrowUpDown
          className={cn('w-3 h-3', isActive ? 'text-accent' : 'text-slate-300')}
        />
        {isActive && (
          <span className="text-[10px] text-accent">{asc ? 'ASC' : 'DESC'}</span>
        )}
      </button>
    </th>
  );
}
