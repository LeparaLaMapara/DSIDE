// Small geometry helpers that run in the browser, so a reader's location
// never has to leave their phone.

export type LngLat = [number, number];

const R = 6_371_008.8; // mean Earth radius in metres
const rad = (d: number) => (d * Math.PI) / 180;

/** Great-circle distance in metres. */
export function distanceM(a: LngLat, b: LngLat): number {
  const dLat = rad(b[1] - a[1]);
  const dLng = rad(b[0] - a[0]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** A circle as a GeoJSON polygon (64 points), for drawing. */
export function circle(center: LngLat, radiusM: number, steps = 64): GeoJSON.Feature<GeoJSON.Polygon> {
  const [lng, lat] = center;
  const ring: number[][] = [];
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * 2 * Math.PI;
    const dLat = (radiusM * Math.cos(t)) / R;
    const dLng = (radiusM * Math.sin(t)) / (R * Math.cos(rad(lat)));
    ring.push([lng + (dLng * 180) / Math.PI, lat + (dLat * 180) / Math.PI]);
  }
  return { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [ring] } };
}

function inRing(pt: LngLat, ring: number[][]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (yi > pt[1] !== yj > pt[1] && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function polygons(g: GeoJSON.Geometry): number[][][][] {
  return g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
}

/** Is the point inside the (multi)polygon, holes excluded? */
export function contains(g: GeoJSON.Geometry, pt: LngLat): boolean {
  return polygons(g).some((p) => inRing(pt, p[0]) && !p.slice(1).some((h) => inRing(pt, h)));
}

/** Shortest distance in metres from the point to the shape (0 when inside).
 *  Uses a flat projection around the point, accurate to well under 1% at ward scale. */
export function distanceToShapeM(g: GeoJSON.Geometry, pt: LngLat): number {
  if (contains(g, pt)) return 0;
  const kx = R * rad(1) * Math.cos(rad(pt[1]));
  const ky = R * rad(1);
  let best = Infinity;
  for (const poly of polygons(g)) {
    for (const ring of poly) {
      for (let i = 1; i < ring.length; i++) {
        const ax = (ring[i - 1][0] - pt[0]) * kx, ay = (ring[i - 1][1] - pt[1]) * ky;
        const bx = (ring[i][0] - pt[0]) * kx, by = (ring[i][1] - pt[1]) * ky;
        const dx = bx - ax, dy = by - ay;
        const len2 = dx * dx + dy * dy;
        const t = len2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2)) : 0;
        best = Math.min(best, Math.hypot(ax + t * dx, ay + t * dy));
      }
    }
  }
  return best;
}

/** Ask the phone for its location once. Rejects with a plain-language message. */
export function locate(): Promise<{ pt: LngLat; accuracyM: number }> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      reject(new Error("Your browser cannot share your location."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ pt: [pos.coords.longitude, pos.coords.latitude], accuracyM: pos.coords.accuracy }),
      (err) => reject(new Error(err.code === err.PERMISSION_DENIED ? "Location was not shared." : "Your location could not be found.")),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  });
}
