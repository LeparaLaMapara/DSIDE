"use client";

import { TrendingUp, TrendingDown, type LucideIcon } from "lucide-react";

interface StatsCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  trend?: {
    direction: "up" | "down";
    percentage: number;
    label?: string;
  };
  color?: "green" | "gold" | "blue" | "red";
}

const colorMap = {
  green: "bg-sa-green/10 text-sa-green",
  gold: "bg-sa-gold/10 text-sa-gold",
  blue: "bg-sa-blue/10 text-sa-blue",
  red: "bg-red-50 text-red-600",
};

export default function StatsCard({
  icon: Icon,
  label,
  value,
  trend,
  color = "green",
}: StatsCardProps) {
  return (
    <div className="card flex items-start gap-4">
      <div className={`rounded-xl p-3 ${colorMap[color]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-500 truncate">{label}</p>
        <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
        {trend && (
          <div className="mt-1 flex items-center gap-1">
            {trend.direction === "up" ? (
              <TrendingUp className="h-3.5 w-3.5 text-sa-green" />
            ) : (
              <TrendingDown className="h-3.5 w-3.5 text-red-500" />
            )}
            <span
              className={`text-xs font-medium ${
                trend.direction === "up" ? "text-sa-green" : "text-red-500"
              }`}
            >
              {trend.percentage}%
            </span>
            {trend.label && (
              <span className="text-xs text-gray-400">{trend.label}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function StatsCardSkeleton() {
  return (
    <div className="card flex items-start gap-4">
      <div className="skeleton h-11 w-11 rounded-xl" />
      <div className="flex-1">
        <div className="skeleton h-4 w-24 rounded" />
        <div className="skeleton mt-2 h-7 w-16 rounded" />
      </div>
    </div>
  );
}
