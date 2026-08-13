import asyncio
import json
import re

from playwright.async_api import async_playwright


URL = "https://jacobandco.com/timepiece-prices"


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        responses = []

        # 记录页面加载过程中调用的接口
        page.on(
            "response",
            lambda response: responses.append(
                (
                    response.status,
                    response.url
                )
            )
        )

        print("=" * 70)
        print("OPENING TIMEPIECE PRICE PAGE")
        print("=" * 70)

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        # --------------------------------------------------
        # 页面基本信息
        # --------------------------------------------------

        print()
        print("TITLE:")
        print(await page.title())

        print()
        print("FINAL URL:")
        print(page.url)

        # --------------------------------------------------
        # 页面文字
        # --------------------------------------------------

        body_text = await page.locator(
            "body"
        ).inner_text()

        print()
        print("=" * 70)
        print("PAGE TEXT SAMPLE")
        print("=" * 70)

        print(
            body_text[:15000]
        )

        # --------------------------------------------------
        # 找 Item Number
        # --------------------------------------------------

        item_numbers = sorted(
            set(
                re.findall(
                    r"\b[A-Z]{1,5}"
                    r"[0-9]{2,5}"
                    r"(?:\.[A-Z0-9]+){2,8}\b",
                    body_text
                )
            )
        )

        print()
        print("=" * 70)
        print("ITEM NUMBERS FOUND")
        print("=" * 70)

        print(
            "COUNT:",
            len(item_numbers)
        )

        for item in item_numbers[:100]:

            print(item)

        # --------------------------------------------------
        # 找美元价格
        # --------------------------------------------------

        prices = re.findall(
            r"\$\s*"
            r"[0-9][0-9,]*"
            r"(?:\.[0-9]{1,2})?",
            body_text
        )

        print()
        print("=" * 70)
        print("USD PRICES FOUND")
        print("=" * 70)

        print(
            "COUNT:",
            len(prices)
        )

        for price in prices[:100]:

            print(price)

        # --------------------------------------------------
        # HTML 中寻找 JSON / Next 数据
        # --------------------------------------------------

        html = await page.content()

        print()
        print("=" * 70)
        print("HTML SIZE")
        print("=" * 70)

        print(
            len(html)
        )

        keywords = [
            "__NEXT_DATA__",
            "timepiece",
            "price",
            "itemNumber",
            "sku",
            "variant"
        ]

        print()
        print("=" * 70)
        print("KEYWORD CHECK")
        print("=" * 70)

        lower_html = html.lower()

        for keyword in keywords:

            print(
                keyword,
                ":",
                keyword.lower()
                in lower_html
            )

        # --------------------------------------------------
        # 网络请求
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("INTERESTING NETWORK REQUESTS")
        print("=" * 70)

        seen = set()

        for status, request_url in responses:

            lower = request_url.lower()

            interesting = any(
                word in lower
                for word in [
                    "api",
                    "json",
                    "price",
                    "product",
                    "timepiece",
                    "variant",
                    "graphql"
                ]
            )

            if not interesting:
                continue

            if request_url in seen:
                continue

            seen.add(request_url)

            print(
                status,
                request_url
            )

        print()
        print("=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)

        await browser.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
