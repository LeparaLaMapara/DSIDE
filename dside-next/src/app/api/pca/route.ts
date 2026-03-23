import { NextRequest, NextResponse } from "next/server";
import { createServiceClient } from "@/lib/supabase-server";

/**
 * GET /api/pca
 *
 * Returns PCA results for frontend visualisation.
 *
 * Query params:
 *   - province: filter by province name
 *   - cluster:  filter by cluster number (0-3)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const province = searchParams.get("province");
    const cluster = searchParams.get("cluster");

    const supabase = createServiceClient();

    // Build query for pca_results joined with municipalities for province info
    let query = supabase
      .from("pca_results")
      .select(
        `
        mun_code,
        pc1,
        pc2,
        pc3,
        cluster,
        profile_label,
        feature_loadings,
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
      );

    if (province) {
      query = query.eq("municipalities.province", province);
    }

    if (cluster !== null && cluster !== undefined) {
      const clusterNum = parseInt(cluster, 10);
      if (isNaN(clusterNum) || clusterNum < 0 || clusterNum > 3) {
        return NextResponse.json(
          { error: "Invalid cluster parameter. Must be 0-3." },
          { status: 400 }
        );
      }
      query = query.eq("cluster", clusterNum);
    }

    const { data, error } = await query;

    if (error) {
      console.error("Supabase error fetching PCA results:", error);
      return NextResponse.json(
        { error: "Failed to fetch PCA results", details: error.message },
        { status: 500 }
      );
    }

    // Flatten the nested municipalities object
    const results = (data ?? []).map((row: Record<string, unknown>) => {
      const municipality = row.municipalities as Record<string, unknown> | null;
      return {
        mun_code: row.mun_code,
        pc1: row.pc1,
        pc2: row.pc2,
        pc3: row.pc3,
        cluster: row.cluster,
        profile_label: row.profile_label,
        feature_loadings: row.feature_loadings,
        mun_name: municipality?.mun_name ?? null,
        province: municipality?.province ?? null,
        district: municipality?.district ?? null,
        latitude: municipality?.latitude ?? null,
        longitude: municipality?.longitude ?? null,
        population: municipality?.population ?? null,
        youth_population: municipality?.youth_population ?? null,
      };
    });

    return NextResponse.json({
      data: results,
      count: results.length,
    });
  } catch (err) {
    console.error("PCA API error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
