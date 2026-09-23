// Split the engine's output into small files the browser loads on demand:
// one national map, and one ward map and project list per municipality.
// Runs before every build (npm "prebuild").
import fs from "node:fs";
import path from "node:path";

const data = (f) => JSON.parse(fs.readFileSync(path.join("data", f), "utf8"));
const out = (f, v) => {
  const p = path.join("public", "geo", f);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(v));
};


const munis = new Map(data("municipalities.json").map((m) => [m.code, m]));
const features = data("boundaries.json")
  .filter((b) => !b.code.startsWith("DC"))
  .map((b) => {
    const m = munis.get(b.code) ?? {};
    return {
      type: "Feature",
      id: b.code,
      geometry: JSON.parse(b.geometry),
      properties: {
        code: b.code, name: b.name, wellbeing: m.wellbeing, money: m.money_score,
        water: m.water, lighting: m.lighting, murder: m.murder_rate, audit: m.audit_code,
      },
    };
  });
out("municipalities.geojson", { type: "FeatureCollection", features });

const wards = {};
for (const w of data("wards.json")) {
  (wards[w.code] ??= []).push({
    type: "Feature",
    id: Number(w.ward_id),
    geometry: JSON.parse(w.geometry),
    properties: Object.fromEntries(Object.entries(w).filter(([k]) => k !== "geometry")),
  });
}
for (const [code, fs_] of Object.entries(wards)) out(`wards/${code}.geojson`, { type: "FeatureCollection", features: fs_ });

const projects = {};
for (const p of data("projects.json")) {
  (projects[p.code] ??= []).push({
    n: p.name, s: p.sector, st: p.stage, c: p.estimated_total_project_cost,
    lat: p.latitude, lng: p.longitude, u: p.url_path,
  });
}
for (const [code, list] of Object.entries(projects)) out(`projects/${code}.json`, list);
// MapLibre runs its map work in a web worker that bundlers cannot follow, so
// ship the worker (and the chunk it imports) as plain static files.
fs.mkdirSync(path.join("public", "maplibre"), { recursive: true });
for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  fs.copyFileSync(path.join("node_modules", "maplibre-gl", "dist", f), path.join("public", "maplibre", f));
}

console.log(`prepared ${features.length} municipalities, ${Object.keys(wards).length} ward maps, ${Object.keys(projects).length} project lists`);

