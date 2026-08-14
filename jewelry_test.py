import asyncio
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"
START_URL = "https://jacobandco.shop/pages/collections"


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

    # 排除一些明显不是我们需要的特殊路径
    if path == "/collections/all":
        return ""

    return BASE_URL + path


async def main():
    print("=" * 70)
    print("JACOB & CO. COLLECTION DISCOVERY TEST")
    print("=" * 70)

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            locale="en-US",
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()

        print()
        print("Opening:")
        print(START_URL)
        print()

        response = await page.goto(
            START_URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        if response:
            print("HTTP status:", response.status)

        await page.wait_for_timeout(5000)

        # 直接读取页面所有链接
        links = await page.locator("a").evaluate_all(
            """
            elements => elements.map(a => ({
                href: a.href || "",
                text: (a.innerText || "").trim()
            }))
            """
        )

        print("All <a> elements found:", len(links))

        collections = {}

        for link in links:

            url = normalize_collection_url(
                link.get("href", "")
            )

            if not url:
                continue

            text = (
                link.get("text", "")
                .replace("\\n", " ")
                .strip()
            )

            if url not in collections:
                collections[url] = text

        print()
        print("=" * 70)
        print("COLLECTIONS FOUND")
        print("=" * 70)

        for number, (url, name) in enumerate(
            sorted(collections.items()),
            start=1
        ):
            print(
                f"{number:03d}",
                "|",
                name or "(no text)",
                "|",
                url
            )

        print()
        print("=" * 70)
        print("RESULT")
        print("=" * 70)
        print("Collection URLs found:", len(collections))
        print("=" * 70)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
