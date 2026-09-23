export const pct = (v: number | null | undefined, digits = 0) =>
  v == null ? "no data" : `${(v * 100).toFixed(digits)}%`;

export const outOf10 = (v: number | null | undefined) => (v == null ? null : Math.round(v * 10));

export function rand(v: number | null | undefined): string {
  if (v == null) return "no data";
  const a = Math.abs(v);
  if (a >= 1e9) return `R${(v / 1e9).toFixed(a >= 1e10 ? 0 : 1)} billion`;
  if (a >= 1e6) return `R${(v / 1e6).toFixed(0)} million`;
  if (a >= 1e3) return `R${(v / 1e3).toFixed(0)} thousand`;
  return `R${v.toFixed(0)}`;
}

export const num = (v: number | null | undefined) =>
  v == null ? "no data" : Math.round(v).toLocaleString("en-ZA");

export type Status = "good" | "warn" | "serious" | "bad" | "none";

export function scoreStatus(score: number | null | undefined): Status {
  if (score == null) return "none";
  if (score >= 70) return "good";
  if (score >= 50) return "warn";
  if (score >= 35) return "serious";
  return "bad";
}

export const STATUS_WORDS: Record<Status, string> = {
  good: "Doing well",
  warn: "Getting by",
  serious: "Struggling",
  bad: "In trouble",
  none: "No data",
};

export const AUDIT_PLAIN: Record<string, string> = {
  unqualified: "Clean audit",
  unqualified_emphasis_of_matter: "Books OK, rules broken",
  qualified: "Some books wrong",
  adverse: "Books badly wrong",
  disclaimer: "Books could not be checked",
  outstanding: "Books not handed in",
};

export const AUDIT_STATUS: Record<string, Status> = {
  unqualified: "good",
  unqualified_emphasis_of_matter: "warn",
  qualified: "serious",
  adverse: "bad",
  disclaimer: "bad",
  outstanding: "bad",
};

export const PEER_NAMES: Record<string, string> = {
  A: "big cities",
  B1: "secondary cities",
  B2: "large towns",
  B3: "small towns",
  B4: "mostly rural areas",
};
