// The plain story at the top of a municipality page: one headline and a few
// short lines, each with an icon for its topic and a mark for good or bad.
import { Banknote, Briefcase, Check, Droplets, House, ShieldAlert, TriangleAlert, X } from "lucide-react";
import type { StoryLine } from "@/lib/data";

const TOPIC = { services: House, money: Banknote, water: Droplets, safety: ShieldAlert, work: Briefcase };
const TONE = {
  good: { Icon: Check, ring: "border-good", badge: "bg-good text-white", word: "Good" },
  bad: { Icon: X, ring: "border-bad", badge: "bg-bad text-white", word: "Problem" },
  mixed: { Icon: TriangleAlert, ring: "border-warn", badge: "bg-warn text-foreground", word: "Watch" },
};

export function Story({ headline, lines }: { headline: string | null; lines: StoryLine[] }) {
  return (
    <section aria-labelledby="story" className="board rounded p-4 sm:p-6">
      <h2 id="story" className="font-display text-2xl leading-snug sm:text-3xl">{headline ?? "In short"}</h2>
      <ul className="mt-4 space-y-3">
        {lines.map((l) => {
          const Topic = TOPIC[l.topic];
          const t = TONE[l.tone];
          return (
            <li key={l.text} className={`flex items-start gap-3 rounded border-l-8 bg-surface p-3 ${t.ring}`}>
              <Topic className="mt-0.5 shrink-0" size={26} aria-hidden />
              <div className="flex-1">
                <p className="text-lg leading-snug">{l.text}</p>
                <p className="mt-1 text-xs text-muted">Source: {l.source}</p>
              </div>
              <span className={`inline-flex shrink-0 items-center gap-1 rounded px-2 py-0.5 text-xs font-bold ${t.badge}`}>
                <t.Icon size={13} strokeWidth={3} aria-hidden />{t.word}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
