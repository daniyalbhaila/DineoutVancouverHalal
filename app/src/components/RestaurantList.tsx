"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { formatPrice } from "../lib/format";
import type { RestaurantSummary } from "../lib/data";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";
import { Input } from "./ui/input";

const PAGE_SIZE = 24;

type Filters = {
  noPork: boolean;
  noAlcohol: boolean;
  seafood: boolean;
  vegetarian: boolean;
};

type Confidence = "friendly" | "listed";

const defaultFilters: Filters = {
  noPork: false,
  noAlcohol: false,
  seafood: false,
  vegetarian: false,
};

export default function RestaurantList({
  restaurants,
}: {
  restaurants: RestaurantSummary[];
}) {
  const [query, setQuery] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [confidence, setConfidence] = useState<Confidence>("friendly");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const min = minPrice ? Number(minPrice) : null;
    const max = maxPrice ? Number(maxPrice) : null;

    return restaurants.filter((restaurant) => {
      if (normalizedQuery) {
        const nameMatch = restaurant.name.toLowerCase().includes(normalizedQuery);
        if (!nameMatch) return false;
      }

      if (confidence === "listed" && !restaurant.halalSource) return false;
      if (confidence === "friendly") {
        const qualifies =
          restaurant.halalFriendly || Boolean(restaurant.halalSource);
        if (!qualifies) return false;
      }
      if (filters.noPork && restaurant.containsPork) return false;
      if (filters.noAlcohol && restaurant.containsAlcohol) return false;
      if (filters.seafood && !restaurant.hasSeafood) return false;
      if (filters.vegetarian && !restaurant.hasVegetarian) return false;

      if (min !== null) {
        if (restaurant.fromPrice === null || restaurant.fromPrice < min) return false;
      }
      if (max !== null) {
        if (restaurant.fromPrice === null || restaurant.fromPrice > max) return false;
      }

      return true;
    });
  }, [confidence, filters, maxPrice, minPrice, query, restaurants]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [confidence, filters, maxPrice, minPrice, query]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setVisibleCount((prev) => Math.min(prev + PAGE_SIZE, filtered.length));
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [filtered.length]);

  const visible = filtered.slice(0, visibleCount);

  const toggleFilter = (key: keyof Filters) => {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-8">
      <Card className="fade-rise">
        <CardContent className="space-y-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[var(--muted)]">
                Dine Out Vancouver 2026
              </p>
              <h1 className="mt-2 text-4xl font-semibold">Halal-friendly menus</h1>
              <div className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
                <p>
                  Halal-friendly means each course has at least one seafood or vegetarian option and
                  alcohol is not included in the menu price. Alcohol may be served. Cross-contamination
                  risk possible.
                </p>
                <p className="mt-2">
                  Halal listed means the restaurant appears in external halal directories.
                </p>
              </div>
            </div>
            <Badge variant="secondary">{filtered.length} restaurants</Badge>
          </div>
          <div className="hidden flex-wrap gap-2 text-xs text-[var(--muted)] md:flex">
            <Badge variant="outline">Step 1: Choose confidence</Badge>
            <Badge variant="outline">Step 2: Set constraints</Badge>
            <Badge variant="outline">Step 3: Pick a restaurant</Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <div className="space-y-4">
          <details className="rounded-3xl border border-[var(--stroke)] bg-white px-5 py-4 md:hidden" open>
            <summary className="cursor-pointer text-sm font-semibold text-[var(--ink)]">
              Filters
              <span className="ml-2 text-xs font-normal text-[var(--muted)]">
                Step-by-step
              </span>
            </summary>
            <div className="mt-4 space-y-5">
              <FilterPanel
                confidence={confidence}
                setConfidence={setConfidence}
                query={query}
                setQuery={setQuery}
                minPrice={minPrice}
                setMinPrice={setMinPrice}
                maxPrice={maxPrice}
                setMaxPrice={setMaxPrice}
                filters={filters}
                toggleFilter={toggleFilter}
              />
            </div>
          </details>

          <aside className="hidden md:block">
            <Card>
              <CardContent>
                <h2 className="text-lg font-semibold">Filters</h2>
                <p className="mt-1 text-xs text-[var(--muted)]">Step-by-step guidance.</p>
                <div className="mt-5">
                  <FilterPanel
                    confidence={confidence}
                    setConfidence={setConfidence}
                    query={query}
                    setQuery={setQuery}
                    minPrice={minPrice}
                    setMinPrice={setMinPrice}
                    maxPrice={maxPrice}
                    setMaxPrice={setMaxPrice}
                    filters={filters}
                    toggleFilter={toggleFilter}
                  />
                </div>
              </CardContent>
            </Card>
          </aside>
        </div>

        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            {visible.map((restaurant) => (
              <RestaurantCard
                key={restaurant.id}
                restaurant={restaurant}
                hideDisclaimers={confidence === "listed" || Boolean(restaurant.halalSource)}
              />
            ))}
          </div>

          {visible.length === 0 && (
            <Card>
              <CardContent>
                <p className="text-sm text-[var(--muted)]">
                  No restaurants match these filters yet.
                </p>
              </CardContent>
            </Card>
          )}

          <div ref={sentinelRef} />
        </div>
      </div>
    </div>
  );
}

function FilterPanel({
  confidence,
  setConfidence,
  query,
  setQuery,
  minPrice,
  setMinPrice,
  maxPrice,
  setMaxPrice,
  filters,
  toggleFilter,
}: {
  confidence: Confidence;
  setConfidence: (value: Confidence) => void;
  query: string;
  setQuery: (value: string) => void;
  minPrice: string;
  setMinPrice: (value: string) => void;
  maxPrice: string;
  setMaxPrice: (value: string) => void;
  filters: Filters;
  toggleFilter: (key: keyof Filters) => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
          Step 1: Confidence
        </p>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Halal listed means the restaurant appears in external halal directories.
        </p>
        <div className="mt-2 flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={confidence === "friendly" ? "default" : "outline"}
            onClick={() => setConfidence("friendly")}
          >
            Halal-friendly
          </Button>
          <Button
            type="button"
            size="sm"
            variant={confidence === "listed" ? "default" : "outline"}
            onClick={() => setConfidence("listed")}
          >
            Halal listed only
          </Button>
        </div>
      </div>

      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
          Step 2: Constraints
        </p>
        <div className="mt-2 flex flex-col gap-3">
          <Input
            placeholder="Search restaurants"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="flex gap-2">
            <Input
              placeholder="Min $"
              value={minPrice}
              onChange={(event) => setMinPrice(event.target.value)}
            />
            <Input
              placeholder="Max $"
              value={maxPrice}
              onChange={(event) => setMaxPrice(event.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <FilterChip
              label="No pork"
              active={filters.noPork}
              onClick={() => toggleFilter("noPork")}
            />
            <FilterChip
              label="No alcohol"
              active={filters.noAlcohol}
              onClick={() => toggleFilter("noAlcohol")}
            />
          </div>
        </div>
      </div>

      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
          Step 3: Options
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <FilterChip
            label="Seafood options"
            active={filters.seafood}
            onClick={() => toggleFilter("seafood")}
          />
          <FilterChip
            label="Vegetarian options"
            active={filters.vegetarian}
            onClick={() => toggleFilter("vegetarian")}
          />
        </div>
      </div>
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant={active ? "default" : "outline"}
      onClick={onClick}
    >
      {label}
    </Button>
  );
}

function RestaurantCard({
  restaurant,
  hideDisclaimers,
}: {
  restaurant: RestaurantSummary;
  hideDisclaimers: boolean;
}) {
  const disclaimers = [] as string[];
  if (restaurant.containsPork) disclaimers.push("Cross-contamination risk");
  if (restaurant.containsAlcohol) disclaimers.push("Alcohol served");

  return (
    <Card className="transition hover:shadow-md">
      <CardContent className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <Link href={`/restaurants/${restaurant.slug}`}>
              <h3 className="text-base font-semibold text-[var(--ink)]">
                {restaurant.name}
              </h3>
            </Link>
            <div className="mt-1 flex flex-wrap gap-1">
              {restaurant.menuTypes.slice(0, 2).map((type) => (
                <Badge key={`${restaurant.id}-${type}`} variant="outline">
                  {type}
                </Badge>
              ))}
            </div>
          </div>
          <div className="text-right">
            <span className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)]">
              From
            </span>
            <p className="text-lg font-semibold text-[var(--accent)]">
              {formatPrice(restaurant.fromPrice)}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant={restaurant.halalFriendly ? "default" : "secondary"}>
            {restaurant.halalFriendly ? "Halal-friendly" : "Not enough halal options"}
          </Badge>
          {restaurant.halalSource && <Badge variant="warning">Halal listed</Badge>}
        </div>

        {!hideDisclaimers && disclaimers.length > 0 && (
          <p className="text-xs text-[var(--muted)]">{disclaimers.join(" · ")}</p>
        )}

        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">
            Halal-friendly dishes
          </p>
          <p className="mt-1 text-sm text-[var(--ink)]">
            {restaurant.halalDishes.length > 0
              ? restaurant.halalDishes.join(" · ")
              : "No clear halal-friendly dishes listed"}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
