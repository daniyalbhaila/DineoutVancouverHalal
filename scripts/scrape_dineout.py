import csv
import json
import re
import time
from html import unescape
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


BASE_URL = "https://www.dineoutvancouver.com"
API_FIND = urljoin(BASE_URL, "/includes/rest_v2/plugins_listings_listings/find/")
TOKEN = "e7496507047ac9fb349e1e32b0e8dd33"

LISTING_FILTER = {
    "categories.subcatid": {"$eq": 4204},
    "$and": [
        {
            "$or": [
                {"amenities.dineoutbreakfastbrunchmenu_enablemenu.value_raw": True},
                {"amenities.dineout_enablemenu.value_raw": True},
                {"amenities.dineoutlunchmenu_enablemenu.value_raw": True},
                {"amenities.dineoutbreakfastmenu_enablemenu.value_raw": True},
                {"amenities.dineouttogo_enablemenu.value_raw": True},
                {"amenities.dineoutspecialoffer_enablemenu.value_raw": True},
            ]
        }
    ],
    "amenities_array.amenitytabid": {"$in": [1007, 1008, 1009, 1011]},
}

DEFAULT_HOOKS = ["afterFind_offers"]

COURSE_KEYWORDS = [
    "appetizer",
    "starter",
    "soup",
    "salad",
    "entree",
    "main",
    "mains",
    "dessert",
    "desserts",
    "course",
    "courses",
    "brunch",
    "lunch",
    "dinner",
    "sides",
    "small plates",
    "large plates",
    "pasta",
    "pizza",
    "vegetarian",
    "vegan",
]

NOTES_REGEX = re.compile(r"\b(GF|V|VG|DF|Vegan|Vegetarian|Gluten[- ]?Free|Halal)\b", re.I)
PRICE_REGEX = re.compile(r"\$\s*\d+(?:\.\d{1,2})?")
SLASH_SPLIT_REGEX = re.compile(r"\s*/\s*")


def fetch_url(url, timeout=30):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def api_find(filter_obj, options):
    payload = {
        "json": json.dumps({"filter": filter_obj, "options": options}),
        "token": TOKEN,
    }
    url = API_FIND + "?" + urlencode(payload)
    raw = fetch_url(url)
    return json.loads(raw)


def get_restaurants():
    listings = []
    skip = 0
    limit = 200
    while True:
        options = {
            "limit": limit,
            "skip": skip,
            "fields": {"detailURL": 1, "title": 1},
            "count": True,
            "castDocs": False,
            "hooks": DEFAULT_HOOKS,
        }
        res = api_find(LISTING_FILTER, options)
        docs = res.get("docs", {}).get("docs", [])
        count = res.get("docs", {}).get("count", 0)
        if not docs:
            break
        listings.extend(docs)
        skip += limit
        if skip >= count:
            break
    return listings


def clean_text(text):
    if text is None:
        return ""
    text = unescape(text)
    text = text.replace("\u00a0", " ")
    return text.strip()


def compact_text(text):
    return " ".join(text.split()).strip()


def extract_notes(text):
    if not text:
        return ""
    notes = NOTES_REGEX.findall(text)
    if not notes:
        return ""
    return ", ".join(sorted(set([n.upper() if len(n) <= 3 else n for n in notes])))


def split_text_blocks(lines):
    blocks = []
    current = []
    for line in lines:
        norm = line.strip().lower()
        if is_or_separator(line):
            if current:
                blocks.append(current)
                current = []
            continue
        if norm in {"-or-", "- or -", "or-", "-or"}:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def split_dish_from_lines(lines):
    if not lines:
        return "", ""
    if len(lines) == 1:
        line = lines[0]
        if "/" in line and "http" not in line:
            parts = [part.strip() for part in SLASH_SPLIT_REGEX.split(line) if part.strip()]
            if len(parts) > 1:
                return None, parts
        for sep in [" - ", ": "]:
            if sep in line:
                name, desc = line.split(sep, 1)
                return name.strip(), desc.strip()
        return line.strip(), ""
    name = lines[0].strip()
    desc = " ".join([ln.strip() for ln in lines[1:] if ln.strip()])
    return name, desc


def parse_dish_text(raw_text):
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    blocks = split_text_blocks(lines)
    dishes = []
    for block in blocks:
        name, desc_or_list = split_dish_from_lines(block)
        if name is None and isinstance(desc_or_list, list):
            for opt in desc_or_list:
                dishes.append((opt, ""))
        else:
            dishes.append((name, desc_or_list))
    return dishes


def parse_menu_info(dineout_menu):
    info = {}
    for field in dineout_menu.select("div.dineout-menu-section.dineout-menu-info span.dineout-menu-field"):
        label_el = field.select_one(".dineout-label")
        value_el = field.select_one(".dineout-value")
        if not label_el or not value_el:
            continue
        label = clean_text(label_el.get_text(" "))
        label = label.rstrip(":")
        value = clean_text(value_el.get_text(" "))
        info[label] = value
    return info


def find_menu_price(menu_info):
    for key, val in menu_info.items():
        if "price for this menu" in key.lower():
            return val
    for key, val in menu_info.items():
        if "menu price" in key.lower():
            return val
    return ""


def is_course_heading(line):
    if not line:
        return False
    lower = line.lower().strip().rstrip(":")
    if "$" in lower or "per person" in lower or "wine pairing" in lower:
        return False
    if any(word in lower for word in COURSE_KEYWORDS):
        return len(lower.split()) <= 3
    if lower.endswith(":") and len(lower) <= 60:
        return True
    if line.isupper() and len(line) <= 40:
        return True
    return False


def is_non_ascii(text):
    return bool(re.search(r"[^\x00-\x7F]", text))


def split_alt_blocks(lines):
    blocks = []
    current = []
    for line in lines:
        if line.lower().startswith("dine out vancouver"):
            if current:
                blocks.append(current)
            current = [line]
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks or [lines]


def extract_block_price(lines):
    for line in lines:
        lower = line.lower()
        if "per person" in lower or "per menu" in lower:
            match = PRICE_REGEX.search(line)
            if match:
                return match.group(0)
    return ""


def is_ignorable_line(line):
    lower = line.lower()
    if lower.startswith("dine out vancouver"):
        return True
    if "wine pairing" in lower:
        return True
    if "per glass" in lower:
        return True
    if "taxes not included" in lower:
        return True
    if re.search(r"\b\d{4}\b", line) and "-" in line:
        return True
    if re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b", lower):
        return True
    return False


def is_or_separator(line):
    lower = line.lower().strip()
    if lower in {"or", "-or-"}:
        return True
    if lower.startswith("or "):
        return True
    if lower.startswith("or") and is_non_ascii(line[2:]):
        return True
    return False


def parse_alt_menu_text(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = []

    for block in split_alt_blocks(lines):
        block_price = extract_block_price(block)
        course = "Unspecified"
        current_name = None
        current_desc = []
        pending_split = None

        def flush_current():
            nonlocal current_name, current_desc
            if current_name:
                desc = " ".join(current_desc).strip()
                raw = "\n".join([current_name] + current_desc).strip()
                rows.append((block_price, course, current_name, desc, extract_notes(raw), raw))
            current_name = None
            current_desc = []

        for line in block:
            if is_ignorable_line(line):
                continue
            if is_or_separator(line):
                flush_current()
                pending_split = None
                continue

            if is_course_heading(line):
                flush_current()
                course = line.rstrip(":").strip()
                continue

            match = re.match(r"^[A-D]\)\s*(.+)", line)
            if match:
                flush_current()
                current_name = match.group(1).strip()
                continue

            if "/" in line and not is_non_ascii(line):
                flush_current()
                parts = [p.strip() for p in SLASH_SPLIT_REGEX.split(line) if p.strip()]
                pending_split = parts
                continue

            if pending_split and is_non_ascii(line) and "/" in line:
                desc_parts = [p.strip() for p in SLASH_SPLIT_REGEX.split(line) if p.strip()]
                if len(desc_parts) == len(pending_split):
                    for name, desc in zip(pending_split, desc_parts):
                        raw = "\n".join([name, desc]).strip()
                        rows.append((block_price, course, name, desc, extract_notes(raw), raw))
                    pending_split = None
                    continue

            if pending_split:
                for name in pending_split:
                    raw = name
                    rows.append((block_price, course, name, "", extract_notes(raw), raw))
                pending_split = None

            if current_name is None:
                current_name = line
            else:
                current_desc.append(line)

        if pending_split:
            for name in pending_split:
                raw = name
                rows.append((block_price, course, name, "", extract_notes(raw), raw))
            pending_split = None
        if current_name:
            desc = " ".join(current_desc).strip()
            raw = "\n".join([current_name] + current_desc).strip()
            rows.append((block_price, course, current_name, desc, extract_notes(raw), raw))

    return rows


def parse_menu_sections(dineout_menu):
    rows = []
    sections = dineout_menu.select("div.menu-section")
    structured_sections = [s for s in sections if "alt-menu" not in (s.get("class") or [])]
    for section in structured_sections:
        course_name = ""
        prev = section.find_previous_sibling()
        while prev and prev.name not in {"h3", "h4", "h5"}:
            prev = prev.find_previous_sibling()
        if prev and prev.name in {"h3", "h4", "h5"}:
            course_name = clean_text(prev.get_text(" "))
        dish_nodes = section.select("span.dineout-menu-field > span.dineout-value")
        if not dish_nodes:
            dish_nodes = section.select("span.dineout-value")
        for node in dish_nodes:
            raw_text = clean_text(node.get_text("\n"))
            if not raw_text:
                continue
            for dish_name, dish_desc in parse_dish_text(raw_text):
                raw = raw_text
                notes = extract_notes(raw)
                rows.append((course_name, dish_name, dish_desc, notes, raw))

    if not rows:
        alt = dineout_menu.select_one("div.menu-section.alt-menu span.dineout-value")
        if alt:
            raw_text = clean_text(alt.get_text("\n"))
            rows.extend(parse_alt_menu_text(raw_text))
    return rows


def extract_menu_raw_text(dineout_menu):
    alt = dineout_menu.select_one("div.menu-section.alt-menu span.dineout-value")
    if alt:
        return clean_text(alt.get_text("\n"))
    clone = BeautifulSoup(str(dineout_menu), "html.parser")
    for node in clone.select("div.dineout-menu-section.dineout-menu-info"):
        node.decompose()
    for node in clone.select("div.sep-line"):
        node.decompose()
    return clean_text(clone.get_text("\n"))


def extract_menu_blocks(dineout_menu):
    alt = dineout_menu.select_one("div.menu-section.alt-menu span.dineout-value")
    if alt:
        raw_text = clean_text(alt.get_text("\n"))
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        blocks = split_alt_blocks(lines)
        results = []
        for idx, block in enumerate(blocks, start=1):
            block_price = extract_block_price(block)
            block_text = "\n".join(block).strip()
            results.append((idx, block_price, block_text))
        return results
    return [(1, None, extract_menu_raw_text(dineout_menu))]


def parse_restaurant(html, restaurant_name, restaurant_url):
    soup = BeautifulSoup(html, "html.parser")
    menu_rows = []
    menu_blocks = []
    for menu_tab in soup.select("li.content.menu"):
        menu_title_el = menu_tab.find("h3")
        menu_title = clean_text(menu_title_el.get_text(" ")) if menu_title_el else ""
        dineout_menu = menu_tab.select_one("div.dineout-menu")
        if not dineout_menu:
            continue
        menu_info = parse_menu_info(dineout_menu)
        menu_price = find_menu_price(menu_info)
        for block_idx, block_price, block_text in extract_menu_blocks(dineout_menu):
            menu_blocks.append(
                {
                    "restaurant_name": restaurant_name,
                    "restaurant_page_url": restaurant_url,
                    "menu_title": menu_title,
                    "menu_variant": str(block_idx),
                    "menu_price": block_price or menu_price,
                    "currency": "CAD",
                    "menu_raw_text": block_text,
                }
            )
        course_rows = parse_menu_sections(dineout_menu)
        for course_row in course_rows:
            if len(course_row) == 5:
                course_name, dish_name, dish_desc, notes, raw = course_row
                row_price = menu_price
            else:
                row_price, course_name, dish_name, dish_desc, notes, raw = course_row
                if not row_price:
                    row_price = menu_price
            menu_rows.append(
                {
                    "restaurant_name": restaurant_name,
                    "restaurant_page_url": restaurant_url,
                    "menu_title": menu_title,
                    "menu_price": row_price,
                    "currency": "CAD",
                    "course_name": course_name,
                    "dish_name": dish_name,
                    "dish_description": dish_desc,
                    "notes_raw": notes,
                    "raw_text": raw,
                }
            )
    return menu_rows, menu_blocks


def main():
    restaurants = get_restaurants()
    rows = []
    menu_blocks = []
    for idx, item in enumerate(restaurants, start=1):
        title = item.get("title", "").strip()
        detail_url = item.get("detailURL", "")
        if not detail_url:
            continue
        full_url = urljoin(BASE_URL, detail_url)
        html = fetch_url(full_url)
        menu_rows, menu_block_rows = parse_restaurant(html, title, full_url)
        rows.extend(menu_rows)
        menu_blocks.extend(menu_block_rows)
        if idx % 25 == 0:
            print(f"Fetched {idx}/{len(restaurants)} restaurants...")
        time.sleep(0.2)

    with open("data/dineout_menus_long.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "restaurant_name",
                "restaurant_page_url",
                "menu_title",
                "menu_price",
                "currency",
                "course_name",
                "dish_name",
                "dish_description",
                "notes_raw",
                "raw_text",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    with open("data/dineout_menus_raw.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "restaurant_name",
                "restaurant_page_url",
                "menu_title",
                "menu_variant",
                "menu_price",
                "currency",
                "menu_raw_text",
            ],
        )
        writer.writeheader()
        writer.writerows(menu_blocks)

    print(f"Wrote {len(rows)} rows to data/dineout_menus_long.csv")
    print(f"Wrote {len(menu_blocks)} rows to data/dineout_menus_raw.csv")


if __name__ == "__main__":
    main()
