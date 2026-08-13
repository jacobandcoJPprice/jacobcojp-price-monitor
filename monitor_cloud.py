import asyncio
import csv
import os
import re
from datetime import datetime

from playwright.async_api import async_playwright


URL = "https://jacobandco.com/timepiece-prices"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(BASE_DIR, "current_prices.csv")
HISTORY_CSV = os.path.join(BASE_DIR, "price_history_v2.csv")


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
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def old_price_map(rows):
    result = {}

    for row in rows:
        item_number = str(
            row.get("Item Number", "")
        ).strip()

        if item_number:
            result[item_number] = row

    return result


async def main():

    print("=" * 70)
    print("JACOB & CO. OFFICIAL PRICE PAGE MONITOR")
    print("=" * 70)

    old_rows = read_csv(CURRENT_CSV)
    history = read_csv(HISTORY_CSV)

    old_map = old_price_map(old_rows)

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

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        print("Scrolling full page...")

        last_height = 0

        for i in range(80):

            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            await page.wait_for_timeout(800)

            new_height = await page.evaluate(
                "document.body.scrollHeight"
            )

            if new_height == last_height and i >= 5:
                break

            last_height = new_height

        await page.wait_for_timeout(3000)

        anchors = page.locator(
            'a[href*="/timepieces/"]'
        )

        count = await anchors.count()

        print("Timepiece links found:", count)

        for i in range(count):

            anchor = anchors.nth(i)

            try:

                text = (
                    await anchor.inner_text()
                ).strip()

                href = await anchor.get_attribute(
                    "href"
                )

                if not text or not href:
                    continue

                item_match = ITEM_PATTERN.search(text)

                if not item_match:
                    continue

                item_number = item_match.group(0)

                price_match = PRICE_PATTERN.search(text)

                if not price_match:

                    parent_text = await anchor.evaluate(
                        """
                        el => {
                            let node = el;

                            for (let i = 0; i < 8; i++) {

                                if (!node) break;

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

                    if parent_text:

                        parent_price = PRICE_PATTERN.search(
                            parent_text
                        )

                        if parent_price:
                            price_match = parent_price
                            text = parent_text

                if not price_match:
                    continue

                price = (
                    price_match
                    .group(1)
                    .replace(",", "")
                )

                if href.startswith("/"):
                    href = "https://jacobandco.com" + href

                href = (
                    href
                    .split("#")[0]
                    .rstrip("/")
                )

                if item_number in seen:
                    continue

                seen.add(item_number)

                lines = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip()
                ]

                collection = ""
                variant = ""

                if lines:
                    variant = lines[0]

                if "/timepieces/" in href:
                    parts = [
                        p
                        for p in href.split("/")
                        if p
                    ]

                    try:
                        idx = parts.index("timepieces")

                        if len(parts) > idx + 1:
                            collection = (
                                parts[idx + 1]
                                .replace("-", " ")
                                .title()
                            )

                    except ValueError:
                        pass

                rows.append({
                    "Collection": collection,
                    "Variant": variant,
                    "Item Number": item_number,
                    "Price": price,
                    "Currency": "USD",
                    "Availability": "PRICE AVAILABLE",
                    "URL": href,
                    "Last Seen": now()
                })

            except Exception as e:
                print("CARD ERROR:", e)

        await browser.close()

    rows.sort(
        key=lambda x: (
            x["Collection"].lower(),
            x["Variant"].lower(),
            x["Item Number"].lower()
        )
    )

    if len(rows) < 500:
        raise RuntimeError(
            f"Safety stop: only {len(rows)} rows found."
        )

    changes = 0

    for row in rows:

        item_number = row["Item Number"]

        old = old_map.get(item_number)

        if not old:
            continue

        old_price = str(
            old.get("Price", "")
        ).strip()

        new_price = str(
            row.get("Price", "")
        ).strip()

        if old_price == new_price:
            continue

        history.append({
            "Changed At": now(),
            "Collection": row["Collection"],
            "Variant": row["Variant"],
            "Item Number": item_number,
            "Old Price": old_price,
            "New Price": new_price,
            "Currency": "USD",
            "URL": row["URL"]
        })

        changes += 1

        print()
        print("PRICE CHANGE DETECTED")
        print("Item Number:", item_number)
        print("Old Price  :", old_price)
        print("New Price  :", new_price)

    current_fields = [
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
        current_fields,
        rows
    )

    write_csv(
        HISTORY_CSV,
        history_fields,
        history
    )

    print()
    print("=" * 70)
    print("MONITOR COMPLETED")
    print("=" * 70)
    print("Current rows :", len(rows))
    print("Price changes:", changes)
    print("History rows :", len(history))


if __name__ == "__main__":
    asyncio.run(main())
