import argparse
import json
import os
import re
from typing import Dict, List

import requests


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "restaurant"


def unique_slug(base: str, existing: set) -> str:
    if base not in existing:
        return base
    counter = 2
    while True:
        candidate = f"{base}-{counter}"
        if candidate not in existing:
            return candidate
        counter += 1


def postgrest_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def chunked(items: List[dict], size: int) -> List[List[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def upsert_rows(base_url: str, headers: Dict[str, str], rows: List[dict]) -> None:
    for batch in chunked(rows, 100):
        url = f"{base_url}/halal_restaurants?on_conflict=slug"
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load HalalRestaurants.json into Supabase.")
    parser.add_argument("--json", default="HalalRestaurants.json", help="Path to JSON file")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows for testing")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars.")

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise SystemExit("Expected a list of restaurant objects in JSON.")

    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = postgrest_headers(service_key)

    rows: List[dict] = []
    slugs_in_use = set()

    for idx, item in enumerate(data, start=1):
        if args.limit and idx > args.limit:
            break
        name = (item.get("title") or "").strip()
        if not name:
            continue
        slug = unique_slug(slugify(name), slugs_in_use)
        slugs_in_use.add(slug)

        location = item.get("location") or {}
        rows.append(
            {
                "name": name,
                "slug": slug,
                "category_name": item.get("categoryName"),
                "categories": item.get("categories"),
                "address": item.get("address"),
                "city": item.get("city"),
                "neighborhood": item.get("neighborhood"),
                "postal_code": item.get("postalCode"),
                "state": item.get("state"),
                "country_code": item.get("countryCode"),
                "price": item.get("price"),
                "website": item.get("website"),
                "phone": item.get("phone"),
                "rating": item.get("totalScore"),
                "reviews_count": item.get("reviewsCount"),
                "place_id": item.get("placeId"),
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "google_url": item.get("url"),
                "image_url": item.get("imageUrl"),
                "opening_hours": item.get("openingHours"),
                "permanently_closed": item.get("permanentlyClosed"),
                "temporarily_closed": item.get("temporarilyClosed"),
                "source": "google_maps_list",
                "scraped_at": item.get("scrapedAt"),
            }
        )

    upsert_rows(base_url, headers, rows)
    print(f"Loaded {len(rows)} halal restaurants.")


if __name__ == "__main__":
    main()
