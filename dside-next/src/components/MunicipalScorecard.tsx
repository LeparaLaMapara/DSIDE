'use client';

import GaugeChart from './GaugeChart';
import { PROFILE_CONFIG } from '@/lib/utils';
import { formatNumber } from '@/lib/utils';
import type { MunicipalityWithStats } from '@/types';
import { MapPin, Users, Building2 } from 'lucide-react';

interface MunicipalScorecardProps {
  municipality: MunicipalityWithStats;
}

export default function MunicipalScorecard({ municipality }: MunicipalScorecardProps) {
  const profile = PROFILE_CONFIG[municipality.profile] || PROFILE_CONFIG[3];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="stat-card">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {municipality.mun_name}
            </h1>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {municipality.province}
              </span>
              <span className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {municipality.district}
              </span>
              <span className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                Pop. {formatNumber(municipality.population)}
              </span>
            </div>
          </div>
          <div className={`badge ${profile.bgColor} text-sm px-4 py-1.5`}>
            Profile {municipality.profile}: {profile.label}
          </div>
        </div>
      </div>

      {/* Gauge indicators */}
      <div className="stat-card">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-6">
          Performance Scores
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          <GaugeChart value={municipality.welfare_measure} label="Welfare Measure" />
          <GaugeChart value={municipality.efficiency_measure} label="Efficiency Measure" />
          <GaugeChart value={municipality.opportunity_measure} label="Opportunity Measure" />
          <GaugeChart value={municipality.service_delivery_score} label="Service Delivery" />
        </div>
      </div>
    </div>
  );
}
