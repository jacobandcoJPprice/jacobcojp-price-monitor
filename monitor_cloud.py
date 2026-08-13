import asyncio
import csv
import json
import os
from datetime import datetime
from urllib.parse import urlparse

from playwright.async_api import async_playwright


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(
    BASE_DIR,
    "current_prices.csv"
)

HISTORY_CSV = os.path.join(
    BASE_DIR,
    "price_history_v2.csv"
)

SITE_URL = "https://jacobandco.com/timepieces"

REQUEST_DELAY = 1.2


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_url(url):
    if not url:
        return ""

    url = url.split("#")[0]

    if url.endswith("/"):
        url = url[:-1]

    return url


def read_csv(path):
    if not os.path.exists(path):
        return []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, fieldnames, rows):
    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(rows)


def get_item_number(variant):
    candidates = [
        "sku",
        "itemNumber",
        "item_number",
        "mpn",
        "productID"
    ]

    for key in candidates:
        value = variant.get(key)

        if value:
            return str(value).strip()

    return ""


def get_variant_name(variant):
    for key in [
        "name",
        "model",
        "title"
    ]:

        value = variant.get(key)

        if value:
            return str(value).strip()

    url = variant.get("url", "")

    if url:
        slug = (
            urlparse(url)
            .path
            .rstrip("/")
            .split("/")[-1]
        )

        return (
            slug
            .replace("-", " ")
            .title()
        )

    return ""


def extract_offer(variant):
    offers = variant.get("offers")

    if not offers:
        return None, "", ""

    if isinstance(offers, list):
        if not offers:
            return None, "", ""

        offers = offers[0]

    if not isinstance(offers, dict):
        return None, "", ""

    price = offers.get("price")

    currency = offers.get(
        "priceCurrency",
        ""
    )

    availability = offers.get(
        "availability",
        ""
    )

    if price is not None:
        try:
            price = float(
                str(price).replace(
                    ",",
                    ""
                )
            )
        except Exception:
            price = None

    return (
        price,
        currency,
        availability
    )


def walk_for_schema_product(obj):
    results = []

    if isinstance(obj, dict):

        if "schemaOrgProduct" in obj:
            results.append(
                obj["schemaOrgProduct"]
            )

        for value in obj.values():
            results.extend(
                walk_for_schema_product(
                    value
                )
            )

    elif isinstance(obj, list):

        for value in obj:
            results.extend(
                walk_for_schema_product(
                    value
                )
            )

    return results


async def extract_variants(page):
    scripts = await page.locator(
        "script"
    ).all()

    found = []

    for script in scripts:
        try:
            text = await script.text_content()

            if not text:
                continue

            if "schemaOrgProduct" not in text:
                continue

            try:
                data = json.loads(text)
            except Exception:
                continue

            products = (
                walk_for_schema_product(
                    data
                )
            )

            for product in products:
                if not isinstance(
                    product,
                    dict
                ):
                    continue

                collection_name = str(
                    product.get(
                        "name",
                        ""
                    )
                ).strip()

                variants = product.get(
                    "hasVariant",
                    []
                )

                if isinstance(
                    variants,
                    dict
                ):
                    variants = [
                        variants
                    ]

                if not isinstance(
                    variants,
                    list
                ):
                    continue

                for variant in variants:

                    if not isinstance(
                        variant,
                        dict
                    ):
                        continue

                    (
                        price,
                        currency,
                        availability
                    ) = extract_offer(
                        variant
                    )

                    variant_url = normalize_url(
                        variant.get(
                            "url",
                            ""
                        )
                    )

                    if not variant_url:

                        offers = variant.get(
                            "offers"
                        )

                        if isinstance(
                            offers,
                            dict
                        ):

                            variant_url = normalize_url(
                                offers.get(
                                    "url",
                                    ""
                                )
                            )

                    if not variant_url:
                        continue

                    found.append({

                        "Collection":
                            collection_name,

                        "Variant":
                            get_variant_name(
                                variant
                            ),

                        "Item Number":
                            get_item_number(
                                variant
                            ),

                        "Price":
                            (
                                ""
                                if price is None
                                else price
                            ),

                        "Currency":
                            currency,

                        "Availability":
                            availability,

                        "URL":
                            variant_url,

                        "Last Seen":
                            now()

                    })

        except Exception:
            pass

    unique = {}

    for item in found:
        unique[
            item["URL"]
        ] = item

    return list(
        unique.values()
    )


async def get_collection_links(page):
    print(
        "Scanning Jacob & Co..."
    )

    await page.goto(
        SITE_URL,
        wait_until="domcontentloaded",
        timeout=90000
    )

    await page.wait_for_timeout(
        5000
    )

    for _ in range(10):

        await page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

        await page.wait_for_timeout(
            1000
        )

    links = await page.locator(
        'a[href^="/timepieces/"]'
    ).evaluate_all(
        """
        els => els.map(e => e.href)
        """
    )

    cleaned = set()

    for url in links:

        if not url:
            continue

        parsed = urlparse(url)

        path = parsed.path.rstrip("/")

        parts = [
            p
            for p in path.split("/")
            if p
        ]

        if len(parts) != 2:
            continue

        if parts[0] != "timepieces":
            continue

        cleaned.add(
            normalize_url(url)
        )

    links = sorted(
        cleaned
    )

    print(
        f"Collection pages: {len(links)}"
    )

    return links


def build_old_map(rows):
    result = {}

    for row in rows:

        url = row.get(
            "URL",
            ""
        )

        if url:
            result[url] = row

    return result


def update_history(
    old_map,
    new_rows,
    history
):

    existing_changes = set()

    for row in history:

        key = (
            row.get(
                "Changed At",
                ""
            ),
            row.get(
                "URL",
                ""
            ),
            row.get(
                "Old Price",
                ""
            ),
            row.get(
                "New Price",
                ""
            )
        )

        existing_changes.add(
            key
        )

    for item in new_rows:

        url = item.get(
            "URL",
            ""
        )

        old = old_map.get(
            url
        )

        if not old:
            continue

        old_price = str(
            old.get(
                "Price",
                ""
            )
        ).strip()

        new_price = str(
            item.get(
                "Price",
                ""
            )
        ).strip()

        if (
            old_price
            and new_price
            and old_price != new_price
        ):

            changed_at = now()

            key = (
                changed_at,
                url,
                old_price,
                new_price
            )

            if key in existing_changes:
                continue

            history.append({

                "Changed At":
                    changed_at,

                "Collection":
                    item.get(
                        "Collection",
                        ""
                    ),

                "Variant":
                    item.get(
                        "Variant",
                        ""
                    ),

                "Item Number":
                    item.get(
                        "Item Number",
                        ""
                    ),

                "Old Price":
                    old_price,

                "New Price":
                    new_price,

                "Currency":
                    item.get(
                        "Currency",
                        ""
                    ),

                "URL":
                    url

            })

            print()
            print(
                "PRICE CHANGE"
            )

            print(
                item.get(
                    "Variant",
                    ""
                )
            )

            print(
                old_price,
                "->",
                new_price
            )


async def main():
    old_rows = read_csv(
        CURRENT_CSV
    )

    history = read_csv(
        HISTORY_CSV
    )

    old_map = build_old_map(
        old_rows
    )

    all_rows = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            locale="en-US"
        )

        page = await context.new_page()

        links = await get_collection_links(
            page
        )

        total = len(links)

        for index, url in enumerate(
            links,
            start=1
        ):

            print(
                f"[{index}/{total}] {url}"
            )

            try:

                await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=90000
                )

                await page.wait_for_timeout(
                    2000
                )

                variants = (
                    await extract_variants(
                        page
                    )
                )

                print(
                    f"Variants: {len(variants)}"
                )

                all_rows.extend(
                    variants
                )

            except Exception as e:

                print(
                    f"ERROR: {e}"
                )

            await asyncio.sleep(
                REQUEST_DELAY
            )

        await browser.close()

    unique = {}

    for row in all_rows:
        unique[
            row["URL"]
        ] = row

    all_rows = list(
        unique.values()
    )

    update_history(
        old_map,
        all_rows,
        history
    )

    product_fields = [
        "Collection",
        "Variant",
        "Item Number",
        "Price",
        "Currency",
        "Availability",
        "URL",
        "Last Seen"
    ]

    history_fields = [
        "Changed At",
        "Collection",
        "Variant",
        "Item Number",
        "Old Price",
        "New Price",
        "Currency",
        "URL"
    ]

    write_csv(
        CURRENT_CSV,
        product_fields,
        all_rows
    )

    write_csv(
        HISTORY_CSV,
        history_fields,
        history
    )

    print()
    print(
        "=" * 60
    )

    print(
        "Cloud scan completed."
    )

    print(
        f"Variants: {len(all_rows)}"
    )

    print(
        f"History: {len(history)}"
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":
    asyncio.run(main())
