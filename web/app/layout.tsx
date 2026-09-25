import type { Metadata } from "next";
import { Atkinson_Hyperlegible, Archivo_Black } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const body = Atkinson_Hyperlegible({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-body", display: "swap" });
const heading = Archivo_Black({ subsets: ["latin"], weight: "400", variable: "--font-heading", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Masepala: know your municipality", template: "%s · Masepala" },
  description: "What your municipality is supposed to do, what it did with the money, how people live there, and what you can do about it. Built from public government data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-ZA" className={`${body.variable} ${heading.variable}`}>
      <body>
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:p-2">Skip to content</a>
        <header className="border-b-2 border-foreground bg-surface">
          <nav className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-2">
            <Link href="/" className="board inline-flex min-h-11 items-center rounded px-3 font-display text-xl tracking-wide">MASEPALA</Link>
            <div className="flex gap-1 text-sm font-bold">
              <Link href="/who-does-what" className="inline-flex min-h-11 items-center rounded px-3 hover:bg-sunk">Who does what</Link>
              <Link href="/about" className="inline-flex min-h-11 items-center rounded px-3 hover:bg-sunk">About the data</Link>
              <Link href="/status" className="inline-flex min-h-11 items-center rounded px-3 hover:bg-sunk">Data health</Link>
            </div>
          </nav>
        </header>
        <main id="main" className="mx-auto max-w-5xl px-4 pb-16">{children}</main>
        <footer className="border-t border-border py-6 text-center text-sm text-muted">
          <p>Built from public data: National Treasury, Stats SA, SAPS, the Municipal Demarcation Board, Youth Explorer and Vulekamali.</p>
          <p className="mt-1">You are the government. This is your information.</p>
        </footer>
      </body>
    </html>
  );
}
