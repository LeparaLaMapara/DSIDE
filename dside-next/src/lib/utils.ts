import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge class names with Tailwind CSS conflict resolution.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number with thousands separators (SA locale).
 */
export function formatNumber(value: number, decimals: number = 0): string {
  return new Intl.NumberFormat('en-ZA', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a number as a percentage.
 */
export function formatPercent(value: number, decimals: number = 1): string {
  return new Intl.NumberFormat('en-ZA', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

/**
 * Format a number as South African Rand (ZAR).
 */
export function formatCurrency(value: number, compact: boolean = false): string {
  if (compact) {
    if (value >= 1_000_000_000) {
      return `R${(value / 1_000_000_000).toFixed(1)}B`;
    }
    if (value >= 1_000_000) {
      return `R${(value / 1_000_000).toFixed(1)}M`;
    }
    if (value >= 1_000) {
      return `R${(value / 1_000).toFixed(1)}K`;
    }
  }

  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: 'ZAR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}
