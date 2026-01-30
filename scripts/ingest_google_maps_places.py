import argparse
import json
import os
import re
from typing import Dict, List, Optional

import requests


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "restaurant"


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    text = text.replace("\u00a0", " ")
    text = text.replace("\u202f", " ")
    text = text.replace("\u2007", " ")
    text = text.replace("\u2009", " ")
    text = text.replace("\u200a", " ")
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


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


def fetch_existing(base_url: str, headers: Dict[str, str]) -> List[dict]:
    rows: List[dict] = []
    page = 0
    page_size = 1000
    while True:
        offset = page * page_size
        url = (
            f"{base_url}/halal_restaurants"
            f"?select=id,slug,place_id&limit={page_size}&offset={offset}"
        )
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        rows.extend(data)
        page += 1
    return rows


def patch_by_place_id(base_url: str, headers: Dict[str, str], place_id: str, payload: dict) -> None:
    url = f"{base_url}/halal_restaurants?place_id=eq.{place_id}"
    resp = requests.patch(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")


def insert_rows(base_url: str, headers: Dict[str, str], rows: List[dict]) -> None:
    for batch in chunked(rows, 100):
        url = f"{base_url}/halal_restaurants?on_conflict=slug"
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")


def build_row(item: dict) -> dict:
    location = item.get("location") or {}
    categories = item.get("categories")
    if categories:
        categories = [clean_text(value) for value in categories]
        categories = [value for value in categories if value]
    return {
        "name": clean_text(item.get("title")),
        "category_name": clean_text(item.get("categoryName")),
        "categories": categories,
        "address": clean_text(item.get("address")),
        "city": clean_text(item.get("city")),
        "neighborhood": clean_text(item.get("neighborhood")),
        "postal_code": clean_text(item.get("postalCode")),
        "state": clean_text(item.get("state")),
        "country_code": clean_text(item.get("countryCode")),
        "price": clean_text(item.get("price")),
        "website": clean_text(item.get("website")),
        "phone": clean_text(item.get("phone")),
        "rating": item.get("totalScore"),
        "reviews_count": item.get("reviewsCount"),
        "place_id": clean_text(item.get("placeId")),
        "lat": location.get("lat"),
        "lng": location.get("lng"),
        "google_url": clean_text(item.get("url")),
        "image_url": clean_text(item.get("imageUrl")),
        "opening_hours": item.get("openingHours"),
        "permanently_closed": item.get("permanentlyClosed"),
        "temporarily_closed": item.get("temporarilyClosed"),
        "source": "google_maps_enriched",
        "scraped_at": item.get("scrapedAt"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest enriched Google Maps places JSON into Supabase.")
    parser.add_argument("--json", required=True, help="Path to JSON file (list of places)")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars.")

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise SystemExit("Expected a list of place objects in JSON.")

    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = postgrest_headers(service_key)
    existing = fetch_existing(base_url, headers)

    slugs_in_use = {row["slug"] for row in existing if row.get("slug")}
    existing_place_ids = {row.get("place_id") for row in existing if row.get("place_id")}

    updates = 0
    inserts: List[dict] = []
    missing_place_id: List[str] = []

    for item in data:
        place_id = clean_text(item.get("placeId"))
        name = item.get("title")
        if not place_id:
            if name:
                missing_place_id.append(name)
            continue

        row = build_row(item)
        if place_id in existing_place_ids:
            updates += 1
            if not args.dry_run:
                patch_by_place_id(base_url, headers, place_id, row)
            continue

        base_slug = slugify(name or "restaurant")
        slug = unique_slug(base_slug, slugs_in_use)
        slugs_in_use.add(slug)
        row["slug"] = slug
        inserts.append(row)

    if inserts and not args.dry_run:
        insert_rows(base_url, headers, inserts)

    print(f"Places processed: {len(data)}")
    print(f"Updates (by place_id): {updates}")
    print(f"Inserts: {len(inserts)}")
    print(f"Missing place_id: {len(missing_place_id)}")

    if missing_place_id:
        os.makedirs("reports", exist_ok=True)
        path = os.path.join("reports", "googlemaps_missing_place_id.txt")
        with open(path, "w", encoding="utf-8") as f:
            for name in sorted(set(missing_place_id)):
                f.write(name + "\n")
        print(f"Missing place_id list written to {path}")


if __name__ == "__main__":
    main()
