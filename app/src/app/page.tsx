import HalalDiscoverList from "../components/HalalDiscoverList";
import { getHalalRestaurants } from "../lib/data";

export const metadata = {
  title: "Halal Restaurants in Vancouver",
  description:
    "Explore halal-friendly restaurants across Greater Vancouver with map and list views, confidence tiers, and live hours.",
  alternates: {
    canonical: "/",
  },
};

export default async function Home() {
  const restaurants = await getHalalRestaurants();

  return (
    <div className="min-h-screen px-4 pb-16 pt-8 md:px-10">
      <div className="mx-auto w-full max-w-6xl">
        <HalalDiscoverList restaurants={restaurants} />
      </div>
    </div>
  );
}
