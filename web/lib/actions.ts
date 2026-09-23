// What an ordinary person can do. Every contact here is a public, official
// line; the sources are listed on the About page. Keep business values here,
// never inside components.
import type { Muni } from "./data";

export type Sphere = "municipality" | "province" | "national";

export const SPHERE_LABEL: Record<Sphere, string> = {
  municipality: "Your municipality",
  province: "Your province",
  national: "National government",
};

export const CONTACTS = {
  gbv: { label: "GBV Command Centre (24 hours, free)", tel: "0800 428 428" },
  crimeStop: { label: "SAPS Crime Stop (anonymous tips)", tel: "08600 10111" },
  drugs: { label: "Substance abuse helpline (free)", tel: "0800 12 13 14" },
  publicProtector: { label: "Public Protector (free)", tel: "0800 11 20 40" },
  sahrc: { label: "SA Human Rights Commission", url: "https://www.sahrc.org.za" },
  sayouth: { label: "SAYouth: free job and learning network", url: "https://sayouth.mobi" },
  nyda: { label: "NYDA: support for young people starting a business", url: "https://www.nyda.gov.za" },
  nsfas: { label: "NSFAS: free study funding", url: "https://www.nsfas.org.za" },
  treasury: { label: "Your municipality's money on Municipal Money", url: "https://municipalmoney.gov.za" },
} as const;

/** Cities that publish their own call centre number (pilot). */
export const CITY_LINES: Record<string, { label: string; tel: string }> = {
  TSH: { label: "City of Tshwane call centre", tel: "012 358 9999" },
};

export type Action = {
  id: string;
  title: string;
  why: string;
  who: Sphere[];
  steps: string[];
  right?: string;
  contacts: { label: string; tel?: string; url?: string }[];
};

const muniLine = (m: Muni) =>
  CITY_LINES[m.code] ?? (m.phone ? { label: `${m.name} offices`, tel: m.phone } : null);

const low = (m: Muni, measure: string) => m.problems.some((p) => p.measure === measure);

export function actionsFor(m: Muni): Action[] {
  const line = muniLine(m);
  const local = line ? [line] : [];
  const out: Action[] = [];

  if (low(m, "water") || low(m, "toilet") || (typeof m.water === "number" && m.water < 0.9)) {
    out.push({
      id: "water",
      title: "No water, or no proper toilet",
      why: "Water and sanitation are your municipality's job, and a right in the Constitution.",
      who: ["municipality"],
      steps: [
        "Report every outage to the municipality and write down the reference number.",
        "Take the reference numbers to your ward councillor and ward committee. Ask when it will be fixed, in writing.",
        "If nothing happens, complain to the SA Human Rights Commission. Water is a right, not a favour.",
      ],
      right: "Constitution, section 27: everyone has the right to sufficient water.",
      contacts: [...local, CONTACTS.sahrc],
    });
  }
  if (low(m, "lighting") || (typeof m.lighting === "number" && m.lighting < 0.9)) {
    out.push({
      id: "electricity",
      title: "No electricity, or illegal connections",
      why: "Illegal connections overload transformers, so paying households lose power too.",
      who: ["municipality", "national"],
      steps: [
        "Report illegal connections to the municipality. Do not confront the people selling connections yourself: it can be dangerous.",
        "Ask your councillor for the plan to electrify nearby informal settlements properly. That is the lasting fix.",
        "Check your bill or meter: it shows if Eskom or the municipality supplies you, so you complain to the right one.",
      ],
      contacts: [...local],
    });
  }
  if (low(m, "refuse")) {
    out.push({
      id: "refuse",
      title: "Rubbish not collected",
      why: "Rubbish removal is a municipal service you pay for through rates or service charges.",
      who: ["municipality"],
      steps: [
        "Report missed collections and illegal dumping, with the street name and a photo.",
        "Ask the ward committee to put collection days on the next ward meeting agenda.",
      ],
      contacts: [...local],
    });
  }

  out.push({
    id: "safety",
    title: "Crime, rape and drugs",
    why: "Police are national, but communities have a legal seat at the table through the Community Policing Forum.",
    who: ["national", "municipality"],
    steps: [
      "Join the Community Policing Forum (CPF) at your police station. It meets with the station commander.",
      "Report drug dealing anonymously to Crime Stop. You do not have to give your name.",
      "If someone is hurt or raped: call the GBV Command Centre any time, day or night. A Thuthuzela Care Centre helps rape survivors in one place.",
    ],
    contacts: [CONTACTS.gbv, CONTACTS.crimeStop, CONTACTS.drugs],
  });

  out.push({
    id: "jobs",
    title: "Young people without work",
    why: "Jobs programmes are mostly national, but they only help people who are registered.",
    who: ["national", "municipality"],
    steps: [
      "Register on SAYouth. It is free and zero-rated on most networks, and employers search it.",
      "Ask the municipality about its internships and EPWP work. They must be advertised publicly.",
      "Starting something? NYDA gives grants and mentoring to young business owners.",
    ],
    contacts: [CONTACTS.sayouth, CONTACTS.nyda, CONTACTS.nsfas],
  });

  const spentLittle = typeof m.build_spent_share === "number" && m.build_spent_share < 0.8;
  const badAudit = ["qualified", "adverse", "disclaimer", "outstanding"].includes(m.audit_code ?? "");
  if (spentLittle || badAudit || low(m, "wasted_share")) {
    out.push({
      id: "money",
      title: "Money not spent, or spent wrongly",
      why: "The budget is public, and the law says residents must be able to comment on it before it is passed.",
      who: ["municipality"],
      steps: [
        "Every April and May the draft budget is published for comment. Ask your councillor for the date of the public meeting, then go.",
        "Ask in writing why the building budget was not spent, and which projects in your ward were delayed.",
        "Read what the Auditor-General found, and ask the council's oversight committee (MPAC) what was done about it.",
      ],
      right: "Municipal Finance Management Act: the draft budget must be made public and comments considered.",
      contacts: [...local, CONTACTS.publicProtector, CONTACTS.treasury],
    });
  }
  return out;
}

export const YEAR_CALENDAR = [
  { months: "Aug", text: "Council sets the timetable for next year's plan (IDP) and budget." },
  { months: "Sep to Nov", text: "Ward meetings collect what each area needs. Go and say it." },
  { months: "By Mar", text: "The draft budget and plan are tabled in council." },
  { months: "Apr to May", text: "Public comment on the budget. This is when your voice changes the money.", key: true },
  { months: "By end May", text: "Council passes the budget." },
  { months: "Jan to Mar", text: "Annual report and audit results are published for comment." },
];
