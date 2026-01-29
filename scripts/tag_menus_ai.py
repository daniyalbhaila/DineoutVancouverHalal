import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import requests


DEFAULT_MODEL = "gpt-4o"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
TAG_VALUES = {"yes", "no", "uncertain"}
COURSE_VALUES = {"none", "some", "most", "all"}


def openai_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def supabase_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def fetch_all_menus(base_url: str, headers: Dict[str, str]) -> List[dict]:
    results = []
    offset = 0
    limit = 1000
    while True:
        url = f"{base_url}/menus?select=id,menu_raw_text,restaurant_id&limit={limit}&offset={offset}"
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        batch = resp.json()
        results.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return results


def fetch_existing_tags(base_url: str, headers: Dict[str, str], model: str) -> set:
    results = set()
    offset = 0
    limit = 1000
    while True:
        url = f"{base_url}/menu_tags?select=menu_id,model&limit={limit}&offset={offset}"
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        batch = resp.json()
        for row in batch:
            if row.get("model") == model:
                results.add(row["menu_id"])
        if len(batch) < limit:
            break
        offset += limit
    return results


def fetch_restaurants_with_sources(base_url: str, headers: Dict[str, str]) -> set:
    results = set()
    offset = 0
    limit = 1000
    while True:
        url = f"{base_url}/halal_sources?select=restaurant_id&limit={limit}&offset={offset}"
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        batch = resp.json()
        results.update(row["restaurant_id"] for row in batch if row.get("restaurant_id"))
        if len(batch) < limit:
            break
        offset += limit
    return results


def delete_existing_tags(base_url: str, headers: Dict[str, str], model: str) -> None:
    url = f"{base_url}/menu_tags?model=eq.{model}"
    resp = requests.delete(url, headers=headers, timeout=60)
    resp.raise_for_status()


def append_failure(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def call_openai(api_key: str, model: str, menu_text: str, retries: int = 3) -> dict:
    prompt = (
        "You are labeling a restaurant menu for halal-friendly filtering. "
        "Return a single JSON object with keys: "
        "contains_pork, contains_alcohol, has_seafood_option, has_vegetarian_option, "
        "course_coverage, halal_friendly_menu, halal_friendly_dishes, confidence, evidence_snippets. "
        "Each yes/no field must be one of: yes, no, uncertain. "
        "course_coverage must be one of: none, some, most, all. "
        "confidence is a number between 0 and 1. "
        "halal_friendly_dishes is an array of dish names that are seafood or vegetarian and do not include alcohol in the dish. "
        "evidence_snippets is an array of short quoted phrases from the menu text. "
        "Mark contains_pork = yes if pork or pork-derived items are listed (e.g., bacon, ham, pork belly, lard, cured meats, etc.). "
        "Mark contains_alcohol = yes if alcoholic beverages or alcohol-containing items are listed (e.g., wine/beer/spirits, cocktails, pairings, etc.). "
        "When determining has_seafood_option, has_vegetarian_option, and course_coverage, ignore dishes that include alcohol in the dish itself "
        "(e.g., beer-battered, wine sauce, sake glaze, rum/whiskey/cognac reductions). "
        "halal_friendly_menu = yes only if there is at least one seafood or vegetarian option in each course "
        "(courses may be inferred if the structure implies them) AND alcohol is not included in the menu price. "
        "If alcohol only appears in a separate pairing section or with separate per-glass pricing, treat it as not included. "
        "Pork does not disqualify halal_friendly_menu, but should set contains_pork = yes. "
        "Use uncertain if unclear. Output JSON only.\n\n"
        f"MENU TEXT:\n{menu_text}"
    )

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
    }

    last_error = None
    for attempt in range(1, retries + 1):
        resp = requests.post(OPENAI_URL, headers=openai_headers(api_key), json=payload, timeout=60)
        if resp.status_code in {429, 500, 502, 503, 504}:
            last_error = f"OpenAI error {resp.status_code}: {resp.text}"
            time.sleep(min(2 ** attempt, 10))
            continue
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        if not content:
            last_error = "Empty response from OpenAI"
            time.sleep(min(2 ** attempt, 10))
            continue
        return json.loads(content)
    raise RuntimeError(last_error or "OpenAI call failed")


def normalize_tag(value) -> str:
    if isinstance(value, str) and value.lower() in TAG_VALUES:
        return value.lower()
    return "uncertain"


def normalize_course(value):
    if isinstance(value, str) and value.lower() in COURSE_VALUES:
        return value.lower()
    return None


def normalize_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Tag menus using OpenAI.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model")
    parser.add_argument("--limit", type=int, default=None, help="Limit menus for testing")
    parser.add_argument("--reset", action="store_true", help="Delete existing tags for this model")
    parser.add_argument(
        "--include-halal-sources",
        action="store_true",
        help="Also tag restaurants that already have halal_sources entries",
    )
    parser.add_argument("--concurrency", type=int, default=10, help="Parallel OpenAI calls")
    parser.add_argument("--retries", type=int, default=3, help="Retry count for OpenAI calls")
    parser.add_argument(
        "--failures-file",
        default="data/tag_failures.json",
        help="Path to write failed menu IDs",
    )
    parser.add_argument(
        "--menu-ids-file",
        help="Optional JSONL or text file of menu_ids to tag",
    )
    parser.add_argument(
        "--tag-empty",
        action="store_true",
        help="Tag menus with empty text as uncertain",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    api_key = os.environ.get("OPENAI_API_KEY")

    if not supabase_url or not service_key or not api_key:
        raise SystemExit("Missing SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or OPENAI_API_KEY env vars.")

    base_url = supabase_url.rstrip("/") + "/rest/v1"
    headers = supabase_headers(service_key)

    if args.reset:
        delete_existing_tags(base_url, headers, args.model)
        if os.path.exists(args.failures_file):
            os.remove(args.failures_file)

    menus = fetch_all_menus(base_url, headers)
    existing = fetch_existing_tags(base_url, headers, args.model)
    halal_restaurants = (
        set()
        if args.include_halal_sources
        else fetch_restaurants_with_sources(base_url, headers)
    )

    menu_id_filter = None
    if args.menu_ids_file:
        ids = set()
        with open(args.menu_ids_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict) and "menu_id" in payload:
                        ids.add(payload["menu_id"])
                    elif isinstance(payload, str):
                        ids.add(payload)
                except json.JSONDecodeError:
                    ids.add(line)
        menu_id_filter = ids

    to_process = [
        m
        for m in menus
        if m["id"] not in existing
        and (m.get("restaurant_id") not in halal_restaurants)
        and (menu_id_filter is None or m["id"] in menu_id_filter)
    ]
    if args.limit:
        to_process = to_process[: args.limit]

    rows = []
    failures = []
    completed = 0

    def build_row(menu: dict) -> dict:
        menu_text = menu.get("menu_raw_text", "")
        if not menu_text:
            if not args.tag_empty:
                return {}
            return {
                "menu_id": menu["id"],
                "contains_pork": "uncertain",
                "contains_alcohol": "uncertain",
                "has_seafood_option": "uncertain",
                "has_vegetarian_option": "uncertain",
                "course_coverage": None,
                "halal_friendly_menu": "uncertain",
                "halal_friendly_dishes": [],
                "confidence": 0,
                "evidence_snippets": [],
                "model": args.model,
            }
        result = call_openai(api_key, args.model, menu_text, retries=args.retries)
        return {
            "menu_id": menu["id"],
            "contains_pork": normalize_tag(result.get("contains_pork")),
            "contains_alcohol": normalize_tag(result.get("contains_alcohol")),
            "has_seafood_option": normalize_tag(result.get("has_seafood_option")),
            "has_vegetarian_option": normalize_tag(result.get("has_vegetarian_option")),
            "course_coverage": normalize_course(result.get("course_coverage")),
            "halal_friendly_menu": normalize_tag(result.get("halal_friendly_menu")),
            "halal_friendly_dishes": normalize_list(result.get("halal_friendly_dishes")),
            "confidence": result.get("confidence"),
            "evidence_snippets": normalize_list(result.get("evidence_snippets")),
            "model": args.model,
        }

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        future_map = {executor.submit(build_row, menu): menu["id"] for menu in to_process}
        for future in as_completed(future_map):
            menu_id = future_map[future]
            try:
                row = future.result()
            except Exception as exc:
                failure = {"menu_id": menu_id, "error": str(exc)}
                failures.append(failure)
                append_failure(args.failures_file, failure)
                print(f"Error tagging menu {menu_id}: {exc}")
                continue

            if row:
                rows.append(row)
            completed += 1

            if len(rows) >= 25:
                url = f"{base_url}/menu_tags"
                resp = requests.post(url, headers=headers, json=rows, timeout=60)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")
                rows = []
            if completed % 10 == 0:
                print(f"Tagged {completed}/{len(to_process)} menus...")
            time.sleep(0.05)

    if rows:
        url = f"{base_url}/menu_tags"
        resp = requests.post(url, headers=headers, json=rows, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")

    if failures:
        print(f"Failures written to {args.failures_file}")

    print(f"Tagged {len(to_process)} menus.")


if __name__ == "__main__":
    main()
