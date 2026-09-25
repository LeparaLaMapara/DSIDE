import type { Metadata } from "next";
import { meta } from "@/lib/data";

export const metadata: Metadata = {
  title: "About the data",
  description: "Where every number on Masepala comes from, how the scores are made, and what they cannot tell you.",
};

const fy = (y: number) => `${y - 1}-${String(y).slice(2)}`;

export default function About() {
  const m = meta();
  const t = m.audit_model.test;
  const bestSilhouette = Math.max(...Object.values(m.groups.kmeans_silhouette_by_k));
  const jobsUrl = m.jobs.source.split(" ")[0];
  const jobsFallback = m.jobs.source.includes("last saved");

  return (
    <div className="max-w-3xl space-y-10 pt-8">
      <header>
        <h1 className="font-display text-4xl">About the data</h1>
        <p className="mt-3 text-lg">
          Every number here comes from a public government source. Nothing is typed in by hand. The data is collected
          again whenever the pipeline runs, and this page shows how old each piece is.
        </p>
        <p className="mt-2 text-muted">Last collected: {new Date(m.built_at).toUTCString()}.</p>
        {m.stale_sources && Object.keys(m.stale_sources).length > 0 && (
          <p className="mt-2 rounded border-2 border-warn p-3 text-sm">
            At the last collection these sources could not be reached, so their last good copy is shown:{" "}
            {Object.entries(m.stale_sources).map(([k, v]) => `${k.replace(/_/g, " ")} (copy from ${v.fetched_at?.slice(0, 10) ?? "an earlier run"})`).join(", ")}.
          </p>
        )}
      </header>

      <section>
        <h2 className="font-display text-2xl">Sources</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li><strong>Money and audits:</strong> National Treasury, Municipal Money (municipaldata.treasury.gov.za): budgets, audited spending, building spending, wasted money and audit outcomes. Year used: {fy(m.money_year)}, the latest with budgets and audited results for most municipalities.</li>
          <li><strong>How people live:</strong> Stats SA Census 2022 per municipality, through the Wazimap API run by OpenUp.</li>
          <li><strong>Young people:</strong> Youth Explorer (Census 2011), through the same API. It is the newest youth data published for every municipality.</li>
          <li><strong>Crime:</strong> SAPS quarterly crime statistics per police station, {m.safety.period} (<a className="text-link underline" href={m.safety.source}>file</a>). Stations are linked to municipalities with Adrian Frith&apos;s cleaned police precinct table, built from Stats SA boundaries and Census 2022 population. Stations not yet in that table: {m.safety.unmatched_stations || "none"}.</li>
          <li><strong>Jobs now:</strong> Stats SA Quarterly Labour Force Survey, {m.jobs.period} (<a className="text-link underline" href={jobsUrl}>file</a>).{jobsFallback && " Stats SA's server did not respond at the last collection, so the last saved copy was used."}</li>
          <li><strong>Wards:</strong> Municipal Demarcation Board ward profiles (Census 2011 figures re-mapped to the 2021 wards). Ward councillors: 2021 election results for every ward, with the City of Tshwane&apos;s own list (and phone numbers) where it is newer.</li>
          <li><strong>Government projects:</strong> Vulekamali (National Treasury): every provincial and national project with a location.</li>
          <li><strong>This year&apos;s money, debts and grants:</strong> National Treasury monthly returns for the current financial year (who owes the municipality, what it owes Eskom and water boards, grants received and spent, cash at year end), and the officials list with office contacts.</li>
          <li><strong>Jobs and pay:</strong> the Spatial Tax Panel (SARS, National Treasury and HSRC), formal jobs, youth jobs and median pay per municipality from tax records, latest tax year. It counts formal jobs only.</li>
          <li><strong>Population now:</strong> Stats SA mid-year estimates for 2026, published for districts and metros; local municipalities show their district&apos;s figure.</li>
          <li><strong>Grants to people:</strong> SASSA monthly report of Social Relief of Distress (R370) payments per municipality.</li>
          <li><strong>Water quality:</strong> Department of Water and Sanitation Green Drop (waste water) and Blue Drop (drinking water) reports. Only water services authorities are scored, so some local municipalities show their district&apos;s score.</li>
          <li><strong>Schools and matric:</strong> the Department of Basic Education school master list (with locations corrected where latitude and longitude were swapped) and the 2024 National Senior Certificate school performance report.</li>
          <li><strong>Elections:</strong> 2021 local election and 2024 national election results for every ward, published by the Electoral Commission through SANEF&apos;s Wazimap.</li>
          <li><strong>What residents say (Gauteng):</strong> Gauteng City-Region Observatory Quality of Life survey 2023/24. Samples for small municipalities are small, so treat those shares as indicative.</li>
          <li><strong>Investigations:</strong> Special Investigating Unit local government proclamations.</li>
          <li><strong>Live layer, every few hours:</strong> the City of Tshwane&apos;s public electricity outage map, Eskom&apos;s loadshedding status, and headlines from South African news feeds (SABC, eNCA, News24, IOL, The Citizen, Daily Maverick, GroundUp, SAnews, gov.za, Rekord, Lowvelder and city notices). We show only the headline, outlet, date and link. Headlines are placed by matching place names by computer and are not checked by a person.</li>
          <li><strong>Satellite images:</strong> Esri World Imagery, with road and place names from Esri.</li>
          <li><strong>What you can do:</strong> official public lines only: the GBV Command Centre, SAPS Crime Stop, the substance abuse helpline, the Public Protector, the SA Human Rights Commission, SAYouth, NYDA and NSFAS.</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl">How the scores are made</h2>
        <h3 className="mt-3 font-bold">Handling money (0 to 100)</h3>
        <p>
          Up to five parts, each compared with National Treasury norms: the audit outcome; the share of the building
          budget actually spent (full marks at 95%); money spent against the rules or wasted (full marks at 0%); bills
          never paid (full marks at 5% or less); and income collected against the plan. A part is left out, and the page
          says so, when Treasury&apos;s own number is impossible, for example spending more than three times the budget.
        </p>
        <p className="mt-2 text-sm text-muted">
          We do not use Treasury&apos;s ready-made Municipal Money indicators for recent years. For many municipalities
          they are broken (actual spending shown as eight times the budget, for example), so everything is recalculated
          from the raw tables.
        </p>

        <h3 className="mt-4 font-bold">Life here (wellbeing, 0 to 100)</h3>
        <p>
          Four equal parts, following Stats SA&apos;s multidimensional poverty index: home and services (water, toilet,
          electricity, rubbish, housing, cooking fuel); learning (adults with matric, children in early learning); work
          and income (formal jobs per working-age adult and typical formal pay, from the latest tax records); and safety (murders and sexual offences per person). Each measure is scaled so 0 is the
          worst municipality and 100 the best. These are shares of people, not a household poverty count, because only
          totals are published per municipality.
        </p>
        <p className="mt-2">
          Weights are a choice, so we test the choice: every ranking is recalculated 5,000 times with random weights.
          When a municipality&apos;s rank moves a lot, its page says so.
        </p>

        <h3 className="mt-4 font-bold">Four kinds of municipality</h3>
        <p>
          We first asked a clustering algorithm (k-means) to find natural groups. It found none worth trusting: the best
          split scored {bestSilhouette.toFixed(2)} on a scale where anything under 0.5 means weak groups, and some
          municipalities landed in groups their own numbers contradicted. So we use a simple, honest grid: services above
          or below the national middle, and money handling above or below the middle.
        </p>

        <h3 id="audit-model" className="mt-4 font-bold">Audit chance</h3>
        <p>
          {m.audit_model.question} A {m.audit_model.model === "logistic" ? "logistic regression" : "gradient boosting"} model
          learned from audit history ({m.audit_model.trained_on_years}) and was tested on {m.audit_model.tested_on_year},
          a year it never saw.
        </p>
        <div className="scroll-x mt-2">
          <table className="w-full min-w-[420px] text-left text-sm">
            <thead>
              <tr className="border-b-2 border-foreground">
                <th className="py-1">Tested on {m.audit_model.tested_on_year} ({t.n} municipalities)</th><th>Right</th><th>Error score (lower is better)</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border"><td className="py-1">Our model</td><td>{(t.model_accuracy * 100).toFixed(1)}%</td><td>{t.model_brier}</td></tr>
              <tr className="border-b border-border"><td className="py-1">Simple guess: same as last year</td><td>{(t.naive_accuracy * 100).toFixed(1)}%</td><td>{t.naive_brier}</td></tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2">
          The honest reading: the model is only a little better than guessing &quot;same as last year&quot;. Its value is that it
          gives a chance instead of a yes or no. A municipality&apos;s past is the strongest sign of its next audit.
        </p>
        <p className="mt-2">
          Every quarter a new version is trained and kept in a model registry with these scores. It only replaces the version in
          use if it beats the simple guess and does no worse than the current version; otherwise the current one stays. When the
          Auditor-General publishes the year we predicted, the prediction is scored against what really happened.{" "}
          {m.audit_model.registry?.live_version && <>Version in use: {m.audit_model.registry.live_version}. </>}
          <a href="/status" className="text-link underline">See the checks and the track record</a>.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl">What these numbers cannot tell you</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>Census 2022 did not ask about jobs or income. Tax records give formal jobs and pay per municipality up to the latest tax year, but informal work (spaza shops, piece jobs) is not in them.</li>
          <li>Ward figures on water, toilets and schooling are still from Census 2011, because Census 2022 results per ward are not published yet.</li>
          <li>Police precincts do not follow municipal borders. A station is counted in the municipality where most of its precinct lies.</li>
          <li>&quot;What goes with these problems&quot; shows facts that sit side by side. It does not prove what caused what.</li>
          <li>We never show nationality or origin next to crime or service failures. The research does not support blaming a group, and doing so has led to violence.</li>
        </ul>
      </section>
    </div>
  );
}
