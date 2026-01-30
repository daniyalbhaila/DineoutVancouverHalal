import argparse
import json
import os
import time
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


def text_search(api_key: str, query: str, center: str, radius: int) -> List[dict]:
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "location": center,
        "radius": radius,
        "key": api_key,
    }
    results: List[dict] = []
    page_token = None

    for _ in range(3):
        if page_token:
            params["pagetoken"] = page_token
            time.sleep(2)
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        results.extend(payload.get("results", []))
        page_token = payload.get("next_page_token")
        if not page_token:
            break

    return results


def simplify(place: dict) -> dict:
    return {
        "name": place.get("name"),
        "place_id": place.get("place_id"),
        "formatted_address": place.get("formatted_address"),
        "business_status": place.get("business_status"),
        "rating": place.get("rating"),
        "user_ratings_total": place.get("user_ratings_total"),
        "types": place.get("types"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Find candidate branches for ambiguous names.")
    parser.add_argument("--input", required=True, help="Path to file with one name per line")
    parser.add_argument("--output", default="reports/googlemaps_ambiguous_candidates.json", help="Output JSON path")
    parser.add_argument("--center", default=DEFAULT_CENTER, help="Location center lat,lng")
    parser.add_argument("--radius", type=int, default=DEFAULT_RADIUS_METERS, help="Radius meters")
    parser.add_argument("--overrides", help="Path to JSON overrides keyed by name")
    parser.add_argument("--suffix", default="Vancouver BC", help="Default query suffix")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between queries")
    parser.add_argument("--max-results", type=int, default=20, help="Max results per query")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no API calls")
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise SystemExit("Missing GOOGLE_PLACES_API_KEY env var.")

    names = load_names(args.input)
    overrides = load_overrides(args.overrides)

    if args.dry_run:
        print(f"Planned searches: {len(names)}")
        return

    output: Dict[str, List[dict]] = {}

    for idx, name in enumerate(names, start=1):
        override = overrides.get(name) or {}
        query = override.get("query", f"{name} {args.suffix}")
        center = override.get("center", args.center)
        radius = override.get("radius", args.radius)
        places = text_search(api_key, query, center, radius)
        simplified = [simplify(p) for p in places[: args.max_results]]
        output[name] = simplified
        if args.sleep:
            time.sleep(args.sleep)
        if idx % 5 == 0:
            print(f"Processed {idx}/{len(names)}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=True, indent=2)

    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
