"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { HalalRestaurant } from "../lib/data";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";

type Direction = "left" | "right" | null;

const SWIPE_THRESHOLD = 120;
const DEFAULT_RADIUS = 20;
const radiusOptions = [
  { label: "5 km", value: 5 },
  { label: "10 km", value: 10 },
  { label: "20 km", value: 20 },
  { label: "30 km", value: 30 },
  { label: "Any distance", value: 0 },
];

export default function HalalSwipe({ restaurants }: { restaurants: HalalRestaurant[] }) {
  const [index, setIndex] = useState(0);
  const [liked, setLiked] = useState<HalalRestaurant[]>([]);
  const [dismissed, setDismissed] = useState<HalalRestaurant[]>([]);
  const [drag, setDrag] = useState({ x: 0, y: 0, active: false });
  const [radiusKm, setRadiusKm] = useState(DEFAULT_RADIUS);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(
    null
  );
  const [locationError, setLocationError] = useState<string | null>(null);
  const [seed, setSeed] = useState(() => Math.random().toString(36).slice(2));
  const start = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setLocationError(null);
      },
      () => {
        setLocationError("Enable location to filter by radius.");
      }
    );
  }, []);

  const cards = useMemo(() => {
    const filtered = restaurants.filter((item) => {
      if (item.permanentlyClosed || item.temporarilyClosed) return false;
      if (radiusKm === 0 || !userLocation) return true;
      return distanceKm(userLocation, item) <= radiusKm;
    });

    return shuffleArray(filtered, seed).slice(0, 200);
  }, [restaurants, radiusKm, seed, userLocation]);
  const current = cards[index];
  const next = cards[index + 1];

  const direction: Direction = drag.x > 50 ? "right" : drag.x < -50 ? "left" : null;

  const handleDecision = (dir: Direction) => {
    if (!current || !dir) return;
    if (dir === "right") {
      setLiked((prev) => [...prev, current]);
    } else {
      setDismissed((prev) => [...prev, current]);
    }
    setDrag({ x: 0, y: 0, active: false });
    setIndex((prev) => prev + 1);
  };

  const onPointerDown = (event: React.PointerEvent) => {
    start.current = { x: event.clientX, y: event.clientY };
    setDrag({ x: 0, y: 0, active: true });
  };

  const onPointerMove = (event: React.PointerEvent) => {
    if (!drag.active) return;
    const deltaX = event.clientX - start.current.x;
    const deltaY = event.clientY - start.current.y;
    setDrag({ x: deltaX, y: deltaY, active: true });
  };

  const onPointerUp = () => {
    if (!drag.active) return;
    if (Math.abs(drag.x) > SWIPE_THRESHOLD) {
      handleDecision(drag.x > 0 ? "right" : "left");
    } else {
      setDrag({ x: 0, y: 0, active: false });
    }
  };

  const rotation = drag.x / 18;
  const translate = `translate(${drag.x}px, ${drag.y}px) rotate(${rotation}deg)`;

  return (
    <div className="min-h-screen px-4 pb-16 pt-8 md:px-10">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <Card className="fade-rise">
          <CardContent className="space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--muted)]">
              Halal Discovery
            </p>
            <h1 className="text-3xl font-semibold">Swipe to find a place</h1>
            <p className="text-sm text-[var(--muted)]">
              Swipe right to save, left to skip. Results are randomized each session.
            </p>
            <div className="flex gap-3 text-xs text-[var(--muted)]">
              <span>Saved: {liked.length}</span>
              <span>Skipped: {dismissed.length}</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="text-xs text-[var(--muted)]">Radius</div>
              <div className="flex flex-wrap gap-2">
                {radiusOptions.map((option) => (
                  <Button
                    key={option.label}
                    size="sm"
                    variant={radiusKm === option.value ? "default" : "outline"}
                    onClick={() => {
                      setRadiusKm(option.value);
                      setIndex(0);
                      setLiked([]);
                      setDismissed([]);
                      setSeed(Math.random().toString(36).slice(2));
                    }}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>
            {locationError && (
              <p className="text-xs text-[var(--muted)]">{locationError}</p>
            )}
          </CardContent>
        </Card>

        <div className="relative mx-auto flex h-[520px] w-full max-w-xl items-center justify-center">
          {next && (
            <SwipeCard
              restaurant={next}
              className="absolute scale-[0.97] opacity-70"
            />
          )}

          {current ? (
            <div
              className="absolute inset-0"
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerLeave={onPointerUp}
              style={{ touchAction: "pan-y" }}
            >
              <SwipeCard
                restaurant={current}
                className="h-full"
                style={{ transform: translate }}
              />
              {direction && (
                <div
                  className={`absolute top-6 ${
                    direction === "right" ? "left-6" : "right-6"
                  } rounded-full border-2 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
                    direction === "right"
                      ? "border-emerald-500 text-emerald-600"
                      : "border-rose-500 text-rose-600"
                  }`}
                >
                  {direction === "right" ? "Save" : "Skip"}
                </div>
              )}
            </div>
          ) : (
            <Card className="w-full">
              <CardContent className="text-center text-sm text-[var(--muted)]">
                That’s all for now. Check your saved list below.
              </CardContent>
            </Card>
          )}
        </div>

        <div className="flex items-center justify-center gap-3">
          <Button
            variant="outline"
            onClick={() => handleDecision("left")}
            disabled={!current}
          >
            Skip
          </Button>
          <Button onClick={() => handleDecision("right")} disabled={!current}>
            Save
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setIndex(0);
              setLiked([]);
              setDismissed([]);
              setSeed(Math.random().toString(36).slice(2));
            }}
          >
            Shuffle
          </Button>
        </div>

        {liked.length > 0 && (
          <Card>
            <CardContent className="space-y-3">
              <h2 className="text-lg font-semibold">Saved places</h2>
              <div className="grid gap-2 md:grid-cols-2">
                {liked.map((restaurant) => (
                  <div key={restaurant.id} className="rounded-2xl border border-[var(--stroke)] p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-semibold text-[var(--ink)]">
                          {restaurant.name}
                        </p>
                        <p className="text-xs text-[var(--muted)]">
                          {restaurant.categoryName ?? "Halal restaurant"}
                        </p>
                      </div>
                      {restaurant.googleUrl && (
                        <Button asChild size="sm" variant="outline">
                          <a href={restaurant.googleUrl} target="_blank" rel="noreferrer">
                            Open
                          </a>
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function shuffleArray<T>(items: T[], seed: string) {
  const array = [...items];
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0;
  }
  let random = Math.abs(hash) + 1;
  for (let i = array.length - 1; i > 0; i -= 1) {
    random = (random * 9301 + 49297) % 233280;
    const j = Math.floor((random / 233280) * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array;
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

function SwipeCard({
  restaurant,
  className,
  style,
}: {
  restaurant: HalalRestaurant;
  className?: string;
  style?: React.CSSProperties;
}) {
  const priceTier = priceTierFromRange(restaurant.price);
  const locationLabel = [restaurant.neighborhood, restaurant.city]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card
      className={`h-[520px] w-full max-w-xl transition ${className ?? ""}`}
      style={style}
    >
      <CardContent className="flex h-full flex-col gap-4">
        <div className="h-64 w-full overflow-hidden rounded-2xl bg-[var(--chip)]">
          {restaurant.imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={restaurant.imageUrl}
              alt={restaurant.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-[var(--muted)]">
              No image available
            </div>
          )}
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-2xl font-semibold text-[var(--ink)]">
              {restaurant.name}
            </h3>
            {restaurant.rating && (
              <Badge variant="secondary">{restaurant.rating.toFixed(1)} ★</Badge>
            )}
          </div>
          <div className="text-sm text-[var(--muted)]">
            {restaurant.categoryName ?? "Halal restaurant"}
            {priceTier && ` · ${priceTier}`}
            {restaurant.reviewsCount ? ` · ${restaurant.reviewsCount} reviews` : ""}
          </div>
          <div className="text-sm text-[var(--ink)]">
            {locationLabel || "Location not available"}
          </div>
        </div>
        <div className="mt-auto flex flex-wrap gap-2 text-xs text-[var(--muted)]">
          {restaurant.googleUrl && (
            <a
              href={restaurant.googleUrl}
              target="_blank"
              rel="noreferrer"
              className="text-[var(--accent)]"
            >
              Open in Maps
            </a>
          )}
          {restaurant.website && (
            <a
              href={restaurant.website}
              target="_blank"
              rel="noreferrer"
              className="text-[var(--muted)]"
            >
              Website
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
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
