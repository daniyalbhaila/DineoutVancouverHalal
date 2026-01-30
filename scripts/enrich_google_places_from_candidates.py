import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List

import requests


def place_details(api_key: str, place_id: str) -> dict:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    fields = ",".join(
        [
            "place_id",
            "name",
            "formatted_address",
            "address_component",
            "geometry",
            "types",
            "website",
            "formatted_phone_number",
            "rating",
            "user_ratings_total",
            "price_level",
            "url",
            "opening_hours",
            "business_status",
        ]
    )
    params = {
        "place_id": place_id,
        "fields": fields,
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    result = payload.get("result")
    if not result:
        raise RuntimeError(f"No result for place_id {place_id}")
    return result


def address_component(components: List[dict], type_name: str, short: bool = False) -> str:
    for component in components:
        types = component.get("types") or []
        if type_name in types:
            return component.get("short_name" if short else "long_name")
    return ""


def price_level_to_dollars(level: int) -> str:
    if level is None or level < 0:
        return ""
    return "$" * (level + 1)


def to_place_record(result: dict) -> dict:
    components = result.get("address_components") or []
    geometry = result.get("geometry") or {}
    location = geometry.get("location") or {}
    types = result.get("types") or []

    neighborhood = address_component(components, "neighborhood")
    if not neighborhood:
        neighborhood = address_component(components, "sublocality")
    if not neighborhood:
        neighborhood = address_component(components, "sublocality_level_1")

    city = address_component(components, "locality")
    if not city:
        city = address_component(components, "postal_town")

    state = address_component(components, "administrative_area_level_1", short=True)
    country = address_component(components, "country", short=True)
    postal_code = address_component(components, "postal_code")

    business_status = result.get("business_status")
    permanently_closed = business_status == "CLOSED_PERMANENTLY"
    temporarily_closed = business_status == "CLOSED_TEMPORARILY"

    category_name = types[0].replace("_", " ") if types else ""

    return {
        "title": result.get("name"),
        "categoryName": category_name or None,
        "categories": types or None,
        "address": result.get("formatted_address"),
        "city": city or None,
        "neighborhood": neighborhood or None,
        "postalCode": postal_code or None,
        "state": state or None,
        "countryCode": country or None,
        "price": price_level_to_dollars(result.get("price_level")) or None,
        "website": result.get("website"),
        "phone": result.get("formatted_phone_number"),
        "totalScore": result.get("rating"),
        "reviewsCount": result.get("user_ratings_total"),
        "placeId": result.get("place_id"),
        "location": {
            "lat": location.get("lat"),
            "lng": location.get("lng"),
        },
        "url": result.get("url"),
        "imageUrl": None,
        "openingHours": result.get("opening_hours"),
        "permanentlyClosed": permanently_closed,
        "temporarilyClosed": temporarily_closed,
        "scrapedAt": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich Places candidates by place_id.")
    parser.add_argument("--input", required=True, help="Path to candidates JSON (name -> list)")
    parser.add_argument("--output", default="reports/googlemaps_ambiguous_enriched.json", help="Output JSON path")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between requests in seconds")
    parser.add_argument("--max-places", type=int, default=0, help="Max place IDs to process (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no API calls")
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise SystemExit("Missing GOOGLE_PLACES_API_KEY env var.")

    with open(args.input, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    if not isinstance(candidates, dict):
        raise SystemExit("Expected a JSON object keyed by name.")

    place_ids = []
    for places in candidates.values():
        for place in places:
            place_id = place.get("place_id")
            if place_id:
                place_ids.append(place_id)

    unique_ids = []
    seen = set()
    for pid in place_ids:
        if pid in seen:
            continue
        seen.add(pid)
        unique_ids.append(pid)

    if args.max_places > 0:
        unique_ids = unique_ids[: args.max_places]

    if args.dry_run:
        print(f"Planned place_id lookups: {len(unique_ids)}")
        return

    results: List[dict] = []
    failures: List[str] = []

    for idx, place_id in enumerate(unique_ids, start=1):
        try:
            details = place_details(api_key, place_id)
            results.append(to_place_record(details))
        except Exception:
            failures.append(place_id)
        if args.sleep:
            time.sleep(args.sleep)
        if idx % 25 == 0:
            print(f"Processed {idx}/{len(unique_ids)}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=True, indent=2)

    if failures:
        path = "reports/googlemaps_ambiguous_failures.txt"
        with open(path, "w", encoding="utf-8") as f:
            for pid in failures:
                f.write(pid + "\n")
        print(f"Failures: {len(failures)} (see {path})")

    print(f"Enriched places saved: {args.output}")


if __name__ == "__main__":
    main()
