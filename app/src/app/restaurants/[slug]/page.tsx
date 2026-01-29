import { notFound } from "next/navigation";
import RestaurantDetailView from "../../../components/RestaurantDetail";
import { getRestaurantDetail } from "../../../lib/data";

export default async function RestaurantDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const restaurant = await getRestaurantDetail(slug);

  if (!restaurant) {
    notFound();
  }

  return <RestaurantDetailView restaurant={restaurant} />;
}
