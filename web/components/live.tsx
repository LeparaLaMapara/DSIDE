"use client";
// "What's happening now": loaded in the browser from the small files the live
// pipeline refreshes every few hours, so it can be newer than the page itself.
import { useEffect, useState } from "react";
import { Newspaper, Zap, ZapOff } from "lucide-react";

type News = { title: string; url: string; outlet: string; published: string; place: string; code: string; event: string; also_reported_by?: string | null };
type Status = { stage: number; checked_at: string };
type FaultWard = { code: string; ward_id: string; suburbs?: string | null; open_faults: number; oldest_open_hours: number | null; median_repair_hours?: number | null; fixed_60d?: number | null };

/** Where the live files are: GitHub's raw file host in production (refreshed
 * every few hours without rebuilding the site), or the local copy in development. */
export const LIVE_BASE = process.env.NEXT_PUBLIC_LIVE_BASE ?? "/live";

/** Cities whose own outage map we read. */
export const FAULT_CITIES = ["TSH"];

const EVENT_LABEL: Record<string, string> = {
  water: "Water", electricity: "Electricity", sewage: "Sewage", roads: "Roads", protest: "Protest", crime: "Crime",
  gbv: "Gender-based violence", corruption: "Corruption", jobs: "Jobs", housing: "Housing", health: "Health", education: "Education",
};

const ago = (iso: string) => {
  const h = (Date.now() - new Date(iso).getTime()) / 36e5;
  if (!Number.isFinite(h)) return "";
  if (h < 1) return "less than an hour ago";
  if (h < 48) return `${Math.round(h)} hours ago`;
  return `${Math.round(h / 24)} days ago`;
};

export function LiveNow({ code, name }: { code: string; name: string }) {
  const [news, setNews] = useState<News[] | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [wards, setWards] = useState<FaultWard[]>([]);

  useEffect(() => {
    fetch(`${LIVE_BASE}/news.json`).then((r) => r.json()).then((all: News[]) => setNews(all.filter((n) => n.code === code))).catch(() => setNews([]));
    fetch(`${LIVE_BASE}/status.json`).then((r) => r.json()).then((s: Status[]) => setStatus(s[0] ?? null)).catch(() => setStatus(null));
    if (FAULT_CITIES.includes(code)) {
      fetch(`${LIVE_BASE}/fault_wards.json`).then((r) => r.json()).then((w: FaultWard[]) => setWards(w.filter((x) => x.code === code))).catch(() => setWards([]));
    }
  }, [code]);

  const openFaults = wards.reduce((s, w) => s + (w.open_faults ?? 0), 0);
  const worst = [...wards].sort((a, b) => (b.open_faults ?? 0) - (a.open_faults ?? 0)).slice(0, 5);

  return (
    <section aria-labelledby="now" className="space-y-4">
      <h2 id="now" className="font-display text-2xl">What&apos;s happening now</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="card p-4">
          <p className="inline-flex items-center gap-2 font-bold">{status?.stage ? <ZapOff aria-hidden /> : <Zap aria-hidden />}Loadshedding</p>
          <p className="mt-1 font-display text-3xl">{status == null ? "..." : status.stage ? `Stage ${status.stage}` : "None"}</p>
          <p className="text-xs text-muted">Eskom, checked {status ? ago(status.checked_at) : "..."}.</p>
        </div>
        {FAULT_CITIES.includes(code) && (
          <div className="card p-4 md:col-span-2">
            <p className="inline-flex items-center gap-2 font-bold"><ZapOff aria-hidden />Open electricity faults</p>
            <p className="mt-1 font-display text-3xl">{openFaults || "..."}</p>
            <p className="text-sm">reported on the city&apos;s own outage map right now. Wards with the most:</p>
            <ul className="mt-1 flex flex-wrap gap-2 text-sm">
              {worst.map((w) => (
                <li key={w.ward_id} className="rounded bg-sunk px-2 py-1">Ward {Number(w.ward_id.slice(-3))}{w.suburbs ? ` (${w.suburbs})` : ""}: <strong>{w.open_faults}</strong>
                  {w.median_repair_hours != null && <>, fixed in about {Math.round(w.median_repair_hours)} h</>}</li>
              ))}
            </ul>
            <p className="mt-1 text-xs text-muted">Each number is a household report. One big failure, like a substation, can bring hundreds of reports from one suburb. We check every few hours, so repair times build up over the coming weeks.</p>
          </div>
        )}
      </div>
      <div className="card p-4">
        <p className="inline-flex items-center gap-2 font-bold"><Newspaper aria-hidden />In the news</p>
        <p className="text-xs text-muted">Headlines that name a place in {name}, matched by computer, not checked by a person. Read the full story at the source.</p>
        {news == null ? <p className="mt-2 text-muted">Loading...</p> : news.length === 0 ? (
          <p className="mt-2 text-muted">No recent headlines matched a place here.</p>
        ) : (
          <ul className="mt-3 divide-y divide-border">
            {news.map((n) => (
              <li key={n.url} className="py-2">
                <a href={n.url} target="_blank" rel="noopener" className="font-bold text-link underline">{n.title}</a>
                <p className="text-sm text-muted">
                  <span className="mr-2 rounded bg-sunk px-1.5 py-0.5 text-xs font-bold text-foreground">{EVENT_LABEL[n.event] ?? n.event}</span>
                  {n.outlet} · {ago(n.published)} · mentions {n.place}{n.also_reported_by ? ` · also in ${n.also_reported_by}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
