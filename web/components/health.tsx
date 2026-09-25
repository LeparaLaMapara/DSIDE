"use client";
// The /status page body: loaded in the browser from the `registry` branch, which
// every quarterly run updates (engine/dside_engine/health.py), so it is current
// even when a failed run kept the old data on the site.
import { useEffect, useState } from "react";

type Verdict = "ok" | "warn" | "fail";
type Source = { key: string; label: string; status: Verdict; fresh: boolean; fetched_at: string | null; age_days: number | null; rows: number | null; error: string | null };
type Finding = { rule: string; status: Verdict; detail: string; output: string | null };
type Task = { task: string; status: Verdict; ran: boolean; detail?: string; seconds?: number; expectations_checked?: number; gate?: Finding[]; outputs?: Record<string, number | null> };
type Score = { version: string; predicted_year: number; scored: boolean; n?: number; model_accuracy?: number; model_brier?: number; naive_accuracy?: number; naive_brier?: number };
type Model = { status: Verdict; decision?: string; reason?: string; live_version?: string | null; new_version?: string; used?: string; track_record?: Score[]; tested_on_year?: number; predicts_year?: number };
type Report = { checked_at: string; status: Verdict; run_url?: string | null; rules: { max_row_change: number; stale_days: number }; sources: Source[]; tasks: Task[]; model: Model | null };

/** Where the health file is: GitHub's raw file host (the `registry` branch), or a local copy in development. */
export const REGISTRY_BASE =
  process.env.NEXT_PUBLIC_REGISTRY_BASE ?? "https://raw.githubusercontent.com/ubunye-ai-ecosystems/masepala/registry";

const WORD: Record<Verdict, string> = { ok: "Healthy", warn: "Working, with warnings", fail: "Needs attention" };
const COLOUR: Record<Verdict, string> = { ok: "bg-good text-white", warn: "bg-warn text-foreground", fail: "bg-bad text-white" };

const STEP: Record<string, string> = {
  "01_ingest_money": "Collect money and audits (Treasury)",
  "02_ingest_people": "Collect people, crime and jobs",
  "03_ingest_places": "Collect places, wards and projects",
  "03b_ingest_fresh": "Collect newer figures (grants, water, schools, elections)",
  "04_analyse": "Work out scores and the audit prediction",
  "05_publish": "Write the files the site shows",
};

const DECISION: Record<string, string> = {
  promoted: "A newly trained version passed every check and is now used.",
  kept: "A newly trained version did not pass the checks, so the version already in use stays.",
  unchanged: "The audit history has not changed, so the version in use stays.",
  none: "No version has passed the checks yet, so the site shows the simple guess (same as last year).",
};

function Badge({ v }: { v: Verdict }) {
  return <span className={`inline-block rounded px-2 py-0.5 text-sm font-bold ${COLOUR[v]}`}>{WORD[v]}</span>;
}

const day = (iso: string | null) => (iso ? iso.slice(0, 10) : "unknown");

export function Health() {
  const [r, setR] = useState<Report | null | undefined>(undefined);
  useEffect(() => {
    fetch(`${REGISTRY_BASE}/monitoring/latest.json`, { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : null))
      .then(setR)
      .catch(() => setR(null));
  }, []);

  if (r === undefined) return <p className="text-muted">Loading the latest check…</p>;
  if (r === null) return <p className="text-muted">No health check has been published yet. It appears after the next collection.</p>;

  const stale = r.sources.filter((s) => !s.fresh);
  const m = r.model;

  return (
    <>
      <section className="card p-4">
        <p className="text-lg">
          Last check: <strong>{new Date(r.checked_at).toUTCString()}</strong> <Badge v={r.status} />
        </p>
        <p className="mt-2">
          {r.sources.length - stale.length} of {r.sources.length} sources answered.
          {stale.length > 0 && ` ${stale.length} could not be reached, so their last good copy was used.`}
        </p>
        {r.run_url && <p className="mt-1 text-sm"><a className="text-link underline" href={r.run_url} target="_blank" rel="noopener">See the run on GitHub</a></p>}
      </section>

      <section>
        <h2 className="font-display text-2xl">Sources</h2>
        <p className="mt-1 text-sm text-muted">A copy older than {r.rules.stale_days} days counts as a failure.</p>
        <div className="scroll-x mt-3">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b-2 border-foreground"><th className="py-1">Source</th><th>State</th><th>Data from</th><th>Rows</th></tr>
            </thead>
            <tbody>
              {r.sources.map((s) => (
                <tr key={s.key} className="border-b border-border align-top">
                  <td className="py-1 pr-2">{s.label.replace(/_/g, " ")}</td>
                  <td className="pr-2">{s.fresh ? "Fresh" : <span title={s.error ?? ""}>Last good copy ({s.age_days} days old)</span>}</td>
                  <td className="pr-2">{day(s.fetched_at)}</td>
                  <td>{s.rows?.toLocaleString("en-ZA") ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="font-display text-2xl">Checks on each step</h2>
        <p className="mt-1 text-sm">
          Every step declares what its data must look like (for example: every ward has one code, shares lie between 0 and 1,
          at least 4,000 wards). The Ubunye Engine checks these before anything is written, then compares the run with the last
          one: a table whose size moved by more than {Math.round(r.rules.max_row_change * 100)}% fails.
        </p>
        <ul className="mt-3 space-y-3">
          {r.tasks.map((t) => (
            <li key={t.task} className="card p-3">
              <p className="flex flex-wrap items-center gap-2"><strong>{STEP[t.task] ?? t.task}</strong> <Badge v={t.status} /></p>
              {!t.ran && <p className="mt-1 text-sm">{t.detail}</p>}
              {t.ran && <p className="mt-1 text-sm text-muted">{t.expectations_checked} checks{t.seconds != null && `, ${Math.round(t.seconds)} s`}</p>}
              {t.gate && t.gate.length > 0 && (
                <ul className="mt-1 list-disc pl-5 text-sm">
                  {t.gate.map((g, i) => <li key={i}>{g.output ? `${g.output}: ` : ""}{g.detail}</li>)}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </section>

      {m && m.decision && (
        <section>
          <h2 className="font-display text-2xl">The audit prediction</h2>
          <p className="mt-2">{DECISION[m.decision] ?? m.decision}</p>
          {m.decision === "kept" && m.reason && <p className="mt-1 text-sm text-muted">Why: {m.reason}</p>}
          <p className="mt-1 text-sm">
            Version in use: {m.live_version ?? "none (simple guess)"}. Every version is kept in a model registry with its test
            scores, and only goes live if it beats the simple guess and the version already in use.
          </p>
          {m.track_record && m.track_record.length > 0 && (
            <>
              <h3 className="mt-4 font-bold">Did past predictions come true?</h3>
              <div className="scroll-x mt-2">
                <table className="w-full min-w-[480px] text-left text-sm">
                  <thead>
                    <tr className="border-b-2 border-foreground"><th className="py-1">Version</th><th>Predicted year</th><th>Model right</th><th>Simple guess right</th></tr>
                  </thead>
                  <tbody>
                    {m.track_record.map((s) => (
                      <tr key={s.version} className="border-b border-border">
                        <td className="py-1">{s.version}</td>
                        <td>{s.predicted_year}</td>
                        <td>{s.scored ? `${((s.model_accuracy ?? 0) * 100).toFixed(1)}%` : "not published yet"}</td>
                        <td>{s.scored ? `${((s.naive_accuracy ?? 0) * 100).toFixed(1)}%` : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </>
  );
}
