import { NationalMap } from "@/components/maps";
import { Search } from "@/components/search";
import { meta, serving } from "@/lib/data";
import { rand } from "@/lib/format";
import Link from "next/link";

const fy = (y: number) => `${y - 1}-${String(y).slice(2)}`;

export default function Home() {
  const m = meta();
  const n = m.national;
  const munis = serving();
  const items = munis.map((x) => ({ code: x.code, name: x.name, province: x.province_name }));
  const noWater = Math.round((1 - n["share:water"]) * 100);
  const quadrants = Object.entries(m.groups.sizes);
  const worst = [...munis].filter((x) => x.wellbeing != null).sort((a, b) => a.wellbeing! - b.wellbeing!).slice(0, 5);

  return (
    <div className="space-y-12 pt-8">
      <section className="space-y-5">
        <h1 className="font-display text-4xl leading-tight sm:text-6xl">You are the government.</h1>
        <p className="max-w-2xl text-xl">
          See what your municipality is supposed to do, what it did with the money, how people live there,
          and what <strong>you</strong> can do about it.
        </p>
        <div className="max-w-xl"><Search items={items} /></div>
      </section>

      <section aria-labelledby="pulse">
        <h2 id="pulse" className="font-display text-2xl">South Africa right now</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Tile big={`${n.clean_audits} of ${n.audited}`} text={`municipalities got a clean audit for ${fy(m.money_year)}.`} />
          <Tile big={rand(n.wasted)} text={`spent against the rules or wasted by municipalities in ${fy(m.money_year)}.`} />
          <Tile big={`${m.jobs.youth_unemployment_15_34}%`} text={`of young people (15 to 34) who want work have none (${m.jobs.period}).`} />
          <Tile big={`${noWater} in 100`} text="people do not have tap water at home or within 200 metres (Census 2022)." />
        </div>
      </section>

      <section aria-labelledby="map">
        <h2 id="map" className="font-display text-2xl">Every municipality on one map</h2>
        <p className="mt-1 text-muted">Choose what to colour the map by. Tap a municipality to open its page.</p>
        <div className="mt-3"><NationalMap /></div>
      </section>

      <section aria-labelledby="kinds" className="grid gap-6 md:grid-cols-2">
        <div>
          <h2 id="kinds" className="font-display text-2xl">Four kinds of municipality</h2>
          <p className="mt-2">
            We place every municipality on two questions: <strong>do people get basic services?</strong> and
            <strong> is the public money handled well?</strong> Good money handling does not always mean good services yet,
            and good services can hide a municipality that is running out of money.
          </p>
          <ul className="mt-3 space-y-2">
            {quadrants.map(([k, v]) => (
              <li key={k} className="flex items-center justify-between gap-3 border-b border-border pb-1">
                <span>{k}</span><span className="font-bold tabular">{v}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="font-display text-2xl">Where life is hardest</h2>
          <p className="mt-2 text-muted">Lowest wellbeing scores. Tap to see why, and what can be done.</p>
          <ol className="mt-3 space-y-1">
            {worst.map((w) => (
              <li key={w.code}>
                <Link href={`/m/${w.code}`} className="flex min-h-11 items-center justify-between gap-3 rounded px-2 hover:bg-sunk">
                  <span><strong>{w.name}</strong> <span className="text-sm text-muted">{w.province_name}</span></span>
                  <span className="font-bold tabular">{w.wellbeing}/100</span>
                </Link>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <p className="text-sm text-muted">
        Data last collected {new Date(m.built_at).toLocaleDateString("en-ZA", { day: "numeric", month: "long", year: "numeric" })}.{" "}
        <Link href="/about" className="text-link underline">Where every number comes from</Link>.
      </p>
    </div>
  );
}

function Tile({ big, text }: { big: string; text: string }) {
  return (
    <div className="card p-4">
      <p className="font-display text-3xl">{big}</p>
      <p className="mt-1">{text}</p>
    </div>
  );
}
