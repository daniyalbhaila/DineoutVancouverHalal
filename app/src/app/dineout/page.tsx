import RestaurantList from "../../components/RestaurantList";
import { getRestaurantSummaries } from "../../lib/data";

export const metadata = {
  title: "Dine Out 2026 — Halal-Friendly Menus",
  description:
    "Filter Dine Out Vancouver 2026 menus for halal-friendly options, price tiers, and dietary tags with transparent sourcing.",
  alternates: {
    canonical: "/dineout",
  },
};

export default async function DineOutPage() {
  const restaurants = await getRestaurantSummaries();

  return (
    <div className="min-h-screen px-4 pb-16 pt-8 md:px-10">
      <div className="mx-auto w-full max-w-6xl">
        <RestaurantList restaurants={restaurants} />
      </div>
    </div>
  );
}
