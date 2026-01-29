import argparse
import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://vancouverfoodies.ca"
LISTINGS_PATH = "/restaurants/"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

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


def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    return resp.text


def normalize_name(text: str) -> str:
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    return " ".join(tokens)


def tokenize_name(text: str) -> List[str]:
    return normalize_name(text).split()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def prefix_match_score(a_tokens: List[str], b_tokens: List[str]) -> float:
    if not a_tokens or not b_tokens:
        return 0.0
    a_prefix = a_tokens[:3]
    b_prefix = b_tokens[:3]
    if a_prefix == b_prefix and len(a_prefix) >= 2:
        return 0.93
    if len(a_tokens) >= 2 and len(b_tokens) >= 2 and a_tokens[:2] == b_tokens[:2]:
        return 0.9
    return 0.0


def token_overlap_score(a_tokens: List[str], b_tokens: List[str]) -> float:
    if len(a_tokens) < 2 or len(b_tokens) < 2:
        return 0.0
    overlap = set(a_tokens) & set(b_tokens)
    ratio = len(overlap) / min(len(a_tokens), len(b_tokens))
    if ratio >= 0.75:
        return 0.9
    return 0.0


def parse_listing_cards(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for card in soup.select("article.hp-listing.hp-listing--view-block"):
        name_el = card.select_one("h4.hp-listing__title > a")
        if not name_el:
            continue
        name = name_el.get_text(" ").strip()
        href = name_el.get("href")
        href = href if isinstance(href, str) else ""
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        alcohol = bool(card.select_one(".hp-listing__attribute--alcohol"))
        bcma = bool(card.select_one(".hp-listing__attribute--bcma-certified"))
        badges = []
        if bcma:
            badges.append("BCMA Certified")
        if alcohol:
            badges.append("Alcohol Served")

        cards.append(
            {
                "name": name,
                "url": url,
                "badges": badges,
                "halal_certified": bcma,
                "alcohol_served": alcohol,
            }
        )
    return cards


def discover_total_pages(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pages = []
    for link in soup.select(".pagination .page-numbers"):
        text = link.get_text(strip=True)
        if text.isdigit():
            pages.append(int(text))
    return max(pages) if pages else 1


def fetch_all_listings() -> List[dict]:
    first_url = f"{BASE_URL}{LISTINGS_PATH}"
    first_html = fetch(first_url)
    listings = parse_listing_cards(first_html)
    total_pages = discover_total_pages(first_html)

    for page in range(2, total_pages + 1):
        url = f"{BASE_URL}{LISTINGS_PATH}page/{page}/"
        html = fetch(url)
        listings.extend(parse_listing_cards(html))

    unique_by_url = {}
    for listing in listings:
        unique_by_url[listing["url"]] = listing
    return list(unique_by_url.values())


def get_postgrest_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def fetch_restaurants(base_url: str, headers: Dict[str, str]) -> List[dict]:
    url = f"{base_url}/restaurants?select=id,name,slug,dineout_url"
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_overrides(base_url: str, headers: Dict[str, str]) -> Dict[str, str]:
    url = f"{base_url}/match_overrides?select=dineout_name,vancouverfoodies_name"
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    overrides = {}
    for row in resp.json():
        overrides[row["dineout_name"].strip().lower()] = row["vancouverfoodies_name"].strip().lower()
    return overrides


def match_listing(dineout_name: str, listings: List[dict], overrides: Dict[str, str]) -> Tuple[Optional[dict], float, str]:
    override_key = dineout_name.strip().lower()
    if override_key in overrides:
        target = overrides[override_key]
        for listing in listings:
            if listing["name"].strip().lower() == target:
                return listing, 1.0, "override"

    dineout_norm = normalize_name(dineout_name)
    dineout_tokens = tokenize_name(dineout_name)
    listing_norms = [(listing, normalize_name(listing["name"])) for listing in listings]

    for listing, norm in listing_norms:
        if dineout_norm and dineout_norm == norm:
            return listing, 0.95, "exact"

    best = None
    best_score = 0.0
    for listing, norm in listing_norms:
        listing_tokens = tokenize_name(listing["name"])
        score = similarity(dineout_norm, norm)
        score = max(score, prefix_match_score(dineout_tokens, listing_tokens), token_overlap_score(dineout_tokens, listing_tokens))
        if score > best_score:
            best = listing
            best_score = score

    return best, best_score, "fuzzy"


def upsert_halal_sources(base_url: str, headers: Dict[str, str], rows: List[dict]) -> None:
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        url = f"{base_url}/halal_sources?on_conflict=restaurant_id,source_name"
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        resp.raise_for_status()


def delete_existing_sources(base_url: str, headers: Dict[str, str], source_name: str) -> None:
    url = f"{base_url}/halal_sources?source_name=eq.{source_name}"
    resp = requests.delete(url, headers=headers, timeout=60)
    resp.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-reference Vancouver Foodies listings.")
    parser.add_argument("--threshold", type=float, default=0.86, help="Fuzzy match threshold")
    parser.add_argument("--reset", action="store_true", help="Delete existing Vancouver Foodies rows before insert")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars.")

    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = get_postgrest_headers(service_key)

    if args.reset:
        delete_existing_sources(base_url, headers, "Vancouver Foodies")

    listings = fetch_all_listings()
    restaurants = fetch_restaurants(base_url, headers)
    overrides = fetch_overrides(base_url, headers)

    matched = 0
    unmatched = []
    rows = []

    for restaurant in restaurants:
        listing, score, match_type = match_listing(restaurant["name"], listings, overrides)
        if not listing or score < args.threshold:
            unmatched.append({"name": restaurant["name"], "score": score})
            continue

        badges = listing["badges"]
        status = "halal_certified" if listing["halal_certified"] else "halal_listed"
        evidence = "Vancouver Foodies listing"
        if badges:
            evidence += ": " + "; ".join(badges)

        rows.append(
            {
                "restaurant_id": restaurant["id"],
                "source_name": "Vancouver Foodies",
                "source_url": listing["url"],
                "status": status,
                "evidence_snippet": evidence,
                "confidence": round(score, 3),
            }
        )
        matched += 1

    if rows:
        upsert_halal_sources(base_url, headers, rows)

    print(f"Listings scraped: {len(listings)}")
    print(f"Restaurants matched: {matched}")
    print(f"Restaurants unmatched: {len(unmatched)}")
    if unmatched:
        print("Top unmatched examples:")
        for item in unmatched[:10]:
            print(f"- {item['name']} (score {item['score']:.2f})")


if __name__ == "__main__":
    main()
