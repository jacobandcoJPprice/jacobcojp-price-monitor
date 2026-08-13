import asyncio
import re
from playwright.async_api import async_playwright


URL = "https://jacobandco.com/timepiece-prices"


ITEM_PATTERN = re.compile(
    r"\b[A-Z]{1,8}[0-9]{2,8}"
    r"(?:\.[A-Z0-9]+){2,10}\b",
    re.I
)

PRICE_PATTERN = re.compile(
    r"\b[0-9]{1,3}(?:,[0-9]{3})+\s*\(USD\)",
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
        print("JACOB & CO. TIMEPIECE PRICE PAGE DOM TEST")
        print("=" * 70)

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        # ====================================================
        # 自动滚到底部，确保所有商品都渲染出来
        # ====================================================

        print()
        print("Scrolling full page...")

        last_height = 0

        for i in range(60):

            height = await page.evaluate(
                "document.body.scrollHeight"
            )

            print(
                f"Scroll {i + 1}: height = {height}"
            )

            await page.evaluate(
                """
                window.scrollTo(
                    0,
                    document.body.scrollHeight
                )
                """
            )

            await page.wait_for_timeout(1000)

            new_height = await page.evaluate(
                "document.body.scrollHeight"
            )

            if (
                new_height == last_height
                and i >= 5
            ):
                break

            last_height = new_height

        await page.wait_for_timeout(3000)

        # ====================================================
        # 获取页面最终可见文字
        # ====================================================

        body_text = await page.locator(
            "body"
        ).inner_text()

        # ====================================================
        # Item Number
        # ====================================================

        item_numbers = sorted(
            set(
                ITEM_PATTERN.findall(
                    body_text
                )
            )
        )

        print()
        print("=" * 70)
        print("ITEM NUMBERS FOUND ON FINAL PAGE")
        print("=" * 70)

        print(
            "ITEM NUMBER COUNT:",
            len(item_numbers)
        )

        for item in item_numbers:
            print(item)

        # ====================================================
        # USD Price
        # ====================================================

        prices = PRICE_PATTERN.findall(
            body_text
        )

        print()
        print("=" * 70)
        print("USD PRICES FOUND ON FINAL PAGE")
        print("=" * 70)

        print(
            "USD PRICE COUNT:",
            len(prices)
        )

        # ====================================================
        # 商品链接
        # ====================================================

        links = await page.locator(
            'a[href*="/timepieces/"]'
        ).evaluate_all(
            """
            els => els.map(e => e.href)
            """
        )

        product_links = sorted(
            set(
                link.split("#")[0].rstrip("/")
                for link in links
                if "/timepieces/" in link
            )
        )

        print()
        print("=" * 70)
        print("PRODUCT LINKS")
        print("=" * 70)

        print(
            "UNIQUE PRODUCT LINKS:",
            len(product_links)
        )

        # ====================================================
        # 图片
        # ====================================================

        images = await page.locator(
            "img"
        ).evaluate_all(
            """
            els => els
                .map(e => e.currentSrc || e.src)
                .filter(Boolean)
            """
        )

        unique_images = sorted(
            set(images)
        )

        print(
            "UNIQUE IMAGES:",
            len(unique_images)
        )

        # ====================================================
        # 尝试按商品链接提取每张卡片文字
        # ====================================================

        print()
        print("=" * 70)
        print("PRODUCT CARD TEXT SAMPLES")
        print("=" * 70)

        anchors = page.locator(
            'a[href*="/timepieces/"]'
        )

        anchor_count = await anchors.count()

        card_texts = []

        for i in range(anchor_count):

            anchor = anchors.nth(i)

            try:

                text = (
                    await anchor.inner_text()
                ).strip()

                href = await anchor.get_attribute(
                    "href"
                )

                if not text:
                    continue

                if not ITEM_PATTERN.search(text):
                    continue

                card_texts.append(
                    (
                        href,
                        text
                    )
                )

            except Exception:
                pass

        unique_cards = {}

        for href, text in card_texts:

            item_match = ITEM_PATTERN.search(
                text
            )

            if not item_match:
                continue

            item = item_match.group(0)

            unique_cards[item] = {
                "href": href,
                "text": text
            }

        print(
            "CARDS WITH ITEM NUMBER:",
            len(unique_cards)
        )

        print()

        for index, (
            item,
            card
        ) in enumerate(
            unique_cards.items(),
            start=1
        ):

            if index > 20:
                break

            print("-" * 70)
            print("ITEM:", item)
            print("URL :", card["href"])
            print(card["text"])

        # ====================================================
        # 最终汇总
        # ====================================================

        print()
        print("=" * 70)
        print("FINAL PAGE COUNTS")
        print("=" * 70)

        print(
            "Item Numbers      :",
            len(item_numbers)
        )

        print(
            "USD Prices        :",
            len(prices)
        )

        print(
            "Product Links     :",
            len(product_links)
        )

        print(
            "Cards w/ Item No. :",
            len(unique_cards)
        )

        print(
            "Images            :",
            len(unique_images)
        )

        print("=" * 70)

        await browser.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
