import { createClient } from '@/lib/supabase';
import { formatNumber, formatPercent } from '@/lib/utils';
import type { MunicipalityWithStats, ProvinceSummary } from '@/types';
import MunicipalDashboardClient from './dashboard-client';
import {
  Building2,
  TrendingDown,
  TrendingUp,
  Users,
} from 'lucide-react';

export const metadata = {
  title: 'Municipal Intelligence | DSIDE',
  description: 'South African municipal service delivery and unemployment intelligence dashboard.',
};

async function getMunicipalData() {
  const supabase = createClient();

  // Fetch municipalities with joined profile and unemployment data
  const { data: municipalities, error: munError } = await supabase
    .from('municipalities')
    .select(`
      *,
      municipal_profiles!inner(
        profile,
        welfare_measure,
        efficiency_measure,
        opportunity_measure,
        service_delivery_score
      ),
      unemployment_data!inner(
        unemployment_rate,
        youth_unemployment_rate,
        neet_rate
      ),
      pca_results(
        pc1,
        pc2,
        cluster,
        profile_label
      )
    `)
    .order('mun_name');

  if (munError) {
    console.error('Error fetching municipalities:', munError);
    return { municipalities: [], provinceSummaries: [] };
  }

  // Flatten the joined data
  const flatMunicipalities: MunicipalityWithStats[] = (municipalities || []).map((m: Record<string, unknown>) => {
    const profile = (m.municipal_profiles as Record<string, unknown>) || {};
    const unemployment = (m.unemployment_data as Record<string, unknown>) || {};
    const pca = (m.pca_results as Record<string, unknown>) || {};
    return {
      id: m.id as string,
      mun_code: m.mun_code as string,
      mun_name: m.mun_name as string,
      province: m.province as string,
      district: m.district as string,
      latitude: m.latitude as number,
      longitude: m.longitude as number,
      population: m.population as number,
      youth_population: m.youth_population as number,
      unemployment_rate: (unemployment.unemployment_rate as number) || 0,
      youth_unemployment_rate: (unemployment.youth_unemployment_rate as number) || 0,
      neet_rate: (unemployment.neet_rate as number) || 0,
      service_delivery_score: (profile.service_delivery_score as number) || 0,
      profile: (profile.profile as number) || 3,
      profile_label: (pca.profile_label as string) || 'Unknown',
      welfare_measure: (profile.welfare_measure as number) || 0,
      efficiency_measure: (profile.efficiency_measure as number) || 0,
      opportunity_measure: (profile.opportunity_measure as number) || 0,
      cluster: (pca.cluster as number) || 3,
      pc1: (pca.pc1 as number) || 0,
      pc2: (pca.pc2 as number) || 0,
    };
  });

  // Compute province summaries
  const provinceMap = new Map<string, MunicipalityWithStats[]>();
  flatMunicipalities.forEach((m) => {
    const existing = provinceMap.get(m.province) || [];
    existing.push(m);
    provinceMap.set(m.province, existing);
  });

  const provinceSummaries: ProvinceSummary[] = Array.from(provinceMap.entries()).map(
    ([province, muns]) => {
      const avgUnemployment =
        muns.reduce((sum, m) => sum + m.youth_unemployment_rate, 0) / muns.length;
      const avgServiceDelivery =
        muns.reduce((sum, m) => sum + m.service_delivery_score, 0) / muns.length;

      return {
        province,
        avg_unemployment_rate: avgUnemployment,
        avg_service_delivery_score: avgServiceDelivery,
        municipality_count: muns.length,
        trend: avgUnemployment > 40 ? 'up' : avgUnemployment < 25 ? 'down' : 'stable',
      };
    }
  );

  provinceSummaries.sort((a, b) => a.province.localeCompare(b.province));

  return { municipalities: flatMunicipalities, provinceSummaries };
}

export default async function MunicipalDashboardPage() {
  const { municipalities, provinceSummaries } = await getMunicipalData();

  // Compute national stats
  const totalMunicipalities = municipalities.length;
  const avgUnemployment =
    totalMunicipalities > 0
      ? municipalities.reduce((sum, m) => sum + m.youth_unemployment_rate, 0) / totalMunicipalities
      : 0;

  const sorted = [...municipalities].sort(
    (a, b) => a.youth_unemployment_rate - b.youth_unemployment_rate
  );
  const bestMunicipality = sorted[0];
  const worstMunicipality = sorted[sorted.length - 1];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Municipal Intelligence Dashboard
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Service delivery performance and youth unemployment patterns across South Africa&apos;s municipalities.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center gap-2 text-accent">
            <Users className="w-5 h-5" />
          </div>
          <p className="stat-card-value mt-2">{formatPercent(avgUnemployment)}</p>
          <p className="stat-card-label">National Avg. Youth Unemployment</p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-2 text-primary">
            <TrendingDown className="w-5 h-5" />
          </div>
          <p className="stat-card-value mt-2 text-primary">
            {bestMunicipality?.mun_name || 'N/A'}
          </p>
          <p className="stat-card-label">
            Best Performing ({bestMunicipality ? formatPercent(bestMunicipality.youth_unemployment_rate) : 'N/A'})
          </p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-2 text-danger">
            <TrendingUp className="w-5 h-5" />
          </div>
          <p className="stat-card-value mt-2 text-danger">
            {worstMunicipality?.mun_name || 'N/A'}
          </p>
          <p className="stat-card-label">
            Worst Performing ({worstMunicipality ? formatPercent(worstMunicipality.youth_unemployment_rate) : 'N/A'})
          </p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-2 text-secondary-700">
            <Building2 className="w-5 h-5" />
          </div>
          <p className="stat-card-value mt-2">{formatNumber(totalMunicipalities)}</p>
          <p className="stat-card-label">Municipalities Tracked</p>
        </div>
      </div>

      {/* Map + Province table (client interactive part) */}
      <MunicipalDashboardClient
        municipalities={municipalities}
        provinceSummaries={provinceSummaries}
      />
    </div>
  );
}
