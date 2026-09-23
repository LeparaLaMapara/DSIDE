"use client";
// "Use my location" on the home page: finds the municipality the reader is
// standing in, then opens its page with their ward already found.
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LocateFixed } from "lucide-react";
import { contains, locate } from "@/lib/geo";

export function LocateMe() {
  const router = useRouter();
  const [msg, setMsg] = useState("");

  const go = async () => {
    setMsg("Finding you...");
    try {
      const { pt } = await locate();
      const munis: GeoJSON.FeatureCollection = await fetch("/geo/municipalities.geojson").then((r) => r.json());
      const hit = munis.features.find((f) => contains(f.geometry, pt));
      if (!hit) return setMsg("You seem to be outside South Africa's municipalities. Type a name instead.");
      setMsg(`You are in ${hit.properties?.name}. Opening it...`);
      router.push(`/m/${hit.properties?.code}/?locate=1`);
    } catch (err) {
      setMsg(`${(err as Error).message} Type the name of your area instead.`);
    }
  };

  return (
    <div>
      <button type="button" onClick={go} className="board inline-flex min-h-12 items-center gap-2 rounded px-4 text-lg font-bold">
        <LocateFixed size={20} aria-hidden /> Use my location
      </button>
      <p className="mt-1 text-sm text-muted" role="status">
        {msg || "Finds your municipality and your ward. Your location stays on your phone."}
      </p>
    </div>
  );
}
