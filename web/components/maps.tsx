"use client";
// Two maps. The national one colours every municipality by one measure and
// opens its page on click. The ward one zooms into a municipality, finds
// the reader's ward from their location, and shows government projects.
import * as maplibregl from "maplibre-gl";
import type { ExpressionSpecification, GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { LocateFixed } from "lucide-react";

const BASEMAP = "https://tiles.openfreemap.org/styles/positron";
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs"); // copied there by scripts/prepare.mjs
const BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
const ORANGE = ["#fde0cf", "#f5a77f", "#eb6834", "#b8461c", "#7a2c0f"];
const NO_DATA = "#e1e0d9";

type Measure = { key: string; label: string; ramp: string[]; fmt: (v: number) => string; lowIsGood?: boolean; note: string };

// One decimal near the top, where most wards in a city sit and whole numbers would all read "99%".
const pctFmt = (v: number) => (v >= 0.95 && v < 1 ? `${(v * 100).toFixed(1)}%` : `${Math.round(v * 100)}%`);
const scoreFmt = (v: number) => `${Math.round(v)}`;

export const NATIONAL_MEASURES: Measure[] = [
  { key: "wellbeing", label: "Life here", ramp: BLUE, fmt: scoreFmt, note: "Wellbeing score out of 100: homes and services, learning, work and safety" },
  { key: "money", label: "Money handling", ramp: BLUE, fmt: scoreFmt, note: "Score out of 100 for how well the municipality handles public money" },
  { key: "water", label: "Tap water", ramp: BLUE, fmt: pctFmt, note: "People with tap water at home or within 200 m (Census 2022)" },
  { key: "murder", label: "Murders", ramp: ORANGE, fmt: (v) => `${v.toFixed(1)} per 100 000`, lowIsGood: true, note: "Murders per 100 000 people in the latest 3 months (SAPS)" },
];

function breaks(values: number[]): number[] {
  const v = values.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  return [0.2, 0.4, 0.6, 0.8].map((q) => v[Math.floor(q * (v.length - 1))]);
}

function colourExpr(prop: string, b: number[], ramp: string[]): ExpressionSpecification {
  return ["case", ["==", ["get", prop], null], NO_DATA,
    ["step", ["get", prop], ramp[0], b[0], ramp[1], b[1], ramp[2], b[2], ramp[3], b[3], ramp[4]]] as ExpressionSpecification;
}

function Legend({ b, m }: { b: number[]; m: Measure }) {
  const edges = [null, ...b];
  return (
    <div className="mt-2 text-sm">
      <p className="text-muted">{m.note}</p>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
        {m.ramp.map((c, i) => (
          <span key={c} className="inline-flex items-center gap-1">
            <span className="inline-block h-3.5 w-5 rounded-sm border border-border" style={{ background: c }} />
            <span className="tabular">{i === 0 ? `under ${m.fmt(b[0])}` : i === 4 ? `${m.fmt(b[3])}+` : `${m.fmt(edges[i]!)}+`}</span>
          </span>
        ))}
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3.5 w-5 rounded-sm border border-border" style={{ background: NO_DATA }} />no data
        </span>
      </div>
      <p className="mt-1 text-muted">{m.lowIsGood ? "Darker means more, which is worse." : "Darker means better."}</p>
    </div>
  );
}

function Chips<T extends { key: string; label: string }>({ items, value, onChange, name }: {
  items: T[]; value: string; onChange: (k: string) => void; name: string;
}) {
  return (
    <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={name}>
      {items.map((i) => (
        <button key={i.key} type="button" role="radio" aria-checked={value === i.key} onClick={() => onChange(i.key)}
          className={`min-h-11 rounded border-2 px-3 text-sm font-bold transition-colors duration-[var(--duration-fast)] ${
            value === i.key ? "border-foreground bg-accent text-accent-ink" : "border-border bg-surface hover:border-foreground"}`}>
          {i.label}
        </button>
      ))}
    </div>
  );
}

export function NationalMap() {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [data, setData] = useState<GeoJSON.FeatureCollection | null>(null);
  const [key, setKey] = useState("wellbeing");
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const measure = NATIONAL_MEASURES.find((m) => m.key === key)!;
  const b = useMemo(() => (data ? breaks(data.features.map((f) => f.properties?.[key] as number)) : [0, 0, 0, 0]), [data, key]);

  useEffect(() => {
    fetch("/geo/municipalities.geojson").then((r) => r.json()).then(setData);
  }, []);

  useEffect(() => {
    if (!box.current || !data || map.current) return;
    const m = new maplibregl.Map({ container: box.current, style: BASEMAP, bounds: [16.3, -34.9, 33, -22.1],
      fitBoundsOptions: { padding: 10 }, attributionControl: { compact: true }, cooperativeGestures: true });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
    m.on("load", () => {
      m.addSource("munis", { type: "geojson", data });
      m.addLayer({ id: "fill", type: "fill", source: "munis", paint: { "fill-color": NO_DATA, "fill-opacity": 0.85 } });
      m.addLayer({ id: "line", type: "line", source: "munis", paint: { "line-color": "#ffffff", "line-width": 0.8 } });
      m.addLayer({ id: "hover", type: "line", source: "munis", paint: { "line-color": "#141414", "line-width": 2.5 },
        filter: ["==", ["get", "code"], ""] });
      setReady(true);
    });
    m.on("mousemove", "fill", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      m.getCanvas().style.cursor = "pointer";
      m.setFilter("hover", ["==", ["get", "code"], f.properties.code]);
      popup.setLngLat(e.lngLat).setHTML(`<strong>${f.properties.name}</strong><br/>Tap to open`).addTo(m);
    });
    m.on("mouseleave", "fill", () => { m.getCanvas().style.cursor = ""; popup.remove(); m.setFilter("hover", ["==", ["get", "code"], ""]); });
    m.on("click", "fill", (e) => { const c = e.features?.[0]?.properties?.code; if (c) router.push(`/m/${c}`); });
    return () => { m.remove(); map.current = null; setReady(false); };
  }, [data, router]);

  useEffect(() => {
    if (ready) map.current?.setPaintProperty("fill", "fill-color", colourExpr(key, b, measure.ramp));
  }, [ready, key, b, measure]);

  return (
    <div>
      <Chips items={NATIONAL_MEASURES} value={key} onChange={setKey} name="What to show on the map" />
      <div ref={box} className="mt-3 h-[420px] w-full overflow-hidden rounded border border-border sm:h-[520px]"
        aria-label="Map of South Africa's municipalities" role="region" />
      <Legend b={b} m={measure} />
    </div>
  );
}

// ---------------------------------------------------------------------------

type WardProps = {
  ward_no: number; population: number; water: number | null; toilet: number | null; refuse: number | null;
  unemployment: number | null; matric_or_more: number | null; councillor?: string | null; party?: string | null; phone?: string | null;
};

const WARD_MEASURES: Measure[] = [
  { key: "water", label: "Tap water", ramp: BLUE, fmt: pctFmt, note: "People with tap water at home, in the yard or within 200 m" },
  { key: "unemployment", label: "Unemployment", ramp: ORANGE, fmt: pctFmt, lowIsGood: true, note: "Share of people who want work and have none" },
  { key: "refuse", label: "Rubbish collected", ramp: BLUE, fmt: pctFmt, note: "People whose rubbish is collected every week" },
  { key: "toilet", label: "Proper toilets", ramp: BLUE, fmt: pctFmt, note: "People with a flush or ventilated pit toilet" },
];

type Project = { n: string; s: string; st: string; c: number | null; lat: number; lng: number; u: string };
const STAGE_COLOUR: Record<string, string> = { Planned: "#86b6ef", "Being built": "#eda100", Finished: "#0ca30c", "Stopped or on hold": "#d03b3b" };

function inRing(pt: [number, number], ring: number[][]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (yi > pt[1] !== yj > pt[1] && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
function contains(g: GeoJSON.Geometry, pt: [number, number]) {
  const polys = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
  return polys.some((p) => inRing(pt, p[0]) && !p.slice(1).some((h) => inRing(pt, h)));
}

export function WardMap({ code, wardYearNote }: { code: string; wardYearNote: string }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [wards, setWards] = useState<GeoJSON.FeatureCollection | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [key, setKey] = useState("water");
  const [selected, setSelected] = useState<WardProps | null>(null);
  const [ready, setReady] = useState(false);
  const [locMsg, setLocMsg] = useState("");
  const measure = WARD_MEASURES.find((m) => m.key === key)!;
  const b = useMemo(() => (wards ? breaks(wards.features.map((f) => f.properties?.[key] as number)) : [0, 0, 0, 0]), [wards, key]);

  useEffect(() => {
    fetch(`/geo/wards/${code}.geojson`).then((r) => r.json()).then(setWards).catch(() => setWards(null));
    fetch(`/geo/projects/${code}.json`).then((r) => (r.ok ? r.json() : [])).then(setProjects).catch(() => setProjects([]));
  }, [code]);

  useEffect(() => {
    if (!box.current || !wards || map.current) return;
    const bbox = wards.features.reduce((acc, f) => {
      const walk = (c: unknown): void => {
        if (typeof (c as number[])[0] === "number") {
          const [x, y] = c as number[];
          acc[0] = Math.min(acc[0], x); acc[1] = Math.min(acc[1], y); acc[2] = Math.max(acc[2], x); acc[3] = Math.max(acc[3], y);
        } else (c as unknown[]).forEach(walk);
      };
      walk((f.geometry as GeoJSON.Polygon).coordinates);
      return acc;
    }, [180, 90, -180, -90]);
    const m = new maplibregl.Map({ container: box.current, style: BASEMAP, bounds: bbox as [number, number, number, number],
      fitBoundsOptions: { padding: 16 }, attributionControl: { compact: true }, cooperativeGestures: true });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      m.addSource("wards", { type: "geojson", data: wards });
      m.addLayer({ id: "fill", type: "fill", source: "wards", paint: { "fill-color": NO_DATA, "fill-opacity": 0.75 } });
      m.addLayer({ id: "line", type: "line", source: "wards", paint: { "line-color": "#ffffff", "line-width": 1 } });
      m.addLayer({ id: "sel", type: "line", source: "wards", paint: { "line-color": "#141414", "line-width": 3.5 }, filter: ["==", ["get", "ward_no"], -1] });
      m.addLayer({ id: "labels", type: "symbol", source: "wards", minzoom: 10.5,
        layout: { "text-field": ["to-string", ["get", "ward_no"]], "text-size": 11 },
        paint: { "text-color": "#141414", "text-halo-color": "#ffffff", "text-halo-width": 1.5 } });
      m.addSource("projects", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "projects", type: "circle", source: "projects", paint: {
        "circle-radius": 5, "circle-stroke-width": 1.5, "circle-stroke-color": "#141414",
        "circle-color": ["match", ["get", "st"], ...Object.entries(STAGE_COLOUR).flat(), "#898781"] as unknown as ExpressionSpecification } });
      setReady(true);
    });
    m.on("click", "fill", (e) => setSelected((e.features?.[0]?.properties as WardProps) ?? null));
    m.on("click", "projects", (e) => {
      const p = e.features?.[0]?.properties;
      if (p) new maplibregl.Popup().setLngLat(e.lngLat)
        .setHTML(`<strong>${p.n}</strong><br/>${p.s} · ${p.st}<br/><a href="https://vulekamali.gov.za${p.u}" target="_blank" rel="noopener">Details on Vulekamali</a>`).addTo(m);
    });
    return () => { m.remove(); map.current = null; setReady(false); };
  }, [wards]);

  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    m.setPaintProperty("fill", "fill-color", colourExpr(key, b, measure.ramp));
    (m.getSource("projects") as GeoJSONSource).setData({ type: "FeatureCollection", features: projects.map((p) => ({
      type: "Feature", properties: p, geometry: { type: "Point", coordinates: [p.lng, p.lat] } })) });
    m.setFilter("sel", ["==", ["get", "ward_no"], selected?.ward_no ?? -1]);
  }, [ready, key, b, measure, projects, selected]);

  const findMe = () => {
    if (!navigator.geolocation) return setLocMsg("Your browser cannot share your location. Choose your ward from the list instead.");
    setLocMsg("Finding you...");
    navigator.geolocation.getCurrentPosition((pos) => {
      const pt: [number, number] = [pos.coords.longitude, pos.coords.latitude];
      const hit = wards?.features.find((f) => contains(f.geometry, pt));
      if (!hit) return setLocMsg("You seem to be outside this municipality. Choose a ward from the list.");
      setSelected(hit.properties as WardProps);
      setLocMsg("");
      map.current?.flyTo({ center: pt, zoom: 12 });
    }, () => setLocMsg("Location was not shared. Choose your ward from the list instead."), { timeout: 10000 });
  };

  const list = wards?.features.map((f) => f.properties as WardProps).sort((a, b2) => a.ward_no - b2.ward_no) ?? [];
  const stages = Object.keys(STAGE_COLOUR).map((s) => ({ s, n: projects.filter((p) => p.st === s).length }));

  if (!wards) return <p className="text-muted">Ward map loading...</p>;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={findMe}
          className="board inline-flex min-h-11 items-center gap-2 rounded px-3 font-bold">
          <LocateFixed size={18} aria-hidden /> Find my ward
        </button>
        <label className="inline-flex items-center gap-2 text-sm">
          <span>or choose</span>
          <select className="min-h-11 rounded border-2 border-border bg-surface px-2" value={selected?.ward_no ?? ""}
            onChange={(e) => setSelected(list.find((w) => w.ward_no === Number(e.target.value)) ?? null)}>
            <option value="">Ward...</option>
            {list.map((w) => <option key={w.ward_no} value={w.ward_no}>Ward {w.ward_no}</option>)}
          </select>
        </label>
      </div>
      {locMsg && <p className="mt-2 text-sm text-muted" role="status">{locMsg}</p>}
      <div className="mt-3"><Chips items={WARD_MEASURES} value={key} onChange={setKey} name="What to show on the ward map" /></div>
      <div className="mt-3 grid gap-4 lg:grid-cols-[1fr_320px]">
        <div>
          <div ref={box} className="h-[420px] w-full overflow-hidden rounded border border-border" role="region" aria-label="Ward map" />
          <Legend b={b} m={measure} />
          <p className="mt-1 text-sm text-muted">{wardYearNote}</p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <span className="font-bold">Government projects on the map:</span>
            {stages.map(({ s, n }) => (
              <span key={s} className="inline-flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded-full border border-foreground" style={{ background: STAGE_COLOUR[s] }} />
                {s} ({n})
              </span>
            ))}
          </div>
        </div>
        <aside className="card p-4" aria-live="polite">
          {!selected ? (
            <p className="text-muted">Tap a ward on the map, use <strong>Find my ward</strong>, or pick one from the list.</p>
          ) : (
            <div>
              <h3 className="font-display text-2xl">Ward {selected.ward_no}</h3>
              <p className="text-muted">{Math.round(selected.population).toLocaleString("en-ZA")} people</p>
              <dl className="mt-3 space-y-2">
                {[["Tap water nearby", selected.water], ["Proper toilet", selected.toilet], ["Rubbish collected weekly", selected.refuse],
                  ["Unemployed (of those who want work)", selected.unemployment], ["Adults with matric or more", selected.matric_or_more]]
                  .map(([l, v]) => (
                    <div key={l as string}>
                      <dt className="text-sm">{l as string}</dt>
                      <dd className="flex items-center gap-2">
                        <span className="h-2 flex-1 rounded bg-sunk"><span className="block h-2 rounded bg-seq-4" style={{ width: `${((v as number) ?? 0) * 100}%` }} /></span>
                        <span className="w-12 text-right font-bold tabular">{v == null ? "?" : `${Math.round((v as number) * 100)}%`}</span>
                      </dd>
                    </div>
                  ))}
              </dl>
              {selected.councillor ? (
                <div className="mt-4 rounded border-2 border-foreground p-3">
                  <p className="text-sm text-muted">Your ward councillor</p>
                  <p className="text-lg font-bold">{selected.councillor}</p>
                  <p className="text-sm">{selected.party}</p>
                  {selected.phone && <a className="mt-1 inline-block font-bold text-link underline" href={`tel:${selected.phone.replace(/\s/g, "")}`}>{selected.phone}</a>}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted">Ask the municipality for your ward councillor's details. This city does not publish them in a form we can read yet.</p>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
