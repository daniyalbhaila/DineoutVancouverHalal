# Implementation Plan

This checklist is the canonical status tracker. Mark items complete as they are delivered.

## Phase 1: Foundations
- [ ] Finalize halal-friendly definition and disclaimer text.
- [ ] Choose filter defaults for the MVP.

## Phase 2: Supabase Setup
- [x] Create Supabase project.
- [x] Define schema for restaurants, menus, menu_tags, halal_sources, match_overrides.
- [x] Configure public read-only access (RLS).

## Phase 3: Data Ingestion
- [x] Build ingestion script for data/dineout_menus_raw.csv.
- [x] Upsert restaurants and menu variants into Supabase.
- [x] Validate menu_raw_text integrity after upload.

## Phase 4: Vancouver Foodies Cross-Reference
- [x] Scrape all Vancouver Foodies restaurant pages.
- [x] Implement fuzzy matching to Dine Out names.
- [ ] Add manual overrides list for edge cases.
- [x] Populate halal_sources with evidence snippets.
- [x] Ingest Google Maps halal list (halalList.html).

## Phase 5: AI Menu Tagging
- [x] Define AI JSON schema for menu tags.
- [x] Implement batch tagging script using gpt-4o-mini.
- [ ] Cache by hash to avoid reprocessing.
- [ ] Store tags with evidence and confidence.

## Phase 6: Next.js App
- [x] Create Next.js app and connect Supabase.
- [x] Build filterable list view.
- [x] Build restaurant detail view.
- [x] Add disclaimers and tag badges.
- [ ] Add shareable URL filters.

## Phase 7: QA and Launch
- [ ] Spot-check AI tags vs raw menus.
- [ ] Validate cross-reference accuracy.
- [ ] Deploy to Netlify.
- [ ] Announce and share with users.
