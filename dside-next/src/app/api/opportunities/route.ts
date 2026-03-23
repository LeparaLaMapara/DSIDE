import { NextRequest, NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase-server";

// Fallback opportunities for when Supabase is not configured
const FALLBACK_OPPORTUNITIES = [
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

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const province = searchParams.get("province");
  const type = searchParams.get("type");
  const sector = searchParams.get("sector");
  const isFree = searchParams.get("is_free");
  const page = parseInt(searchParams.get("page") || "1", 10);
  const limit = Math.min(parseInt(searchParams.get("limit") || "12", 10), 50);
  const offset = (page - 1) * limit;

  const supabase = createServerSupabaseClient();

  if (!supabase) {
    // Use fallback data
    let filtered = [...FALLBACK_OPPORTUNITIES];
    if (province) filtered = filtered.filter((o) => o.province === province);
    if (type) filtered = filtered.filter((o) => o.type === type);
    if (sector) filtered = filtered.filter((o) => o.sector === sector);
    if (isFree === "true") filtered = filtered.filter((o) => o.is_free);

    // Sort by deadline
    filtered.sort(
      (a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime()
    );

    const total = filtered.length;
    const paginated = filtered.slice(offset, offset + limit);

    return NextResponse.json({
      opportunities: paginated,
      total,
      page,
      limit,
    });
  }

  try {
    let query = supabase.from("opportunities").select("*", { count: "exact" });

    // Apply filters
    if (province) query = query.eq("province", province);
    if (type) query = query.eq("type", type);
    if (sector) query = query.eq("sector", sector);
    if (isFree === "true") query = query.eq("is_free", true);

    // Order: soonest deadline first, then newest
    query = query
      .order("deadline", { ascending: true })
      .order("created_at", { ascending: false });

    // Pagination
    query = query.range(offset, offset + limit - 1);

    const { data, error, count } = await query;

    if (error) {
      throw error;
    }

    return NextResponse.json({
      opportunities: data || [],
      total: count || 0,
      page,
      limit,
    });
  } catch (error) {
    console.error("Opportunities API error:", error);

    // Fall back to hardcoded data
    let filtered = [...FALLBACK_OPPORTUNITIES];
    if (province) filtered = filtered.filter((o) => o.province === province);
    if (type) filtered = filtered.filter((o) => o.type === type);
    if (sector) filtered = filtered.filter((o) => o.sector === sector);
    if (isFree === "true") filtered = filtered.filter((o) => o.is_free);

    filtered.sort(
      (a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime()
    );

    return NextResponse.json({
      opportunities: filtered.slice(offset, offset + limit),
      total: filtered.length,
      page,
      limit,
    });
  }
}
