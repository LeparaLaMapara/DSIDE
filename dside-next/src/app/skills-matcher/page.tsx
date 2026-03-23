"use client";

import SkillsMatcher from "@/components/SkillsMatcher";
import { Compass } from "lucide-react";

export default function SkillsMatcherPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {/* Page header */}
      <div className="mb-8 text-center">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-sa-green/10 mb-4">
          <Compass className="h-7 w-7 text-sa-green" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Skills Matcher</h1>
        <p className="mt-2 text-sm text-gray-500 max-w-sm mx-auto">
          Answer a few questions and we will match you with skills and training
          programs that lead to real jobs in your area.
        </p>
      </div>

      {/* Wizard */}
      <SkillsMatcher />
    </div>
  );
}
