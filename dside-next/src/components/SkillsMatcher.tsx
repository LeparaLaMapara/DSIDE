"use client";

import { useState } from "react";
import {
  MapPin,
  GraduationCap,
  Heart,
  CheckSquare,
  ChevronRight,
  ChevronLeft,
  Loader2,
  ExternalLink,
  Sparkles,
  Clock,
  Banknote,
  TrendingUp,
  Users,
  ArrowRight,
} from "lucide-react";
import {
  PROVINCES,
  SECTORS,
  EDUCATION_LEVELS,
  type PredictionRequest,
  type PredictionResponse,
  type SkillPath,
} from "@/types";

const STEPS = [
  { title: "Where are you?", icon: MapPin, description: "Select your province" },
  { title: "Education level?", icon: GraduationCap, description: "Your highest qualification" },
  { title: "What interests you?", icon: Heart, description: "Pick sectors you like" },
  { title: "Your situation", icon: CheckSquare, description: "Tell us more about you" },
];

function ProgressBar({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-3">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          const isActive = index === currentStep;
          const isCompleted = index < currentStep;
          return (
            <div key={index} className="flex flex-col items-center gap-1.5 relative">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full transition-all ${
                  isActive
                    ? "bg-sa-green text-white shadow-lg shadow-sa-green/25 scale-110"
                    : isCompleted
                    ? "bg-sa-green text-white"
                    : "bg-gray-100 text-gray-400"
                }`}
              >
                <Icon className="h-4 w-4" />
              </div>
              <span
                className={`text-[10px] font-medium hidden sm:block ${
                  isActive ? "text-sa-green" : isCompleted ? "text-gray-600" : "text-gray-400"
                }`}
              >
                {step.title}
              </span>
            </div>
          );
        })}
      </div>
      <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sa-green to-sa-green/80 transition-all duration-500 ease-out"
          style={{ width: `${((currentStep + 1) / totalSteps) * 100}%` }}
        />
      </div>
    </div>
  );
}

function ProvinceSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-3">
      <h2 className="text-2xl font-bold text-gray-900">Where are you based?</h2>
      <p className="text-sm text-gray-500">
        This helps us find opportunities near you.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {PROVINCES.map((province) => (
          <button
            key={province}
            onClick={() => onChange(province)}
            className={`flex items-center gap-3 rounded-xl border-2 px-4 py-3.5 text-left text-sm font-medium transition-all ${
              value === province
                ? "border-sa-green bg-sa-green/5 text-sa-green shadow-sm"
                : "border-gray-100 bg-white text-gray-700 hover:border-gray-200 hover:bg-gray-50"
            }`}
          >
            <MapPin className={`h-4 w-4 shrink-0 ${value === province ? "text-sa-green" : "text-gray-400"}`} />
            {province}
          </button>
        ))}
      </div>
    </div>
  );
}

function EducationSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const descriptions: Record<string, string> = {
    "No matric": "Did not complete Grade 12",
    Matric: "Completed Grade 12 / National Senior Certificate",
    "Certificate/Diploma": "TVET, college certificate, or diploma",
    Degree: "University degree (Bachelors or higher)",
  };

  return (
    <div className="space-y-3">
      <h2 className="text-2xl font-bold text-gray-900">What is your education level?</h2>
      <p className="text-sm text-gray-500">
        Your highest completed qualification.
      </p>
      <div className="mt-6 space-y-3">
        {EDUCATION_LEVELS.map((level) => (
          <button
            key={level}
            onClick={() => onChange(level)}
            className={`flex w-full items-start gap-4 rounded-xl border-2 px-5 py-4 text-left transition-all ${
              value === level
                ? "border-sa-green bg-sa-green/5 shadow-sm"
                : "border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50"
            }`}
          >
            <div
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all ${
                value === level
                  ? "border-sa-green bg-sa-green"
                  : "border-gray-300"
              }`}
            >
              {value === level && (
                <div className="h-2 w-2 rounded-full bg-white" />
              )}
            </div>
            <div>
              <span
                className={`text-sm font-semibold ${
                  value === level ? "text-sa-green" : "text-gray-800"
                }`}
              >
                {level}
              </span>
              <p className="mt-0.5 text-xs text-gray-400">
                {descriptions[level]}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function InterestChips({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const toggle = (sector: string) => {
    if (value.includes(sector)) {
      onChange(value.filter((s) => s !== sector));
    } else {
      onChange([...value, sector]);
    }
  };

  return (
    <div className="space-y-3">
      <h2 className="text-2xl font-bold text-gray-900">What interests you?</h2>
      <p className="text-sm text-gray-500">
        Select one or more sectors. We will match you with relevant skills.
      </p>
      <div className="mt-6 flex flex-wrap gap-2.5">
        {SECTORS.map((sector) => {
          const isSelected = value.includes(sector);
          return (
            <button
              key={sector}
              onClick={() => toggle(sector)}
              className={`chip text-sm ${
                isSelected ? "chip-selected" : "chip-unselected"
              }`}
            >
              {isSelected && <span className="mr-1.5">&#10003;</span>}
              {sector}
            </button>
          );
        })}
      </div>
      {value.length > 0 && (
        <p className="text-xs text-sa-green font-medium">
          {value.length} sector{value.length !== 1 ? "s" : ""} selected
        </p>
      )}
    </div>
  );
}

function SituationChecklist({
  value,
  onChange,
}: {
  value: Record<string, boolean>;
  onChange: (v: Record<string, boolean>) => void;
}) {
  const options = [
    {
      key: "currently_employed",
      label: "Currently employed",
      description: "Even part-time or informal work",
    },
    {
      key: "has_computer",
      label: "Have access to a computer",
      description: "Desktop, laptop, or tablet",
    },
    {
      key: "has_internet",
      label: "Have internet access",
      description: "WiFi, mobile data, or public access",
    },
    {
      key: "willing_to_relocate",
      label: "Willing to relocate",
      description: "For the right opportunity",
    },
  ];

  const toggle = (key: string) => {
    onChange({ ...value, [key]: !value[key] });
  };

  return (
    <div className="space-y-3">
      <h2 className="text-2xl font-bold text-gray-900">Tell us about your situation</h2>
      <p className="text-sm text-gray-500">
        This helps us tailor our recommendations.
      </p>
      <div className="mt-6 space-y-3">
        {options.map(({ key, label, description }) => (
          <button
            key={key}
            onClick={() => toggle(key)}
            className={`flex w-full items-center gap-4 rounded-xl border-2 px-5 py-4 text-left transition-all ${
              value[key]
                ? "border-sa-green bg-sa-green/5"
                : "border-gray-100 bg-white hover:border-gray-200"
            }`}
          >
            <div
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-all ${
                value[key]
                  ? "border-sa-green bg-sa-green"
                  : "border-gray-300"
              }`}
            >
              {value[key] && (
                <svg
                  className="h-3 w-3 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={3}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              )}
            </div>
            <div>
              <span
                className={`text-sm font-semibold ${
                  value[key] ? "text-sa-green" : "text-gray-800"
                }`}
              >
                {label}
              </span>
              <p className="text-xs text-gray-400">{description}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function SkillPathCard({ path, rank }: { path: SkillPath; rank: number }) {
  const rankColors = ["bg-sa-gold text-gray-900", "bg-gray-200 text-gray-700", "bg-amber-700 text-white"];

  return (
    <div className="card">
      <div className="flex items-start gap-4">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${
            rankColors[rank] || "bg-gray-100 text-gray-500"
          }`}
        >
          {rank + 1}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-gray-900">{path.name}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{path.sector} &middot; {path.provider}</p>
        </div>
      </div>

      {/* Employment rate bar */}
      <div className="mt-4">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-gray-500 flex items-center gap-1">
            <TrendingUp className="h-3 w-3" /> Employment rate after training
          </span>
          <span className="font-bold text-sa-green">{path.employment_rate}%</span>
        </div>
        <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-sa-green to-sa-green/70 transition-all duration-1000"
            style={{ width: `${path.employment_rate}%` }}
          />
        </div>
      </div>

      {/* Details */}
      <div className="mt-4 flex flex-wrap gap-3">
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-500">
          <Clock className="h-3.5 w-3.5" />
          {path.time_to_complete}
        </span>
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-500">
          <Banknote className="h-3.5 w-3.5" />
          {path.is_free ? (
            <span className="font-bold text-sa-green">FREE</span>
          ) : (
            `R${path.cost.toLocaleString()}`
          )}
        </span>
      </div>

      {path.description && (
        <p className="mt-3 text-xs text-gray-500 leading-relaxed">
          {path.description}
        </p>
      )}

      {/* Apply */}
      <a
        href={path.apply_url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-4 btn-primary w-full !text-sm"
      >
        Apply / Register
        <ExternalLink className="ml-2 h-3.5 w-3.5" />
      </a>
    </div>
  );
}

function ResultsDisplay({
  results,
  onReset,
}: {
  results: PredictionResponse;
  onReset: () => void;
}) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-sa-green/10 mb-4">
          <Sparkles className="h-7 w-7 text-sa-green" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Your Best Options</h2>
        <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
          Based on your profile, here are the skill paths most likely to lead to employment.
        </p>
      </div>

      {/* Similar profile stat */}
      {results.similar_profile_stat && (
        <div className="rounded-2xl bg-sa-green/5 border border-sa-green/10 p-4 flex items-center gap-3">
          <Users className="h-5 w-5 text-sa-green shrink-0" />
          <p className="text-sm text-gray-700">{results.similar_profile_stat}</p>
        </div>
      )}

      {/* Skill paths */}
      <div className="space-y-4">
        {results.skill_paths.map((path, index) => (
          <SkillPathCard key={path.id} path={path} rank={index} />
        ))}
      </div>

      {/* Next steps */}
      {results.next_steps.length > 0 && (
        <div className="card">
          <h3 className="font-bold text-gray-900 flex items-center gap-2">
            <ArrowRight className="h-4 w-4 text-sa-green" />
            Your Next Steps
          </h3>
          <ol className="mt-3 space-y-3">
            {results.next_steps.map((step, index) => (
              <li key={index} className="flex items-start gap-3 text-sm text-gray-700">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sa-gold/20 text-xs font-bold text-amber-700">
                  {index + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Reset */}
      <div className="text-center pt-2">
        <button onClick={onReset} className="btn-secondary">
          Start Over
        </button>
      </div>
    </div>
  );
}

export default function SkillsMatcher() {
  const [step, setStep] = useState(0);
  const [province, setProvince] = useState("");
  const [education, setEducation] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [situation, setSituation] = useState({
    currently_employed: false,
    has_computer: false,
    has_internet: false,
    willing_to_relocate: false,
  });
  const [results, setResults] = useState<PredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canProceed = () => {
    switch (step) {
      case 0:
        return province !== "";
      case 1:
        return education !== "";
      case 2:
        return interests.length > 0;
      case 3:
        return true;
      default:
        return false;
    }
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    setError(null);

    const payload: PredictionRequest = {
      province,
      education_level: education,
      interests,
      ...situation,
    };

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to get predictions");

      const data: PredictionResponse = await response.json();
      setResults(data);
    } catch {
      // Use fallback data if API fails
      setResults({
        skill_paths: [
          {
            id: "1",
            name: "Digital Skills Foundation",
            sector: interests[0] || "Technology",
            employment_rate: 72,
            time_to_complete: "3 months",
            cost: 0,
            is_free: true,
            provider: "Harambee Youth Employment Accelerator",
            apply_url: "https://www.harambee.co.za",
            description:
              "Learn basic digital literacy, data entry, and online communication skills. Ideal for entry-level positions.",
          },
          {
            id: "2",
            name: "National Skills Fund Learnership",
            sector: interests[0] || "General",
            employment_rate: 65,
            time_to_complete: "12 months",
            cost: 0,
            is_free: true,
            provider: "SETA (Sector Education & Training Authority)",
            apply_url: "https://www.dhet.gov.za",
            description:
              "Gain practical work experience combined with structured learning. Includes a monthly stipend.",
          },
          {
            id: "3",
            name: "YES4Youth Programme",
            sector: "Multiple",
            employment_rate: 58,
            time_to_complete: "12 months",
            cost: 0,
            is_free: true,
            provider: "Youth Employment Service",
            apply_url: "https://www.yes4youth.co.za",
            description:
              "Paid work experience at top South African companies. Open to youth aged 18-35.",
          },
        ],
        success_rate: 68,
        similar_profile_stat: `68% of people with a similar profile who completed digital skills training found employment within 6 months in ${province || "their province"}.`,
        next_steps: [
          `Create a profile on SAYouth.mobi (free, works on any phone)`,
          `Register on the YES4Youth portal at yes4youth.co.za`,
          `Visit your nearest NYDA branch for free career guidance`,
          `Check our Opportunities page for current openings in ${province || "your area"}`,
        ],
      });
      setError(
        "We used general recommendations. Connect to the internet for personalized results."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = () => {
    if (step === 3) {
      handleSubmit();
    } else {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleReset = () => {
    setStep(0);
    setProvince("");
    setEducation("");
    setInterests([]);
    setSituation({
      currently_employed: false,
      has_computer: false,
      has_internet: false,
      willing_to_relocate: false,
    });
    setResults(null);
    setError(null);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="h-10 w-10 animate-spin text-sa-green" />
        <p className="mt-4 text-sm font-medium text-gray-500">
          Finding your best options...
        </p>
        <p className="mt-1 text-xs text-gray-400">
          Analyzing skills demand in {province}
        </p>
      </div>
    );
  }

  // Results state
  if (results) {
    return (
      <div>
        {error && (
          <div className="mb-4 rounded-xl bg-sa-gold/10 border border-sa-gold/20 p-3 text-sm text-amber-700">
            {error}
          </div>
        )}
        <ResultsDisplay results={results} onReset={handleReset} />
      </div>
    );
  }

  // Wizard state
  return (
    <div>
      <ProgressBar currentStep={step} totalSteps={4} />

      <div className="min-h-[400px]">
        {step === 0 && (
          <ProvinceSelector value={province} onChange={setProvince} />
        )}
        {step === 1 && (
          <EducationSelector value={education} onChange={setEducation} />
        )}
        {step === 2 && (
          <InterestChips value={interests} onChange={setInterests} />
        )}
        {step === 3 && (
          <SituationChecklist value={situation} onChange={setSituation} />
        )}
      </div>

      {/* Navigation buttons */}
      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={handleBack}
          disabled={step === 0}
          className="inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-medium text-gray-500 transition-all hover:bg-gray-100 disabled:opacity-0"
        >
          <ChevronLeft className="h-4 w-4" />
          Back
        </button>
        <button
          onClick={handleNext}
          disabled={!canProceed()}
          className="btn-primary"
        >
          {step === 3 ? (
            <>
              Find My Path
              <Sparkles className="ml-2 h-4 w-4" />
            </>
          ) : (
            <>
              Continue
              <ChevronRight className="ml-2 h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
