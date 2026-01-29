create extension if not exists "pgcrypto";

do $$
begin
  if not exists (select 1 from pg_type where typname = 'tag_value') then
    create type tag_value as enum ('yes', 'no', 'uncertain');
  end if;
  if not exists (select 1 from pg_type where typname = 'coverage_value') then
    create type coverage_value as enum ('none', 'some', 'most', 'all');
  end if;
  if not exists (select 1 from pg_type where typname = 'source_status') then
    create type source_status as enum ('halal_certified', 'halal_listed', 'unknown');
  end if;
end $$;

create table if not exists restaurants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  dineout_url text unique,
  city text,
  neighborhood text,
  created_at timestamptz not null default now()
);

create table if not exists menus (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references restaurants(id) on delete cascade,
  menu_title text not null,
  menu_variant integer not null default 1,
  menu_price text,
  menu_price_min numeric,
  menu_price_max numeric,
  currency text not null default 'CAD',
  menu_raw_text text not null,
  created_at timestamptz not null default now(),
  unique (restaurant_id, menu_title, menu_variant)
);

create table if not exists menu_tags (
  id uuid primary key default gen_random_uuid(),
  menu_id uuid not null references menus(id) on delete cascade,
  contains_pork tag_value not null default 'uncertain',
  contains_alcohol tag_value not null default 'uncertain',
  contains_non_halal_ingredients tag_value not null default 'uncertain',
  has_seafood_option tag_value not null default 'uncertain',
  has_vegetarian_option tag_value not null default 'uncertain',
  course_coverage coverage_value,
  halal_friendly_menu tag_value not null default 'uncertain',
  halal_friendly_dishes jsonb not null default '[]'::jsonb,
  confidence numeric,
  evidence_snippets jsonb,
  model text,
  created_at timestamptz not null default now()
);

create table if not exists halal_sources (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references restaurants(id) on delete cascade,
  source_name text not null,
  source_url text,
  status source_status not null default 'unknown',
  evidence_snippet text,
  confidence numeric,
  created_at timestamptz not null default now()
);

create table if not exists match_overrides (
  id uuid primary key default gen_random_uuid(),
  dineout_name text not null,
  vancouverfoodies_name text not null,
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_restaurants_name on restaurants (name);
create index if not exists idx_restaurants_slug on restaurants (slug);
create index if not exists idx_menus_restaurant_id on menus (restaurant_id);
create index if not exists idx_menus_price_min on menus (menu_price_min);
create index if not exists idx_menu_tags_menu_id on menu_tags (menu_id);
create index if not exists idx_halal_sources_restaurant_id on halal_sources (restaurant_id);
create unique index if not exists idx_halal_sources_unique on halal_sources (restaurant_id, source_name);

alter table restaurants enable row level security;
alter table menus enable row level security;
alter table menu_tags enable row level security;
alter table halal_sources enable row level security;
alter table match_overrides enable row level security;

create policy "public read restaurants" on restaurants for select using (true);
create policy "public read menus" on menus for select using (true);
create policy "public read menu_tags" on menu_tags for select using (true);
create policy "public read halal_sources" on halal_sources for select using (true);
create policy "public read match_overrides" on match_overrides for select using (true);
