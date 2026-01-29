import RestaurantList from "../components/RestaurantList";
import { getRestaurantSummaries } from "../lib/data";

export default async function Home() {
  const restaurants = await getRestaurantSummaries();

  return (
    <div className="min-h-screen px-4 pb-16 pt-8 md:px-10">
      <RestaurantList restaurants={restaurants} />
    </div>
  );
}
