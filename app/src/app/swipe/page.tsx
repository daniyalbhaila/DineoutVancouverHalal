import HalalSwipe from "../../components/HalalSwipe";
import { getHalalRestaurants } from "../../lib/data";

export const metadata = {
  title: "Swipe Halal-Friendly Picks",
  description:
    "Swipe through halal-friendly restaurant picks in Vancouver and save favorites for later.",
  alternates: {
    canonical: "/swipe",
  },
};

export default async function SwipePage() {
  const restaurants = await getHalalRestaurants();

  return <HalalSwipe restaurants={restaurants} />;
}
