import { fetchAll, fetchOne } from "./supabase";
import { normalizeMenuType } from "./format";

export type RestaurantSummary = {
  id: string;
  slug: string;
  name: string;
  dineoutUrl: string | null;
  fromPrice: number | null;
  maxPrice: number | null;
  menuTypes: string[];
  halalFriendly: boolean;
  containsPork: boolean;
  containsAlcohol: boolean;
  hasSeafood: boolean;
  hasVegetarian: boolean;
  halalDishes: string[];
  halalSource: "certified" | "listed" | null;
  menuCount: number;
};

export type MenuVariant = {
  id: string;
  title: string;
  variant: number;
  priceMin: number | null;
  priceMax: number | null;
  rawText: string;
  tags: {
    halalFriendly: string;
    containsPork: string;
    containsAlcohol: string;
    hasSeafood: string;
    hasVegetarian: string;
    courseCoverage: string | null;
    halalDishes: string[];
  } | null;
};

export type RestaurantDetail = {
  id: string;
  name: string;
  slug: string;
  dineoutUrl: string | null;
  halalSource: "certified" | "listed" | null;
  menuVariants: MenuVariant[];
};

export type HalalRestaurant = {
  id: string;
  name: string;
  slug: string;
  categoryName: string | null;
  categories: string[] | null;
  address: string | null;
  city: string | null;
  neighborhood: string | null;
  price: string | null;
  website: string | null;
  phone: string | null;
  rating: number | null;
  reviewsCount: number | null;
  googleUrl: string | null;
  imageUrl: string | null;
  lat: number | null;
  lng: number | null;
  openingHours: { day: string; hours: string }[] | null;
  permanentlyClosed: boolean | null;
  temporarilyClosed: boolean | null;
};

type OpeningHoursEntry = { day: string; hours: string };

type RestaurantRow = {
  id: string;
  name: string;
  slug: string;
  dineout_url: string | null;
};

type MenuRow = {
  id: string;
  restaurant_id: string;
  menu_title: string;
  menu_variant: number;
  menu_price_min: number | null;
  menu_price_max: number | null;
  menu_raw_text: string;
};

type MenuTagRow = {
  menu_id: string;
  halal_friendly_menu: string;
  contains_pork: string;
  contains_alcohol: string;
  has_seafood_option: string;
  has_vegetarian_option: string;
  course_coverage: string | null;
  halal_friendly_dishes: string[] | null;
};

type HalalSourceRow = {
  restaurant_id: string;
  status: string;
};

type HalalRestaurantRow = {
  id: string;
  name: string;
  slug: string;
  category_name: string | null;
  categories: string[] | null;
  address: string | null;
  city: string | null;
  neighborhood: string | null;
  price: string | null;
  website: string | null;
  phone: string | null;
  rating: number | null;
  reviews_count: number | null;
  google_url: string | null;
  image_url: string | null;
  lat: number | null;
  lng: number | null;
  opening_hours: unknown | null;
  permanently_closed: boolean | null;
  temporarily_closed: boolean | null;
};

function toNumber(value: number | null): number | null {
  if (value === null || Number.isNaN(value)) {
    return null;
  }
  return value;
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    const key = value.trim().toLowerCase();
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(value.trim());
  }
  return result;
}

function normalizeOpeningHours(value: unknown): OpeningHoursEntry[] | null {
  if (!value) return null;
  if (Array.isArray(value)) {
    const entries = value
      .map((entry) => {
        if (!entry || typeof entry !== "object") return null;
        const record = entry as { day?: string; hours?: string };
        if (!record.day || !record.hours) return null;
        return { day: record.day, hours: record.hours };
      })
      .filter((entry): entry is OpeningHoursEntry => Boolean(entry));
    return entries.length ? entries : null;
  }

  if (typeof value === "object") {
    const record = value as { weekday_text?: string[] };
    if (Array.isArray(record.weekday_text)) {
      const entries = record.weekday_text
        .map((line) => {
          if (typeof line !== "string") return null;
          const [dayRaw, hoursRaw] = line.split(/:\s+/, 2);
          if (!dayRaw || !hoursRaw) return null;
          return { day: dayRaw.trim(), hours: hoursRaw.trim() };
        })
        .filter((entry): entry is OpeningHoursEntry => Boolean(entry));
      return entries.length ? entries : null;
    }
  }

  return null;
}

export async function getRestaurantSummaries(): Promise<RestaurantSummary[]> {
  const [restaurants, menus, tags, sources] = await Promise.all([
    fetchAll<RestaurantRow>("restaurants", {
      select: "id,name,slug,dineout_url",
    }),
    fetchAll<MenuRow>("menus", {
      select: "id,restaurant_id,menu_title,menu_variant,menu_price_min,menu_price_max,menu_raw_text",
    }),
    fetchAll<MenuTagRow>("menu_tags", {
      select:
        "menu_id,halal_friendly_menu,contains_pork,contains_alcohol,has_seafood_option,has_vegetarian_option,course_coverage,halal_friendly_dishes",
      filters: ["model=eq.gpt-4o"],
    }),
    fetchAll<HalalSourceRow>("halal_sources", {
      select: "restaurant_id,status",
    }),
  ]);

  const menuByRestaurant = new Map<string, MenuRow[]>();
  for (const menu of menus) {
    const list = menuByRestaurant.get(menu.restaurant_id) ?? [];
    list.push(menu);
    menuByRestaurant.set(menu.restaurant_id, list);
  }

  const tagsByMenu = new Map<string, MenuTagRow>();
  for (const tag of tags) {
    if (!tagsByMenu.has(tag.menu_id)) {
      tagsByMenu.set(tag.menu_id, tag);
    }
  }

  const sourceByRestaurant = new Map<string, "certified" | "listed">();
  for (const source of sources) {
    if (source.status === "halal_certified") {
      sourceByRestaurant.set(source.restaurant_id, "certified");
    } else if (!sourceByRestaurant.has(source.restaurant_id)) {
      sourceByRestaurant.set(source.restaurant_id, "listed");
    }
  }

  return restaurants.map((restaurant) => {
    const menusForRestaurant = menuByRestaurant.get(restaurant.id) ?? [];
    const prices = menusForRestaurant
      .map((menu) => toNumber(menu.menu_price_min))
      .filter((price): price is number => price !== null);

    const fromPrice = prices.length ? Math.min(...prices) : null;
    const maxPrice = prices.length ? Math.max(...prices) : null;

    const menuTypes = uniqueStrings(
      menusForRestaurant.map((menu) => normalizeMenuType(menu.menu_title))
    );

    let halalFriendly = false;
    let containsPork = false;
    let containsAlcohol = false;
    let hasSeafood = false;
    let hasVegetarian = false;
    const halalDishes: string[] = [];

    for (const menu of menusForRestaurant) {
      const tag = tagsByMenu.get(menu.id);
      if (!tag) continue;
      if (tag.halal_friendly_menu === "yes") halalFriendly = true;
      if (tag.contains_pork === "yes") containsPork = true;
      if (tag.contains_alcohol === "yes") containsAlcohol = true;
      if (tag.has_seafood_option === "yes") hasSeafood = true;
      if (tag.has_vegetarian_option === "yes") hasVegetarian = true;
      if (Array.isArray(tag.halal_friendly_dishes)) {
        for (const dish of tag.halal_friendly_dishes) {
          if (dish && !halalDishes.includes(dish)) {
            halalDishes.push(dish);
          }
        }
      }
    }

    return {
      id: restaurant.id,
      slug: restaurant.slug,
      name: restaurant.name,
      dineoutUrl: restaurant.dineout_url,
      fromPrice,
      maxPrice,
      menuTypes,
      halalFriendly,
      containsPork,
      containsAlcohol,
      hasSeafood,
      hasVegetarian,
      halalDishes: uniqueStrings(halalDishes).slice(0, 3),
      halalSource: sourceByRestaurant.get(restaurant.id) ?? null,
      menuCount: menusForRestaurant.length,
    };
  });
}

export async function getRestaurantDetail(slug: string): Promise<RestaurantDetail | null> {
  const restaurant = await fetchOne<RestaurantRow>("restaurants", {
    select: "id,name,slug,dineout_url",
    filters: [`slug=eq.${slug}`],
  });

  if (!restaurant) return null;

  const [menus, tags, sources] = await Promise.all([
    fetchAll<MenuRow>("menus", {
      select:
        "id,restaurant_id,menu_title,menu_variant,menu_price_min,menu_price_max,menu_raw_text",
      filters: [`restaurant_id=eq.${restaurant.id}`],
    }),
    fetchAll<MenuTagRow>("menu_tags", {
      select:
        "menu_id,halal_friendly_menu,contains_pork,contains_alcohol,has_seafood_option,has_vegetarian_option,course_coverage,halal_friendly_dishes",
      filters: ["model=eq.gpt-4o"],
    }),
    fetchAll<HalalSourceRow>("halal_sources", {
      select: "restaurant_id,status",
      filters: [`restaurant_id=eq.${restaurant.id}`],
    }),
  ]);

  const tagsByMenu = new Map<string, MenuTagRow>();
  for (const tag of tags) {
    tagsByMenu.set(tag.menu_id, tag);
  }

  let halalSource: "certified" | "listed" | null = null;
  for (const source of sources) {
    if (source.status === "halal_certified") {
      halalSource = "certified";
      break;
    }
    if (source.status === "halal_listed") {
      halalSource = "listed";
    }
  }

  const menuVariants = menus
    .sort((a, b) => {
      if (a.menu_title === b.menu_title) {
        return a.menu_variant - b.menu_variant;
      }
      return a.menu_title.localeCompare(b.menu_title);
    })
    .map((menu) => {
      const tag = tagsByMenu.get(menu.id) ?? null;
      return {
        id: menu.id,
        title: menu.menu_title,
        variant: menu.menu_variant,
        priceMin: toNumber(menu.menu_price_min),
        priceMax: toNumber(menu.menu_price_max),
        rawText: menu.menu_raw_text,
        tags: tag
          ? {
              halalFriendly: tag.halal_friendly_menu,
              containsPork: tag.contains_pork,
              containsAlcohol: tag.contains_alcohol,
              hasSeafood: tag.has_seafood_option,
              hasVegetarian: tag.has_vegetarian_option,
              courseCoverage: tag.course_coverage,
              halalDishes: Array.isArray(tag.halal_friendly_dishes)
                ? tag.halal_friendly_dishes
                : [],
            }
          : null,
      } as MenuVariant;
    });

  return {
    id: restaurant.id,
    name: restaurant.name,
    slug: restaurant.slug,
    dineoutUrl: restaurant.dineout_url,
    halalSource,
    menuVariants,
  };
}

export async function getHalalRestaurants(): Promise<HalalRestaurant[]> {
  const rows = await fetchAll<HalalRestaurantRow>("halal_restaurants", {
    select:
      "id,name,slug,category_name,categories,address,city,neighborhood,price,website,phone,rating,reviews_count,google_url,image_url,lat,lng,opening_hours,permanently_closed,temporarily_closed",
  });

  return rows
    .map((row) => ({
      id: row.id,
      name: row.name,
      slug: row.slug,
      categoryName: row.category_name,
      categories: row.categories,
      address: row.address,
      city: row.city,
      neighborhood: row.neighborhood,
      price: row.price,
      website: row.website,
      phone: row.phone,
      rating: row.rating,
      reviewsCount: row.reviews_count,
      googleUrl: row.google_url,
      imageUrl: row.image_url,
      lat: row.lat,
      lng: row.lng,
      openingHours: normalizeOpeningHours(row.opening_hours),
      permanentlyClosed: row.permanently_closed,
      temporarilyClosed: row.temporarily_closed,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
