'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, useCallback, Suspense } from 'react';
import { createBrowserClient } from '@/lib/supabase';
import { formatNumber, formatCurrency, formatPercent, cn, PROFILE_CONFIG } from '@/lib/utils';
import type {
  MunicipalityWithStats,
  MunicipalFinance,
  UnemploymentData,
  SkillsGap,
  TrainingProgram,
} from '@/types';
import MunicipalScorecard from '@/components/MunicipalScorecard';
import TrendChart from '@/components/TrendChart';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Sparkles,
  TrendingUp,
  GraduationCap,
  Building2,
  ArrowRight,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import Link from 'next/link';

function ScorecardContent() {
  const searchParams = useSearchParams();
  const munCode = searchParams.get('mun_code');

  const [municipality, setMunicipality] = useState<MunicipalityWithStats | null>(null);
  const [finance, setFinance] = useState<MunicipalFinance[]>([]);
  const [unemployment, setUnemployment] = useState<UnemploymentData[]>([]);
  const [skillsGaps, setSkillsGaps] = useState<SkillsGap[]>([]);
  const [similarMunicipalities, setSimilarMunicipalities] = useState<MunicipalityWithStats[]>([]);
  const [trainingPrograms, setTrainingPrograms] = useState<TrainingProgram[]>([]);
  const [aiBrief, setAiBrief] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!munCode) {
      setError('No municipality code provided. Please navigate from the dashboard.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const supabase = createBrowserClient();

      // Fetch municipality data with profile and PCA
      const { data: munData, error: munError } = await supabase
        .from('municipalities')
        .select(`
          *,
          municipal_profiles!inner(profile, welfare_measure, efficiency_measure, opportunity_measure, service_delivery_score),
          unemployment_data!inner(unemployment_rate, youth_unemployment_rate, neet_rate),
          pca_results(pc1, pc2, cluster, profile_label)
        `)
        .eq('mun_code', munCode)
        .single();

      if (munError || !munData) {
        setError(`Municipality not found: ${munCode}`);
        setLoading(false);
        return;
      }

      const profile = (munData.municipal_profiles as Record<string, unknown>) || {};
      const unemp = (munData.unemployment_data as Record<string, unknown>) || {};
      const pca = (munData.pca_results as Record<string, unknown>) || {};

      const flatMun: MunicipalityWithStats = {
        id: munData.id,
        mun_code: munData.mun_code,
        mun_name: munData.mun_name,
        province: munData.province,
        district: munData.district,
        latitude: munData.latitude,
        longitude: munData.longitude,
        population: munData.population,
        youth_population: munData.youth_population,
        unemployment_rate: (unemp.unemployment_rate as number) || 0,
        youth_unemployment_rate: (unemp.youth_unemployment_rate as number) || 0,
        neet_rate: (unemp.neet_rate as number) || 0,
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
      setMunicipality(flatMun);

      // Fetch financial data
      const { data: finData } = await supabase
        .from('municipal_finances')
        .select('*')
        .eq('mun_code', munCode)
        .order('financial_year', { ascending: true });
      setFinance(finData || []);

      // Fetch unemployment trends
      const { data: unempTrends } = await supabase
        .from('unemployment_data')
        .select('*')
        .eq('mun_code', munCode)
        .order('year', { ascending: true })
        .order('quarter', { ascending: true });
      setUnemployment(unempTrends || []);

      // Fetch skills gaps for the district
      const { data: skillsData } = await supabase
        .from('skills_gaps')
        .select('*')
        .eq('province', munData.province)
        .order('gap', { ascending: false })
        .limit(10);
      setSkillsGaps(skillsData || []);

      // Fetch training programs for the province
      const { data: trainingData } = await supabase
        .from('training_programs')
        .select('*')
        .eq('province', munData.province)
        .order('employment_rate', { ascending: false })
        .limit(5);
      setTrainingPrograms(trainingData || []);

      // Fetch similar municipalities (same cluster)
      const cluster = (pca.cluster as number) || 3;
      const { data: similarData } = await supabase
        .from('municipalities')
        .select(`
          *,
          municipal_profiles!inner(profile, welfare_measure, efficiency_measure, opportunity_measure, service_delivery_score),
          unemployment_data!inner(unemployment_rate, youth_unemployment_rate, neet_rate),
          pca_results(pc1, pc2, cluster, profile_label)
        `)
        .neq('mun_code', munCode)
        .limit(20);

      // Filter by same cluster in JS since we can't join-filter easily
      const similar = (similarData || [])
        .filter((s: Record<string, unknown>) => {
          const sPca = (s.pca_results as Record<string, unknown>) || {};
          return (sPca.cluster as number) === cluster;
        })
        .slice(0, 5)
        .map((s: Record<string, unknown>) => {
          const sProfile = (s.municipal_profiles as Record<string, unknown>) || {};
          const sUnemp = (s.unemployment_data as Record<string, unknown>) || {};
          const sPca = (s.pca_results as Record<string, unknown>) || {};
          return {
            id: s.id as string,
            mun_code: s.mun_code as string,
            mun_name: s.mun_name as string,
            province: s.province as string,
            district: s.district as string,
            latitude: s.latitude as number,
            longitude: s.longitude as number,
            population: s.population as number,
            youth_population: s.youth_population as number,
            unemployment_rate: (sUnemp.unemployment_rate as number) || 0,
            youth_unemployment_rate: (sUnemp.youth_unemployment_rate as number) || 0,
            neet_rate: (sUnemp.neet_rate as number) || 0,
            service_delivery_score: (sProfile.service_delivery_score as number) || 0,
            profile: (sProfile.profile as number) || 3,
            profile_label: (sPca.profile_label as string) || 'Unknown',
            welfare_measure: (sProfile.welfare_measure as number) || 0,
            efficiency_measure: (sProfile.efficiency_measure as number) || 0,
            opportunity_measure: (sProfile.opportunity_measure as number) || 0,
            cluster: (sPca.cluster as number) || 3,
            pc1: (sPca.pc1 as number) || 0,
            pc2: (sPca.pc2 as number) || 0,
          } as MunicipalityWithStats;
        });
      setSimilarMunicipalities(similar);
    } catch (err) {
      console.error('Error fetching scorecard data:', err);
      setError('Failed to load municipality data.');
    } finally {
      setLoading(false);
    }
  }, [munCode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleGenerateAIBrief = async () => {
    if (!munCode) return;
    setAiLoading(true);
    try {
      const res = await fetch('/api/municipal/ai-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mun_code: munCode }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setAiBrief(data.brief);
    } catch (err) {
      console.error('AI brief error:', err);
      setAiBrief('Unable to generate AI analysis at this time. Please try again later.');
    } finally {
      setAiLoading(false);
    }
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="skeleton h-28 w-full rounded-xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-40 rounded-xl" />
          ))}
        </div>
        <div className="skeleton h-72 w-full rounded-xl" />
        <div className="skeleton h-72 w-full rounded-xl" />
      </div>
    );
  }

  // Error state
  if (error || !municipality) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-12 h-12 text-danger mb-4" />
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          {error || 'Municipality not found'}
        </h2>
        <Link
          href="/municipal"
          className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-600 transition-colors"
        >
          Back to Dashboard
        </Link>
      </div>
    );
  }

  // Finance chart data
  const financeChartData = finance.map((f) => ({
    year: f.financial_year.toString(),
    Revenue: f.total_revenue,
    Expenditure: f.total_expenditure,
    'Capital Exp.': f.capital_expenditure,
    'Operating Exp.': f.operating_expenditure,
    'Service Delivery': f.service_delivery_spend,
  }));

  // Unemployment trend data
  const trendData = unemployment.map((u) => ({
    period: `${u.year} Q${u.quarter}`,
    youth_unemployment: u.youth_unemployment_rate,
    neet: u.neet_rate,
    overall: u.unemployment_rate,
  }));

  // Find the best-performing similar municipality for comparison
  const bestSimilar = similarMunicipalities.length > 0
    ? similarMunicipalities.reduce((best, m) =>
      m.service_delivery_score > best.service_delivery_score ? m : best
    )
    : null;

  const sdDiff = bestSimilar
    ? Math.round(bestSimilar.service_delivery_score - municipality.service_delivery_score)
    : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back link */}
      <Link
        href="/municipal"
        className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-600 transition-colors"
      >
        &larr; Back to Dashboard
      </Link>

      {/* Scorecard header with gauges */}
      <MunicipalScorecard municipality={municipality} />

      {/* AI Brief */}
      <div className="stat-card">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-secondary" />
            AI Executive Brief
          </h2>
          {!aiBrief && (
            <button
              onClick={handleGenerateAIBrief}
              disabled={aiLoading}
              className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-600 transition-colors disabled:opacity-50"
            >
              {aiLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate AI Analysis
                </>
              )}
            </button>
          )}
        </div>
        {aiBrief && (
          <div className="mt-4 prose prose-sm max-w-none text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">
            {aiBrief}
          </div>
        )}
      </div>

      {/* Finance breakdown */}
      {financeChartData.length > 0 && (
        <div className="stat-card">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2 mb-4">
            <Building2 className="w-5 h-5 text-primary" />
            Financial Overview
          </h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={financeChartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => formatCurrency(v, true)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(var(--card))',
                    border: '1px solid rgb(var(--border))',
                    borderRadius: '8px',
                    fontSize: '13px',
                  }}
                  formatter={(value: number, name: string) => [formatCurrency(value, true), name]}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="Revenue" fill="#007A4D" radius={[2, 2, 0, 0]} />
                <Bar dataKey="Expenditure" fill="#DE3831" radius={[2, 2, 0, 0]} />
                <Bar dataKey="Service Delivery" fill="#002395" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Unemployment trends */}
      {trendData.length > 0 && (
        <div className="stat-card">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-danger" />
            Unemployment Trends
          </h2>
          <TrendChart
            data={trendData}
            xKey="period"
            series={[
              { key: 'youth_unemployment', label: 'Youth Unemployment', color: '#DE3831' },
              { key: 'neet', label: 'NEET Rate', color: '#ea8c3f' },
              { key: 'overall', label: 'Overall Unemployment', color: '#002395', dashed: true },
            ]}
            yLabel="Rate (%)"
            formatY={(v: number) => `${v.toFixed(0)}%`}
          />
        </div>
      )}

      {/* Skills gap for the area */}
      {skillsGaps.length > 0 && (
        <div className="stat-card">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2 mb-4">
            <GraduationCap className="w-5 h-5 text-accent" />
            Skills Demand in {municipality.province}
          </h2>
          <div className="grid gap-3">
            {skillsGaps.slice(0, 5).map((sg, i) => (
              <div
                key={sg.id || i}
                className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {sg.occupation}
                  </p>
                  <p className="text-xs text-slate-500">
                    {sg.sector} &middot; {sg.qualification_required}
                  </p>
                </div>
                <div className="text-right">
                  <p className={cn('text-sm font-bold', sg.gap > 0 ? 'text-danger' : 'text-primary')}>
                    Gap: {sg.gap > 0 ? '+' : ''}{formatNumber(sg.gap)}
                  </p>
                  <p className="text-xs text-slate-500">
                    Demand: {formatNumber(sg.demand_count)} | Supply: {formatNumber(sg.supply_count)}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Training programs */}
          {trainingPrograms.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Matching Training Programs
              </h3>
              <div className="overflow-x-auto scrollbar-thin">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 uppercase">Program</th>
                      <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 uppercase">Duration</th>
                      <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 uppercase">Cost</th>
                      <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 uppercase">Employment Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trainingPrograms.map((tp) => (
                      <tr
                        key={tp.id}
                        className="border-b border-slate-100 dark:border-slate-700/50"
                      >
                        <td className="px-3 py-2">
                          <p className="font-medium text-slate-900 dark:text-slate-100">{tp.name}</p>
                          <p className="text-xs text-slate-500">{tp.provider}</p>
                        </td>
                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                          {tp.duration_months} months
                        </td>
                        <td className="px-3 py-2">
                          {tp.is_free ? (
                            <span className="badge badge-primary">FREE</span>
                          ) : (
                            <span className="text-slate-600 dark:text-slate-400">
                              {formatCurrency(tp.cost)}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={cn(
                              'font-semibold',
                              tp.employment_rate > 70 ? 'text-primary' : tp.employment_rate > 40 ? 'text-secondary-700' : 'text-danger'
                            )}
                          >
                            {formatPercent(tp.employment_rate)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Similar municipalities */}
      {similarMunicipalities.length > 0 && (
        <div className="stat-card">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Similar Municipalities
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Municipalities in the same performance cluster (Cluster {municipality.cluster}: {PROFILE_CONFIG[municipality.cluster]?.label || 'Unknown'}).
          </p>

          {bestSimilar && sdDiff > 0 && (
            <div className="mb-4 p-3 bg-primary/5 border border-primary/20 rounded-lg text-sm text-slate-700 dark:text-slate-300">
              <strong>{bestSimilar.mun_name}</strong> has similar characteristics but scores{' '}
              <strong className="text-primary">{sdDiff}% better</strong> on service delivery.
              Comparing expenditure patterns could reveal actionable differences.
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {similarMunicipalities.map((sm) => (
              <Link
                key={sm.mun_code}
                href={`/municipal/scorecard?mun_code=${sm.mun_code}`}
                className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-slate-900 dark:text-slate-100 text-sm">
                    {sm.mun_name}
                  </h3>
                  <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-accent transition-colors" />
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{sm.province}</p>
                <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                  <div>
                    <span className="text-slate-500">Service Delivery</span>
                    <p className="font-semibold" style={{ color: sm.service_delivery_score > 70 ? '#007A4D' : sm.service_delivery_score > 40 ? '#FFB612' : '#DE3831' }}>
                      {sm.service_delivery_score.toFixed(0)}%
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500">Youth Unemp.</span>
                    <p className="font-semibold" style={{ color: sm.youth_unemployment_rate < 25 ? '#007A4D' : sm.youth_unemployment_rate < 40 ? '#FFB612' : '#DE3831' }}>
                      {sm.youth_unemployment_rate.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ScorecardPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6 animate-fade-in">
          <div className="skeleton h-28 w-full rounded-xl" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton h-40 rounded-xl" />
            ))}
          </div>
        </div>
      }
    >
      <ScorecardContent />
    </Suspense>
  );
}
