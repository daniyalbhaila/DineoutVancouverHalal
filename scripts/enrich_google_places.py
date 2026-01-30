import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests


DEFAULT_CENTER = "49.2827,-123.1207"
DEFAULT_RADIUS_METERS = 50000


def load_names(path: str) -> List[str]:
    names: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            names.append(line)
    return names


def load_overrides(path: Optional[str]) -> Dict[str, dict]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit("Overrides file must be a JSON object keyed by name.")
    return data


def place_id_lookup(api_key: str, name: str, center: str, radius: int) -> Optional[dict]:
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": name,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address",
        "locationbias": f"circle:{radius}@{center}",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        return None
    return candidates[0]


def place_details(api_key: str, place_id: str) -> Optional[dict]:
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
    return result if result else None


def address_component(components: List[dict], type_name: str, short: bool = False) -> Optional[str]:
    for component in components:
        types = component.get("types") or []
        if type_name in types:
            return component.get("short_name" if short else "long_name")
    return None


def price_level_to_dollars(level: Optional[int]) -> Optional[str]:
    if level is None:
        return None
    if level < 0:
        return None
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

    category_name = None
    if types:
        category_name = types[0].replace("_", " ")

    return {
        "title": result.get("name"),
        "categoryName": category_name,
        "categories": types or None,
        "address": result.get("formatted_address"),
        "city": city,
        "neighborhood": neighborhood,
        "postalCode": postal_code,
        "state": state,
        "countryCode": country,
        "price": price_level_to_dollars(result.get("price_level")),
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
    parser = argparse.ArgumentParser(description="Enrich places via Google Places API.")
    parser.add_argument("--input", required=True, help="Path to file with one place name per line")
    parser.add_argument("--output", default="reports/googlemaps_enriched_places.json", help="Output JSON path")
    parser.add_argument("--center", default=DEFAULT_CENTER, help="Location bias center lat,lng")
    parser.add_argument("--radius", type=int, default=DEFAULT_RADIUS_METERS, help="Location bias radius meters")
    parser.add_argument("--overrides", help="Path to JSON overrides keyed by name")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between requests in seconds")
    parser.add_argument("--max-places", type=int, default=0, help="Max places to process (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no API calls")
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise SystemExit("Missing GOOGLE_PLACES_API_KEY env var.")

    names = load_names(args.input)
    overrides = load_overrides(args.overrides)
    if args.max_places > 0:
        names = names[: args.max_places]

    if args.dry_run:
        print(f"Planned lookups: {len(names)}")
        return

    results: List[dict] = []
    missing: List[str] = []

    for idx, name in enumerate(names, start=1):
        override = overrides.get(name) or {}
        query_name = override.get("query", name)
        center = override.get("center", args.center)
        radius = override.get("radius", args.radius)
        candidate = place_id_lookup(api_key, query_name, center, radius)
        if not candidate:
            missing.append(name)
            continue
        place_id = candidate.get("place_id")
        if not place_id:
            missing.append(name)
            continue
        details = place_details(api_key, place_id)
        if not details:
            missing.append(name)
            continue
        results.append(to_place_record(details))
        if args.sleep:
            time.sleep(args.sleep)

        if idx % 25 == 0:
            print(f"Processed {idx}/{len(names)}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=True, indent=2)

    if missing:
        missing_path = "reports/googlemaps_enrichment_missing.txt"
        with open(missing_path, "w", encoding="utf-8") as f:
            for name in missing:
                f.write(name + "\n")
        print(f"Missing matches: {len(missing)} (see {missing_path})")

    print(f"Enriched places saved: {args.output}")


if __name__ == "__main__":
    main()
