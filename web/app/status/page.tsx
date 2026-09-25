import type { Metadata } from "next";
import { Health } from "@/components/health";

export const metadata: Metadata = {
  title: "Is the data healthy?",
  description: "Which government sources answered at the last collection, which checks passed, and whether the audit prediction earned its place.",
};

export default function Status() {
  return (
    <div className="max-w-3xl space-y-10 pt-8">
      <header>
        <h1 className="font-display text-4xl">Is the data healthy?</h1>
        <p className="mt-3 text-lg">
          Government websites break quietly: a page moves, a table shrinks, a site stops answering. After every
          collection the pipeline checks each source and each step, compares the result with the last one, and
          writes what it found here. If a check fails, the site keeps showing the last good data and a person is told.
        </p>
      </header>
      <Health />
    </div>
  );
}
