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

        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page(
            viewport={"width": 1440, "height": 1000}
        )

        print("Opening:", URL)

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        # 自动滚到底，确保全部卡片加载
        last_height = 0

        for _ in range(80):

            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            await page.wait_for_timeout(800)

            new_height = await page.evaluate(
                "document.body.scrollHeight"
            )

            if new_height == last_height:
                break

            last_height = new_height

        await page.wait_for_timeout(3000)

        # 找所有 timepieces 链接
        anchors = page.locator('a[href*="/timepieces/"]')

        count = await anchors.count()

        rows = []
        seen = set()

        for i in range(count):

            anchor = anchors.nth(i)

            try:
                text = (await anchor.inner_text()).strip()

                href = await anchor.get_attribute("href")

                if not text or not href:
                    continue

                item_match = ITEM_PATTERN.search(text)
                item_match = ITEM_PATTERN.search(text)

if not item_match:
    continue

# 先从链接自身找价格
price_match = PRICE_PATTERN.search(text)

# 如果链接自身没有价格，
# 就向外层商品卡找，最多向上找 6 层
if not price_match:

    try:
        parent_text = await anchor.evaluate(
            """
            el => {
                let node = el;

                for (let i = 0; i < 6; i++) {
                    if (!node) break;

                    const text = node.innerText || "";

                    if (
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

        price_match = PRICE_PATTERN.search(parent_text)

        if price_match:
            text = parent_text

    except Exception:
        pass

if not price_match:
    print()
    print("ITEM WITHOUT MATCHED PRICE:")
    print(item_match.group(0))
    print(text[:500])
    continue

                item_number = item_match.group(0)

                price = price_match.group(1).replace(",", "")

                if href.startswith("/"):
                    href = "https://jacobandco.com" + href

                href = href.split("#")[0].rstrip("/")

                key = item_number

                if key in seen:
                    continue

                seen.add(key)

                rows.append({
                    "Item Number": item_number,
                    "Price": price,
                    "Currency": "USD",
                    "URL": href,
                    "Card Text": " | ".join(
                        line.strip()
                        for line in text.splitlines()
                        if line.strip()
                    )
                })

            except Exception:
                pass

        rows.sort(key=lambda x: x["Item Number"])

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
            writer.writerows(rows)

        print()
        print("=" * 70)
        print("PRICE PAGE CARD EXPORT")
        print("=" * 70)
        print("Rows exported :", len(rows))
        print("Output file   :", OUTPUT)

        for row in rows[:10]:
            print(
                row["Item Number"],
                row["Price"],
                row["URL"]
            )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
