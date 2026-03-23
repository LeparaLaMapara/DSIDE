import { NextRequest, NextResponse } from "next/server";
import { createServiceClient } from "@/lib/supabase-server";

/**
 * GET /api/unemployment
 *
 * Returns unemployment rates with geographic data for map visualisation.
 *
 * Query params:
 *   - province: filter by province name
 *   - year:     filter by year
 *   - quarter:  filter by quarter (1-4)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const province = searchParams.get("province");
    const year = searchParams.get("year");
    const quarter = searchParams.get("quarter");

    const supabase = createServiceClient();

    // Fetch unemployment data joined with municipalities for geo data
    let query = supabase
      .from("unemployment_data")
      .select(
        `
        mun_code,
        year,
        quarter,
        unemployment_rate,
        youth_unemployment_rate,
        neet_rate,
        absorption_rate,
        municipalities!inner (
          mun_name,
          province,
          district,
          latitude,
          longitude,
          population,
          youth_population
        )
      `
      )
      .order("year", { ascending: false })
      .order("quarter", { ascending: false });

    if (province) {
      query = query.eq("municipalities.province", province);
    }
    if (year) {
      query = query.eq("year", parseInt(year, 10));
    }
    if (quarter) {
      const q = parseInt(quarter, 10);
      if (isNaN(q) || q < 1 || q > 4) {
        return NextResponse.json(
          { error: "Invalid quarter parameter. Must be 1-4." },
          { status: 400 }
        );
      }
      query = query.eq("quarter", q);
    }

    const { data, error } = await query;

    if (error) {
      console.error("Error fetching unemployment data:", error);
      return NextResponse.json(
        { error: "Failed to fetch unemployment data", details: error.message },
        { status: 500 }
      );
    }

    // Flatten the nested municipalities object
    const results = (data ?? []).map((row: Record<string, unknown>) => {
      const municipality = row.municipalities as Record<string, unknown> | null;
      return {
        mun_code: row.mun_code,
        year: row.year,
        quarter: row.quarter,
        unemployment_rate: row.unemployment_rate,
        youth_unemployment_rate: row.youth_unemployment_rate,
        neet_rate: row.neet_rate,
        absorption_rate: row.absorption_rate,
        mun_name: municipality?.mun_name ?? null,
        province: municipality?.province ?? null,
        district: municipality?.district ?? null,
        latitude: municipality?.latitude ?? null,
        longitude: municipality?.longitude ?? null,
        population: municipality?.population ?? null,
        youth_population: municipality?.youth_population ?? null,
      };
    });

    // Compute summary statistics
    const summary = computeSummary(results);

    return NextResponse.json({
      data: results,
      count: results.length,
      summary,
      filters: { province, year, quarter },
    });
  } catch (err) {
    console.error("Unemployment API error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface UnemploymentRecord {
  unemployment_rate: number | null;
  youth_unemployment_rate: number | null;
  neet_rate: number | null;
  absorption_rate: number | null;
  province: string | null;
}

function computeSummary(records: UnemploymentRecord[]) {
  if (records.length === 0) {
    return null;
  }

  const validRates = records
    .map((r) => r.unemployment_rate)
    .filter((v): v is number => v !== null && v !== undefined);

  const validYouthRates = records
    .map((r) => r.youth_unemployment_rate)
    .filter((v): v is number => v !== null && v !== undefined);

  const validNeetRates = records
    .map((r) => r.neet_rate)
    .filter((v): v is number => v !== null && v !== undefined);

  const avg = (arr: number[]) =>
    arr.length > 0 ? arr.reduce((s, v) => s + v, 0) / arr.length : null;

  // Per-province averages
  const byProvince: Record<string, number[]> = {};
  for (const r of records) {
    if (r.province && r.youth_unemployment_rate !== null) {
      if (!byProvince[r.province]) byProvince[r.province] = [];
      byProvince[r.province].push(r.youth_unemployment_rate);
    }
  }

  const provinceAverages: Record<string, number> = {};
  for (const [prov, rates] of Object.entries(byProvince)) {
    const a = avg(rates);
    if (a !== null) {
      provinceAverages[prov] = Math.round(a * 10) / 10;
    }
  }

  return {
    total_records: records.length,
    avg_unemployment_rate:
      avg(validRates) !== null
        ? Math.round(avg(validRates)! * 10) / 10
        : null,
    avg_youth_unemployment_rate:
      avg(validYouthRates) !== null
        ? Math.round(avg(validYouthRates)! * 10) / 10
        : null,
    avg_neet_rate:
      avg(validNeetRates) !== null
        ? Math.round(avg(validNeetRates)! * 10) / 10
        : null,
    max_youth_unemployment_rate:
      validYouthRates.length > 0 ? Math.max(...validYouthRates) : null,
    min_youth_unemployment_rate:
      validYouthRates.length > 0 ? Math.min(...validYouthRates) : null,
    province_averages: provinceAverages,
  };
}
