"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { formatPriceRange, normalizeMenuType } from "../lib/format";
import type { MenuVariant, RestaurantDetail } from "../lib/data";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

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
        key: menu.id,
        label: `${baseLabel}${variantLabel}`,
        menu,
      };
    });
  }, [restaurant.menuVariants]);

  const [activeTab, setActiveTab] = useState(tabs[0]?.key ?? "");

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
        <Card className="fade-rise">
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                Dine Out Vancouver
              </p>
              <h1 className="mt-2 text-3xl font-semibold">{restaurant.name}</h1>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {restaurant.dineoutUrl && (
                <Button asChild>
                  <Link href={restaurant.dineoutUrl} target="_blank">
                    View on Dine Out
                  </Link>
                </Button>
              )}
              {restaurant.halalSource && <Badge variant="warning">Halal listed</Badge>}
              {!hideDisclaimers && overallPork && (
                <Badge variant="outline">Cross-contamination risk</Badge>
              )}
              {!hideDisclaimers && overallAlcohol && (
                <Badge variant="outline">Alcohol served</Badge>
              )}
            </div>

            {!hideDisclaimers && (
              <p className="text-sm text-[var(--muted)]">
                Halal-friendly means each course has at least one seafood or vegetarian option and
                alcohol is not included in the menu price. Alcohol may be served. Cross-contamination
                risk possible.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="flex flex-wrap">
                {tabs.map((tab) => (
                  <TabsTrigger key={tab.key} value={tab.key}>
                    {tab.label}
                  </TabsTrigger>
                ))}
              </TabsList>

              {tabs.map((tab) => (
                <TabsContent key={tab.key} value={tab.key}>
                  <MenuVariantPanel menu={tab.menu} />
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MenuVariantPanel({ menu }: { menu: MenuVariant }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Menu price</p>
          <p className="text-lg font-semibold text-[var(--ink)]">
            {formatPriceRange(menu.priceMin, menu.priceMax)}
          </p>
        </div>
        <Badge variant={menu.tags?.halalFriendly === "yes" ? "default" : "secondary"}>
          {menu.tags?.halalFriendly === "yes" ? "Halal-friendly" : "Not enough halal options"}
        </Badge>
      </div>

      {menu.tags && (
        <div className="flex flex-wrap gap-2 text-xs">
          {menu.tags.containsPork === "yes" && <Badge variant="outline">Contains pork</Badge>}
          {menu.tags.containsAlcohol === "yes" && (
            <Badge variant="outline">Alcohol listed</Badge>
          )}
          {menu.tags.hasSeafood === "yes" && <Badge variant="secondary">Seafood options</Badge>}
          {menu.tags.hasVegetarian === "yes" && (
            <Badge variant="secondary">Vegetarian options</Badge>
          )}
        </div>
      )}

      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">
          Halal-friendly dishes
        </p>
        <p className="mt-2 text-sm text-[var(--ink)]">
          {menu.tags?.halalDishes?.length
            ? menu.tags.halalDishes.join(" · ")
            : "No clear halal-friendly dishes listed"}
        </p>
      </div>

      <details className="rounded-2xl border border-dashed border-[var(--stroke)] bg-white/70 px-4 py-3">
        <summary className="cursor-pointer text-sm text-[var(--muted)]">
          Show full menu text
        </summary>
        <pre className="mt-3 whitespace-pre-wrap text-sm text-[var(--ink)]">
          {menu.rawText || "Menu text not available."}
        </pre>
      </details>
    </div>
  );
}
