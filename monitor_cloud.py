import asyncio
import csv
import os
import re
from datetime import datetime

from playwright.async_api import async_playwright


# ============================================================
# CONFIG
# ============================================================

PRICE_PAGE_URL = "https://jacobandco.com/timepiece-prices"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(BASE_DIR, "current_prices.csv")
HISTORY_CSV = os.path.join(BASE_DIR, "price_history_v2.csv")


# Jacob & Co. Item Number
# Examples:
# AF321.30.BB.AA.B
# BU300.22.AA.AA.B
# CA100.30.AB.BC.ABAI.A
ITEM_PATTERN = re.compile(
    r"\b[A-Z]{1,10}[0-9]{2,8}"
    r"(?:\.[A-Z0-9]+){2,12}\b",
    re.I
)

# Example:
# 418,000 (USD)
PRICE_PATTERN = re.compile(
    r"([0-9]{1,3}(?:,[0-9]{3})+)\s*\(USD\)",
    re.I
)


# ============================================================
# BASIC FUNCTIONS
# ============================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_csv(path):
    if not os.path.exists(path):
        return []

    try:
        with open(
            path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            return list(csv.DictReader(f))

    except Exception as e:
        print("CSV READ ERROR:", path, e)
        return []


def write_csv(path, fieldnames, rows):
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

        for row in rows:
            writer.writerow(row)


def normalize_price(value):
    """
    Convert:
    418000
    418000.0
    418,000
    $418,000

    into float 418000.0
    """

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


def display_price(value):
    """
    Convert price into clean integer string.

    418000.0 -> 418000
    """

    number = normalize_price(value)

    if number is None:
        return ""

    return str(int(round(number)))


def build_old_price_map(rows):
    result = {}

    for row in rows:

        item_number = str(
            row.get("Item Number", "")
        ).strip().upper()

        if not item_number:
            continue

        result[item_number] = row

    return result


# ============================================================
# SCRAPER
# ============================================================

async def scrape_price_page():

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

        print()
        print("Opening official price page...")
        print(PRICE_PAGE_URL)

        await page.goto(
            PRICE_PAGE_URL,
            wait_until="networkidle",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        print()
        print("Scrolling full page...")

        last_height = 0
        stable_count = 0

        for _ in range(100):

            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            await page.wait_for_timeout(800)

            new_height = await page.evaluate(
                "document.body.scrollHeight"
            )

            if new_height == last_height:
                stable_count += 1
            else:
                stable_count = 0

            last_height = new_height

            if stable_count >= 4:
                break

        await page.wait_for_timeout(3000)

        anchors = page.locator(
            'a[href*="/timepieces/"]'
        )

        count = await anchors.count()

        print("Timepiece links found:", count)

        for i in range(count):

            anchor = anchors.nth(i)

            try:

                href = await anchor.get_attribute(
                    "href"
                )

                text = (
                    await anchor.inner_text()
                ).strip()

                if not href:
                    continue

                # ------------------------------------------------
                # Try anchor text first
                # ------------------------------------------------

                item_match = ITEM_PATTERN.search(text)
                price_match = PRICE_PATTERN.search(text)

                # ------------------------------------------------
                # If card text isn't directly inside <a>,
                # move upward through parent elements.
                # ------------------------------------------------

                if not item_match or not price_match:

                    parent_text = await anchor.evaluate(
                        """
                        el => {
                            let node = el;

                            for (let i = 0; i < 8; i++) {

                                if (!node) {
                                    break;
                                }

                                const text =
                                    node.innerText || "";

                                if (
                                    /[A-Z]{1,10}[0-9]{2,8}(\\.[A-Z0-9]+){2,12}/i.test(text)
                                    &&
                                    /[0-9]{1,3}(,[0-9]{3})+\\s*\\(USD\\)/i.test(text)
                                ) {
                                    return text;
                                }

                                node = node.parentElement;
                            }

                            return "";
                        }
                        """
                    )

                    if parent_text:

                        parent_item = ITEM_PATTERN.search(
                            parent_text
                        )

                        parent_price = PRICE_PATTERN.search(
                            parent_text
                        )

                        if parent_item:
                            item_match = parent_item

                        if parent_price:
                            price_match = parent_price

                        text = parent_text

                # ------------------------------------------------
                # Need both Item Number + Price
                # ------------------------------------------------

                if not item_match:
                    continue

                if not price_match:
                    continue

                item_number = (
                    item_match
                    .group(0)
                    .strip()
                    .upper()
                )

                price = (
                    price_match
                    .group(1)
                    .replace(",", "")
                )

                # ------------------------------------------------
                # Normalize URL
                # ------------------------------------------------

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

                # ------------------------------------------------
                # One row per Item Number
                # ------------------------------------------------

                if item_number in seen:
                    continue

                seen.add(item_number)

                # ------------------------------------------------
                # Collection from URL
                # ------------------------------------------------

                collection = ""

                if "/timepieces/" in href:

                    parts = [
                        part
                        for part in href.split("/")
                        if part
                    ]

                    try:

                        index = parts.index(
                            "timepieces"
                        )

                        if len(parts) > index + 1:

                            collection = (
                                parts[index + 1]
                                .replace("-", " ")
                                .title()
                            )

                    except ValueError:
                        pass

                # ------------------------------------------------
                # Clean card text
                # ------------------------------------------------

                lines = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip()
                ]

                card_text = " | ".join(lines)

                # ------------------------------------------------
                # Variant
                # ------------------------------------------------

                variant = ""

                # URL normally contains collection / variant
                if "/timepieces/" in href:

                    parts = [
                        part
                        for part in href.split("/")
                        if part
                    ]

                    try:

                        index = parts.index(
                            "timepieces"
                        )

                        if len(parts) > index + 2:

                            variant = (
                                parts[index + 2]
                                .replace("-", " ")
                                .title()
                            )

                    except ValueError:
                        pass

                rows.append({
                    "Collection": collection,
                    "Variant": variant,
                    "Item Number": item_number,
                    "Price": display_price(price),
                    "Currency": "USD",
                    "Availability": "PRICE AVAILABLE",
                    "URL": href,
                    "Card Text": card_text,
                    "Last Seen": now()
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
            row["Collection"].lower(),
            row["Item Number"].lower()
        )
    )

    return rows


# ============================================================
# PRICE CHANGE CHECK
# ============================================================

def detect_price_changes(
    old_rows,
    new_rows,
    history_rows
):

    old_map = build_old_price_map(
        old_rows
    )

    changes = []

    for row in new_rows:

        item_number = (
            row["Item Number"]
            .strip()
            .upper()
        )

        old = old_map.get(
            item_number
        )

        # New product:
        # Do NOT treat it as price change.
        if not old:
            continue

        old_price = normalize_price(
            old.get("Price")
        )

        new_price = normalize_price(
            row.get("Price")
        )

        # Can't compare
        if old_price is None:
            continue

        if new_price is None:
            continue

        # IMPORTANT:
        # 418000.0 == 418000
        if old_price == new_price:
            continue

        old_price_text = display_price(
            old_price
        )

        new_price_text = display_price(
            new_price
        )

        change = {
            "Changed At": now(),
            "Collection": row["Collection"],
            "Variant": row["Variant"],
            "Item Number": item_number,
            "Old Price": old_price_text,
            "New Price": new_price_text,
            "Currency": "USD",
            "URL": row["URL"]
        }

        history_rows.append(
            change
        )

        changes.append(
            change
        )

    return changes


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 70)
    print("JACOB & CO. USA OFFICIAL PRICE MONITOR")
    print("=" * 70)

    # --------------------------------------------------------
    # Read previous data BEFORE scraping
    # --------------------------------------------------------

    old_rows = read_csv(
        CURRENT_CSV
    )

    history_rows = read_csv(
        HISTORY_CSV
    )

    print()
    print(
        "Previous current rows:",
        len(old_rows)
    )

    print(
        "Previous history rows:",
        len(history_rows)
    )

    # --------------------------------------------------------
    # Scrape
    # --------------------------------------------------------

    new_rows = await scrape_price_page()

    print()
    print("=" * 70)
    print("SCRAPE RESULT")
    print("=" * 70)

    print(
        "Rows found:",
        len(new_rows)
    )

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    # We already confirmed the official page currently gives
    # about 582 item-number rows.
    #
    # If the site suddenly gives only 50/100/etc.,
    # DON'T overwrite our good CSV.

    if len(new_rows) < 500:

        raise RuntimeError(
            "SAFETY STOP: "
            f"only {len(new_rows)} rows were found. "
            "current_prices.csv was NOT overwritten."
        )

    # --------------------------------------------------------
    # Detect changes
    # --------------------------------------------------------

    changes = detect_price_changes(
        old_rows,
        new_rows,
        history_rows
    )

    # --------------------------------------------------------
    # Print real changes
    # --------------------------------------------------------

    if changes:

        print()
        print("=" * 70)
        print("PRICE CHANGES")
        print("=" * 70)

        for change in changes:

            print()

            print(
                "Item Number:",
                change["Item Number"]
            )

            print(
                "Old Price:",
                change["Old Price"]
            )

            print(
                "New Price:",
                change["New Price"]
            )

            print(
                "URL:",
                change["URL"]
            )

    # --------------------------------------------------------
    # Save current prices
    # --------------------------------------------------------

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

    write_csv(
        CURRENT_CSV,
        current_fields,
        new_rows
    )

    # --------------------------------------------------------
    # Save history
    # --------------------------------------------------------

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
        HISTORY_CSV,
        history_fields,
        history_rows
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

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
        len(changes)
    )

    print(
        "History rows :",
        len(history_rows)
    )

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
