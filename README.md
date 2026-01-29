# Dine Out Vancouver Halal Friendly Finder

Public, read-only web app for halal restaurant discovery, with a dedicated Dine Out Vancouver menu filter. The Dine Out data is scraped from the official site, then enriched with AI tags and cross-referenced with halal listings.

## Repository Layout
- scripts/: data ingestion and enrichment scripts
- data/: generated datasets
- docs: product docs (PRD.md, IMPLEMENTATION_PLAN.md)

## Data Outputs
- data/dineout_menus_raw.csv
  - One row per restaurant + menu tab + menu variant
  - menu_raw_text preserves exact menu text for traceability
- data/dineout_menus_long.csv
  - Dish-level long format (optional analytics use)

## Regenerate the Dataset
```bash
python3 scripts/scrape_dineout.py
```

## Run the Web App
```bash
cd app
cp .env.example .env.local
npm install
npm run dev
```

Set `SUPABASE_ANON_KEY` in `app/.env.local` (from Supabase Project Settings → API).
The map view uses mapcn + MapLibre with free tiles (no API key required).

## Disclaimers
Halal-friendly means each course has at least one seafood or vegetarian option and alcohol is not included in the menu price. Alcohol may be served, and cross-contamination risk is possible. Tags are generated from menu text and external sources. Always confirm with the restaurant.

## Next Steps
See IMPLEMENTATION_PLAN.md for the build checklist and status.
