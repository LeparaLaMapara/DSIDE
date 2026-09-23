import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Droplets, Lightbulb, Toilet, Trash2, House, Flame, GraduationCap, Baby, ShieldAlert, Briefcase, Landmark, Phone, Globe,
  Waves, School, Mail, Search as SearchIcon, MessageSquare,
} from "lucide-react";
import { WardMap } from "@/components/maps";
import { Story } from "@/components/story";
import { LiveNow } from "@/components/live";
import { AuditStrip, Bars, PeerStrip, PeopleRow, PlannedSpent, Quadrant, ScoreMeter, SplitBar, Sparkline, StatusBadge, YearColumns, YearProgress } from "@/components/viz";
import { actionsFor, SPHERE_LABEL, YEAR_CALENDAR } from "@/lib/actions";
import { byCode, meta, serving, stations } from "@/lib/data";
import { AUDIT_PLAIN, AUDIT_STATUS, num, outOf10, PEER_NAMES, pct, rand, scoreStatus } from "@/lib/format";

export const dynamicParams = false;

export function generateStaticParams() {
  return serving().map((m) => ({ code: m.code }));
}

export async function generateMetadata({ params }: { params: Promise<{ code: string }> }): Promise<Metadata> {
  const m = byCode((await params).code);
  return m ? { title: m.name, description: `How ${m.name} is doing: money, services, safety, jobs, and what residents can do.` } : {};
}

const n = (v: unknown) => (typeof v === "number" ? v : null);
const fy = (y: number) => `${y - 1}-${String(y).slice(2)}`;
const ordinal = (k: number) => `${k}${["th", "st", "nd", "rd"][((k % 100) - 20) % 10] || ["th", "st", "nd", "rd"][k % 100] || "th"}`;

export default async function MuniPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const m = byCode(code);
  if (!m) notFound();
  const info = meta();
  const peers = m.peer_group ? PEER_NAMES[m.peer_group] : "similar places";
  const wellStatus = scoreStatus(m.wellbeing);
  const moneyStatus = scoreStatus(m.money_score);
  const rankSpread = m.rank_best != null && m.rank_worst != null ? m.rank_worst - m.rank_best : null;
  const st = stations(code);
  const years = info.safety.years;
  const trend = (crime: string) =>
    years.map((_, i) => st.reduce((s, x) => s + (((x[`${crime}_trend`] as number[] | undefined)?.[i]) ?? 0), 0));
  const murdersNow = n(m.murders), murdersBefore = n(m.murders_last_year);
  const actions = actionsFor(m);
  const jobsChange = n(m.formal_jobs) != null && n(m.formal_jobs_before) ? n(m.formal_jobs)! / n(m.formal_jobs_before)! - 1 : null;
  const officials = (m.officials as { role: string; name: string; office_phone: string | null; email: string | null }[]) ?? [];
  const grants = (m.grants as { grant: string; budget: number; spent: number | null; spent_share: number | null; financial_year: string }[]) ?? [];
  const residentsSay = (m.residents_say as { question: string; share: number; year: number }[]) ?? [];
  const siu = (m.siu as { proclamation: string; date: string; title: string; link: string }[]) ?? [];

  return (
    <article className="space-y-14 pt-6">
      {/* 1. Who and where */}
      <header className="grid gap-6 md:grid-cols-[1fr_auto]">
        <div>
          <p className="text-muted">
            <Link href="/" className="text-link underline">South Africa</Link> · {m.province_name} ·{" "}
            {m.kind === "metro" ? "metro (big city)" : `local municipality, one of the ${peers}`}
          </p>
          <h1 className="mt-1 font-display text-4xl leading-tight sm:text-5xl">{m.name}</h1>
          <p className="mt-2 text-lg">
            <strong>{num(n(m.population_2022))}</strong> people live here (Census 2022)
            {n(m.population_growth) != null && <>, {n(m.population_growth)! >= 0 ? "up" : "down"} <strong>{pct(Math.abs(n(m.population_growth)!))}</strong> since 2011</>}.
          </p>
          {n(m.pop_2026) != null && (
            <p className="text-muted">About {num(n(m.pop_2026))} people in 2026{m.pop_2026_level === "district" ? " in its wider district" : ""} (Stats SA estimate).</p>
          )}
          {m.group && <p className="mt-3"><span className="board inline-block rounded px-3 py-1 font-bold">{m.group}</span></p>}
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            {m.phone && <a className="inline-flex min-h-11 items-center gap-1 font-bold text-link underline" href={`tel:${m.phone.replace(/\s/g, "")}`}><Phone size={16} aria-hidden />{m.phone}</a>}
            {m.website && <a className="inline-flex min-h-11 items-center gap-1 font-bold text-link underline" href={m.website} target="_blank" rel="noopener"><Globe size={16} aria-hidden />Website</a>}
          </div>
        </div>
        {m.wellbeing != null && m.money_score != null && (
          <figure className="w-[220px]">
            <Quadrant x={n(m["dim:home"]) ?? 0} y={m.money_score} midX={info.groups.services_median} midY={info.groups.money_median} />
            <figcaption className="text-xs text-muted">Yellow dot: {m.name}. Lines: the middle of South Africa.</figcaption>
          </figure>
        )}
      </header>

      {m.story.length > 0 && <Story headline={m.headline} lines={m.story} />}

      <LiveNow code={m.code} name={m.name} />

      {/* 2. Report card */}
      <section aria-labelledby="card">
        <h2 id="card" className="font-display text-2xl">Report card</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Card icon={<House aria-hidden />} title="Life here" status={wellStatus}
            big={m.wellbeing != null ? `${m.wellbeing}/100` : "no data"}>
            <ScoreMeter score={m.wellbeing} status={wellStatus} middle={50} />
            {m.rank != null && (
              <p className="mt-2 text-sm">
                {ordinal(m.rank)} of {m.ranked_out_of} municipalities.{" "}
                {rankSpread != null && (rankSpread > 60
                  ? <>This rank <strong>moves a lot</strong> ({ordinal(m.rank_best!)} to {ordinal(m.rank_worst!)}) depending on what you value most.</>
                  : <>This rank is <strong>solid</strong> however you weigh the parts.</>)}
              </p>
            )}
          </Card>
          <Card icon={<Landmark aria-hidden />} title="Handling money" status={moneyStatus}
            big={m.money_score != null ? `${m.money_score}/100` : "no data"}>
            <ScoreMeter score={m.money_score} status={moneyStatus} middle={info.groups.money_median} />
            {m.audit_code && <p className="mt-2 text-sm">Audit {fy(m.year ?? info.money_year)}: <StatusBadge status={AUDIT_STATUS[m.audit_code]} label={AUDIT_PLAIN[m.audit_code]} /></p>}
          </Card>
          <Card icon={<Droplets aria-hidden />} title="Tap water" status={statusShare(n(m.water))}
            big={outOf10(n(m.water)) != null ? `${outOf10(n(m.water))} in 10` : "no data"}>
            <PeopleRow share={n(m.water)} />
            <p className="mt-2 text-sm">people have tap water at home or within 200 m.</p>
          </Card>
          <Card icon={<ShieldAlert aria-hidden />} title="Murders" status={murdersNow != null && murdersBefore != null ? (murdersNow <= murdersBefore ? "warn" : "bad") : "none"}
            statusLabel={murdersNow != null && murdersBefore != null ? (murdersNow < murdersBefore ? "Fewer than last year" : murdersNow > murdersBefore ? "More than last year" : "Same as last year") : undefined}
            big={num(murdersNow)}>
            <p className="text-sm">in {info.safety.period}, against <strong>{num(murdersBefore)}</strong> in the same months a year before.</p>
          </Card>
          <Card icon={<Briefcase aria-hidden />} title="Formal jobs" big={num(n(m.formal_jobs))}
            status={jobsChange == null ? "none" : jobsChange >= 0.01 ? "good" : jobsChange <= -0.01 ? "bad" : "warn"}
            statusLabel={jobsChange == null ? undefined : jobsChange >= 0.01 ? "Growing" : jobsChange <= -0.01 ? "Shrinking" : "Flat"}>
            <p className="text-sm">
              jobs registered with SARS in {String(m.jobs_year ?? "the latest tax year")}, of which <strong>{num(n(m.youth_jobs))}</strong> are held by young people.
              Typical formal pay: <strong>R{num(n(m.median_income))}</strong> a month.
              {n(m.unemployment_now) != null && <> Unemployment in {m.jobs_area_level as string}: <strong>{n(m.unemployment_now)}%</strong>.</>}
            </p>
          </Card>
          <Card icon={<Waves aria-hidden />} title="Sewage works" big={n(m.green_drop_score) != null ? `${n(m.green_drop_score)}%` : "no data"}
            status={n(m.green_drop_score) == null ? "none" : n(m.green_drop_score)! >= 70 ? "good" : n(m.green_drop_score)! >= 50 ? "warn" : "bad"}
            statusLabel={n(m.green_drop_score) == null ? undefined : n(m.green_drop_score)! >= 70 ? "Safe" : n(m.green_drop_score)! >= 50 ? "At risk" : "Serious risk"}>
            <p className="text-sm">
              national Green Drop score ({String(m.report_year ?? "latest")}) for cleaning waste water{m.water_quality_level === "district" ? ", measured for its district" : ""}.
              Under 50% means sewage may reach rivers.
              {typeof m.blue_drop_risk_category === "string" && <> Drinking water risk: <strong>{m.blue_drop_risk_category}</strong>.</>}
            </p>
          </Card>
        </div>
      </section>

      {/* 3. Good and bad, and why */}
      <section aria-labelledby="why" className="grid gap-8 md:grid-cols-2">
        <div>
          <h2 id="why" className="font-display text-2xl">Where it does worse than similar places</h2>
          <p className="mt-1 text-sm text-muted">Compared with other {peers}. Red dot: here. Circle: the middle of similar places.</p>
          <ul className="mt-4 space-y-5">
            {m.problems.length === 0 && <li className="text-muted">Nothing stands out as worse than similar places.</li>}
            {m.problems.map((p) => (
              <li key={p.measure}>
                <p className="font-bold">{p.label}</p>
                <PeerStrip value={p.value} median={p.peer_median} higherIsBetter={p.higher_is_better} format={fmtFor(p.measure)} />
                {p.best_peer && p.best_peer !== m.name && <p className="text-sm text-muted">Best among similar places: {p.best_peer}. So better is possible.</p>}
              </li>
            ))}
          </ul>
          {m.reasons.length > 0 && (
            <div className="mt-6 rounded border-2 border-foreground p-4">
              <h3 className="font-bold">What goes with these problems</h3>
              <p className="text-sm text-muted">Facts that sit next to the problems in the data. They are warning signs, not proof of the cause.</p>
              <ul className="mt-2 list-disc space-y-2 pl-5">
                {m.reasons.map((r) => <li key={r.text}>{r.text} <span className="text-sm text-muted">({r.evidence})</span></li>)}
              </ul>
            </div>
          )}
        </div>
        <div>
          <h2 className="font-display text-2xl">Where it does better</h2>
          <p className="mt-1 text-sm text-muted">Green dot: here. Circle: the middle of similar places.</p>
          <ul className="mt-4 space-y-5">
            {m.strengths.length === 0 && <li className="text-muted">Nothing stands out as better than similar places.</li>}
            {m.strengths.map((p) => (
              <li key={p.measure}>
                <p className="font-bold">{p.label}</p>
                <PeerStrip value={p.value} median={p.peer_median} higherIsBetter={p.higher_is_better} format={fmtFor(p.measure)} />
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 4. Money */}
      <section aria-labelledby="money" className="space-y-6">
        <div>
          <h2 id="money" className="font-display text-2xl">The money, {fy(m.year ?? info.money_year)}</h2>
          <p className="mt-1">
            It received <strong>{rand(n(m.income_actual))}</strong> and spent <strong>{rand(n(m.spend_actual))}</strong> on running the municipality.
            {n(m.wasted) != null && <> Of that, <strong>{rand(n(m.wasted))}</strong> was spent against the rules or wasted.</>}
          </p>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          {n(m.build_planned) != null && n(m.build_actual) != null && (
            <div className="card p-4">
              <h3 className="font-bold">Building and fixing (pipes, roads, power lines)</h3>
              <PlannedSpent planned={n(m.build_planned)!} spent={n(m.build_actual)!} format={rand} />
              <p className="mt-1 text-sm text-muted">Money not spent on building is a delay you can feel: a pipe that is not replaced, a road that is not fixed.</p>
            </div>
          )}
          <div className="card p-4">
            <h3 className="font-bold">Where the money was planned to go</h3>
            <p className="text-sm text-muted">Budget for running services. Actual spending by service is not reliable in Treasury's data yet.</p>
            <div className="mt-3">
              <Bars items={m.planned_by_service.filter((s) => s.amount > 0).sort((a, b) => b.amount - a.amount).map((s) => ({ label: s.service, value: s.amount }))} format={rand} />
            </div>
          </div>
          <div className="card p-4">
            <h3 className="font-bold">What the money was actually spent on</h3>
            <div className="mt-3">
              <Bars format={rand} items={Object.entries(m).filter(([k, v]) => k.startsWith("out:") && typeof v === "number" && v > 0)
                .map(([k, v]) => ({ label: k.slice(4), value: v as number })).sort((a, b) => b.value - a.value).slice(0, 7)} />
            </div>
          </div>
          <div className="card p-4">
            <h3 className="font-bold">Audit results over the years</h3>
            <p className="text-sm text-muted">Each square is one year. The Auditor-General checks whether the books are true.</p>
            <div className="mt-3">
              <AuditStrip history={m.audit_history} lastYear={m.year ?? info.money_year} statusOf={(c) => AUDIT_STATUS[c] ?? "none"} labelOf={(c) => AUDIT_PLAIN[c] ?? c} />
            </div>
            {m.chance_unqualified != null && (
              <p className="mt-3 text-sm">
                Chance of an acceptable audit for {fy(m.predicted_year ?? info.audit_model.predicts_year)}: <strong>{pct(m.chance_unqualified)}</strong>.{" "}
                <Link href="/about#audit-model" className="text-link underline">How we estimate this</Link>
              </p>
            )}
            {m.audit_url && <p className="mt-2 text-sm"><a className="text-link underline" href={m.audit_url} target="_blank" rel="noopener">Read the Auditor-General's report</a></p>}
          </div>
        </div>
        {n(m.ytd_months_reported) != null && n(m.ytd_expected_share) != null && (
          <div className="card p-4">
            <h3 className="font-bold">This year so far ({String(m.ytd_financial_year)}, to {String(m.ytd_latest_month)})</h3>
            <p className="text-sm text-muted">Red means it is behind: less used than the time gone.</p>
            <div className="mt-3 grid gap-4 md:grid-cols-3">
              {n(m.ytd_capital_budget) ? <YearProgress label="Building and fixing" share={n(m.ytd_capital_ytd)! / n(m.ytd_capital_budget)!} timeGone={n(m.ytd_expected_share)!} detail={`${rand(n(m.ytd_capital_ytd))} of ${rand(n(m.ytd_capital_budget))}`} /> : null}
              {n(m.ytd_spending_budget) ? <YearProgress label="Running costs" share={n(m.ytd_spending_ytd)! / n(m.ytd_spending_budget)!} timeGone={n(m.ytd_expected_share)!} detail={`${rand(n(m.ytd_spending_ytd))} of ${rand(n(m.ytd_spending_budget))}`} /> : null}
              {n(m.ytd_revenue_budget) ? <YearProgress label="Money coming in" share={n(m.ytd_revenue_ytd)! / n(m.ytd_revenue_budget)!} timeGone={n(m.ytd_expected_share)!} detail={`${rand(n(m.ytd_revenue_ytd))} of ${rand(n(m.ytd_revenue_budget))}`} /> : null}
            </div>
          </div>
        )}
        <div className="grid gap-6 md:grid-cols-2">
          {n(m.owed_total) != null && (
            <div className="card p-4">
              <h3 className="font-bold">Who owes the municipality: {rand(n(m.owed_total))}</h3>
              <p className="text-sm text-muted">Unpaid bills for rates, water and electricity ({String(m.owed_period)}). {pct(n(m.owed_over_1yr)! / n(m.owed_total)!)} is more than a year old.</p>
              <div className="mt-3">
                <SplitBar format={rand} parts={[
                  { label: "Households", value: n(m.owed_households) ?? 0, color: "var(--color-seq-4)" },
                  { label: "Businesses", value: n(m.owed_business) ?? 0, color: "var(--color-seq-2)" },
                  { label: "Government", value: n(m.owed_government) ?? 0, color: "var(--color-risk-3)" },
                ]} />
              </div>
              {n(m.owes_total) != null && (
                <p className="mt-3 text-sm">The municipality itself owes <strong>{rand(n(m.owes_total))}</strong>
                  {n(m.owes_eskom) ? <>, of which <strong>{rand(n(m.owes_eskom))}</strong> is to Eskom</> : null}
                  {n(m.owes_water_boards) ? <> and <strong>{rand(n(m.owes_water_boards))}</strong> to water boards</> : null}.</p>
              )}
              {n(m.months_cover) != null && (
                <p className="mt-1 text-sm">Cash in the bank at the end of {String(m.cash_year)}: {n(m.months_cover)! <= 0
                  ? <strong className="text-bad-ink">below zero, so it was running on borrowed money</strong>
                  : <><strong>{n(m.months_cover)!.toFixed(1)} months</strong> of running costs (a healthy municipality keeps 1 to 3)</>}.</p>
              )}
            </div>
          )}
          {grants.length > 0 && (
            <div className="card p-4">
              <h3 className="font-bold">Money from national government, and how much is used</h3>
              <p className="text-sm text-muted">Grants for {grants[0].financial_year}, budget against spent so far.</p>
              <ul className="mt-3 space-y-3">
                {grants.map((g) => (
                  <li key={g.grant}>
                    <p className="text-sm">{g.grant}</p>
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 flex-1 rounded bg-sunk"><span className="block h-2.5 rounded bg-seq-4" style={{ width: `${Math.min(1, g.spent_share ?? 0) * 100}%` }} /></span>
                      <span className="w-44 text-right text-sm tabular">{g.spent ? <><strong>{rand(g.spent)}</strong> of {rand(g.budget)}</> : <>no spending reported of {rand(g.budget)}</>}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        {m.warnings.length > 0 && <p className="text-sm text-bad-ink">Left out because the government's own numbers look wrong: {m.warnings.join("; ")}.</p>}
      </section>

      {/* 5. Life here */}
      <section aria-labelledby="life" className="space-y-4">
        <h2 id="life" className="font-display text-2xl">How people live (Census 2022)</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Life icon={<Droplets aria-hidden />} label="Tap water nearby" v={n(m.water)} />
          <Life icon={<Toilet aria-hidden />} label="A proper toilet" v={n(m.toilet)} />
          <Life icon={<Lightbulb aria-hidden />} label="Electricity for lights" v={n(m.lighting)} />
          <Life icon={<Trash2 aria-hidden />} label="Rubbish collected weekly" v={n(m.refuse)} />
          <Life icon={<House aria-hidden />} label="A proper house or flat" v={n(m.dwelling)} />
          <Life icon={<Flame aria-hidden />} label="Cooks with electricity or gas" v={n(m.cooking)} />
          <Life icon={<GraduationCap aria-hidden />} label="Adults with matric or more" v={n(m.matric_adults)} />
          <Life icon={<Baby aria-hidden />} label="Small children in early learning" v={n(m.early_learning)} />
        </div>
        {n(m.sch_schools) != null && (
          <div className="card flex flex-wrap items-center gap-4 p-4">
            <School aria-hidden size={32} />
            <p className="flex-1">
              <strong>{num(n(m.sch_schools))} schools</strong>, {pct(n(m.sch_no_fee_share))} of them no-fee.
              {n(m.sch_matric_pass_rate) != null && <> In 2024, <strong>{Math.round(n(m.sch_matric_pass_rate)! * 10)} in 10</strong> matric learners passed ({num(n(m.sch_matric_passed))} of {num(n(m.sch_matric_wrote))}).</>}
              {" "}<a href="#ward" className="text-link underline">See every school on the ward map</a>.
            </p>
          </div>
        )}
        <div className="card p-4">
          <h3 className="font-bold">The parts of the wellbeing score</h3>
          <p className="text-sm text-muted">Each part is 0 (worst in South Africa) to 100 (best). The line is the middle.</p>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            {Object.entries(info.dimensions).map(([k, label]) => {
              const v = n(m[`dim:${k}`]);
              return (
                <div key={k}>
                  <dt className="flex justify-between text-sm"><span>{label}</span><span className="font-bold">{v ?? "?"}/100</span></dt>
                  <dd><ScoreMeter score={v} status={scoreStatus(v)} middle={50} /></dd>
                </div>
              );
            })}
          </dl>
          <p className="mt-2 text-sm text-muted">Work and income uses SARS tax data for {String(m.jobs_year ?? "the latest tax year")}: formal jobs per working-age adult, and typical formal pay.</p>
        </div>
      </section>

      {/* 6. Safety */}
      <section aria-labelledby="safety" className="space-y-4">
        <h2 id="safety" className="font-display text-2xl">Safety</h2>
        <p className="text-muted">Crimes reported to police stations here, {info.safety.period.replace(/ \d{4}/g, "")} each year. The same months are compared, because crime changes with the seasons.</p>
        <div className="grid gap-4 sm:grid-cols-2">
          {[["murders", "Murders"], ["sexual_offences", "Sexual offences (including rape)"], ["drug_crimes", "Drug crimes found by police"], ["house_burglaries", "House break-ins"]].map(([k, label]) => (
            <div key={k} className="card p-4">
              <h3 className="font-bold">{label}</h3>
              <YearColumns values={trend(k)} years={years} />
            </div>
          ))}
        </div>
        {st.length > 0 && (
          <div className="scroll-x">
            <table className="w-full min-w-[520px] text-left text-sm">
              <caption className="pb-2 text-left font-bold">Police stations here, {info.safety.period}</caption>
              <thead><tr className="border-b-2 border-foreground">
                <th className="py-1">Station</th><th>People served</th><th>Murders</th><th>Sexual offences</th><th>Drug crimes</th><th>Murders a year before</th>
              </tr></thead>
              <tbody>
                {[...st].sort((a, b) => (b.murders as number) - (a.murders as number)).map((s) => (
                  <tr key={s.station} className="border-b border-border">
                    <td className="py-1 font-bold">{s.station}</td>
                    <td className="tabular">{num(s.precinct_population)}</td>
                    <td className="tabular">{num(s.murders as number)}</td>
                    <td className="tabular">{num(s.sexual_offences as number)}</td>
                    <td className="tabular">{num(s.drug_crimes as number)}</td>
                    <td className="tabular text-muted">{num(s.murders_last_year as number)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-sm text-muted">Drug crime counts show police activity as much as drug use: more arrests can mean more policing, not more drugs.</p>
      </section>

      {/* 7. Work */}
      <section aria-labelledby="work" className="grid gap-6 md:grid-cols-2">
        <div>
          <h2 id="work" className="font-display text-2xl">Work</h2>
          <p className="mt-1">Unemployment in {m.jobs_area_level as string}, last two years (Stats SA, official definition).</p>
          {m.unemployment_trend && m.unemployment_trend.length > 0 && (
            <div className="card mt-3 p-4"><Sparkline values={m.unemployment_trend} labels={info.jobs.periods} color="var(--color-risk-4)" /></div>
          )}
        </div>
        <div>
          <h2 className="font-display text-2xl">Young people</h2>
          <p className="mt-1">
            <strong>{num(n(m.youth_jobs))}</strong> formal jobs here are held by young people (15 to 34), typically paying <strong>R{num(n(m.youth_median_income))}</strong> a month ({String(m.jobs_year ?? "")} tax data).
            Nationally, <strong>{info.jobs.youth_unemployment_15_34}%</strong> of young people who want work have none ({info.jobs.period}).
          </p>
          {n(m.srd_paid) != null && (
            <p className="mt-2"><strong>{num(n(m.srd_paid))}</strong> people here received the R370 SRD grant in {String(m.srd_period)}.</p>
          )}
          <p className="mt-2 text-sm text-muted">In 2011, {pct(n(m.youth_neet))} of young people here had no job, school or training: the last census that asked.</p>
        </div>
      </section>

      {/* 8. Ward */}
      <section id="ward" aria-labelledby="ward-h" className="space-y-3">
        <h2 id="ward-h" className="font-display text-2xl">Your ward</h2>
        <p className="text-muted">A ward is the area your councillor represents. Zoom in to your street.</p>
        <WardMap code={m.code} wardYearNote="Ward figures: Census 2011, re-mapped by the Municipal Demarcation Board to the wards used since 2021. New ward lines apply from the November 2026 election." />
      </section>

      <section aria-labelledby="who" className="space-y-4">
        <h2 id="who" className="font-display text-2xl">Who runs it, and who is watching</h2>
        {officials.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {officials.map((o) => (
              <div key={o.role + o.name} className="card p-3">
                <p className="text-sm text-muted">{o.role}</p>
                <p className="font-bold">{o.name}</p>
                {o.office_phone && <a className="mt-1 flex min-h-11 items-center gap-1 text-sm font-bold text-link underline" href={`tel:${o.office_phone.replace(/\s/g, "")}`}><Phone size={14} aria-hidden />{o.office_phone}</a>}
                {o.email && <a className="flex min-h-11 items-center gap-1 break-all text-sm text-link underline" href={`mailto:${o.email}`}><Mail size={14} aria-hidden />{o.email}</a>}
              </div>
            ))}
          </div>
        )}
        <p className="text-sm text-muted">Office contacts published by National Treasury. The mayor and speaker are elected councillors; the municipal manager and chief financial officer are the officials who run the administration and the money.</p>
        <div className="grid gap-6 md:grid-cols-2">
          {residentsSay.length > 0 && (
            <div className="card p-4">
              <h3 className="inline-flex items-center gap-2 font-bold"><MessageSquare size={18} aria-hidden />What residents here say</h3>
              <p className="text-sm text-muted">Gauteng City-Region Observatory Quality of Life survey, {residentsSay[0].year}.</p>
              <div className="mt-3"><Bars items={residentsSay.map((r) => ({ label: r.question, value: r.share }))} format={(v) => `${Math.round(v * 100)}%`} /></div>
            </div>
          )}
          <div className="card p-4">
            <h3 className="inline-flex items-center gap-2 font-bold"><SearchIcon size={18} aria-hidden />Investigations</h3>
            {siu.length > 0 ? (
              <ul className="mt-2 space-y-2 text-sm">
                {siu.map((c) => (
                  <li key={c.proclamation}><a className="text-link underline" href={c.link} target="_blank" rel="noopener">{c.proclamation}</a> ({c.date}): {c.title}</li>
                ))}
              </ul>
            ) : <p className="mt-2 text-sm">No Special Investigating Unit proclamation names this municipality.</p>}
            <p className="mt-2 text-sm text-muted">A proclamation means the President has ordered the SIU to investigate. It is not a finding of guilt.</p>
          </div>
        </div>
      </section>

      {/* 9. What you can do */}
      <section aria-labelledby="do" className="space-y-4">
        <h2 id="do" className="font-display text-3xl">What you can do</h2>
        <p className="max-w-2xl">These are chosen from the problems above. Start with the one that affects you most. Every step is free.</p>
        <div className="grid gap-4 md:grid-cols-2">
          {actions.map((a) => (
            <div key={a.id} className="card flex flex-col p-4">
              <h3 className="font-display text-xl">{a.title}</h3>
              <p className="mt-1 text-sm">{a.why}</p>
              <p className="mt-2 flex flex-wrap gap-1 text-xs font-bold">
                {a.who.map((w) => <span key={w} className="rounded bg-sunk px-2 py-0.5">{SPHERE_LABEL[w]}</span>)}
              </p>
              <ol className="mt-3 list-decimal space-y-1 pl-5">{a.steps.map((s) => <li key={s}>{s}</li>)}</ol>
              {a.right && <p className="mt-2 text-sm text-muted">{a.right}</p>}
              <ul className="mt-3 space-y-1 text-sm">
                {a.contacts.map((c) => (
                  <li key={c.label}>
                    {c.tel ? <a className="font-bold text-link underline" href={`tel:${c.tel.replace(/\s/g, "")}`}>{c.label}: {c.tel}</a>
                      : <a className="font-bold text-link underline" href={c.url} target="_blank" rel="noopener">{c.label}</a>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="board rounded p-4">
          <h3 className="font-display text-xl">The year, and when your voice counts most</h3>
          <ol className="mt-2 grid gap-2 sm:grid-cols-2">
            {YEAR_CALENDAR.map((c) => (
              <li key={c.months} className={c.key ? "font-bold" : ""}><span className="inline-block w-24">{c.months}</span>{c.text}</li>
            ))}
          </ol>
        </div>
      </section>

      <p className="text-sm text-muted"><Link href="/about" className="text-link underline">Where these numbers come from, and what they cannot tell you</Link>.</p>
    </article>
  );
}

function statusShare(v: number | null) {
  if (v == null) return "none" as const;
  return v >= 0.9 ? "good" : v >= 0.75 ? "warn" : v >= 0.6 ? "serious" : "bad";
}

function fmtFor(measure: string) {
  if (measure.endsWith("_rate")) return (v: number) => v.toFixed(1);
  return (v: number) => `${Math.round(v * 100)}%`;
}

function Card({ icon, title, big, status, statusLabel, children }: {
  icon: React.ReactNode; title: string; big: string; status: "good" | "warn" | "serious" | "bad" | "none"; statusLabel?: string; children?: React.ReactNode;
}) {
  return (
    <div className="card flex flex-col gap-2 p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="inline-flex items-center gap-2 font-bold">{icon}{title}</h3>
        {status !== "none" && <StatusBadge status={status} label={statusLabel} />}
      </div>
      <p className="font-display text-4xl">{big}</p>
      {children}
    </div>
  );
}

function Life({ icon, label, v }: { icon: React.ReactNode; label: string; v: number | null }) {
  return (
    <div className="card p-3">
      <p className="inline-flex items-center gap-2 text-sm font-bold">{icon}{label}</p>
      <p className="mt-1 font-display text-2xl">{v == null ? "no data" : `${Math.round(v * 10)} in 10`}</p>
      <PeopleRow share={v} />
    </div>
  );
}

