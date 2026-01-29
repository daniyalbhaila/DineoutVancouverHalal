import argparse
import csv
import os
import re
from typing import Dict, List, Optional, Tuple

import requests


PRICE_NUMBER_REGEX = re.compile(r"\d+(?:\.\d+)?")


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


def parse_price_range(raw: str) -> Tuple[Optional[float], Optional[float]]:
    if not raw:
        return None, None
    numbers = [float(n) for n in PRICE_NUMBER_REGEX.findall(raw)]
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return min(numbers), max(numbers)


def chunked(items: List[dict], size: int) -> List[List[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def postgrest_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def upsert_restaurants(base_url: str, headers: Dict[str, str], restaurants: List[dict]) -> Dict[str, str]:
    slug_to_id: Dict[str, str] = {}
    for batch in chunked(restaurants, 200):
        url = f"{base_url}/restaurants?on_conflict=slug"
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        resp.raise_for_status()
        for item in resp.json():
            slug_to_id[item["slug"]] = item["id"]
    return slug_to_id


def upsert_menus(base_url: str, headers: Dict[str, str], menus: List[dict]) -> None:
    for batch in chunked(menus, 50):
        url = f"{base_url}/menus?on_conflict=restaurant_id,menu_title,menu_variant"
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        resp.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Dine Out menus into Supabase.")
    parser.add_argument("--csv", default="data/dineout_menus_raw.csv", help="Path to menus CSV")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows for testing")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars.")

    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = postgrest_headers(service_key)

    restaurants_by_url: Dict[str, dict] = {}
    slugs_in_use: set = set()
    menus: List[dict] = []

    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            if args.limit and idx > args.limit:
                break
            url = row["restaurant_page_url"].strip()
            if url in restaurants_by_url:
                continue
            name = row["restaurant_name"].strip()
            base_slug = slugify(name)
            slug = unique_slug(base_slug, slugs_in_use)
            slugs_in_use.add(slug)
            restaurants_by_url[url] = {
                "name": name,
                "slug": slug,
                "dineout_url": url or None,
            }

    slug_to_id = upsert_restaurants(base_url, headers, list(restaurants_by_url.values()))
    url_to_slug = {url: data["slug"] for url, data in restaurants_by_url.items()}

    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            if args.limit and idx > args.limit:
                break
            url = row["restaurant_page_url"].strip()
            slug = url_to_slug.get(url)
            if not slug:
                continue
            restaurant_id = slug_to_id.get(slug)
            if not restaurant_id:
                continue
            menu_price = row.get("menu_price", "").strip()
            price_min, price_max = parse_price_range(menu_price)
            menu_variant = int(row.get("menu_variant") or 1)
            menus.append(
                {
                    "restaurant_id": restaurant_id,
                    "menu_title": row.get("menu_title", "").strip(),
                    "menu_variant": menu_variant,
                    "menu_price": menu_price or None,
                    "menu_price_min": price_min,
                    "menu_price_max": price_max,
                    "currency": row.get("currency", "CAD").strip() or "CAD",
                    "menu_raw_text": row.get("menu_raw_text", "").strip(),
                }
            )

    upsert_menus(base_url, headers, menus)
    print(f"Loaded {len(menus)} menus into Supabase.")


if __name__ == "__main__":
    main()
