'use client';

import { Inter } from 'next/font/google';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  LayoutDashboard,
  Compass,
  Briefcase,
  Building2,
  MessageCircle,
  Menu,
  X,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/skills', label: 'Skills Matcher', icon: Compass },
  { href: '/opportunities', label: 'Opportunities', icon: Briefcase },
  { href: '/municipal', label: 'Municipal Intelligence', icon: Building2 },
  { href: '/chat', label: 'Chat', icon: MessageCircle },
];

function Sidebar({ mobile = false, onClose }: { mobile?: boolean; onClose?: () => void }) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        'flex flex-col bg-[rgb(var(--sidebar))] border-r border-[rgb(var(--sidebar-border))]',
        mobile ? 'w-72 h-full' : 'hidden lg:flex w-64 min-h-screen fixed left-0 top-0'
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-5 py-5 border-b border-[rgb(var(--sidebar-border))]">
        <Link href="/" className="flex items-center gap-2.5" onClick={onClose}>
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary text-white">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-[rgb(var(--sidebar-foreground))]">
              DSIDE
            </span>
            <span className="block text-[10px] uppercase tracking-widest text-[rgb(var(--muted-foreground))] leading-none">
              Intelligence Platform
            </span>
          </div>
        </Link>
        {mobile && onClose && (
          <button onClick={onClose} className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="w-5 h-5 text-[rgb(var(--muted-foreground))]" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={cn('nav-link', isActive && 'nav-link-active')}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-[rgb(var(--sidebar-border))]">
        <p className="text-[11px] text-[rgb(var(--muted-foreground))] leading-relaxed">
          Data from{' '}
          <a href="https://municipaldata.treasury.gov.za" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">
            Municipal Money
          </a>
          ,{' '}
          <a href="https://vulekamali.gov.za" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">
            Vulekamali
          </a>
          ,{' '}
          <a href="https://www.statssa.gov.za" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">
            StatsSA
          </a>
        </p>
      </div>
    </aside>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <html lang="en" className={inter.variable}>
      <head>
        <title>DSIDE - Data Science for Service Delivery &amp; Employment</title>
        <meta
          name="description"
          content="South African youth unemployment and municipal service delivery intelligence platform. Explore skills gaps, find opportunities, and understand municipal performance across all 257 municipalities."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="font-sans antialiased">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-40 flex items-center justify-between px-4 py-3 bg-[rgb(var(--card))] border-b border-[rgb(var(--border))] shadow-sm">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-white">
              <TrendingUp className="w-4 h-4" />
            </div>
            <span className="text-base font-bold tracking-tight">DSIDE</span>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        </header>

        {/* Mobile menu overlay */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-black/40"
              onClick={() => setMobileMenuOpen(false)}
            />
            <div className="relative h-full w-72 animate-fade-in">
              <Sidebar mobile onClose={() => setMobileMenuOpen(false)} />
            </div>
          </div>
        )}

        {/* Desktop sidebar */}
        <Sidebar />

        {/* Main content */}
        <main className="lg:ml-64 min-h-screen">
          <div className="px-4 py-6 sm:px-6 lg:px-8 max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
