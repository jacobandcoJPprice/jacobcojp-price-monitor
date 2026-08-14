import asyncio
import csv
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"
START_URL = "https://jacobandco.shop/pages/collections"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(BASE_DIR, "jewelry_current_prices.csv")
PRICE_HISTORY_CSV = os.path.join(BASE_DIR, "jewelry_price_history.csv")
CHANGE_HISTORY_CSV = os.path.join(BASE_DIR, "jewelry_change_history.csv")
MISSING_CANDIDATES_CSV = os.path.join(BASE_DIR, "jewelry_missing_candidates.csv")

MIN_COLLECTIONS = 30
MIN_VARIANTS = 620
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
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def normalize_collection_url(url):
    if not url:
        return ""

    url = urljoin(BASE_URL, url)
    parsed = urlparse(url)

    if parsed.netloc != "jacobandco.shop":
        return ""

    path = parsed.path.rstrip("/")

    if not path.startswith("/collections/"):
        return ""

    if path == "/collections/all":
        return ""

    return BASE_URL + path


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


async def discover_collections(page):
    print()
    print("=" * 70)
    print("DISCOVERING SHOP COLLECTIONS")
    print("=" * 70)

    response = await page.goto(
        START_URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    if response:
        print("HTTP status:", response.status)

    await page.wait_for_timeout(3000)

    links = await page.locator("a").evaluate_all(
        """
        els => els.map(a => ({
            href: a.href || "",
            text: (a.innerText || "").trim()
        }))
        """
    )

    collections = {}

    for link in links:
        url = normalize_collection_url(
            link.get("href", "")
        )

        if not url:
            continue

        name = (
            link.get("text", "")
            .replace("\\n", " ")
            .strip()
        )

        if url not in collections:
            collections[url] = name

    print("Collections found:", len(collections))
    return collections


async def fetch_collection_products(
    request_context,
    collection_url,
    collection_name
):
    parsed = urlparse(collection_url)

    handle = (
        parsed.path
        .rstrip("/")
        .split("/")[-1]
    )

    api_url = (
        BASE_URL
        + "/collections/"
        + handle
        + "/products.json?limit=250"
    )

    response = await request_context.get(
        api_url,
        timeout=60000
    )

    if not response.ok:
        raise RuntimeError(
            f"{collection_name or handle}: "
            f"HTTP {response.status}"
        )

    data = await response.json()
    products = data.get("products", [])

    if not isinstance(products, list):
        return []

    return products


async def scrape_current_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            locale="en-US"
        )

        page = await context.new_page()

        collections = await discover_collections(page)

        if len(collections) < MIN_COLLECTIONS:
            await browser.close()
            raise RuntimeError(
                "SAFETY STOP: "
                f"only {len(collections)} collections found."
            )

        product_map = {}
        failed_count = 0

        print()
        print("=" * 70)
        print("READING SHOPIFY COLLECTION DATA")
        print("=" * 70)

        for collection_url, collection_name in sorted(
            collections.items()
        ):
            try:
                products = await fetch_collection_products(
                    context.request,
                    collection_url,
                    collection_name
                )

                print(
                    collection_name or collection_url,
                    ":",
                    len(products)
                )

            except Exception as e:
                failed_count += 1
                print(
                    "COLLECTION ERROR:",
                    collection_name,
                    repr(e)
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
                        "collections": set()
                    }

                product_map[product_id]["collections"].add(
                    collection_name or collection_url
                )

        await browser.close()

    if failed_count > 0:
        raise RuntimeError(
            "SAFETY STOP: "
            f"{failed_count} collection API calls failed."
        )

    rows = []

    for product_id, info in product_map.items():
        product = info["product"]

        title = str(product.get("title", "")).strip()
        handle = str(product.get("handle", "")).strip()
        vendor = str(product.get("vendor", "")).strip()

        product_type = str(
            product.get(
                "product_type",
                product.get("type", "")
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
                "Last Seen": now()
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
            row.get("Unique Key", "").lower()
        )
    )

    if len(rows) < MIN_VARIANTS:
        raise RuntimeError(
            "SAFETY STOP: "
            f"only {len(rows)} variants found."
        )

    return collections, product_map, rows


def detect_price_changes(
    old_rows,
    new_rows,
    history
):
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
            "URL": row.get("URL", "")
        }

        history.append(event)
        changes.append(event)

    return changes


def detect_structure_changes(
    old_rows,
    new_rows,
    change_history,
    missing_candidates
):
    events = []

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
                row.get("Consecutive Misses", 0)
                or 0
            )
        except Exception:
            misses = 0

        missing_map[key] = {
            "Unique Key": key,
            "Consecutive Misses": misses,
            "First Missing At": str(
                row.get("First Missing At", "")
            ).strip(),
            "Last Missing At": str(
                row.get("Last Missing At", "")
            ).strip()
        }

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
            "URL": row.get("URL", "")
        }

        change_history.append(event)
        events.append(event)

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
            "URL": new.get("URL", "")
        }

        change_history.append(event)
        events.append(event)

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
            "Last Missing At": current_time
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
            "URL": old.get("URL", "")
        }

        change_history.append(event)
        events.append(event)

    for key in list(missing_map.keys()):
        if key in new_keys:
            del missing_map[key]

    updated_missing = sorted(
        missing_map.values(),
        key=lambda row: row["Unique Key"]
    )

    return events, updated_missing


async def main():
    print()
    print("=" * 70)
    print("JACOB & CO. USA JEWELRY MONITOR")
    print("=" * 70)

    old_rows = read_csv(CURRENT_CSV)

    price_history = read_csv(
        PRICE_HISTORY_CSV
    )

    change_history = read_csv(
        CHANGE_HISTORY_CSV
    )

    missing_candidates = read_csv(
        MISSING_CANDIDATES_CSV
    )

    print()
    print(
        "Previous variants:",
        len(old_rows)
    )

    print(
        "Previous price history:",
        len(price_history)
    )

    print(
        "Previous change history:",
        len(change_history)
    )

    collections, product_map, new_rows = (
        await scrape_current_state()
    )

    print()
    print("=" * 70)
    print("CURRENT SHOP STATE")
    print("=" * 70)

    print(
        "Collections:",
        len(collections)
    )

    print(
        "Unique products:",
        len(product_map)
    )

    print(
        "Variants:",
        len(new_rows)
    )

    print(
        "With SKU:",
        sum(
            1
            for row in new_rows
            if row.get("SKU", "")
        )
    )

    print(
        "With price:",
        sum(
            1
            for row in new_rows
            if row.get("Price", "")
        )
    )

    price_changes = detect_price_changes(
        old_rows,
        new_rows,
        price_history
    )

    (
        structure_changes,
        missing_candidates
    ) = detect_structure_changes(
        old_rows,
        new_rows,
        change_history,
        missing_candidates
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
        "Last Seen"
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
        "URL"
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
        "URL"
    ]

    missing_fields = [
        "Unique Key",
        "Consecutive Misses",
        "First Missing At",
        "Last Missing At"
    ]

    write_csv(
        CURRENT_CSV,
        current_fields,
        new_rows
    )

    write_csv(
        PRICE_HISTORY_CSV,
        price_history_fields,
        price_history
    )

    write_csv(
        CHANGE_HISTORY_CSV,
        change_history_fields,
        change_history
    )

    write_csv(
        MISSING_CANDIDATES_CSV,
        missing_fields,
        missing_candidates
    )

    print()
    print("=" * 70)
    print("JEWELRY MONITOR COMPLETED")
    print("=" * 70)

    print(
        "Current variants       :",
        len(new_rows)
    )

    print(
        "Price changes          :",
        len(price_changes)
    )

    print(
        "Structure changes      :",
        len(structure_changes)
    )

    print(
        "Price history rows     :",
        len(price_history)
    )

    print(
        "Change history rows    :",
        len(change_history)
    )

    print(
        "Pending missing items  :",
        len(missing_candidates)
    )

    print("=" * 70)

    if not old_rows:
        print()
        print("BASELINE CREATED.")
        print(
            "First run does NOT count "
            "all current products as NEW ITEM."
        )


if __name__ == "__main__":
    asyncio.run(main())
