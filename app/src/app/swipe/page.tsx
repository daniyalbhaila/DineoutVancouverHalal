import HalalSwipe from "../../components/HalalSwipe";
import { getHalalRestaurants } from "../../lib/data";

export default async function SwipePage() {
  const restaurants = await getHalalRestaurants();

  return <HalalSwipe restaurants={restaurants} />;
}
