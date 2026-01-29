import HalalDiscoverList from "../components/HalalDiscoverList";
import { getHalalRestaurants } from "../lib/data";

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
