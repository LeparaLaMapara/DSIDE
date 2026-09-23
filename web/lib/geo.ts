// Small geometry helpers that run in the browser, so a reader's location
// never has to leave their phone.

export type LngLat = [number, number];

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
