import asyncio
import csv
import os
import re
from datetime import datetime

from playwright.async_api import async_playwright


PRICE_PAGE_URL = "https://jacobandco.com/timepiece-prices"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(
    BASE_DIR,
    "current_prices.csv"
)

HISTORY_CSV = os.path.join(
    BASE_DIR,
    "price_history_v2.csv"
)

PRODUCT_HISTORY_CSV = os.path.join(
    BASE_DIR,
    "product_change_history.csv"
)

MISSING_CANDIDATES_CSV = os.path.join(
    BASE_DIR,
    "missing_item_candidates.csv"
)


ITEM_PATTERN = re.compile(
    r"\b[A-Z]{1,8}[0-9]{2,8}"
    r"(?:\.[A-Z0-9]+){2,10}\b",
    re.I
)

PRICE_PATTERN = re.compile(
    r"([0-9]{1,3}(?:,[0-9]{3})+)\s*\(USD\)",
    re.I
)


def now():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def read_csv(path):

    if not os.path.exists(path):
        return []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def write_csv(
    path,
    fieldnames,
    rows
):

    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
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
        .replace(",", "")
        .replace("$", "")
        .replace("USD", "")
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

    return str(
        int(round(number))
    )


def build_old_map(rows):

    result = {}

    for row in rows:

        item_number = str(
            row.get(
                "Item Number",
                ""
            )
        ).strip().upper()

        if item_number:
            result[
                item_number
            ] = row

    return result


async def scrape_prices():

    rows = []
    seen = set()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000
            }
        )

        print("=" * 70)
        print(
            "OPENING JACOB & CO. "
            "OFFICIAL PRICE PAGE"
        )
        print("=" * 70)

        await page.goto(
            PRICE_PAGE_URL,
            wait_until="networkidle",
            timeout=120000
        )

        await page.wait_for_timeout(
            5000
        )

        print(
            "Scrolling full page..."
        )

        last_height = 0

        for i in range(80):

            await page.evaluate(
                "window.scrollTo("
                "0, document.body.scrollHeight)"
            )

            await page.wait_for_timeout(
                800
            )

            new_height = await page.evaluate(
                "document.body.scrollHeight"
            )

            if (
                new_height == last_height
                and i >= 5
            ):
                break

            last_height = new_height

        await page.wait_for_timeout(
            3000
        )

        anchors = page.locator(
            'a[href*="/timepieces/"]'
        )

        count = await anchors.count()

        print(
            "Timepiece links found:",
            count
        )

        for i in range(count):

            anchor = anchors.nth(i)

            try:

                text = (
                    await anchor.inner_text()
                ).strip()

                href = (
                    await anchor.get_attribute(
                        "href"
                    )
                )

                if not text or not href:
                    continue

                item_match = (
                    ITEM_PATTERN.search(
                        text
                    )
                )

                if not item_match:
                    continue

                item_number = (
                    item_match
                    .group(0)
                    .strip()
                    .upper()
                )

                price_match = (
                    PRICE_PATTERN.search(
                        text
                    )
                )

                if not price_match:

                    parent_text = (
                        await anchor.evaluate(
                            """
                            el => {
                                let node = el;

                                for (
                                    let i = 0;
                                    i < 8;
                                    i++
                                ) {

                                    if (!node) {
                                        break;
                                    }

                                    const text =
                                        node.innerText || "";

                                    if (
                                        text.includes("(USD)")
                                    ) {
                                        return text;
                                    }

                                    node =
                                        node.parentElement;
                                }

                                return "";
                            }
                            """
                        )
                    )

                    if parent_text:

                        parent_price = (
                            PRICE_PATTERN.search(
                                parent_text
                            )
                        )

                        if parent_price:

                            price_match = (
                                parent_price
                            )

                            text = (
                                parent_text
                            )

                if not price_match:
                    continue

                price = (
                    price_match
                    .group(1)
                    .replace(",", "")
                )

                price = clean_price(
                    price
                )

                if href.startswith("/"):

                    href = (
                        "https://jacobandco.com"
                        + href
                    )

                href = (
                    href
                    .split("#")[0]
                    .split("?")[0]
                    .rstrip("/")
                )

                if item_number in seen:
                    continue

                seen.add(
                    item_number
                )

                collection = ""
                variant = ""

                parts = [
                    part
                    for part
                    in href.split("/")
                    if part
                ]

                try:

                    idx = parts.index(
                        "timepieces"
                    )

                    if len(parts) > idx + 1:

                        collection = (
                            parts[idx + 1]
                            .replace("-", " ")
                            .title()
                        )

                    if len(parts) > idx + 2:

                        variant = (
                            parts[idx + 2]
                            .replace("-", " ")
                            .title()
                        )

                except ValueError:
                    pass

                lines = [
                    line.strip()
                    for line
                    in text.splitlines()
                    if line.strip()
                ]

                card_text = (
                    " | ".join(
                        lines
                    )
                )

                rows.append({

                    "Collection":
                        collection,

                    "Variant":
                        variant,

                    "Item Number":
                        item_number,

                    "Price":
                        price,

                    "Currency":
                        "USD",

                    "Availability":
                        "PRICE AVAILABLE",

                    "URL":
                        href,

                    "Card Text":
                        card_text,

                    "Last Seen":
                        now()

                })

            except Exception as e:

                print(
                    "CARD ERROR:",
                    i,
                    e
                )

        await browser.close()

    rows.sort(
        key=lambda row: (
            row.get(
                "Collection",
                ""
            ).lower(),
            row.get(
                "Item Number",
                ""
            ).lower()
        )
    )

    return rows


def detect_price_changes(
    old_rows,
    new_rows,
    history
):

    old_map = build_old_map(
        old_rows
    )

    changes = []

    for row in new_rows:

        item_number = (
            row.get(
                "Item Number",
                ""
            )
            .strip()
            .upper()
        )

        old = old_map.get(
            item_number
        )

        if not old:
            continue

        old_price = normalize_price(
            old.get(
                "Price",
                ""
            )
        )

        new_price = normalize_price(
            row.get(
                "Price",
                ""
            )
        )

        if (
            old_price is None
            or new_price is None
        ):
            continue

        if old_price == new_price:
            continue

        change = {

            "Changed At":
                now(),

            "Collection":
                row.get(
                    "Collection",
                    ""
                ),

            "Variant":
                row.get(
                    "Variant",
                    ""
                ),

            "Item Number":
                item_number,

            "Old Price":
                clean_price(
                    old_price
                ),

            "New Price":
                clean_price(
                    new_price
                ),

            "Currency":
                "USD",

            "URL":
                row.get(
                    "URL",
                    ""
                )

        }

        history.append(
            change
        )

        changes.append(
            change
        )

    return changes


def detect_product_changes(
    old_rows,
    new_rows,
    product_history,
    missing_candidates
):

    old_map = build_old_map(
        old_rows
    )

    new_map = build_old_map(
        new_rows
    )

    events = []

    if not old_rows:
        return events, []

    old_items = set(
        old_map.keys()
    )

    new_items = set(
        new_map.keys()
    )

    # Existing missing-candidate state
    candidate_map = {}

    for row in missing_candidates:

        item_number = str(
            row.get(
                "Item Number",
                ""
            )
        ).strip().upper()

        if not item_number:
            continue

        try:
            miss_count = int(
                row.get(
                    "Consecutive Misses",
                    0
                )
                or 0
            )
        except Exception:
            miss_count = 0

        candidate_map[
            item_number
        ] = {
            "Item Number":
                item_number,
            "Consecutive Misses":
                miss_count,
            "First Missing At":
                str(
                    row.get(
                        "First Missing At",
                        ""
                    )
                ).strip(),
            "Last Missing At":
                str(
                    row.get(
                        "Last Missing At",
                        ""
                    )
                ).strip()
        }

    # NEW ITEM: record immediately
    for item_number in sorted(
        new_items - old_items
    ):

        row = new_map[
            item_number
        ]

        event = {
            "Changed At":
                now(),
            "Change Type":
                "NEW ITEM",
            "Item Number":
                item_number,
            "Collection":
                row.get(
                    "Collection",
                    ""
                ),
            "Variant":
                row.get(
                    "Variant",
                    ""
                ),
            "Old Status":
                "",
            "New Status":
                row.get(
                    "Availability",
                    ""
                ),
            "Price":
                row.get(
                    "Price",
                    ""
                ),
            "URL":
                row.get(
                    "URL",
                    ""
                )
        }

        product_history.append(
            event
        )

        events.append(
            event
        )

    # STATUS CHANGE: record immediately
    for item_number in sorted(
        old_items & new_items
    ):

        old = old_map[
            item_number
        ]

        new = new_map[
            item_number
        ]

        old_status = str(
            old.get(
                "Availability",
                ""
            )
        ).strip()

        new_status = str(
            new.get(
                "Availability",
                ""
            )
        ).strip()

        if old_status == new_status:
            continue

        event = {
            "Changed At":
                now(),
            "Change Type":
                "STATUS CHANGE",
            "Item Number":
                item_number,
            "Collection":
                new.get(
                    "Collection",
                    ""
                ),
            "Variant":
                new.get(
                    "Variant",
                    ""
                ),
            "Old Status":
                old_status,
            "New Status":
                new_status,
            "Price":
                new.get(
                    "Price",
                    ""
                ),
            "URL":
                new.get(
                    "URL",
                    ""
                )
        }

        product_history.append(
            event
        )

        events.append(
            event
        )

    # REMOVED ITEM:
    # Do NOT declare it removed on the first missing scan.
    # Require 2 consecutive successful monitor runs where the item is absent.
    missing_now = (
        old_items - new_items
    )

    current_time = now()

    for item_number in sorted(
        missing_now
    ):

        previous = candidate_map.get(
            item_number
        )

        if previous:

            miss_count = (
                previous[
                    "Consecutive Misses"
                ]
                + 1
            )

            first_missing_at = (
                previous[
                    "First Missing At"
                ]
                or current_time
            )

        else:

            miss_count = 1
            first_missing_at = (
                current_time
            )

        candidate_map[
            item_number
        ] = {
            "Item Number":
                item_number,
            "Consecutive Misses":
                miss_count,
            "First Missing At":
                first_missing_at,
            "Last Missing At":
                current_time
        }

        if miss_count != 2:
            continue

        row = old_map[
            item_number
        ]

        event = {
            "Changed At":
                current_time,
            "Change Type":
                "REMOVED ITEM",
            "Item Number":
                item_number,
            "Collection":
                row.get(
                    "Collection",
                    ""
                ),
            "Variant":
                row.get(
                    "Variant",
                    ""
                ),
            "Old Status":
                row.get(
                    "Availability",
                    ""
                ),
            "New Status":
                "NOT FOUND (2 RUNS)",
            "Price":
                row.get(
                    "Price",
                    ""
                ),
            "URL":
                row.get(
                    "URL",
                    ""
                )
        }

        product_history.append(
            event
        )

        events.append(
            event
        )

    # Any item that exists again is no longer a missing candidate.
    for item_number in list(
        candidate_map.keys()
    ):

        if item_number in new_items:
            del candidate_map[
                item_number
            ]

    updated_candidates = sorted(
        candidate_map.values(),
        key=lambda row:
            row[
                "Item Number"
            ]
    )

    return events, updated_candidates


async def main():

    print("=" * 70)
    print(
        "JACOB & CO. USA "
        "OFFICIAL PRICE MONITOR"
    )
    print("=" * 70)

    old_rows = read_csv(
        CURRENT_CSV
    )

    history = read_csv(
        HISTORY_CSV
    )

    product_history = read_csv(
        PRODUCT_HISTORY_CSV
    )

    missing_candidates = read_csv(
        MISSING_CANDIDATES_CSV
    )

    print()
    print(
        "Previous current rows:",
        len(old_rows)
    )

    print(
        "Previous price history rows:",
        len(history)
    )

    print(
        "Previous product-change rows:",
        len(product_history)
    )

    new_rows = (
        await scrape_prices()
    )

    print()
    print("=" * 70)
    print("SCRAPE RESULT")
    print("=" * 70)

    print(
        "Rows found:",
        len(new_rows)
    )

    # Hard safety stop:
    # never overwrite healthy data if the scraper only found
    # an obviously incomplete subset.
    if len(new_rows) < 570:

        raise RuntimeError(
            "SAFETY STOP: "
            f"only {len(new_rows)} rows found. "
            "Existing CSV will NOT be overwritten."
        )

    price_changes = detect_price_changes(
        old_rows,
        new_rows,
        history
    )

    (
        product_changes,
        missing_candidates
    ) = detect_product_changes(
        old_rows,
        new_rows,
        product_history,
        missing_candidates
    )

    if price_changes:

        print()
        print("=" * 70)
        print("PRICE CHANGES")
        print("=" * 70)

        for change in price_changes:

            print()
            print(
                "Item Number:",
                change["Item Number"]
            )

            print(
                "Old:",
                change["Old Price"]
            )

            print(
                "New:",
                change["New Price"]
            )

    if product_changes:

        print()
        print("=" * 70)
        print("PRODUCT STRUCTURE CHANGES")
        print("=" * 70)

        for event in product_changes:

            print()
            print(
                "Type:",
                event["Change Type"]
            )

            print(
                "Item Number:",
                event["Item Number"]
            )

            print(
                "Old Status:",
                event["Old Status"]
            )

            print(
                "New Status:",
                event["New Status"]
            )

    current_fields = [
        "Collection",
        "Variant",
        "Item Number",
        "Price",
        "Currency",
        "Availability",
        "URL",
        "Card Text",
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

    product_history_fields = [
        "Changed At",
        "Change Type",
        "Item Number",
        "Collection",
        "Variant",
        "Old Status",
        "New Status",
        "Price",
        "URL"
    ]


    missing_candidate_fields = [
        "Item Number",
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
        HISTORY_CSV,
        history_fields,
        history
    )

    write_csv(
        PRODUCT_HISTORY_CSV,
        product_history_fields,
        product_history
    )


    write_csv(
        MISSING_CANDIDATES_CSV,
        missing_candidate_fields,
        missing_candidates
    )

    print()
    print("=" * 70)
    print("MONITOR COMPLETED")
    print("=" * 70)

    print(
        "Current rows :",
        len(new_rows)
    )

    print(
        "Price changes:",
        len(price_changes)
    )

    print(
        "Product changes:",
        len(product_changes)
    )

    print(
        "Price history rows:",
        len(history)
    )

    print(
        "Product history rows:",
        len(product_history)
    )


    print(
        "Pending missing items:",
        len(missing_candidates)
    )

    print("=" * 70)


if __name__ == "__main__":

    asyncio.run(
        main()
    )
