// Small hand-built SVG charts. Each one makes a single point a person can
// read in a second; numbers are always written out next to the marks, so the
// meaning never depends on colour alone.
import { Check, AlertTriangle, TriangleAlert, X, Minus, User } from "lucide-react";
import { STATUS_WORDS, type Status, pct } from "@/lib/format";

const STATUS_CLASS: Record<Status, string> = {
  good: "bg-good text-white",
  warn: "bg-warn text-foreground",
  serious: "bg-serious text-foreground",
  bad: "bg-bad text-white",
  none: "bg-sunk text-muted",
};
const STATUS_FILL: Record<Status, string> = {
  good: "var(--color-good)",
  warn: "var(--color-warn)",
  serious: "var(--color-serious)",
  bad: "var(--color-bad)",
  none: "var(--color-border)",
};
const STATUS_ICON = { good: Check, warn: AlertTriangle, serious: TriangleAlert, bad: X, none: Minus };

export function StatusBadge({ status, label }: { status: Status; label?: string }) {
  const Icon = STATUS_ICON[status];
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-sm font-bold ${STATUS_CLASS[status]}`}>
      <Icon size={15} strokeWidth={3} aria-hidden />
      {label ?? STATUS_WORDS[status]}
    </span>
  );
}

/** 0 to 100 score on a track, with a tick for the national middle. */
export function ScoreMeter({ score, status, middle }: { score: number | null; status: Status; middle?: number }) {
  return (
    <svg viewBox="0 0 200 16" className="w-full" role="img" aria-label={`Score ${score ?? "unknown"} out of 100`}>
      <rect x="0" y="4" width="200" height="8" rx="4" fill="var(--color-sunk)" />
      {score != null && <rect x="0" y="4" width={Math.max(8, score * 2)} height="8" rx="4" fill={STATUS_FILL[status]} />}
      {middle != null && (
        <g>
          <line x1={middle * 2} x2={middle * 2} y1="0" y2="16" stroke="var(--color-foreground)" strokeWidth="2" />
          <title>{`South Africa's middle: ${Math.round(middle)}`}</title>
        </g>
      )}
    </svg>
  );
}

/** "9 in 10 people": ten figures, filled for the share that has it. */
export function PeopleRow({ share, color = "var(--color-seq-4)" }: { share: number | null; color?: string }) {
  const filled = share == null ? 0 : Math.round(share * 10);
  return (
    <div className="flex gap-0.5" role="img" aria-label={share == null ? "no data" : `${filled} in 10 people`}>
      {Array.from({ length: 10 }, (_, i) => (
        <User key={i} size={20} strokeWidth={2.5} aria-hidden
          style={{ color: i < filled ? color : "var(--color-border)", fill: i < filled ? color : "none" }} />
      ))}
    </div>
  );
}

/** This place compared with similar places on one track: "Here" above, "Similar places" below. */
export function PeerStrip({ value, median, higherIsBetter, format = pct }: {
  value: number; median: number; higherIsBetter: boolean; format?: (v: number) => string;
}) {
  const max = Math.max(1, value, median) * (value > 1 || median > 1 ? 1.1 : 1);
  const x = (v: number) => 8 + (Math.min(v, max) / max) * 284;
  const anchor = (px: number) => (px > 230 ? "end" : px < 70 ? "start" : "middle");
  const better = higherIsBetter ? value >= median : value <= median;
  return (
    <svg viewBox="0 0 300 62" className="w-full" role="img"
      aria-label={`Here ${format(value)}, similar places ${format(median)}`}>
      <text x={x(value)} y="13" textAnchor={anchor(x(value))} fontSize="13" fontWeight="700" fill="var(--color-foreground)">
        Here {format(value)}
      </text>
      <line x1="8" x2="292" y1="30" y2="30" stroke="var(--color-border)" strokeWidth="6" strokeLinecap="round" />
      <circle cx={x(median)} cy="30" r="7" fill="var(--color-surface)" stroke="var(--color-muted)" strokeWidth="2.5" />
      <circle cx={x(value)} cy="30" r="8" fill={better ? "var(--color-good)" : "var(--color-bad)"}
        stroke="var(--color-surface)" strokeWidth="2" />
      <text x={x(median)} y="56" textAnchor={anchor(x(median))} fontSize="12" fill="var(--color-muted)">
        Similar places {format(median)}
      </text>
    </svg>
  );
}

/** Planned money against money actually used. */
export function PlannedSpent({ planned, spent, format }: { planned: number; spent: number; format: (v: number) => string }) {
  const max = Math.max(planned, spent);
  const share = planned ? spent / planned : 0;
  return (
    <svg viewBox="0 0 300 76" className="w-full" role="img" aria-label={`Planned ${format(planned)}, spent ${format(spent)}`}>
      <text x="0" y="12" fontSize="12" fill="var(--color-muted)">Planned</text>
      <rect x="0" y="16" width={(planned / max) * 300} height="18" rx="3" fill="var(--color-seq-2)" />
      <text x="4" y="30" fontSize="12" fontWeight="700" fill="var(--color-foreground)">{format(planned)}</text>
      <text x="0" y="52" fontSize="12" fill="var(--color-muted)">Actually spent</text>
      <rect x="0" y="56" width={Math.max(2, (spent / max) * 300)} height="18" rx="3"
        fill={share >= 0.9 ? "var(--color-good)" : share >= 0.7 ? "var(--color-warn)" : "var(--color-bad)"} />
      <text x={Math.min(296, Math.max(4, (spent / max) * 300 + 4))} y="70" fontSize="12" fontWeight="700"
        textAnchor={(spent / max) * 300 > 200 ? "end" : "start"}
        fill={share >= 0.9 && (spent / max) * 300 > 200 ? "white" : "var(--color-foreground)"}>
        {format(spent)} ({Math.round(share * 100)}%)
      </text>
    </svg>
  );
}

/** A small line with the latest value labelled. */
export function Sparkline({ values, labels, unit = "%", color = "var(--color-seq-4)" }: {
  values: number[]; labels: string[]; unit?: string; color?: string;
}) {
  if (!values.length) return null;
  const w = 300, h = 70, pad = 8;
  const lo = Math.min(...values), hi = Math.max(...values);
  const span = hi - lo || 1;
  const xs = values.map((_, i) => pad + (i / Math.max(1, values.length - 1)) * (w - 2 * pad - 40));
  const ys = values.map((v) => pad + (1 - (v - lo) / span) * (h - 2 * pad - 14));
  const last = values.length - 1;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img"
      aria-label={`${labels[0]} ${values[0]}${unit} to ${labels[last]} ${values[last]}${unit}`}>
      <polyline points={xs.map((x, i) => `${x},${ys[i]}`).join(" ")} fill="none" stroke={color} strokeWidth="2.5"
        strokeLinejoin="round" strokeLinecap="round" />
      {values.map((v, i) => (
        <circle key={i} cx={xs[i]} cy={ys[i]} r={i === last ? 5 : 3} fill={i === last ? color : "var(--color-surface)"}
          stroke={color} strokeWidth="2">
          <title>{`${labels[i]}: ${v}${unit}`}</title>
        </circle>
      ))}
      <text x={xs[last] + 9} y={ys[last] + 4} fontSize="14" fontWeight="700" fill="var(--color-foreground)">
        {values[last]}{unit}
      </text>
      <text x={pad} y={h - 1} fontSize="11" fill="var(--color-muted)">{labels[0]}</text>
      <text x={xs[last]} y={h - 1} fontSize="11" textAnchor="end" fill="var(--color-muted)">{labels[last]}</text>
    </svg>
  );
}

/** Same quarter, year after year, as small columns (crime is seasonal). */
export function YearColumns({ values, years, color = "var(--color-risk-3)" }: { values: number[]; years: number[]; color?: string }) {
  const max = Math.max(...values, 1);
  const w = 300, h = 90, bw = (w - 20) / values.length;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img"
      aria-label={years.map((y, i) => `${y}: ${values[i]}`).join(", ")}>
      {values.map((v, i) => {
        const bh = (v / max) * (h - 34);
        const last = i === values.length - 1;
        return (
          <g key={i}>
            <rect x={10 + i * bw + 4} y={h - 18 - bh} width={bw - 8} height={Math.max(bh, 1)} rx="3"
              fill={last ? color : "var(--color-risk-1)"} />
            <text x={10 + i * bw + bw / 2} y={h - 22 - bh} textAnchor="middle" fontSize="12"
              fontWeight={last ? 700 : 400} fill="var(--color-foreground)">{Math.round(v)}</text>
            <text x={10 + i * bw + bw / 2} y={h - 4} textAnchor="middle" fontSize="11" fill="var(--color-muted)">{years[i]}</text>
            <title>{`${years[i]}: ${v}`}</title>
          </g>
        );
      })}
    </svg>
  );
}

/** Horizontal bars, largest first, with the amount written on each. */
export function Bars({ items, format }: { items: { label: string; value: number }[]; format: (v: number) => string }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <ul className="space-y-2">
      {items.map((i) => (
        <li key={i.label}>
          <div className="flex justify-between gap-2 text-sm">
            <span>{i.label}</span>
            <span className="font-bold tabular">{format(i.value)}</span>
          </div>
          <div className="h-2.5 rounded bg-sunk">
            <div className="h-2.5 rounded bg-seq-4" style={{ width: `${Math.max(1, (i.value / max) * 100)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/** One square per year of audit results, oldest to newest. */
export function AuditStrip({ history, lastYear, statusOf, labelOf }: {
  history: string[]; lastYear: number; statusOf: (c: string) => Status; labelOf: (c: string) => string;
}) {
  const first = lastYear - history.length + 1;
  return (
    <div>
      <div className="flex flex-wrap gap-1" role="list">
        {history.map((c, i) => {
          const s = statusOf(c);
          const Icon = STATUS_ICON[s];
          return (
            <span key={i} role="listitem" title={`${first + i}: ${labelOf(c)}`} aria-label={`${first + i}: ${labelOf(c)}`}
              className={`grid h-7 w-7 place-items-center rounded ${STATUS_CLASS[s]}`}>
              <Icon size={14} strokeWidth={3} aria-hidden />
            </span>
          );
        })}
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted" style={{ maxWidth: history.length * 32 }}>
        <span>{first}</span><span>{lastYear}</span>
      </div>
    </div>
  );
}

/** Where this municipality sits: services (across) and money handling (up). */
export function Quadrant({ x, y, midX, midY }: { x: number; y: number; midX: number; midY: number }) {
  const px = (v: number) => 10 + (v / 100) * 180, py = (v: number) => 190 - (v / 100) * 180;
  return (
    <svg viewBox="0 0 200 200" className="w-full max-w-[220px]" role="img"
      aria-label={`Services score ${x}, money score ${y}`}>
      <rect x="10" y="10" width="180" height="180" fill="var(--color-sunk)" rx="4" />
      <line x1={px(midX)} x2={px(midX)} y1="10" y2="190" stroke="var(--color-border)" strokeWidth="2" />
      <line x1="10" x2="190" y1={py(midY)} y2={py(midY)} stroke="var(--color-border)" strokeWidth="2" />
      <text x="186" y="24" textAnchor="end" fontSize="10" fill="var(--color-muted)">good services, well run</text>
      <text x="14" y="184" fontSize="10" fill="var(--color-muted)">poor services, badly run</text>
      <circle cx={px(x)} cy={py(y)} r="9" fill="var(--color-accent)" stroke="var(--color-foreground)" strokeWidth="2.5" />
      <text x="100" y="199" textAnchor="middle" fontSize="9" fill="var(--color-muted)">services →</text>
    </svg>
  );
}

/** Progress through the year: a bar for money used, and a line for time gone. */
export function YearProgress({ label, share, timeGone, detail }: { label: string; share: number; timeGone: number; detail: string }) {
  const behind = share < timeGone - 0.1;
  return (
    <div>
      <div className="flex justify-between gap-2 text-sm"><span className="font-bold">{label}</span><span className="tabular">{detail}</span></div>
      <svg viewBox="0 0 300 26" className="w-full" role="img" aria-label={`${label}: ${Math.round(share * 100)}% used, ${Math.round(timeGone * 100)}% of the year gone`}>
        <rect x="0" y="6" width="300" height="12" rx="4" fill="var(--color-sunk)" />
        <rect x="0" y="6" width={Math.min(1, share) * 300} height="12" rx="4" fill={behind ? "var(--color-bad)" : "var(--color-seq-4)"} />
        <line x1={timeGone * 300} x2={timeGone * 300} y1="1" y2="23" stroke="var(--color-foreground)" strokeWidth="2.5" />
      </svg>
      <p className="text-xs text-muted">{Math.round(share * 100)}% used. Black line: {Math.round(timeGone * 100)}% of the year gone.</p>
    </div>
  );
}

/** One bar split into parts, each labelled with its amount. */
export function SplitBar({ parts, format }: { parts: { label: string; value: number; color: string }[]; format: (v: number) => string }) {
  const total = parts.reduce((s, p) => s + Math.max(0, p.value), 0) || 1;
  return (
    <div>
      <div className="flex h-7 w-full overflow-hidden rounded" role="img"
        aria-label={parts.map((p) => `${p.label} ${format(p.value)}`).join(", ")}>
        {parts.filter((p) => p.value > 0).map((p) => (
          <div key={p.label} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} className="border-r-2 border-surface last:border-r-0" title={`${p.label}: ${format(p.value)}`} />
        ))}
      </div>
      <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center gap-2">
            <span className="inline-block h-3.5 w-3.5 rounded-sm" style={{ background: p.color }} />
            <span className="flex-1">{p.label}</span><span className="font-bold tabular">{format(p.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
