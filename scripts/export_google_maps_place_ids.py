import argparse
import json
import os
from typing import Dict, List

import requests


def get_headers() -> Dict[str, str]:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not key:
        raise SystemExit("Missing SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY env vars.")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def fetch_place_ids(base_url: str, headers: Dict[str, str]) -> List[str]:
    place_ids: List[str] = []
    page = 0
    page_size = 1000
    while True:
        offset = page * page_size
        url = (
            f"{base_url}/halal_restaurants"
            f"?select=place_id&place_id=not.is.null&limit={page_size}&offset={offset}"
        )
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for row in data:
            place_id = (row.get("place_id") or "").strip()
            if place_id:
                place_ids.append(place_id)
        page += 1

    unique_ids = sorted(set(place_ids))
    return unique_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Google Maps place IDs from Supabase.")
    parser.add_argument("--output-dir", default="reports", help="Output directory")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url:
        raise SystemExit("Missing SUPABASE_URL env var.")

    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = get_headers()

    place_ids = fetch_place_ids(base_url, headers)
    os.makedirs(args.output_dir, exist_ok=True)

    ids_path = os.path.join(args.output_dir, "googlemaps_place_ids.txt")
    urls_path = os.path.join(args.output_dir, "googlemaps_place_id_urls.txt")
    json_path = os.path.join(args.output_dir, "googlemaps_place_id_start_urls.json")

    with open(ids_path, "w", encoding="utf-8") as f:
        for place_id in place_ids:
            f.write(place_id + "\n")

    with open(urls_path, "w", encoding="utf-8") as f:
        for place_id in place_ids:
            f.write(f"https://www.google.com/maps/place/?q=place_id:{place_id}\n")

    start_urls = [{"url": f"https://www.google.com/maps/place/?q=place_id:{pid}"} for pid in place_ids]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"startUrls": start_urls}, f, indent=2)

    print(f"Exported {len(place_ids)} place IDs.")
    print(f"- {ids_path}")
    print(f"- {urls_path}")
    print(f"- {json_path}")


if __name__ == "__main__":
    main()
