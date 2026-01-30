# Vancouver Halal Finder + Dine Out

## Project Summary
We are building a public, read-only web app for halal restaurant discovery in Vancouver, plus a dedicated Dine Out Vancouver menu filter. The base Dine Out dataset comes from the official Dine Out Vancouver website. We enrich it with AI tags and cross-reference halal listing sources for context.

## Data Sources
- Dine Out Vancouver restaurants and menu pages.
- Vancouver Foodies halal listings: https://vancouverfoodies.ca/restaurants/
- Public Google Maps halal lists (imported source data).

## Core Outputs
- data/dineout_menus_raw.csv: canonical menu text per restaurant + menu variant.
- data/dineout_menus_long.csv: dish-level long-format rows (optional for analytics).

## Current Pipeline
- scripts/scrape_dineout.py: scrapes Dine Out Vancouver menus and outputs CSVs.
- Menu variants are split when a single menu block contains multiple menus (e.g., two price tiers).

## Rules of Thumb
- Do not manually edit generated data files in data/.
- Keep menu_raw_text intact for traceability.
- Store AI tagging outputs in separate tables/exports; never overwrite raw text.
- Use Supabase as the source of truth for the web app.
- One-way door rule: always ask for explicit permission before any irreversible or write action (DB writes, deploys, destructive commands, billing/security changes).

## Product Decisions
- Public read-only app.
- Flexible halal-friendly definition with a disclaimer.
- Netlify deployment.

## How to Contribute
- Add code changes through scripts/ and app/ only.
- Update IMPLEMENTATION_PLAN.md as milestones are completed.
- Keep documentation in README.md, PRD.md, and IMPLEMENTATION_PLAN.md up to date.
