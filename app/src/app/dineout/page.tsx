import RestaurantList from "../../components/RestaurantList";
import { getRestaurantSummaries } from "../../lib/data";

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
