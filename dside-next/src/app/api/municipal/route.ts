import { NextRequest, NextResponse } from "next/server";
import { createServiceClient } from "@/lib/supabase-server";

/**
 * GET /api/municipal
 *
 * Returns comprehensive municipal intelligence data including
 * financial data, profile assignment, PCA position, and peer comparison.
 *
 * Query params:
 *   - mun_code: specific municipality code
 *   - province: filter by province
 *   - year:     financial year filter
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const munCode = searchParams.get("mun_code");
    const province = searchParams.get("province");
    const year = searchParams.get("year");

    const supabase = createServiceClient();

    // --- Fetch municipalities ---
    let munQuery = supabase
      .from("municipalities")
      .select("*");

    if (munCode) {
      munQuery = munQuery.eq("mun_code", munCode);
    }
    if (province) {
      munQuery = munQuery.eq("province", province);
    }

    const { data: municipalities, error: munError } = await munQuery;

    if (munError) {
      console.error("Error fetching municipalities:", munError);
      return NextResponse.json(
        { error: "Failed to fetch municipalities", details: munError.message },
        { status: 500 }
      );
    }

    if (!municipalities || municipalities.length === 0) {
      return NextResponse.json(
        { error: "No municipalities found for the given filters" },
        { status: 404 }
      );
    }

    const munCodes = municipalities.map(
      (m: { mun_code: string }) => m.mun_code
    );

    // --- Fetch related data in parallel ---
    const [financesResult, profilesResult, pcaResult, unemploymentResult] =
      await Promise.all([
        // Municipal finances
        (() => {
          let q = supabase
            .from("municipal_finances")
            .select("*")
            .in("mun_code", munCodes)
            .order("financial_year", { ascending: false });
          if (year) {
            q = q.eq("financial_year", year);
          }
          return q;
        })(),

        // Municipal profiles
        (() => {
          let q = supabase
            .from("municipal_profiles")
            .select("*")
            .in("mun_code", munCodes)
            .order("year", { ascending: false });
          if (year) {
            q = q.eq("year", parseInt(year, 10));
          }
          return q;
        })(),

        // PCA results
        supabase
          .from("pca_results")
          .select("*")
          .in("mun_code", munCodes),

        // Unemployment data
        (() => {
          let q = supabase
            .from("unemployment_data")
            .select("*")
            .in("mun_code", munCodes)
            .order("year", { ascending: false });
          if (year) {
            q = q.eq("year", parseInt(year, 10));
          }
          return q;
        })(),
      ]);

    // Index related data by mun_code for fast lookup
    const financesByMun = groupBy(financesResult.data ?? [], "mun_code");
    const profilesByMun = groupBy(profilesResult.data ?? [], "mun_code");
    const pcaByMun = indexBy(pcaResult.data ?? [], "mun_code");
    const unempByMun = groupBy(unemploymentResult.data ?? [], "mun_code");

    // --- Compute peer comparison (provincial averages) ---
    const allFinances = financesResult.data ?? [];
    const provincialAverages: Record<
      string,
      {
        avg_revenue: number;
        avg_expenditure: number;
        avg_service_delivery_spend: number;
        municipality_count: number;
      }
    > = {};

    for (const mun of municipalities) {
      const prov = mun.province as string;
      if (!provincialAverages[prov]) {
        const provFinances = allFinances.filter(
          (f: { mun_code: string }) =>
            municipalities
              .filter((m: { province: string }) => m.province === prov)
              .map((m: { mun_code: string }) => m.mun_code)
              .includes(f.mun_code)
        );
        const count = Math.max(provFinances.length, 1);
        provincialAverages[prov] = {
          avg_revenue:
            provFinances.reduce(
              (s: number, f: { total_revenue: number | null }) =>
                s + (Number(f.total_revenue) || 0),
              0
            ) / count,
          avg_expenditure:
            provFinances.reduce(
              (s: number, f: { total_expenditure: number | null }) =>
                s + (Number(f.total_expenditure) || 0),
              0
            ) / count,
          avg_service_delivery_spend:
            provFinances.reduce(
              (s: number, f: { service_delivery_spend: number | null }) =>
                s + (Number(f.service_delivery_spend) || 0),
              0
            ) / count,
          municipality_count: provFinances.length,
        };
      }
    }

    // --- Build response objects ---
    const results = municipalities.map(
      (mun: {
        mun_code: string;
        mun_name: string;
        province: string;
        district: string;
        latitude: number;
        longitude: number;
        population: number;
        youth_population: number;
      }) => {
        const code = mun.mun_code;
        const finances = financesByMun[code] ?? [];
        const profiles = profilesByMun[code] ?? [];
        const pca = pcaByMun[code] ?? null;
        const unemployment = unempByMun[code] ?? [];

        return {
          municipality: {
            mun_code: code,
            mun_name: mun.mun_name,
            province: mun.province,
            district: mun.district,
            latitude: mun.latitude,
            longitude: mun.longitude,
            population: mun.population,
            youth_population: mun.youth_population,
          },
          finances: finances.length > 0 ? finances[0] : null,
          finance_history: finances,
          profile: profiles.length > 0 ? profiles[0] : null,
          pca: pca
            ? {
                pc1: pca.pc1,
                pc2: pca.pc2,
                pc3: pca.pc3,
                cluster: pca.cluster,
                profile_label: pca.profile_label,
                feature_loadings: pca.feature_loadings,
              }
            : null,
          unemployment: unemployment.length > 0 ? unemployment[0] : null,
          unemployment_history: unemployment,
          peer_comparison: provincialAverages[mun.province] ?? null,
        };
      }
    );

    // Return single object for mun_code queries, array otherwise
    if (munCode && results.length === 1) {
      return NextResponse.json({ data: results[0] });
    }

    return NextResponse.json({
      data: results,
      count: results.length,
    });
  } catch (err) {
    console.error("Municipal API error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupBy<T extends Record<string, unknown>>(
  items: T[],
  key: string
): Record<string, T[]> {
  const result: Record<string, T[]> = {};
  for (const item of items) {
    const k = String(item[key]);
    if (!result[k]) result[k] = [];
    result[k].push(item);
  }
  return result;
}

function indexBy<T extends Record<string, unknown>>(
  items: T[],
  key: string
): Record<string, T> {
  const result: Record<string, T> = {};
  for (const item of items) {
    result[String(item[key])] = item;
  }
  return result;
}
