import { NextRequest, NextResponse } from "next/server";
import { createServiceClient } from "@/lib/supabase-server";
import { readFile } from "fs/promises";
import { join } from "path";

/**
 * GET /api/skills-gap
 *
 * Returns skills gap data ranked by opportunity, with matched training programs.
 *
 * Query params:
 *   - province: filter by province name
 *   - sector:   filter by sector name
 *   - source:   "json" (read from pre-computed file) or "db" (query live). Default: "db"
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const province = searchParams.get("province");
    const sector = searchParams.get("sector");
    const source = searchParams.get("source") ?? "db";

    // If source=json, read from pre-computed skills_gap_analysis.json
    if (source === "json") {
      return await getFromJson(province, sector);
    }

    return await getFromDb(province, sector);
  } catch (err) {
    console.error("Skills gap API error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

async function getFromJson(
  province: string | null,
  sector: string | null
): Promise<NextResponse> {
  try {
    const filePath = join(
      process.cwd(),
      "data",
      "skills_gap_analysis.json"
    );
    const raw = await readFile(filePath, "utf-8");
    const analysis = JSON.parse(raw);

    let result = analysis;

    // Filter by province if requested
    if (province && analysis.province_breakdown) {
      const provinceData = analysis.province_breakdown[province];
      if (!provinceData) {
        return NextResponse.json(
          { error: `Province '${province}' not found in analysis` },
          { status: 404 }
        );
      }
      result = {
        province,
        ...provinceData,
        top_occupations_national: analysis.top_occupations_national,
        recommended_paths: analysis.recommended_paths?.[province] ?? [],
      };
    }

    // Filter by sector within province data
    if (sector && result.sectors) {
      result.sectors = result.sectors.filter(
        (s: { sector: string }) =>
          s.sector.toLowerCase() === sector.toLowerCase()
      );
    }

    return NextResponse.json({ data: result });
  } catch (err) {
    console.error("Error reading skills gap JSON:", err);
    return NextResponse.json(
      {
        error:
          "Skills gap analysis file not found. Run the ML pipeline first.",
      },
      { status: 404 }
    );
  }
}

async function getFromDb(
  province: string | null,
  sector: string | null
): Promise<NextResponse> {
  const supabase = createServiceClient();

  // Fetch skills gaps
  let skillsQuery = supabase
    .from("skills_gaps")
    .select("*")
    .order("gap", { ascending: false });

  if (province) {
    skillsQuery = skillsQuery.eq("province", province);
  }
  if (sector) {
    skillsQuery = skillsQuery.eq("sector", sector);
  }

  const { data: skillsData, error: skillsError } = await skillsQuery;

  if (skillsError) {
    console.error("Error fetching skills_gaps:", skillsError);
    return NextResponse.json(
      { error: "Failed to fetch skills gaps", details: skillsError.message },
      { status: 500 }
    );
  }

  // Fetch matching training programs
  let trainingQuery = supabase
    .from("training_programs")
    .select("*")
    .order("employment_rate", { ascending: false });

  if (province) {
    trainingQuery = trainingQuery.eq("province", province);
  }
  if (sector) {
    trainingQuery = trainingQuery.eq("sector", sector);
  }

  const { data: trainingData, error: trainingError } = await trainingQuery;

  if (trainingError) {
    console.error("Error fetching training_programs:", trainingError);
  }

  // Group skills by sector and compute opportunity scores
  const sectorMap: Record<
    string,
    {
      sector: string;
      total_demand: number;
      total_supply: number;
      net_gap: number;
      occupations: Array<{
        occupation: string;
        demand_count: number;
        supply_count: number;
        gap: number;
        is_scarce: boolean;
        qualification_required: string | null;
      }>;
    }
  > = {};

  for (const row of skillsData ?? []) {
    const s = row.sector as string;
    if (!sectorMap[s]) {
      sectorMap[s] = {
        sector: s,
        total_demand: 0,
        total_supply: 0,
        net_gap: 0,
        occupations: [],
      };
    }
    const demand = Number(row.demand_count) || 0;
    const supply = Number(row.supply_count) || 0;
    sectorMap[s].total_demand += demand;
    sectorMap[s].total_supply += supply;
    sectorMap[s].net_gap += demand - supply;
    sectorMap[s].occupations.push({
      occupation: row.occupation,
      demand_count: demand,
      supply_count: supply,
      gap: Number(row.gap) || 0,
      is_scarce: Boolean(row.is_scarce),
      qualification_required: row.qualification_required ?? null,
    });
  }

  // Compute opportunity score and match training programs
  const sectors = Object.values(sectorMap).map((s) => {
    const matchedTraining = (trainingData ?? [])
      .filter((t: { sector: string }) => t.sector === s.sector)
      .map(
        (t: {
          name: string;
          provider: string;
          cost: number | null;
          is_free: boolean;
          employment_rate: number | null;
        }) => ({
          name: t.name,
          provider: t.provider,
          cost: t.cost,
          is_free: t.is_free,
          employment_rate: t.employment_rate,
        })
      );

    const trainingAvailable = matchedTraining.length > 0;
    const opportunityScore =
      (s.net_gap / Math.max(s.total_demand, 1)) * 0.5 +
      (trainingAvailable ? 1.0 : 0.0) * 0.3 +
      (Math.min(s.total_demand, 1000) / 1000) * 0.2;

    return {
      ...s,
      opportunity_score: Math.round(opportunityScore * 1000) / 1000,
      matched_training: matchedTraining,
    };
  });

  // Sort by opportunity score descending
  sectors.sort((a, b) => b.opportunity_score - a.opportunity_score);

  return NextResponse.json({
    data: {
      sectors,
      total_records: (skillsData ?? []).length,
      filters: { province, sector },
    },
  });
}
