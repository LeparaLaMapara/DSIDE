// Reads the files the Ubunye pipeline writes to web/data. Runs at build time
// only (server components), so none of this reaches the browser as code.
import fs from "node:fs";
import path from "node:path";

export type Item = {
  measure: string;
  label: string;
  value: number;
  peer_median: number;
  peer_pct: number;
  higher_is_better: boolean;
  best_peer: string | null;
};

export type StoryLine = { topic: "services" | "money" | "water" | "safety" | "work"; tone: "good" | "bad" | "mixed"; text: string; source: string };

export type Reason = { kind: "money" | "honesty" | "pressure"; text: string; evidence: string };

export type Muni = {
  code: string;
  name: string;
  kind: "metro" | "local" | "district";
  province: string;
  province_name: string;
  peer_group: string | null;
  parent: string;
  phone: string | null;
  website: string | null;
  year: number | null;
  population_2022: number | null;
  population_growth: number | null;
  households_2022: number | null;
  wellbeing: number | null;
  rank: number | null;
  rank_best: number | null;
  rank_worst: number | null;
  ranked_out_of: number | null;
  money_score: number | null;
  group: string | null;
  audit_code: string | null;
  audit_url: string | null;
  audit_history: string[];
  chance_unqualified: number | null;
  predicted_year: number | null;
  strengths: Item[];
  problems: Item[];
  reasons: Reason[];
  planned_by_service: { service: string; amount: number }[];
  unemployment_trend: number[] | null;
  headline: string | null;
  story: StoryLine[];
  warnings: string[];
  [key: string]: unknown;
};

const dir = path.join(process.cwd(), "data");
const read = <T,>(f: string): T => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
const parse = (v: unknown) => (typeof v === "string" && /^[[{]/.test(v) ? JSON.parse(v) : v);

const LISTS = ["strengths", "problems", "reasons", "planned_by_service", "audit_history", "warnings", "unemployment_trend", "story", "officials", "grants", "residents_say", "siu"];

let cache: Muni[] | null = null;
export function municipalities(): Muni[] {
  if (!cache) {
    cache = read<Record<string, unknown>[]>("municipalities.json").map((r) => {
      const m = { ...r } as Record<string, unknown>;
      for (const k of LISTS) m[k] = parse(m[k]) ?? [];
      return m as Muni;
    });
  }
  return cache;
}

export const serving = () => municipalities().filter((m) => m.kind !== "district");
export const byCode = (code: string) => municipalities().find((m) => m.code === code);

export type Station = {
  station: string;
  muni_code: string;
  precinct_population: number;
  murder_rate: number;
  [k: string]: unknown;
};
export function stations(code: string): Station[] {
  return read<Station[]>("stations.json")
    .filter((s) => s.muni_code === code)
    .map((s) => {
      const out = { ...s } as Record<string, unknown>;
      for (const k of Object.keys(out)) if (k.endsWith("_trend")) out[k] = parse(out[k]);
      return out as Station;
    });
}

export type Meta = {
  built_at: string;
  money_year: number;
  groups: { method: string; services_median: number; money_median: number; sizes: Record<string, number>; kmeans_silhouette_by_k: Record<string, number> };
  audit_model: {
    question: string; trained_on_years: string; tested_on_year: number; model: string; model_beats_naive: boolean; predicts_year: number;
    test: { n: number; model_accuracy: number; model_balanced_accuracy: number; model_brier: number; naive_accuracy: number; naive_balanced_accuracy: number; naive_brier: number };
  };
  national: Record<string, number>;
  dimensions: Record<string, string>;
  safety: { period: string; year: number; years: number[]; labels: Record<string, string>; source: string; unmatched_stations: string };
  jobs: { period: string; periods: string[]; national_unemployment: number; youth_unemployment_15_34: number; source: string };
};
export const meta = (): Meta => JSON.parse(read<{ json: string }[]>("meta.json")[0].json);
