# Dine Out Vancouver Halal Friendly Finder

Public, read-only web app that makes Dine Out Vancouver menus easier to filter for halal-friendly options. The canonical menu text is scraped from the official Dine Out site, then enriched with AI tags and a halal listing cross-reference.

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

## Disclaimers
Halal-friendly means each course has at least one seafood or vegetarian option and alcohol is not included in the menu price. Pork may still be present. Tags are generated from menu text and external sources. Always confirm with the restaurant.

## Next Steps
See IMPLEMENTATION_PLAN.md for the build checklist and status.
