'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { createBrowserClient } from '@/lib/supabase';
import { cn, SA_PROVINCES } from '@/lib/utils';
import type { MunicipalityWithStats, FeatureLoading, PCAVariance } from '@/types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  Filter,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Loader2,
} from 'lucide-react';

// Dynamic import for PCA Biplot (uses D3 which needs DOM)
const PCABiplot = dynamic(() => import('@/components/PCABiplot'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-96 bg-slate-50 dark:bg-slate-800 rounded-lg">
      <div className="text-center">
        <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-500 mt-3">Loading biplot visualization...</p>
      </div>
    </div>
  ),
});

const CLUSTER_COLORS: Record<number, string> = {
  1: '#007A4D',
  2: '#FFB612',
  3: '#ea8c3f',
  4: '#DE3831',
};

const CLUSTER_DESCRIPTIONS: Record<number, { label: string; description: string }> = {
  1: {
    label: 'High Performing',
    description:
      'Municipalities with strong service delivery, lower unemployment, healthy finances, and effective governance. These are often metro or well-resourced local municipalities.',
  },
  2: {
    label: 'Developing',
    description:
      'Municipalities showing improvement trajectories. They have moderate service delivery with some challenges in financial management or employment but are trending positively.',
  },
  3: {
    label: 'Challenged',
    description:
      'Municipalities facing significant difficulties in service delivery or employment. Often characterized by financial constraints, high vacancy rates, or infrastructure backlogs.',
  },
  4: {
    label: 'Critical',
    description:
      'Municipalities in severe distress. Very high unemployment, poor audit outcomes, low service delivery scores, and often under financial strain or administration intervention.',
  },
};

export default function PCAExplorerPage() {
  const router = useRouter();
  const [municipalities, setMunicipalities] = useState<MunicipalityWithStats[]>([]);
  const [featureLoadings, setFeatureLoadings] = useState<FeatureLoading[]>([]);
  const [variance, setVariance] = useState<PCAVariance[]>([]);
  const [selectedProvince, setSelectedProvince] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [showExplainer, setShowExplainer] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const supabase = createBrowserClient();

      // Fetch municipalities with PCA results
      const { data: munData } = await supabase
        .from('municipalities')
        .select(`
          *,
          municipal_profiles!inner(profile, welfare_measure, efficiency_measure, opportunity_measure, service_delivery_score),
          unemployment_data!inner(unemployment_rate, youth_unemployment_rate, neet_rate),
          pca_results!inner(pc1, pc2, cluster, profile_label, feature_loadings)
        `)
        .order('mun_name');

      const flatMunicipalities: MunicipalityWithStats[] = (munData || []).map(
        (m: Record<string, unknown>) => {
          const profile = (m.municipal_profiles as Record<string, unknown>) || {};
          const unemp = (m.unemployment_data as Record<string, unknown>) || {};
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
        }
      );
      setMunicipalities(flatMunicipalities);

      // Extract feature loadings from the first PCA result that has them
      const firstWithLoadings = (munData || []).find(
        (m: Record<string, unknown>) => {
          const pca = (m.pca_results as Record<string, unknown>) || {};
          return pca.feature_loadings && Object.keys(pca.feature_loadings as Record<string, unknown>).length > 0;
        }
      );

      if (firstWithLoadings) {
        const pca = (firstWithLoadings.pca_results as Record<string, unknown>) || {};
        const loadings = (pca.feature_loadings as Record<string, { pc1: number; pc2: number; category?: string }>) || {};
        const featureLoadingArray: FeatureLoading[] = Object.entries(loadings).map(
          ([feature, vals]) => ({
            feature,
            pc1: vals.pc1 || 0,
            pc2: vals.pc2 || 0,
            category: vals.category || categorizeFeature(feature),
          })
        );
        setFeatureLoadings(featureLoadingArray);
      } else {
        // Default feature loadings for demonstration
        setFeatureLoadings([
          { feature: 'unemployment_rate', pc1: 0.65, pc2: -0.2, category: 'employment' },
          { feature: 'service_delivery', pc1: -0.55, pc2: 0.35, category: 'service_delivery' },
          { feature: 'expenditure', pc1: 0.3, pc2: 0.7, category: 'finance' },
          { feature: 'revenue', pc1: -0.4, pc2: 0.5, category: 'finance' },
          { feature: 'neet_rate', pc1: 0.6, pc2: 0.1, category: 'employment' },
          { feature: 'youth_population', pc1: 0.2, pc2: -0.55, category: 'demographics' },
        ]);
      }

      // Fetch explained variance
      const { data: varianceData } = await supabase
        .from('pca_variance')
        .select('*')
        .order('component');

      if (varianceData && varianceData.length > 0) {
        setVariance(varianceData);
      } else {
        // Default variance for demonstration
        setVariance([
          { component: 'PC1', explained_variance: 38.2, cumulative_variance: 38.2 },
          { component: 'PC2', explained_variance: 22.5, cumulative_variance: 60.7 },
          { component: 'PC3', explained_variance: 14.1, cumulative_variance: 74.8 },
          { component: 'PC4', explained_variance: 8.3, cumulative_variance: 83.1 },
          { component: 'PC5', explained_variance: 5.7, cumulative_variance: 88.8 },
        ]);
      }
    } catch (err) {
      console.error('Error fetching PCA data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredMunicipalities = selectedProvince
    ? municipalities.filter((m) => m.province === selectedProvince)
    : municipalities;

  const handleMunicipalityClick = (munCode: string) => {
    router.push(`/municipal/scorecard?mun_code=${munCode}`);
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="skeleton h-10 w-64 rounded" />
        <div className="skeleton h-96 w-full rounded-xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            PCA Explorer
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Principal Component Analysis of municipality performance indicators. Each dot is a municipality, positioned and colored by its statistical profile.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Province filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <select
              value={selectedProvince}
              onChange={(e) => setSelectedProvince(e.target.value)}
              className="pl-9 pr-8 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 appearance-none"
              aria-label="Filter by province"
            >
              <option value="">All Provinces</option>
              {SA_PROVINCES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* PCA Biplot */}
      <div className="stat-card p-4 sm:p-6">
        <PCABiplot
          municipalities={filteredMunicipalities}
          featureLoadings={featureLoadings}
          onMunicipalityClick={handleMunicipalityClick}
        />
      </div>

      {/* Cluster legend with descriptions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(CLUSTER_DESCRIPTIONS).map(([cluster, { label, description }]) => {
          const clusterNum = Number(cluster);
          const count = filteredMunicipalities.filter((m) => m.cluster === clusterNum).length;
          return (
            <div key={cluster} className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: CLUSTER_COLORS[clusterNum] }}
                />
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {label}
                </h3>
                <span className="ml-auto text-xs text-slate-400 font-medium">{count}</span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                {description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Explained variance */}
      {variance.length > 0 && (
        <div className="stat-card">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Explained Variance by Component
          </h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={variance} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="component" tick={{ fontSize: 12 }} />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v: number) => `${v}%`}
                  domain={[0, 50]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(var(--card))',
                    border: '1px solid rgb(var(--border))',
                    borderRadius: '8px',
                    fontSize: '13px',
                  }}
                  formatter={(value: number, name: string) => [
                    `${value.toFixed(1)}%`,
                    name === 'explained_variance' ? 'Variance Explained' : 'Cumulative',
                  ]}
                />
                <Bar dataKey="explained_variance" radius={[4, 4, 0, 0]}>
                  {variance.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={index === 0 ? '#002395' : index === 1 ? '#007A4D' : '#FFB612'}
                      opacity={0.85}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-slate-400 mt-2 text-center">
            PC1 and PC2 together explain{' '}
            <strong>{variance.length >= 2 ? variance[1].cumulative_variance.toFixed(1) : '—'}%</strong>{' '}
            of the total variance in the data.
          </p>
        </div>
      )}

      {/* What does this mean? */}
      <div className="stat-card">
        <button
          onClick={() => setShowExplainer(!showExplainer)}
          className="flex items-center justify-between w-full text-left"
        >
          <div className="flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              What does this mean?
            </h2>
          </div>
          {showExplainer ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>

        {showExplainer && (
          <div className="mt-4 prose prose-sm max-w-none text-slate-600 dark:text-slate-400 leading-relaxed space-y-3">
            <p>
              <strong>Principal Component Analysis (PCA)</strong> is a statistical technique that
              takes many different measurements about each municipality (like unemployment rate,
              service delivery scores, revenue, expenditure, etc.) and summarizes them into a
              smaller number of &quot;components&quot; that capture the most important patterns.
            </p>
            <p>
              Think of it like this: instead of looking at 20 different numbers for each
              municipality, PCA finds the 2-3 most important &quot;dimensions&quot; that explain most of
              the differences between municipalities. The chart above plots each municipality on
              these two most important dimensions (PC1 and PC2).
            </p>
            <p>
              <strong>What the position tells you:</strong> Municipalities that are close together
              on the plot are similar in their overall profile. Municipalities far apart are quite
              different. The arrows show which original measurements drive each dimension -- for
              example, if the &quot;unemployment&quot; arrow points to the right, then municipalities on the
              right tend to have higher unemployment.
            </p>
            <p>
              <strong>What the colors tell you:</strong> The four colors represent groups (clusters)
              of municipalities that have been statistically classified together. Green dots are
              &quot;High Performing,&quot; gold are &quot;Developing,&quot; orange are &quot;Challenged,&quot; and red are
              &quot;Critical.&quot; Dot size represents population.
            </p>
            <p>
              <strong>Why it matters:</strong> This visualization helps identify which municipalities
              face similar challenges and could learn from each other. It also reveals whether a
              municipality&apos;s challenges are primarily related to employment, finance, or service
              delivery.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/** Categorize a feature name into a category for arrow coloring. */
function categorizeFeature(feature: string): string {
  const f = feature.toLowerCase();
  if (f.includes('unemployment') || f.includes('neet') || f.includes('employment') || f.includes('absorption')) {
    return 'employment';
  }
  if (f.includes('revenue') || f.includes('expenditure') || f.includes('finance') || f.includes('audit') || f.includes('capital')) {
    return 'finance';
  }
  if (f.includes('service') || f.includes('delivery') || f.includes('welfare') || f.includes('efficiency')) {
    return 'service_delivery';
  }
  if (f.includes('population') || f.includes('youth') || f.includes('density')) {
    return 'demographics';
  }
  return 'default';
}
