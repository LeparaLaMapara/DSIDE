# DSIDE Next

South African youth unemployment and municipal service delivery intelligence platform.

## Tech Stack
- Next.js 14 (App Router, TypeScript, Server Components)
- Supabase (PostgreSQL, Auth, Realtime)
- Tailwind CSS
- Recharts + D3.js + Leaflet for visualizations
- Claude API for AI chat
- Python scripts for ML pipeline (PCA, SVM, Random Forest)

## Project Structure
- `src/app/` — Next.js App Router pages and API routes
- `src/components/` — Reusable React components
- `src/lib/` — Utilities, Supabase client, data source connectors
- `src/types/` — TypeScript type definitions
- `scripts/` — Python data ingestion and ML pipeline scripts
- `supabase/` — Database migrations and seed data

## Data Sources
- Municipal Money API: https://municipaldata.treasury.gov.za/api
- Vulekamali API: https://vulekamali.gov.za/api
- StatsSA: https://www.statssa.gov.za
- Youth Explorer / Wazimap: https://wazimap.co.za
- DHET Scarce Skills List

## Commands
- `npm run dev` — Start development server
- `python scripts/run-ingestion.py` — Run full data ingestion
- `python scripts/run-ml-pipeline.py` — Run ML pipeline (PCA + SVM + RF)

## Conventions
- Use Server Components by default, 'use client' only when needed
- All data fetching through Supabase client
- API routes in src/app/api/ for mutations and external API calls
- Python scripts communicate with Supabase via service role key
- Mobile-first responsive design
- ZAR currency formatting throughout
