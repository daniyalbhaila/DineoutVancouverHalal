"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import type { HalalRestaurant } from "../lib/data";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "./ui/sheet";
import { Switch } from "./ui/switch";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";
import {
  Map,
  MapControls,
  MapMarker,
  MarkerContent,
  MarkerPopup,
  useMap,
} from "./ui/map";

const PAGE_SIZE = 16;
const DEFAULT_RADIUS = 20;
const VANCOUVER_CENTER: [number, number] = [-123.1207, 49.2827];

type SortMode = "distance" | "rating" | "alpha";

const radiusOptions = [
  { label: "5 km", value: 5 },
  { label: "10 km", value: 10 },
  { label: "20 km", value: 20 },
  { label: "30 km", value: 30 },
  { label: "Any distance", value: 0 },
];

export default function HalalDiscoverList({
  restaurants,
}: {
  restaurants: HalalRestaurant[];
}) {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("all");
  const [openOnly, setOpenOnly] = useState(true);
  const [radiusKm, setRadiusKm] = useState(DEFAULT_RADIUS);
  const [sortMode, setSortMode] = useState<SortMode>("distance");
  const [view, setView] = useState("list");
  const [mapReady, setMapReady] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [hydrated, setHydrated] = useState(false);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(
    null
  );
  const [locationError, setLocationError] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const cities = useMemo(() => {
    const values = new Set<string>();
    restaurants.forEach((item) => {
      if (item.city) values.add(item.city);
    });
    return ["all", ...Array.from(values).sort()];
  }, [restaurants]);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
      },
      () => {
        setLocationError("Enable location to sort by distance.");
      }
    );
  }, []);

  useEffect(() => {
    if (view === "map") {
      setMapReady(true);
    }
  }, [view]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return restaurants.filter((item) => {
      if (item.permanentlyClosed || item.temporarilyClosed) return false;
      if (normalizedQuery) {
        const haystack = `${item.name} ${item.categoryName ?? ""} ${item.address ?? ""}`
          .toLowerCase()
          .trim();
        if (!haystack.includes(normalizedQuery)) return false;
      }
      if (city !== "all" && item.city !== city) return false;
      if (openOnly && hydrated && !isOpenNow(item)) return false;
      if (hydrated && userLocation && radiusKm > 0) {
        const distance = distanceKm(userLocation, item);
        if (distance > radiusKm) return false;
      }
      return true;
    });
  }, [city, hydrated, openOnly, query, radiusKm, restaurants, userLocation]);

  const sorted = useMemo(() => {
    const sortedList = [...filtered];
    const canSortByDistance = hydrated && userLocation;
    const mode = canSortByDistance ? sortMode : sortMode === "distance" ? "alpha" : sortMode;

    sortedList.sort((a, b) => {
      if (mode === "distance") {
        return distanceKm(userLocation!, a) - distanceKm(userLocation!, b);
      }
      if (mode === "rating") {
        return (b.rating ?? 0) - (a.rating ?? 0);
      }
      return a.name.localeCompare(b.name);
    });

    return sortedList;
  }, [filtered, hydrated, sortMode, userLocation]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [query, city, openOnly, radiusKm, sortMode]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setVisibleCount((prev) => Math.min(prev + PAGE_SIZE, sorted.length));
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [sorted.length]);

  const visible = sorted.slice(0, visibleCount);

  const locationStatus = userLocation
    ? "Sorted by distance"
    : sortMode === "rating"
      ? "Sorting by rating"
      : locationError ?? "Sorting by name";

  return (
    <Tabs value={view} onValueChange={setView}>
      <div className="space-y-6">
        <Card className="fade-rise">
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-[var(--muted)]">
                  Halal Restaurant Discovery
                </p>
                <h1 className="mt-2 text-4xl font-semibold">Find halal restaurants</h1>
                <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
                  Curated from a public Google Maps list. Always confirm halal status directly with
                  the restaurant.
                </p>
              </div>
              <Badge variant="secondary">{filtered.length} places</Badge>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <TabsList>
                <TabsTrigger value="list">List</TabsTrigger>
                <TabsTrigger value="map">Map</TabsTrigger>
              </TabsList>
              <div className="flex flex-wrap items-center gap-3">
                <Select value={sortMode} onValueChange={(value) => setSortMode(value as SortMode)}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Sort" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="distance">Sort: Distance</SelectItem>
                    <SelectItem value="rating">Sort: Rating</SelectItem>
                  </SelectContent>
                </Select>
                <Sheet>
                  <SheetTrigger asChild>
                    <Button variant="outline" size="sm">
                      Filters
                    </Button>
                  </SheetTrigger>
                  <SheetContent>
                    <SheetHeader>
                      <SheetTitle>Filters</SheetTitle>
                    </SheetHeader>
                    <FilterPanel
                      query={query}
                      setQuery={setQuery}
                      city={city}
                      setCity={setCity}
                      cities={cities}
                      openOnly={openOnly}
                      setOpenOnly={setOpenOnly}
                      radiusKm={radiusKm}
                      setRadiusKm={setRadiusKm}
                      locationStatus={locationStatus}
                    />
                  </SheetContent>
                </Sheet>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className={`grid gap-6 lg:grid-cols-[280px_1fr] ${view === "map" ? "hidden" : ""}`}>
          <aside className="hidden lg:block">
            <Card>
              <CardContent>
                <FilterPanel
                  query={query}
                  setQuery={setQuery}
                  city={city}
                  setCity={setCity}
                  cities={cities}
                  openOnly={openOnly}
                  setOpenOnly={setOpenOnly}
                  radiusKm={radiusKm}
                  setRadiusKm={setRadiusKm}
                  locationStatus={locationStatus}
                />
              </CardContent>
            </Card>
          </aside>

          <div className="space-y-4">
            <div className="space-y-3">
              {visible.map((restaurant) => (
                <RestaurantRow
                  key={restaurant.id}
                  restaurant={restaurant}
                  userLocation={userLocation}
                  hydrated={hydrated}
                />
              ))}
            </div>
            {visible.length === 0 && (
              <Card>
                <CardContent>
                  <p className="text-sm text-[var(--muted)]">
                    No restaurants match your filters.
                  </p>
                </CardContent>
              </Card>
            )}
            <div ref={sentinelRef} />
          </div>
        </div>
      </div>
      {mapReady && (
        <div
          className={`fixed inset-0 z-[60] flex flex-col bg-[var(--background)] transition-opacity ${
            view === "map" ? "opacity-100" : "pointer-events-none opacity-0"
          }`}
        >
          <div className="flex items-center justify-between border-b border-[var(--stroke)] bg-white/90 px-4 py-3 backdrop-blur md:px-10">
            <Button variant="outline" size="sm" onClick={() => setView("list")}>
              Back to list
            </Button>
            <div className="text-xs text-[var(--muted)]">{locationStatus}</div>
            <div className="flex items-center gap-2">
              <Select value={sortMode} onValueChange={(value) => setSortMode(value as SortMode)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Sort" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="distance">Sort: Distance</SelectItem>
                  <SelectItem value="rating">Sort: Rating</SelectItem>
                </SelectContent>
              </Select>
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm">
                    Filters
                  </Button>
                </SheetTrigger>
                <SheetContent>
                  <SheetHeader>
                    <SheetTitle>Filters</SheetTitle>
                  </SheetHeader>
                  <FilterPanel
                    query={query}
                    setQuery={setQuery}
                    city={city}
                    setCity={setCity}
                    cities={cities}
                    openOnly={openOnly}
                    setOpenOnly={setOpenOnly}
                    radiusKm={radiusKm}
                    setRadiusKm={setRadiusKm}
                    locationStatus={locationStatus}
                  />
                </SheetContent>
              </Sheet>
            </div>
          </div>
          <div className="flex-1 px-4 py-4 md:px-10">
            <MapView
              restaurants={sorted}
              userLocation={userLocation}
              hydrated={hydrated}
              radiusKm={radiusKm}
              onLocate={(coords) => {
                setUserLocation({ lat: coords.latitude, lng: coords.longitude });
                setLocationError(null);
              }}
            />
          </div>
        </div>
      )}
    </Tabs>
  );
}

function FilterPanel({
  query,
  setQuery,
  city,
  setCity,
  cities,
  openOnly,
  setOpenOnly,
  radiusKm,
  setRadiusKm,
  locationStatus,
}: {
  query: string;
  setQuery: (value: string) => void;
  city: string;
  setCity: (value: string) => void;
  cities: string[];
  openOnly: boolean;
  setOpenOnly: (value: boolean) => void;
  radiusKm: number;
  setRadiusKm: (value: number) => void;
  locationStatus: string;
}) {
  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Search</p>
        <Input
          className="mt-2"
          placeholder="Search by name or cuisine"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">City</p>
        <Select value={city} onValueChange={setCity}>
          <SelectTrigger className="mt-2">
            <SelectValue placeholder="All cities" />
          </SelectTrigger>
          <SelectContent>
            {cities.map((value) => (
              <SelectItem key={value} value={value}>
                {value === "all" ? "All" : value}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Open now</p>
          <p className="text-xs text-[var(--muted)]">{locationStatus}</p>
        </div>
        <Switch checked={openOnly} onCheckedChange={setOpenOnly} />
      </div>

      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Radius</p>
        <Select
          value={String(radiusKm)}
          onValueChange={(value) => setRadiusKm(Number(value))}
        >
          <SelectTrigger className="mt-2">
            <SelectValue placeholder="Radius" />
          </SelectTrigger>
          <SelectContent>
            {radiusOptions.map((option) => (
              <SelectItem key={option.label} value={String(option.value)}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

function RestaurantRow({
  restaurant,
  userLocation,
  hydrated,
}: {
  restaurant: HalalRestaurant;
  userLocation: { lat: number; lng: number } | null;
  hydrated: boolean;
}) {
  const openNow = hydrated ? isOpenNow(restaurant) : null;
  const distance = hydrated && userLocation ? distanceKm(userLocation, restaurant) : null;
  const locationLabel = [restaurant.neighborhood, restaurant.city]
    .filter(Boolean)
    .join(" · ");
  const priceTier = priceTierFromRange(restaurant.price);

  return (
    <Card className="transition hover:shadow-md">
      <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
        <div className="flex gap-4">
          <div className="h-20 w-20 overflow-hidden rounded-2xl bg-[var(--chip)]">
            {restaurant.imageUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={restaurant.imageUrl}
                alt={restaurant.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-xs text-[var(--muted)]">
                No image
              </div>
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-[var(--ink)]">
                {restaurant.name}
              </h3>
              {restaurant.rating && (
                <Badge variant="secondary">{restaurant.rating.toFixed(1)} ★</Badge>
              )}
            </div>
            <div className="mt-1 text-xs text-[var(--muted)]">
              {restaurant.categoryName ?? "Halal restaurant"}
              {priceTier && ` · ${priceTier}`}
              {restaurant.reviewsCount ? ` · ${restaurant.reviewsCount} reviews` : ""}
            </div>
            <div className="mt-2 text-sm text-[var(--ink)]">
              {locationLabel || "Location not available"}
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-xs text-[var(--muted)]">
              {openNow === true && <span>Open now</span>}
              {openNow === false && <span>Closed</span>}
              {openNow === null && <span>Hours loading</span>}
              {distance !== null && <span>• {distance.toFixed(1)} km</span>}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-start gap-2">
          {restaurant.googleUrl && (
            <Button asChild size="sm">
              <a href={restaurant.googleUrl} target="_blank" rel="noreferrer">
                Open in Maps
              </a>
            </Button>
          )}
          {restaurant.website && (
            <Button asChild size="sm" variant="outline">
              <a href={restaurant.website} target="_blank" rel="noreferrer">
                Website
              </a>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function MapView({
  restaurants,
  userLocation,
  hydrated,
  radiusKm,
  onLocate,
}: {
  restaurants: HalalRestaurant[];
  userLocation: { lat: number; lng: number } | null;
  hydrated: boolean;
  radiusKm: number;
  onLocate: (coords: { longitude: number; latitude: number }) => void;
}) {
  const points = useMemo(() => {
    return restaurants
      .filter((r) => r.lat !== null && r.lng !== null)
      .filter((r) => {
        if (!hydrated || !userLocation || radiusKm === 0) return true;
        return distanceKm(userLocation, r) <= radiusKm;
      });
  }, [restaurants, hydrated, radiusKm, userLocation]);

  const center = userLocation
    ? [userLocation.lng, userLocation.lat]
    : VANCOUVER_CENTER;

  return (
    <Card>
      <CardContent className="p-2">
        <div className="h-[520px] w-full overflow-hidden rounded-3xl">
          <Map center={center} zoom={userLocation ? 11 : 10}>
            <MapControls showZoom showLocate onLocate={onLocate} />
            {userLocation && (
              <MapMarker longitude={userLocation.lng} latitude={userLocation.lat}>
                <MarkerContent>
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-white shadow">
                    <div className="h-2.5 w-2.5 rounded-full bg-sky-600" />
                  </div>
                </MarkerContent>
              </MapMarker>
            )}
            {points.map((restaurant) => (
              <MapMarker
                key={restaurant.id}
                longitude={restaurant.lng as number}
                latitude={restaurant.lat as number}
              >
                <MarkerContent>
                  <svg
                    viewBox="0 0 24 24"
                    className="h-7 w-7 text-rose-600 drop-shadow"
                    aria-hidden="true"
                  >
                    <path
                      fill="currentColor"
                      d="M12 2c-3.87 0-7 3.13-7 7 0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z"
                    />
                  </svg>
                </MarkerContent>
                <MarkerPopup className="rounded-2xl border border-[var(--stroke)] bg-white p-3 shadow-lg">
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-[var(--ink)]">
                      {restaurant.name}
                    </p>
                    {restaurant.googleUrl && (
                      <a
                        href={restaurant.googleUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-[var(--accent)]"
                      >
                        Open in Maps
                      </a>
                    )}
                  </div>
                </MarkerPopup>
              </MapMarker>
            ))}
            <MapCenterUpdater
              center={center}
              radiusKm={radiusKm}
              hasUserLocation={Boolean(userLocation)}
            />
          </Map>
        </div>
      </CardContent>
    </Card>
  );
}

function radiusToZoom(radiusKm: number) {
  if (radiusKm <= 0) return 11;
  if (radiusKm <= 5) return 13;
  if (radiusKm <= 10) return 12;
  if (radiusKm <= 20) return 11;
  if (radiusKm <= 30) return 10.5;
  return 10;
}

function MapCenterUpdater({
  center,
  radiusKm,
  hasUserLocation,
}: {
  center: [number, number];
  radiusKm: number;
  hasUserLocation: boolean;
}) {
  const { map } = useMap();
  useEffect(() => {
    if (!map) return;
    const zoom = hasUserLocation ? radiusToZoom(radiusKm) : 10;
    map.flyTo({ center, zoom, duration: 600 });
  }, [center, hasUserLocation, map, radiusKm]);
  return null;
}

function priceTierFromRange(value: string | null) {
  if (!value) return null;
  const match = value.match(/(\d+)(?:\D+)(\d+)?/);
  if (!match) return null;
  const min = Number(match[1]);
  const max = match[2] ? Number(match[2]) : min;
  const avg = (min + max) / 2;
  if (avg <= 15) return "$";
  if (avg <= 30) return "$$";
  return "$$$";
}

function distanceKm(
  origin: { lat: number; lng: number },
  restaurant: HalalRestaurant
): number {
  if (restaurant.lat === null || restaurant.lng === null) return Infinity;
  const rad = (value: number) => (value * Math.PI) / 180;
  const dLat = rad(restaurant.lat - origin.lat);
  const dLng = rad(restaurant.lng - origin.lng);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(rad(origin.lat)) *
      Math.cos(rad(restaurant.lat)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const earthRadiusKm = 6371;
  return earthRadiusKm * c;
}

function getVancouverNowParts() {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Vancouver",
    weekday: "long",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  });
  const parts = formatter.formatToParts(new Date());
  const weekday = parts.find((part) => part.type === "weekday")?.value ?? "";
  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? 0);
  return { weekday, minutes: hour * 60 + minute };
}

function parseTimeValue(value: string, fallbackMeridiem?: string) {
  const cleaned = value.trim();
  const match = cleaned.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = match[2] ? Number(match[2]) : 0;
  const meridiem = (match[3] ?? fallbackMeridiem)?.toLowerCase();
  if (!meridiem) return null;
  let adjustedHour = hour % 12;
  if (meridiem === "pm") adjustedHour += 12;
  return adjustedHour * 60 + minute;
}

function parseHourRanges(hours: string): Array<[number, number]> {
  const normalized = hours
    .replace(/\u202f|\u00a0/g, " ")
    .replace(/–|—/g, "-")
    .replace(/\s+to\s+/gi, " to ")
    .trim();

  if (/closed/i.test(normalized)) return [];
  if (/open 24 hours|24 hours/i.test(normalized)) return [[0, 1440]];

  return normalized
    .split(",")
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => {
      const [startRaw, endRaw] = segment.split(" to ").map((v) => v.trim());
      if (!startRaw || !endRaw) return null;
      const endMeridiemMatch = endRaw.match(/(am|pm)/i);
      const fallbackMeridiem = endMeridiemMatch ? endMeridiemMatch[1] : undefined;
      const start = parseTimeValue(startRaw, fallbackMeridiem);
      const end = parseTimeValue(endRaw, fallbackMeridiem);
      if (start === null || end === null) return null;
      return [start, end] as [number, number];
    })
    .filter((range): range is [number, number] => Boolean(range));
}

function isOpenNow(restaurant: HalalRestaurant): boolean {
  if (restaurant.permanentlyClosed) return false;
  if (restaurant.temporarilyClosed) return false;
  if (!restaurant.openingHours || restaurant.openingHours.length === 0) return false;
  const { weekday, minutes } = getVancouverNowParts();
  const today = restaurant.openingHours.find((entry) => entry.day === weekday);
  if (!today || !today.hours) return false;
  const ranges = parseHourRanges(today.hours);
  return ranges.some(([start, end]) => minutes >= start && minutes <= end);
}
