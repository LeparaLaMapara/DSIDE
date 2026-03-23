"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Filter,
  Search,
  Loader2,
  FolderOpen,
  RefreshCw,
} from "lucide-react";
import OpportunityCard, {
  OpportunityCardSkeleton,
} from "@/components/OpportunityCard";
import {
  PROVINCES,
  SECTORS,
  OPPORTUNITY_TYPES,
  type Opportunity,
  type OpportunityType,
} from "@/types";

const TYPE_LABELS: Record<OpportunityType, string> = {
  learnership: "Learnerships",
  internship: "Internships",
  job: "Jobs",
  bursary: "Bursaries",
  training: "Training",
};

// Fallback data when Supabase is not configured
const FALLBACK_OPPORTUNITIES: Opportunity[] = [
  {
    id: "1",
    title: "ICT Learnership Programme 2026",
    provider: "MICT SETA",
    type: "learnership",
    province: "Gauteng",
    sector: "Technology",
    description: "12-month learnership in IT support and digital skills.",
    stipend_amount: 3500,
    is_free: true,
    deadline: "2026-04-30",
    source_url: "https://www.mict.org.za",
    requirements: ["Matric with maths", "Age 18-35", "South African citizen"],
    created_at: "2026-03-01",
  },
  {
    id: "2",
    title: "Youth Employment Service (YES) Programme",
    provider: "YES4Youth",
    type: "internship",
    province: "Western Cape",
    sector: "Multiple",
    description: "Paid 12-month work experience at leading SA companies.",
    stipend_amount: 5000,
    is_free: true,
    deadline: "2026-05-15",
    source_url: "https://www.yes4youth.co.za",
    requirements: ["Age 18-35", "South African citizen", "Currently unemployed"],
    created_at: "2026-03-05",
  },
  {
    id: "3",
    title: "Funza Lushaka Bursary 2026",
    provider: "Department of Basic Education",
    type: "bursary",
    province: "Eastern Cape",
    sector: "Education",
    description: "Full bursary for teaching qualifications at public universities.",
    stipend_amount: null,
    is_free: true,
    deadline: "2026-04-01",
    source_url: "https://www.funzalushaka.doe.gov.za",
    requirements: ["Matric with minimum 60% average", "South African citizen"],
    created_at: "2026-02-15",
  },
  {
    id: "4",
    title: "Harambee Digital Skills Training",
    provider: "Harambee Youth Employment Accelerator",
    type: "training",
    province: "KwaZulu-Natal",
    sector: "Technology",
    description: "Free 3-month digital skills bootcamp with job placement support.",
    stipend_amount: null,
    is_free: true,
    deadline: "2026-06-30",
    source_url: "https://www.harambee.co.za",
    requirements: ["Age 18-34", "Matric certificate"],
    created_at: "2026-03-10",
  },
  {
    id: "5",
    title: "Junior Accountant",
    provider: "National Treasury",
    type: "job",
    province: "Gauteng",
    sector: "Finance",
    description: "Entry-level accounting position for recent graduates.",
    stipend_amount: 15000,
    is_free: false,
    deadline: "2026-03-28",
    source_url: "https://www.treasury.gov.za",
    requirements: ["BCom Accounting degree", "South African citizen"],
    created_at: "2026-03-08",
  },
  {
    id: "6",
    title: "CETA Construction Learnership",
    provider: "Construction Education & Training Authority",
    type: "learnership",
    province: "Limpopo",
    sector: "Construction",
    description: "NQF Level 2-4 learnership in building and civil construction.",
    stipend_amount: 2500,
    is_free: true,
    deadline: "2026-05-01",
    source_url: "https://www.ceta.org.za",
    requirements: ["Grade 10 minimum", "Age 18-35", "Physically fit"],
    created_at: "2026-03-12",
  },
  {
    id: "7",
    title: "Agricultural Internship Programme",
    provider: "Department of Agriculture",
    type: "internship",
    province: "Free State",
    sector: "Agriculture",
    description: "12-month internship for agriculture diploma/degree holders.",
    stipend_amount: 6000,
    is_free: true,
    deadline: "2026-04-15",
    source_url: "https://www.dalrrd.gov.za",
    requirements: ["Diploma/Degree in Agriculture", "South African citizen"],
    created_at: "2026-03-01",
  },
  {
    id: "8",
    title: "HWSETA Healthcare Learnership",
    provider: "Health & Welfare SETA",
    type: "learnership",
    province: "Mpumalanga",
    sector: "Healthcare",
    description: "Community health worker learnership with practical placement.",
    stipend_amount: 3000,
    is_free: true,
    deadline: "2026-07-31",
    source_url: "https://www.hwseta.org.za",
    requirements: ["Matric", "Age 18-35"],
    created_at: "2026-03-15",
  },
];

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Filters
  const [province, setProvince] = useState("");
  const [type, setType] = useState("");
  const [sector, setSector] = useState("");
  const [isFreeOnly, setIsFreeOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const LIMIT = 12;

  const fetchOpportunities = useCallback(
    async (pageNum: number, append: boolean = false) => {
      if (append) {
        setIsLoadingMore(true);
      } else {
        setIsLoading(true);
      }

      try {
        const params = new URLSearchParams();
        if (province) params.set("province", province);
        if (type) params.set("type", type);
        if (sector) params.set("sector", sector);
        if (isFreeOnly) params.set("is_free", "true");
        params.set("page", String(pageNum));
        params.set("limit", String(LIMIT));

        const response = await fetch(`/api/opportunities?${params}`);

        if (!response.ok) throw new Error("Failed to fetch");

        const data = await response.json();

        if (append) {
          setOpportunities((prev) => [...prev, ...data.opportunities]);
        } else {
          setOpportunities(data.opportunities);
        }
        setTotalCount(data.total);
        setHasMore(data.opportunities.length === LIMIT);
      } catch {
        // Use fallback data
        let filtered = [...FALLBACK_OPPORTUNITIES];
        if (province) filtered = filtered.filter((o) => o.province === province);
        if (type) filtered = filtered.filter((o) => o.type === type);
        if (sector) filtered = filtered.filter((o) => o.sector === sector);
        if (isFreeOnly) filtered = filtered.filter((o) => o.is_free);

        if (append) {
          // No more fallback data to load
          setHasMore(false);
        } else {
          setOpportunities(filtered);
          setTotalCount(filtered.length);
          setHasMore(false);
        }
      } finally {
        setIsLoading(false);
        setIsLoadingMore(false);
      }
    },
    [province, type, sector, isFreeOnly]
  );

  useEffect(() => {
    setPage(1);
    fetchOpportunities(1, false);
  }, [fetchOpportunities]);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchOpportunities(nextPage, true);
  };

  const activeFilterCount = [province, type, sector, isFreeOnly].filter(
    Boolean
  ).length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Opportunities</h1>
        <p className="mt-1 text-sm text-gray-500">
          {totalCount} opportunity{totalCount !== 1 ? "ies" : "y"} available
        </p>
      </div>

      {/* Filter bar */}
      <div className="sticky top-[57px] z-40 -mx-4 bg-gray-50/80 backdrop-blur-lg px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-3 overflow-x-auto scrollbar-hide pb-1">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
              activeFilterCount > 0
                ? "border-sa-green bg-sa-green/5 text-sa-green"
                : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
            }`}
          >
            <Filter className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-sa-green text-[10px] font-bold text-white">
                {activeFilterCount}
              </span>
            )}
          </button>

          {/* Quick filter chips */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsFreeOnly(!isFreeOnly)}
              className={`chip shrink-0 !text-xs ${
                isFreeOnly ? "chip-selected" : "chip-unselected"
              }`}
            >
              Free only
            </button>
            {OPPORTUNITY_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => setType(type === t ? "" : t)}
                className={`chip shrink-0 !text-xs capitalize ${
                  type === t ? "chip-selected" : "chip-unselected"
                }`}
              >
                {TYPE_LABELS[t]}
              </button>
            ))}
          </div>
        </div>

        {/* Expanded filters */}
        {showFilters && (
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3 animate-in fade-in">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Province
              </label>
              <select
                value={province}
                onChange={(e) => setProvince(e.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-700 focus:border-sa-green focus:outline-none focus:ring-1 focus:ring-sa-green/20"
              >
                <option value="">All provinces</option>
                {PROVINCES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Sector
              </label>
              <select
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-700 focus:border-sa-green focus:outline-none focus:ring-1 focus:ring-sa-green/20"
              >
                <option value="">All sectors</option>
                {SECTORS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => {
                  setProvince("");
                  setType("");
                  setSector("");
                  setIsFreeOnly(false);
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-500 hover:border-gray-300 transition-all"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Clear all
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <OpportunityCardSkeleton key={i} />
          ))}
        </div>
      ) : opportunities.length === 0 ? (
        <div className="mt-16 flex flex-col items-center justify-center text-center px-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-100">
            <FolderOpen className="h-8 w-8 text-gray-300" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-gray-900">
            No opportunities found
          </h3>
          <p className="mt-2 max-w-sm text-sm text-gray-500">
            No opportunities match your current filters. Try broadening your
            search or clearing some filters.
          </p>
          <button
            onClick={() => {
              setProvince("");
              setType("");
              setSector("");
              setIsFreeOnly(false);
            }}
            className="mt-6 btn-secondary"
          >
            Clear all filters
          </button>
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {opportunities.map((opp) => (
              <OpportunityCard key={opp.id} opportunity={opp} />
            ))}
          </div>

          {/* Load more */}
          {hasMore && (
            <div className="mt-8 text-center">
              <button
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                className="btn-secondary"
              >
                {isLoadingMore ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Load more opportunities
                  </>
                )}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
