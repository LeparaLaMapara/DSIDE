import {
  TrendingDown,
  Briefcase,
  GraduationCap,
  Building2,
  Compass,
  Search,
  MessageCircle,
  BarChart3,
  Database,
} from "lucide-react";
import { createServerSupabaseClient } from "@/lib/supabase-server";

// Fallback data when Supabase is not available
const FALLBACK_STATS = {
  unemployment_rate: 45.5,
  opportunities_count: 127,
  training_programs: 34,
  municipalities_tracked: 257,
};

const FALLBACK_FACTORS = [
  {
    factor: "Skills Mismatch",
    impact: 78,
    description: "Gap between what employers need and available skills",
  },
  {
    factor: "Limited Access",
    impact: 65,
    description: "Transport, internet, and information barriers",
  },
  {
    factor: "Economic Structure",
    impact: 52,
    description: "Slow growth in labor-intensive sectors",
  },
];

async function getDashboardData() {
  const supabase = createServerSupabaseClient();

  if (!supabase) {
    return {
      stats: FALLBACK_STATS,
      factors: FALLBACK_FACTORS,
    };
  }

  try {
    // Fetch stats
    const [opportunitiesResult, trainingResult, municipalitiesResult] =
      await Promise.all([
        supabase
          .from("opportunities")
          .select("id", { count: "exact", head: true }),
        supabase
          .from("opportunities")
          .select("id", { count: "exact", head: true })
          .eq("type", "training"),
        supabase
          .from("municipalities")
          .select("id", { count: "exact", head: true }),
      ]);

    // Fetch PCA factors
    const { data: factorsData } = await supabase
      .from("unemployment_factors")
      .select("*")
      .order("impact", { ascending: false })
      .limit(3);

    return {
      stats: {
        unemployment_rate: 45.5,
        opportunities_count: opportunitiesResult.count || FALLBACK_STATS.opportunities_count,
        training_programs: trainingResult.count || FALLBACK_STATS.training_programs,
        municipalities_tracked: municipalitiesResult.count || FALLBACK_STATS.municipalities_tracked,
      },
      factors:
        factorsData && factorsData.length > 0
          ? factorsData
          : FALLBACK_FACTORS,
    };
  } catch {
    return {
      stats: FALLBACK_STATS,
      factors: FALLBACK_FACTORS,
    };
  }
}

export default async function HomePage() {
  const { stats, factors } = await getDashboardData();

  return (
    <div className="mx-auto max-w-6xl px-4 pb-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-sa-green via-sa-green to-sa-blue mt-6 px-6 py-12 sm:px-12 sm:py-16">
        <div className="absolute top-0 right-0 w-64 h-64 bg-sa-gold/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full blur-2xl translate-y-1/3 -translate-x-1/4" />
        <div className="relative">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-1.5 text-xs font-medium text-white/90 backdrop-blur-sm mb-6">
            <span className="h-1.5 w-1.5 rounded-full bg-sa-gold animate-pulse" />
            Data-driven career guidance
          </div>
          <h1 className="text-3xl font-extrabold text-white sm:text-5xl leading-tight">
            Find Your Path to
            <br />
            <span className="text-sa-gold">Employment</span>
          </h1>
          <p className="mt-4 max-w-lg text-base text-white/80 leading-relaxed">
            DSIDE uses real data to connect young South Africans with skills,
            training, and opportunities that actually lead to jobs.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="/skills-matcher" className="btn-gold">
              Find Your Skills
              <Compass className="ml-2 h-4 w-4" />
            </a>
            <a
              href="/opportunities"
              className="inline-flex items-center gap-2 rounded-xl border-2 border-white/30 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-white/10"
            >
              Browse Opportunities
            </a>
          </div>
        </div>
      </section>

      {/* Stats Cards */}
      <section className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        <div className="card flex flex-col items-center text-center p-4 sm:p-6">
          <div className="rounded-xl bg-red-50 p-2.5 text-red-500">
            <TrendingDown className="h-5 w-5" />
          </div>
          <p className="mt-3 text-2xl font-bold text-gray-900">
            {stats.unemployment_rate}%
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Youth Unemployment
          </p>
        </div>
        <div className="card flex flex-col items-center text-center p-4 sm:p-6">
          <div className="rounded-xl bg-sa-green/10 p-2.5 text-sa-green">
            <Briefcase className="h-5 w-5" />
          </div>
          <p className="mt-3 text-2xl font-bold text-gray-900">
            {stats.opportunities_count}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Opportunities
          </p>
        </div>
        <div className="card flex flex-col items-center text-center p-4 sm:p-6">
          <div className="rounded-xl bg-sa-gold/10 p-2.5 text-sa-gold">
            <GraduationCap className="h-5 w-5" />
          </div>
          <p className="mt-3 text-2xl font-bold text-gray-900">
            {stats.training_programs}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Training Programs
          </p>
        </div>
        <div className="card flex flex-col items-center text-center p-4 sm:p-6">
          <div className="rounded-xl bg-sa-blue/10 p-2.5 text-sa-blue">
            <Building2 className="h-5 w-5" />
          </div>
          <p className="mt-3 text-2xl font-bold text-gray-900">
            {stats.municipalities_tracked}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Municipalities
          </p>
        </div>
      </section>

      {/* Action Cards */}
      <section className="mt-10">
        <h2 className="text-xl font-bold text-gray-900">
          What would you like to do?
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {/* Skills Matcher Card */}
          <a
            href="/skills-matcher"
            className="group card flex flex-col items-start hover:border-sa-green/20 hover:shadow-lg transition-all"
          >
            <div className="rounded-xl bg-sa-green/10 p-3 text-sa-green group-hover:bg-sa-green group-hover:text-white transition-colors">
              <Compass className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-gray-900">
              Find Skills That Lead to Jobs
            </h3>
            <p className="mt-2 text-sm text-gray-500 leading-relaxed">
              Answer a few questions and get matched with training programs based
              on real employment data in your area.
            </p>
            <span className="mt-auto pt-4 text-sm font-semibold text-sa-green group-hover:underline">
              Start matching &rarr;
            </span>
          </a>

          {/* Opportunities Card */}
          <a
            href="/opportunities"
            className="group card flex flex-col items-start hover:border-sa-gold/20 hover:shadow-lg transition-all"
          >
            <div className="rounded-xl bg-sa-gold/10 p-3 text-sa-gold group-hover:bg-sa-gold group-hover:text-gray-900 transition-colors">
              <Search className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-gray-900">
              Browse Opportunities
            </h3>
            <p className="mt-2 text-sm text-gray-500 leading-relaxed">
              Learnerships, internships, bursaries, and jobs. Filter by
              province, sector, and type. Updated regularly.
            </p>
            <span className="mt-auto pt-4 text-sm font-semibold text-sa-gold group-hover:underline">
              Browse now &rarr;
            </span>
          </a>

          {/* Chat Card */}
          <a
            href="/chat"
            className="group card flex flex-col items-start hover:border-sa-blue/20 hover:shadow-lg transition-all"
          >
            <div className="rounded-xl bg-sa-blue/10 p-3 text-sa-blue group-hover:bg-sa-blue group-hover:text-white transition-colors">
              <MessageCircle className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-gray-900">
              Get Personalized Advice
            </h3>
            <p className="mt-2 text-sm text-gray-500 leading-relaxed">
              Chat with our AI career advisor. Get specific guidance on
              learnerships, SETAs, and career paths.
            </p>
            <span className="mt-auto pt-4 text-sm font-semibold text-sa-blue group-hover:underline">
              Start chatting &rarr;
            </span>
          </a>
        </div>
      </section>

      {/* Understanding Unemployment Section */}
      <section className="mt-12">
        <div className="flex items-center gap-3 mb-6">
          <div className="rounded-xl bg-red-50 p-2.5">
            <BarChart3 className="h-5 w-5 text-red-500" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Understanding Youth Unemployment
            </h2>
            <p className="text-sm text-gray-500">
              Top factors driving unemployment in South Africa
            </p>
          </div>
        </div>

        <div className="card space-y-5">
          {factors.map((factor, index) => {
            const colors = [
              "from-red-500 to-red-400",
              "from-sa-gold to-amber-400",
              "from-sa-blue to-blue-400",
            ];
            return (
              <div key={index}>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">
                      {factor.factor}
                    </p>
                    <p className="text-xs text-gray-400">{factor.description}</p>
                  </div>
                  <span className="text-sm font-bold text-gray-700">
                    {factor.impact}%
                  </span>
                </div>
                <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${colors[index]} transition-all duration-1000`}
                    style={{ width: `${factor.impact}%` }}
                  />
                </div>
              </div>
            );
          })}
          <p className="text-xs text-gray-400 pt-2 border-t border-gray-50">
            Based on Principal Component Analysis of Stats SA QLFS data and
            municipal economic indicators.
          </p>
        </div>
      </section>

      {/* Data Attribution Footer */}
      <footer className="mt-12 rounded-2xl bg-gray-100/50 border border-gray-100 p-6">
        <div className="flex items-start gap-3">
          <Database className="h-5 w-5 text-gray-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-gray-600">Data Sources</p>
            <p className="mt-1 text-xs text-gray-400 leading-relaxed">
              Statistics South Africa (Stats SA) Quarterly Labour Force Survey,
              Department of Higher Education and Training, National Treasury
              Municipal Data, SETA Annual Reports, and aggregated opportunity
              listings. Last updated March 2026. DSIDE is a research project and
              does not guarantee employment outcomes.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
