"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { formatPriceRange, normalizeMenuType } from "../lib/format";
import type { MenuVariant, RestaurantDetail } from "../lib/data";

type VariantTab = {
  key: string;
  label: string;
  menu: MenuVariant;
};

export default function RestaurantDetailView({
  restaurant,
}: {
  restaurant: RestaurantDetail;
}) {
  const tabs = useMemo<VariantTab[]>(() => {
    return restaurant.menuVariants.map((menu) => {
      const baseLabel = normalizeMenuType(menu.title);
      const variantLabel = menu.variant > 1 ? ` ${menu.variant}` : "";
      return {
        key: `${menu.id}`,
        label: `${baseLabel}${variantLabel}`,
        menu,
      };
    });
  }, [restaurant.menuVariants]);

  const [activeTab, setActiveTab] = useState(tabs[0]?.key ?? "");
  const activeMenu = tabs.find((tab) => tab.key === activeTab)?.menu;

  const overallPork = restaurant.menuVariants.some(
    (menu) => menu.tags?.containsPork === "yes"
  );
  const overallAlcohol = restaurant.menuVariants.some(
    (menu) => menu.tags?.containsAlcohol === "yes"
  );
  const hideDisclaimers = Boolean(restaurant.halalSource);

  return (
    <div className="min-h-screen px-4 pb-16 pt-8 md:px-10">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="card-surface fade-rise p-6">
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
            Dine Out Vancouver
          </p>
          <h1 className="mt-2 text-3xl font-semibold">{restaurant.name}</h1>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            {restaurant.dineoutUrl && (
              <Link
                href={restaurant.dineoutUrl}
                target="_blank"
                className="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white"
              >
                View on Dine Out
              </Link>
            )}
            {restaurant.halalSource && (
              <span className="rounded-full bg-[var(--accent-warm)] px-3 py-1 text-xs text-white">
                Halal listed
              </span>
            )}
            {!hideDisclaimers && overallPork && (
              <span className="rounded-full bg-white px-3 py-1 text-xs text-[var(--muted)]">
                Cross-contamination risk
              </span>
            )}
            {!hideDisclaimers && overallAlcohol && (
              <span className="rounded-full bg-white px-3 py-1 text-xs text-[var(--muted)]">
                Alcohol served
              </span>
            )}
          </div>

          {!hideDisclaimers && (
            <p className="mt-4 text-sm text-[var(--muted)]">
              Halal-friendly means each course has at least one seafood or vegetarian option and
              alcohol is not included in the menu price. Alcohol may be served. Cross-contamination
              risk possible.
            </p>
          )}
        </header>

        <section className="card-surface p-6">
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`chip px-3 py-1 text-xs transition ${
                  activeTab === tab.key ? "chip-active" : ""
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeMenu ? (
            <div className="mt-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                    Menu price
                  </p>
                  <p className="text-lg font-semibold text-[var(--ink)]">
                    {formatPriceRange(activeMenu.priceMin, activeMenu.priceMax)}
                  </p>
                </div>
                <div className="text-xs text-[var(--muted)]">
                  {activeMenu.tags?.halalFriendly === "yes"
                    ? "Halal-friendly"
                    : "Not enough halal options"}
                </div>
              </div>

              {activeMenu.tags && (
                <div className="flex flex-wrap gap-2 text-xs">
                  {activeMenu.tags.containsPork === "yes" && (
                    <span className="rounded-full bg-white px-3 py-1 text-[var(--muted)]">
                      Contains pork
                    </span>
                  )}
                  {activeMenu.tags.containsAlcohol === "yes" && (
                    <span className="rounded-full bg-white px-3 py-1 text-[var(--muted)]">
                      Alcohol listed
                    </span>
                  )}
                  {activeMenu.tags.hasSeafood === "yes" && (
                    <span className="rounded-full bg-white px-3 py-1 text-[var(--muted)]">
                      Seafood options
                    </span>
                  )}
                  {activeMenu.tags.hasVegetarian === "yes" && (
                    <span className="rounded-full bg-white px-3 py-1 text-[var(--muted)]">
                      Vegetarian options
                    </span>
                  )}
                </div>
              )}

              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">
                  Halal-friendly dishes
                </p>
                <p className="mt-2 text-sm text-[var(--ink)]">
                  {activeMenu.tags?.halalDishes?.length
                    ? activeMenu.tags.halalDishes.join(" · ")
                    : "No clear halal-friendly dishes listed"}
                </p>
              </div>

              <details className="rounded-xl border border-dashed border-[var(--stroke)] bg-white/70 px-4 py-3">
                <summary className="cursor-pointer text-sm text-[var(--muted)]">
                  Show full menu text
                </summary>
                <pre className="mt-3 whitespace-pre-wrap text-sm text-[var(--ink)]">
                  {activeMenu.rawText || "Menu text not available."}
                </pre>
              </details>
            </div>
          ) : (
            <p className="mt-6 text-sm text-[var(--muted)]">No menu variants available.</p>
          )}
        </section>
      </div>
    </div>
  );
}
