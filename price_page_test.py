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

        graphql_responses = []

        async def capture_response(response):

            if "graphql.datocms.com" not in response.url:
                return

            try:
                body = await response.text()

                graphql_responses.append({
                    "url": response.url,
                    "status": response.status,
                    "body": body
                })

            except Exception as e:

                print(
                    "Could not read GraphQL response:",
                    e
                )

        page.on(
            "response",
            capture_response
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

        # ==================================================
        # BODY TEXT
        # ==================================================

        body_text = await page.locator(
            "body"
        ).inner_text()

        print()
        print("=" * 70)
        print("VISIBLE PAGE TEXT")
        print("=" * 70)

        print(body_text[:30000])

        # ==================================================
        # ITEM NUMBERS
        # ==================================================

        item_numbers = sorted(
            set(
                re.findall(
                    r"\b[A-Z]{1,6}"
                    r"[0-9]{2,6}"
                    r"(?:\.[A-Z0-9]+){2,10}\b",
                    body_text
                )
            )
        )

        print()
        print("=" * 70)
        print("VISIBLE ITEM NUMBERS")
        print("=" * 70)

        print("COUNT:", len(item_numbers))

        for item in item_numbers:
            print(item)

        # ==================================================
        # NEXT DATA
        # ==================================================

        print()
        print("=" * 70)
        print("__NEXT_DATA__")
        print("=" * 70)

        next_data = await page.locator(
            "#__NEXT_DATA__"
        ).text_content()

        if next_data:

            print(
                "NEXT DATA SIZE:",
                len(next_data)
            )

            try:

                parsed = json.loads(
                    next_data
                )

                pretty = json.dumps(
                    parsed,
                    indent=2,
                    ensure_ascii=False
                )

                print(
                    pretty[:30000]
                )

            except Exception as e:

                print(
                    "NEXT DATA JSON ERROR:",
                    e
                )

                print(
                    next_data[:30000]
                )

        else:

            print(
                "NO __NEXT_DATA__ CONTENT"
            )

        # ==================================================
        # GRAPHQL RESPONSES
        # ==================================================

        print()
        print("=" * 70)
        print("DATOCMS GRAPHQL RESPONSES")
        print("=" * 70)

        print(
            "GRAPHQL RESPONSE COUNT:",
            len(graphql_responses)
        )

        for index, result in enumerate(
            graphql_responses,
            start=1
        ):

            print()
            print(
                f"--- GRAPHQL RESPONSE {index} ---"
            )

            print(
                "STATUS:",
                result["status"]
            )

            print(
                "URL:",
                result["url"]
            )

            body = result["body"]

            print(
                "BODY SIZE:",
                len(body)
            )

            try:

                data = json.loads(body)

                pretty = json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                )

                print(
                    pretty[:50000]
                )

            except Exception:

                print(
                    body[:50000]
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
