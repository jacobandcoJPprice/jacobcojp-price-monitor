import asyncio
import csv
import re

from playwright.async_api import async_playwright


URL = "https://jacobandco.com/timepiece-prices"
OUTPUT = "price_page_cards.csv"


ITEM_PATTERN = re.compile(
    r"\b[A-Z]{1,8}[0-9]{2,8}"
    r"(?:\.[A-Z0-9]+){2,10}\b",
    re.I
)

PRICE_PATTERN = re.compile(
    r"([0-9]{1,3}(?:,[0-9]{3})+)\s*\(USD\)",
    re.I
)


async def main():

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
        print("JACOB & CO. PRICE PAGE CARD EXPORT")
        print("=" * 70)

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        # ----------------------------------------------------
        # Scroll entire page
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # All product links
        # ----------------------------------------------------

        anchors = page.locator(
            'a[href*="/timepieces/"]'
        )

        count = await anchors.count()

        print(
            "Timepiece links found:",
            count
        )

        rows = []
        seen = set()

        items_without_price = []

        # ----------------------------------------------------
        # Extract cards
        # ----------------------------------------------------

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

                item_match = ITEM_PATTERN.search(
                    text
                )

                if not item_match:
                    continue

                item_number = item_match.group(0)

                # --------------------------------------------
                # First: price inside <a>
                # --------------------------------------------

                price_match = PRICE_PATTERN.search(
                    text
                )

                # --------------------------------------------
                # If missing, walk up through parent elements
                # --------------------------------------------

                if not price_match:

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

                        parent_price = (
                            PRICE_PATTERN.search(
                                parent_text
                            )
                        )

                        if parent_price:

                            price_match = (
                                parent_price
                            )

                            text = parent_text

                # --------------------------------------------
                # Still no price
                # --------------------------------------------

                if not price_match:

                    items_without_price.append(
                        item_number
                    )

                    print()
                    print(
                        "ITEM WITHOUT MATCHED PRICE:",
                        item_number
                    )

                    continue

                price = (
                    price_match
                    .group(1)
                    .replace(",", "")
                )

                # --------------------------------------------
                # Normalize URL
                # --------------------------------------------

                if href.startswith("/"):

                    href = (
                        "https://jacobandco.com"
                        + href
                    )

                href = (
                    href
                    .split("#")[0]
                    .rstrip("/")
                )

                # --------------------------------------------
                # Unique by Item Number
                # --------------------------------------------

                if item_number in seen:
                    continue

                seen.add(
                    item_number
                )

                rows.append({

                    "Item Number":
                        item_number,

                    "Price":
                        price,

                    "Currency":
                        "USD",

                    "URL":
                        href,

                    "Card Text":
                        " | ".join(
                            line.strip()
                            for line
                            in text.splitlines()
                            if line.strip()
                        )
                })

            except Exception as e:

                print(
                    "CARD ERROR:",
                    e
                )

        # ----------------------------------------------------
        # Sort
        # ----------------------------------------------------

        rows.sort(
            key=lambda x:
                x["Item Number"]
        )

        # ----------------------------------------------------
        # Save CSV
        # ----------------------------------------------------

        with open(
            OUTPUT,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "Item Number",
                    "Price",
                    "Currency",
                    "URL",
                    "Card Text"
                ]
            )

            writer.writeheader()

            writer.writerows(
                rows
            )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("PRICE PAGE CARD EXPORT")
        print("=" * 70)

        print(
            "Rows exported :",
            len(rows)
        )

        print(
            "No price match:",
            len(
                set(
                    items_without_price
                )
            )
        )

        print(
            "Output file   :",
            OUTPUT
        )

        if items_without_price:

            print()
            print(
                "ITEMS WITHOUT PRICE"
            )

            print("-" * 70)

            for item in sorted(
                set(
                    items_without_price
                )
            ):

                print(item)

        print()
        print(
            "First 10 rows:"
        )

        for row in rows[:10]:

            print(
                row["Item Number"],
                row["Price"],
                row["URL"]
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
