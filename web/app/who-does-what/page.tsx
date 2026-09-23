import type { Metadata } from "next";
import { Building2, Landmark, Flag } from "lucide-react";

export const metadata: Metadata = {
  title: "Who does what",
  description: "Which part of government is responsible for water, electricity, schools, clinics, police and more.",
};

type Level = "m" | "p" | "n";
type Row = { need: string; who: Level[]; note: string };

const ROWS: Row[] = [
  { need: "Water and sanitation", who: ["m"], note: "The municipality. A water board may supply bulk water; national government sets the rules." },
  { need: "Electricity", who: ["m", "n"], note: "The municipality, or Eskom (national) where Eskom supplies you directly. Your bill shows which." },
  { need: "Rubbish removal", who: ["m"], note: "The municipality." },
  { need: "Local streets and street lights", who: ["m"], note: "The municipality. Big provincial routes: the province. Highways: SANRAL (national)." },
  { need: "RDP and government houses", who: ["p", "n", "m"], note: "The province builds and keeps the waiting list; national funds it; the municipality provides land and services." },
  { need: "Schools", who: ["p"], note: "The provincial education department." },
  { need: "Clinics and hospitals", who: ["p"], note: "Mostly the province. Some big cities run their own clinics." },
  { need: "Police", who: ["n"], note: "SAPS is national. Metro police handle traffic and by-laws." },
  { need: "Grants (SASSA, SRD)", who: ["n"], note: "National: SASSA." },
  { need: "Jobs programmes", who: ["n", "p", "m"], note: "Mostly national (Employment and Labour, NYDA, youth employment programmes). EPWP runs at all three levels." },
  { need: "Land invasions", who: ["m", "n"], note: "The municipality with SAPS. Evicting people needs a court order." },
  { need: "Immigration", who: ["n"], note: "National only: Home Affairs and the Border Management Authority. Never residents or community groups." },
];

const WHO: Record<Level, { label: string; icon: typeof Flag }> = {
  m: { label: "Municipality", icon: Building2 },
  p: { label: "Province", icon: Landmark },
  n: { label: "National", icon: Flag },
};

export default function WhoDoesWhat() {
  return (
    <div className="space-y-6 pt-8">
      <h1 className="font-display text-4xl">Who does what</h1>
      <p className="max-w-2xl text-lg">
        Going to the right door saves weeks. Your ward councillor can only fix what the municipality is responsible
        for, but they can push the province and national government for the rest.
      </p>
      <div className="scroll-x">
        <table className="w-full min-w-[560px] text-left">
          <thead>
            <tr className="border-b-2 border-foreground">
              <th className="py-2">What you need</th>
              {(Object.keys(WHO) as Level[]).map((k) => {
                const Icon = WHO[k].icon;
                return <th key={k} className="px-2 text-center text-sm"><Icon className="mx-auto" aria-hidden />{WHO[k].label}</th>;
              })}
              <th className="py-2">In plain words</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.need} className="border-b border-border align-top">
                <th scope="row" className="py-2 pr-2">{r.need}</th>
                {(Object.keys(WHO) as Level[]).map((k) => {
                  const main = r.who[0] === k;
                  return (
                    <td key={k} className="px-2 py-2 text-center">
                      {r.who.includes(k) ? (
                        <span role="img" aria-label={main ? "Main responsibility" : "Shares responsibility"} title={main ? "Main responsibility" : "Shares responsibility"}
                          className={`inline-block h-6 w-6 rounded-full border-2 border-foreground ${main ? "bg-accent" : "bg-surface"}`} />
                      ) : (
                        <span role="img" aria-label="Not responsible" className="text-faint">·</span>
                      )}
                    </td>
                  );
                })}
                <td className="py-2 text-sm">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-sm text-muted">Yellow circle: main responsibility. White circle: shares responsibility.</p>
    </div>
  );
}
