# Product Requirements Document

## Product Name
Vancouver Halal Finder + Dine Out

## Problem Statement
There is no single place to discover halal restaurants in Vancouver with clear context on confidence and evidence. Separately, the official Dine Out Vancouver site lacks strong filters for halal-friendly or affordability needs. Users must manually read menus and cross-check sources, which is time-consuming and error-prone.

## Target Users
- Muslim diners seeking halal or halal-friendly options year-round
- Families and groups with dietary restrictions
- Dine Out Vancouver visitors who want better filtering

## Goals
- Provide an easy-to-use discovery experience for halal restaurants in Vancouver.
- Provide a filterable interface for Dine Out menus with traceable evidence.
- Preserve exact menu text for transparency and traceability.
- Add AI-based menu tags (pork, alcohol, seafood, vegetarian, halal-friendly).
- Cross-reference external halal listings for certification context.

## Non-Goals
- Confirming halal certification with restaurants directly.
- Handling reservations or payments.
- Replacing the official Dine Out site.

## Key Features (MVP)
- Halal discovery list with map + list views.
- Confidence tiers: listed vs menu-inferred halal-friendly.
- Filter by menu price, menu type, and halal-friendly tags for Dine Out.
- Toggle filters: no pork, no alcohol, seafood options, vegetarian options.
- Restaurant detail pages with raw menu text (Dine Out).
- Halal-listed badge based on external sources.
- Clear disclaimers on AI-generated tags and directory listings.

## Data Sources
- Dine Out Vancouver Restaurants directory and menu pages.
- Vancouver Foodies halal listings (public directory).
- Public Google Maps halal lists (imported source data).

## AI Enrichment
- Model: gpt-4o-mini (cost-efficient, structured output).
- Inputs: menu_raw_text per menu variant.
- Outputs: menu-level tags with evidence snippets and confidence.

## Success Metrics
- Time to find suitable options reduced by 50 percent (user survey).
- 90 percent of Dine Out restaurants match to at least one menu variant in the dataset.
- 80 percent accuracy on AI menu tags in spot checks.

## Risks
- Directory listings may be outdated or incomplete.
- Menu text ambiguity leading to uncertain tags.
- Name matching errors between Dine Out and halal directories.
- Data freshness if menus change during the festival.
