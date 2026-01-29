import argparse
import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


SOURCE_NAME = "Google Maps List"

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
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    return " ".join(tokens)


def tokenize_name(text: str) -> List[str]:
    return normalize_name(text).split()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def parse_list_names(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select("div.fontHeadlineSmall.rZF81c")
    names = [node.get_text(" ", strip=True) for node in nodes]
    return [name for name in names if name]


def get_postgrest_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def fetch_restaurants(base_url: str, headers: Dict[str, str]) -> List[dict]:
    url = f"{base_url}/restaurants?select=id,name"
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


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


def match_name(target: str, candidates: List[dict]) -> Tuple[Optional[dict], float]:
    target_norm = normalize_name(target)
    target_tokens = tokenize_name(target)
    if not target_norm:
        return None, 0.0

    best = None
    best_score = 0.0
    for cand in candidates:
        cand_norm = normalize_name(cand["name"])
        cand_tokens = tokenize_name(cand["name"])
        if cand_norm == target_norm:
            return cand, 0.95
        score = similarity(target_norm, cand_norm)
        score = max(score, prefix_match_score(target_tokens, cand_tokens), token_overlap_score(target_tokens, cand_tokens))
        if score > best_score:
            best = cand
            best_score = score

    return best, best_score


def upsert_halal_sources(base_url: str, headers: Dict[str, str], rows: List[dict]) -> None:
    for i in range(0, len(rows), 50):
        batch = rows[i : i + 50]
        url = f"{base_url}/halal_sources?on_conflict=restaurant_id,source_name"
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")


def delete_existing_sources(base_url: str, headers: Dict[str, str], source_name: str) -> None:
    url = f"{base_url}/halal_sources?source_name=eq.{source_name}"
    resp = requests.delete(url, headers=headers, timeout=60)
    resp.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Google Maps list from HTML.")
    parser.add_argument("--html", default="halalList.html", help="Path to Google Maps list HTML")
    parser.add_argument("--threshold", type=float, default=0.88, help="Fuzzy match threshold")
    parser.add_argument("--reset", action="store_true", help="Delete existing Google Maps rows before insert")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars.")

    html = ""
    with open(args.html, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    names = parse_list_names(html)
    unique_names = []
    seen = set()
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_names.append(name)

    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = get_postgrest_headers(service_key)

    if args.reset:
        delete_existing_sources(base_url, headers, SOURCE_NAME)
    restaurants = fetch_restaurants(base_url, headers)

    matched = 0
    unmatched = []
    rows = []

    for name in unique_names:
        match, score = match_name(name, restaurants)
        if not match or score < args.threshold:
            unmatched.append((score, name, match["name"] if match else None))
            continue
        rows.append(
            {
                "restaurant_id": match["id"],
                "source_name": SOURCE_NAME,
                "source_url": None,
                "status": "halal_listed",
                "evidence_snippet": "Google Maps list import",
                "confidence": round(score, 3),
            }
        )
        matched += 1

    if rows:
        unique_rows = {}
        for row in rows:
            key = (row["restaurant_id"], row["source_name"])
            unique_rows[key] = row
        upsert_halal_sources(base_url, headers, list(unique_rows.values()))

    print(f"List entries: {len(unique_names)}")
    print(f"Matched: {matched}")
    print(f"Unmatched: {len(unmatched)}")
    if unmatched:
        unmatched.sort(reverse=True, key=lambda x: x[0])
        print("Top unmatched examples:")
        for score, name, best in unmatched[:15]:
            print(f"{score:.2f} | {name} | best: {best}")


if __name__ == "__main__":
    main()
