import argparse
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


STOPWORDS = {
    "restaurant",
    "restaurants",
    "bar",
    "cafe",
    "café",
    "bistro",
    "kitchen",
    "grill",
    "grille",
    "pub",
    "the",
    "and",
    "&",
    "lounge",
    "house",
    "eatery",
}


def normalize_name(text: str) -> str:
    text = clean_text(text).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    return " ".join(tokens)


def clean_text(value: str) -> str:
    if not value:
        return value
    return re.sub(r"[\x00-\x1f\x7f]", "", value).strip()


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


def get_postgrest_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def parse_reviews(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"\(([^)]+)\)", text)
    if not match:
        return None
    numeric = match.group(1).replace(",", "").strip()
    if not numeric.isdigit():
        return None
    return int(numeric)


def parse_price_and_category(info_line: str) -> Tuple[Optional[str], Optional[str]]:
    if not info_line:
        return None, None
    if "Permanently closed" in info_line:
        return None, None
    parts = [part.strip() for part in info_line.split("·") if part.strip()]
    price = None
    category = None
    for part in parts:
        if "$" in part:
            price = part
        else:
            category = part
    return price, category


def parse_list_entries(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    buttons = soup.select("button.SMP2wb")
    entries: List[dict] = []
    for btn in buttons:
        name_node = btn.select_one("div.fontHeadlineSmall.rZF81c")
        name = clean_text(name_node.get_text(" ", strip=True) if name_node else "")
        if not name:
            continue

        rating_node = btn.select_one("span.MW4etd")
        rating = None
        if rating_node:
            try:
                rating = float(rating_node.get_text(strip=True))
            except ValueError:
                rating = None

        reviews_node = btn.select_one("span.UY7F9")
        reviews_count = parse_reviews(reviews_node.get_text(strip=True) if reviews_node else None)

        info_lines = [clean_text(node.get_text(" ", strip=True)) for node in btn.select("div.IIrLbb")]
        price = None
        category = None
        if len(info_lines) >= 2:
            price, category = parse_price_and_category(info_lines[1])
        elif len(info_lines) == 1:
            price, category = parse_price_and_category(info_lines[0])

        image_node = btn.select_one("img.WkIe8")
        image_url = image_node.get("src") if image_node else None

        text_blob = clean_text(btn.get_text(" ", strip=True))
        permanently_closed = "Permanently closed" in text_blob

        entries.append(
            {
                "name": name,
                "normalized": normalize_name(name),
                "rating": rating,
                "reviews_count": reviews_count,
                "price": price,
                "category_name": category,
                "image_url": image_url,
                "permanently_closed": permanently_closed,
            }
        )
    return entries


def consolidate_entries(entries: List[dict]) -> List[dict]:
    merged: Dict[str, dict] = {}
    for entry in entries:
        key = entry["normalized"]
        if not key:
            continue
        if key not in merged:
            merged[key] = entry
            continue

        current = merged[key]
        current_reviews = current.get("reviews_count") or 0
        candidate_reviews = entry.get("reviews_count") or 0

        if candidate_reviews > current_reviews:
            current.update(entry)
        else:
            if not current.get("price") and entry.get("price"):
                current["price"] = entry["price"]
            if not current.get("category_name") and entry.get("category_name"):
                current["category_name"] = entry["category_name"]
            if not current.get("image_url") and entry.get("image_url"):
                current["image_url"] = entry["image_url"]
            if entry.get("permanently_closed"):
                current["permanently_closed"] = True

    return list(merged.values())


def fetch_existing(base_url: str, headers: Dict[str, str]) -> List[dict]:
    url = (
        f"{base_url}/halal_restaurants"
        "?select=id,name,slug,category_name,price,rating,reviews_count,image_url,permanently_closed"
    )
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def patch_row(base_url: str, headers: Dict[str, str], row_id: str, payload: dict) -> None:
    url = f"{base_url}/halal_restaurants?id=eq.{row_id}"
    resp = requests.patch(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")


def upsert_rows(base_url: str, headers: Dict[str, str], rows: List[dict]) -> None:
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        url = f"{base_url}/halal_restaurants?on_conflict=slug"
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update halal_restaurants from Google Maps list HTML.")
    parser.add_argument("--html", default="GoogleMapsHalalList.html", help="Path to Google Maps list HTML")
    parser.add_argument("--update-only", action="store_true", help="Update matched rows only")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing to Supabase")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars.")

    with open(args.html, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    entries = consolidate_entries(parse_list_entries(html))
    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = get_postgrest_headers(service_key)

    existing = fetch_existing(base_url, headers)
    existing_by_key: Dict[str, List[dict]] = {}
    slugs_in_use = set()
    for row in existing:
        key = normalize_name(row["name"])
        existing_by_key.setdefault(key, []).append(row)
        if row.get("slug"):
            slugs_in_use.add(row["slug"])

    matched_updates: List[Tuple[str, dict]] = []
    new_rows: List[dict] = []
    ambiguous: List[Tuple[str, List[str]]] = []

    for entry in entries:
        key = entry["normalized"]
        matches = existing_by_key.get(key, [])
        if not matches:
            slug = unique_slug(slugify(entry["name"]), slugs_in_use)
            slugs_in_use.add(slug)
            new_rows.append(
                {
                    "name": entry["name"],
                    "slug": slug,
                    "category_name": entry.get("category_name"),
                    "price": entry.get("price"),
                    "rating": entry.get("rating"),
                    "reviews_count": entry.get("reviews_count"),
                    "image_url": entry.get("image_url"),
                    "permanently_closed": entry.get("permanently_closed"),
                    "temporarily_closed": None,
                    "source": "google_maps_list_html",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            continue
        if len(matches) > 1:
            ambiguous.append((entry["name"], [m["name"] for m in matches]))
            continue

        match = matches[0]
        payload = {
            "category_name": entry.get("category_name"),
            "price": entry.get("price"),
            "rating": entry.get("rating"),
            "reviews_count": entry.get("reviews_count"),
            "image_url": entry.get("image_url"),
            "permanently_closed": entry.get("permanently_closed"),
        }
        matched_updates.append((match["id"], payload))

    print(f"Entries parsed: {len(entries)}")
    print(f"Matched updates: {len(matched_updates)}")
    print(f"New rows: {len(new_rows)}")
    print(f"Ambiguous matches: {len(ambiguous)}")
    if ambiguous:
        print("Ambiguous examples (html name -> matches):")
        for name, matches in ambiguous[:15]:
            print(f"- {name} -> {', '.join(matches)}")

    if args.dry_run:
        return

    for row_id, payload in matched_updates:
        patch_row(base_url, headers, row_id, payload)

    if new_rows and not args.update_only:
        upsert_rows(base_url, headers, new_rows)

    print("Update complete.")


if __name__ == "__main__":
    main()
