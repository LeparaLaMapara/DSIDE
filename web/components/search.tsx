"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Search as SearchIcon } from "lucide-react";

export type SearchItem = { code: string; name: string; province: string };

export function Search({ items }: { items: SearchItem[] }) {
  const [q, setQ] = useState("");
  const hits = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (t.length < 2) return [];
    return items.filter((i) => i.name.toLowerCase().includes(t) || i.code.toLowerCase() === t).slice(0, 8);
  }, [q, items]);
  return (
    <div className="relative">
      <label htmlFor="muni-search" className="block font-bold">Find your municipality</label>
      <div className="mt-1 flex items-center gap-2 rounded border-2 border-foreground bg-surface px-3">
        <SearchIcon size={20} aria-hidden />
        <input id="muni-search" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off"
          placeholder="Type a name, e.g. Tshwane or Polokwane" className="min-h-12 w-full bg-transparent outline-none" />
      </div>
      {hits.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded border-2 border-foreground bg-surface shadow-lg">
          {hits.map((h) => (
            <li key={h.code}>
              <Link href={`/m/${h.code}`} className="flex min-h-11 items-center justify-between px-3 py-2 hover:bg-accent">
                <span className="font-bold">{h.name}</span><span className="text-sm text-muted">{h.province}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {q.trim().length >= 2 && hits.length === 0 && <p className="mt-1 text-sm text-muted">No municipality with that name. Try part of the name.</p>}
    </div>
  );
}
