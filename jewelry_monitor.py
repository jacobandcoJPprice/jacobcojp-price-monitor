import asyncio
import csv
import os
from datetime import datetime

from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"

# ONLY the collections visibly listed on:
# https://jacobandco.shop/pages/collections
COLLECTIONS = [
    ("Jacob & Co. X PEACEMINUSONE", "g-dragon-peaceminusone-collection"),
    ("Love Lockdown", "love-lockdown"),
    ("Evil Eye", "evil-eye"),
    ("Lucky You", "lucky-you"),
    ("Infinia", "the-infinia-collection"),
    ("Jezebel", "jezebel"),
    ("Rare Touch", "rare-touch"),
    ("Securus", "securus"),
    ("Office Supplies By Virgil Abloh", "office-supplies"),
    ("Match Collection", "matchstick-collection"),
    ("Estribo", "estribo"),
    ("Cuban Link", "cuban-link"),
    ("Carabin", "carabin"),
    ("Cufflinks", "cufflinks"),
    ("Espada", "espada"),
    ("Super Arrow", "super-arrow"),
    ("Papillon", "papillon"),
    ("Hematite", "hematite"),
    ("Jacob's Code", "jacobs-code"),
    ("Sharq", "sharq"),
    ("Spread The Love", "the-spread-the-love-collection"),
    ("You Are You", "you-are-you"),
    ("Taken", "taken"),
    ("Zodiac", "zodiac-sign"),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(BASE_DIR, "jewelry_current_prices.csv")
PRICE_HISTORY_CSV = os.path.join(BASE_DIR, "jewelry_price_history.csv")
CHANGE_HISTORY_CSV = os.path.join(BASE_DIR, "jewelry_change_history.csv")
MISSING_CANDIDATES_CSV = os.path.join(BASE_DIR, "jewelry_missing_candidates.csv")

# Validated baseline from the audit:
# 24 collections / 298 unique products / 519 variants.
MIN_COLLECTIONS = 24
MIN_PRODUCTS = 280
MIN_VARIANTS = 490

REMOVED_CONFIRM_RUNS = 2


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_csv(path):
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def normalize_price(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = (
        value
        .replace("$", "")
        .replace(",", "")
        .strip()
    )

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def clean_price(value):
    number = normalize_price(value)

    if number is None:
        return ""

    if float(number).is_integer():
        return str(int(number))

    return f"{number:.2f}".rstrip("0").rstrip(".")


def build_current_map(rows):
    result = {}

    for row in rows:
        key = str(row.get("Unique Key", "")).strip()

        if key:
            result[key] = row

    return result


async def fetch_collection_products(request_context, collection_name, handle):
    api_url = (
        f"{BASE_URL}/collections/{handle}"
        "/products.json?limit=250"
    )

    response = await request_context.get(
        api_url,
        timeout=60000,
    )

    if not response.ok:
        raise RuntimeError(
            f"{collection_name}: HTTP {response.status}"
        )

    data = await response.json()
    products = data.get("products", [])

    if not isinstance(products, list):
        return []

    return products


async def scrape_current_state():
    print()
    print("=" * 70)
    print("READING VISIBLE JEWELRY COLLECTIONS")
    print("=" * 70)

    product_map = {}
    success_count = 0
    failed_count = 0

    async with async_playwright() as p:
        request = await p.request.new_context(
            extra_http_headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/151 Safari/537.36"
                )
            }
        )

        for index, (name, handle) in enumerate(COLLECTIONS, start=1):
            try:
                products = await fetch_collection_products(
                    request,
                    name,
                    handle,
                )

                success_count += 1

                print(
                    f"{index:02d}. "
                    f"{name:<34} "
                    f"{len(products):>3} products"
                )

            except Exception as e:
                failed_count += 1

                print(
                    f"{index:02d}. "
                    f"{name:<34} "
                    f"ERROR {e!r}"
                )

                continue

            for product in products:
                product_id = str(
                    product.get("id", "")
                ).strip()

                if not product_id:
                    continue

                if product_id not in product_map:
                    product_map[product_id] = {
                        "product": product,
                        "collections": set(),
                    }

                product_map[
                    product_id
                ][
                    "collections"
                ].add(name)

        await request.dispose()

    if success_count < MIN_COLLECTIONS:
        raise RuntimeError(
            "SAFETY STOP: "
            f"only {success_count}/{MIN_COLLECTIONS} "
            "collections succeeded."
        )

    if failed_count > 0:
        raise RuntimeError(
            "SAFETY STOP: "
            f"{failed_count} collection calls failed."
        )

    if len(product_map) < MIN_PRODUCTS:
        raise RuntimeError(
            "SAFETY STOP: "
            f"only {len(product_map)} unique products found."
        )

    rows = []

    for product_id, info in product_map.items():
        product = info["product"]

        title = str(
            product.get("title", "")
        ).strip()

        handle = str(
            product.get("handle", "")
        ).strip()

        vendor = str(
            product.get("vendor", "")
        ).strip()

        product_type = str(
            product.get(
                "product_type",
                product.get("type", ""),
            )
        ).strip()

        collections_text = " | ".join(
            sorted(info["collections"])
        )

        product_url = (
            BASE_URL
            + "/products/"
            + handle
        )

        variants = product.get("variants", [])

        if not isinstance(variants, list):
            continue

        for variant in variants:
            if not isinstance(variant, dict):
                continue

            variant_id = str(
                variant.get("id", "")
            ).strip()

            sku = str(
                variant.get("sku", "")
                or ""
            ).strip()

            variant_title = str(
                variant.get("title", "")
                or ""
            ).strip()

            price = clean_price(
                variant.get("price")
            )

            compare_at_price = clean_price(
                variant.get("compare_at_price")
            )

            available = bool(
                variant.get("available", False)
            )

            option1 = str(
                variant.get("option1", "")
                or ""
            ).strip()

            option2 = str(
                variant.get("option2", "")
                or ""
            ).strip()

            option3 = str(
                variant.get("option3", "")
                or ""
            ).strip()

            if sku:
                unique_key = "SKU:" + sku
            elif variant_id:
                unique_key = "VARIANT:" + variant_id
            else:
                unique_key = (
                    "PRODUCT:"
                    + product_id
                    + ":"
                    + variant_title
                )

            rows.append({
                "Unique Key": unique_key,
                "Product ID": product_id,
                "Variant ID": variant_id,
                "SKU": sku,
                "Product": title,
                "Variant": variant_title,
                "Product Type": product_type,
                "Vendor": vendor,
                "Collections": collections_text,
                "Price": price,
                "Compare At Price": compare_at_price,
                "Currency": "USD",
                "Available": "YES" if available else "NO",
                "Option 1": option1,
                "Option 2": option2,
                "Option 3": option3,
                "Handle": handle,
                "URL": product_url,
                "Last Seen": now(),
            })

    unique_rows = {}

    for row in rows:
        key = row.get("Unique Key", "")

        if key:
            unique_rows[key] = row

    rows = list(unique_rows.values())

    rows.sort(
        key=lambda row: (
            row.get("Product", "").lower(),
            row.get("Variant", "").lower(),
            row.get("Unique Key", "").lower(),
        )
    )

    if len(rows) < MIN_VARIANTS:
        raise RuntimeError(
            "SAFETY STOP: "
            f"only {len(rows)} variants found."
        )

    return product_map, rows


def detect_price_changes(old_rows, new_rows, history):
    changes = []

    if not old_rows:
        return changes

    old_map = build_current_map(old_rows)

    for row in new_rows:
        key = row["Unique Key"]

        old = old_map.get(key)

        if not old:
            continue

        old_price = normalize_price(
            old.get("Price", "")
        )

        new_price = normalize_price(
            row.get("Price", "")
        )

        if old_price is None or new_price is None:
            continue

        if old_price == new_price:
            continue

        event = {
            "Changed At": now(),
            "Unique Key": key,
            "SKU": row.get("SKU", ""),
            "Variant ID": row.get("Variant ID", ""),
            "Product": row.get("Product", ""),
            "Variant": row.get("Variant", ""),
            "Old Price": clean_price(old_price),
            "New Price": clean_price(new_price),
            "Currency": "USD",
            "URL": row.get("URL", ""),
        }

        history.append(event)
        changes.append(event)

    return changes


def detect_structure_changes(
    old_rows,
    new_rows,
    change_history,
    missing_candidates,
):
    events = []

    # First successful run only establishes baseline.
    if not old_rows:
        return events, []

    old_map = build_current_map(old_rows)
    new_map = build_current_map(new_rows)

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    missing_map = {}

    for row in missing_candidates:
        key = str(
            row.get("Unique Key", "")
        ).strip()

        if not key:
            continue

        try:
            misses = int(
                row.get(
                    "Consecutive Misses",
                    0,
                )
                or 0
            )
        except Exception:
            misses = 0

        missing_map[key] = {
            "Unique Key": key,
            "Consecutive Misses": misses,
            "First Missing At": str(
                row.get(
                    "First Missing At",
                    "",
                )
            ).strip(),
            "Last Missing At": str(
                row.get(
                    "Last Missing At",
                    "",
                )
            ).strip(),
        }

    # New variant
    for key in sorted(new_keys - old_keys):
        row = new_map[key]

        event = {
            "Changed At": now(),
            "Change Type": "NEW ITEM",
            "Unique Key": key,
            "SKU": row.get("SKU", ""),
            "Variant ID": row.get("Variant ID", ""),
            "Product": row.get("Product", ""),
            "Variant": row.get("Variant", ""),
            "Old Status": "",
            "New Status": row.get("Available", ""),
            "Price": row.get("Price", ""),
            "URL": row.get("URL", ""),
        }

        change_history.append(event)
        events.append(event)

    # Availability change
    for key in sorted(old_keys & new_keys):
        old = old_map[key]
        new = new_map[key]

        old_status = str(
            old.get("Available", "")
        ).strip()

        new_status = str(
            new.get("Available", "")
        ).strip()

        if old_status == new_status:
            continue

        event = {
            "Changed At": now(),
            "Change Type": "STATUS CHANGE",
            "Unique Key": key,
            "SKU": new.get("SKU", ""),
            "Variant ID": new.get("Variant ID", ""),
            "Product": new.get("Product", ""),
            "Variant": new.get("Variant", ""),
            "Old Status": old_status,
            "New Status": new_status,
            "Price": new.get("Price", ""),
            "URL": new.get("URL", ""),
        }

        change_history.append(event)
        events.append(event)

    # Removed variant requires two consecutive successful scans.
    current_time = now()
    missing_now = old_keys - new_keys

    for key in sorted(missing_now):
        previous = missing_map.get(key)

        if previous:
            miss_count = (
                previous["Consecutive Misses"]
                + 1
            )

            first_missing = (
                previous["First Missing At"]
                or current_time
            )
        else:
            miss_count = 1
            first_missing = current_time

        missing_map[key] = {
            "Unique Key": key,
            "Consecutive Misses": miss_count,
            "First Missing At": first_missing,
            "Last Missing At": current_time,
        }

        if miss_count != REMOVED_CONFIRM_RUNS:
            continue

        old = old_map[key]

        event = {
            "Changed At": current_time,
            "Change Type": "REMOVED ITEM",
            "Unique Key": key,
            "SKU": old.get("SKU", ""),
            "Variant ID": old.get("Variant ID", ""),
            "Product": old.get("Product", ""),
            "Variant": old.get("Variant", ""),
            "Old Status": old.get("Available", ""),
            "New Status": "NOT FOUND (2 RUNS)",
            "Price": old.get("Price", ""),
            "URL": old.get("URL", ""),
        }

        change_history.append(event)
        events.append(event)

    # If item comes back, cancel pending removal state.
    for key in list(missing_map.keys()):
        if key in new_keys:
            del missing_map[key]

    updated_missing = sorted(
        missing_map.values(),
        key=lambda row: row["Unique Key"],
    )

    return events, updated_missing


async def main():
    print()
    print("=" * 70)
    print(
        "JACOB & CO. USA "
        "VISIBLE COLLECTIONS MONITOR"
    )
    print("=" * 70)

    old_rows = read_csv(CURRENT_CSV)
    price_history = read_csv(PRICE_HISTORY_CSV)
    change_history = read_csv(CHANGE_HISTORY_CSV)
    missing_candidates = read_csv(MISSING_CANDIDATES_CSV)

    print()
    print(
        "Expected collections:",
        len(COLLECTIONS),
    )

    print(
        "Previous variants:",
        len(old_rows),
    )

    print(
        "Previous price history:",
        len(price_history),
    )

    print(
        "Previous change history:",
        len(change_history),
    )

    product_map, new_rows = await scrape_current_state()

    print()
    print("=" * 70)
    print("CURRENT COLLECTION STATE")
    print("=" * 70)

    print(
        "Collections:",
        len(COLLECTIONS),
    )

    print(
        "Unique products:",
        len(product_map),
    )

    print(
        "Variants:",
        len(new_rows),
    )

    print(
        "With SKU:",
        sum(
            1
            for row in new_rows
            if row.get("SKU", "")
        ),
    )

    print(
        "With price:",
        sum(
            1
            for row in new_rows
            if row.get("Price", "")
        ),
    )

    price_changes = detect_price_changes(
        old_rows,
        new_rows,
        price_history,
    )

    (
        structure_changes,
        missing_candidates,
    ) = detect_structure_changes(
        old_rows,
        new_rows,
        change_history,
        missing_candidates,
    )

    current_fields = [
        "Unique Key",
        "Product ID",
        "Variant ID",
        "SKU",
        "Product",
        "Variant",
        "Product Type",
        "Vendor",
        "Collections",
        "Price",
        "Compare At Price",
        "Currency",
        "Available",
        "Option 1",
        "Option 2",
        "Option 3",
        "Handle",
        "URL",
        "Last Seen",
    ]

    price_history_fields = [
        "Changed At",
        "Unique Key",
        "SKU",
        "Variant ID",
        "Product",
        "Variant",
        "Old Price",
        "New Price",
        "Currency",
        "URL",
    ]

    change_history_fields = [
        "Changed At",
        "Change Type",
        "Unique Key",
        "SKU",
        "Variant ID",
        "Product",
        "Variant",
        "Old Status",
        "New Status",
        "Price",
        "URL",
    ]

    missing_fields = [
        "Unique Key",
        "Consecutive Misses",
        "First Missing At",
        "Last Missing At",
    ]

    write_csv(
        CURRENT_CSV,
        current_fields,
        new_rows,
    )

    write_csv(
        PRICE_HISTORY_CSV,
        price_history_fields,
        price_history,
    )

    write_csv(
        CHANGE_HISTORY_CSV,
        change_history_fields,
        change_history,
    )

    write_csv(
        MISSING_CANDIDATES_CSV,
        missing_fields,
        missing_candidates,
    )

    print()
    print("=" * 70)
    print("JEWELRY MONITOR COMPLETED")
    print("=" * 70)

    print(
        "Current products       :",
        len(product_map),
    )

    print(
        "Current variants       :",
        len(new_rows),
    )

    print(
        "Price changes          :",
        len(price_changes),
    )

    print(
        "Structure changes      :",
        len(structure_changes),
    )

    print(
        "Price history rows     :",
        len(price_history),
    )

    print(
        "Change history rows    :",
        len(change_history),
    )

    print(
        "Pending missing items  :",
        len(missing_candidates),
    )

    print("=" * 70)

    if not old_rows:
        print()
        print("BASELINE CREATED.")
        print(
            "Existing products are NOT "
            "counted as NEW ITEM."
        )


if __name__ == "__main__":
    asyncio.run(main())
