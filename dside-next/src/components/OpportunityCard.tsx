"use client";

import {
  MapPin,
  Calendar,
  Banknote,
  ExternalLink,
  Clock,
} from "lucide-react";
import type { Opportunity } from "@/types";

interface OpportunityCardProps {
  opportunity: Opportunity;
}

const typeBadgeColors: Record<Opportunity["type"], string> = {
  learnership: "bg-sa-green/10 text-sa-green border-sa-green/20",
  internship: "bg-sa-blue/10 text-sa-blue border-sa-blue/20",
  job: "bg-sa-gold/10 text-amber-700 border-sa-gold/20",
  bursary: "bg-purple-50 text-purple-700 border-purple-200",
  training: "bg-teal-50 text-teal-700 border-teal-200",
};

const typeLabels: Record<Opportunity["type"], string> = {
  learnership: "Learnership",
  internship: "Internship",
  job: "Job",
  bursary: "Bursary",
  training: "Training",
};

function getDaysUntilDeadline(deadline: string): number {
  const deadlineDate = new Date(deadline);
  const now = new Date();
  const diff = deadlineDate.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export default function OpportunityCard({ opportunity }: OpportunityCardProps) {
  const daysLeft = getDaysUntilDeadline(opportunity.deadline);
  const isUrgent = daysLeft > 0 && daysLeft <= 7;
  const isExpired = daysLeft <= 0;

  return (
    <div className="card group flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`chip !px-2.5 !py-1 !text-xs border ${
                typeBadgeColors[opportunity.type]
              }`}
            >
              {typeLabels[opportunity.type]}
            </span>
            {opportunity.is_free && (
              <span className="chip !px-2.5 !py-1 !text-xs bg-sa-green/10 text-sa-green font-bold">
                FREE
              </span>
            )}
          </div>
          <h3 className="mt-2 text-base font-semibold text-gray-900 leading-tight line-clamp-2">
            {opportunity.title}
          </h3>
          <p className="mt-1 text-sm text-gray-500">{opportunity.provider}</p>
        </div>
      </div>

      {/* Details */}
      <div className="mt-4 flex flex-wrap gap-3 text-sm text-gray-500">
        <span className="inline-flex items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5" />
          {opportunity.province}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Banknote className="h-3.5 w-3.5" />
          {opportunity.stipend_amount
            ? `R${opportunity.stipend_amount.toLocaleString()}/mo`
            : "Free"}
        </span>
      </div>

      {/* Sector */}
      <div className="mt-3">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          {opportunity.sector}
        </span>
      </div>

      {/* Footer */}
      <div className="mt-auto pt-4 flex items-center justify-between border-t border-gray-100">
        <div className="flex items-center gap-1.5">
          {isExpired ? (
            <span className="text-xs font-medium text-gray-400">Expired</span>
          ) : isUrgent ? (
            <>
              <Clock className="h-3.5 w-3.5 text-red-500" />
              <span className="text-xs font-semibold text-red-500">
                Closing in {daysLeft} day{daysLeft !== 1 ? "s" : ""}!
              </span>
            </>
          ) : (
            <>
              <Calendar className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-xs text-gray-400">
                Closes {new Date(opportunity.deadline).toLocaleDateString("en-ZA", { day: "numeric", month: "short" })}
              </span>
            </>
          )}
        </div>
        <a
          href={opportunity.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold transition-all ${
            isExpired
              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
              : "bg-sa-green text-white hover:bg-sa-green/90 active:scale-[0.98]"
          }`}
          onClick={(e) => isExpired && e.preventDefault()}
        >
          Apply
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

export function OpportunityCardSkeleton() {
  return (
    <div className="card flex flex-col">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="skeleton h-5 w-20 rounded-full" />
          <div className="skeleton mt-2 h-5 w-full rounded" />
          <div className="skeleton mt-1 h-4 w-32 rounded" />
        </div>
      </div>
      <div className="mt-4 flex gap-3">
        <div className="skeleton h-4 w-24 rounded" />
        <div className="skeleton h-4 w-20 rounded" />
      </div>
      <div className="mt-auto pt-4 flex items-center justify-between border-t border-gray-100">
        <div className="skeleton h-4 w-24 rounded" />
        <div className="skeleton h-8 w-20 rounded-lg" />
      </div>
    </div>
  );
}
