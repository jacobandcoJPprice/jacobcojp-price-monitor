import asyncio
import json
from urllib.parse import urlparse

from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"
START_URL = "https://jacobandco.shop/pages/collections"


def normalize_collection_url(url):
    if not url:
        return ""

    parsed = urlparse(url)

    if not parsed.netloc:
        url = BASE_URL + url
        parsed = urlparse(url)

    if parsed.netloc != "jacobandco.shop":
        return ""

    path = parsed.path.rstrip("/")

    if not path.startswith("/collections/"):
        return ""

    if path == "/collections/all":
        return ""

    return BASE_URL + path


async def main():

    print("=" * 70)
    print("JACOB & CO. SHOPIFY COLLECTION API TEST")
    print("=" * 70)

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            locale="en-US"
        )

        page = await context.new_page()

        # ====================================================
        # STEP 1 - GET COLLECTIONS
        # ====================================================

        print()
        print("Opening collections page...")

        await page.goto(
            START_URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        await page.wait_for_timeout(3000)

        links = await page.locator("a").evaluate_all(
            """
            els => els.map(a => ({
                href: a.href || "",
                text: (a.innerText || "").trim()
            }))
            """
        )

        collections = {}

        for link in links:

            url = normalize_collection_url(
                link.get("href", "")
            )

            if not url:
                continue

            name = (
                link.get("text", "")
                .replace("\\n", " ")
                .strip()
            )

            if url not in collections:
                collections[url] = name

        print(
            "Collections found:",
            len(collections)
        )

        # ====================================================
        # STEP 2 - TEST SHOPIFY COLLECTION JSON
        # ====================================================

        print()
        print("=" * 70)
        print("TESTING COLLECTION JSON ENDPOINTS")
        print("=" * 70)

        successful = 0
        failed = 0
        total_products = 0

        all_product_ids = set()

        for collection_url, collection_name in sorted(
            collections.items()
        ):

            parsed = urlparse(collection_url)

            handle = (
                parsed.path
                .rstrip("/")
                .split("/")[-1]
            )

            api_url = (
                BASE_URL
                + "/collections/"
                + handle
                + "/products.json?limit=250"
            )

            print()
            print("----------------------------------------")
            print(
                "COLLECTION:",
                collection_name or handle
            )
            print(
                "HANDLE:",
                handle
            )
            print(
                "API:",
                api_url
            )

            try:

                response = await context.request.get(
                    api_url,
                    timeout=60000
                )

                print(
                    "HTTP:",
                    response.status
                )

                if not response.ok:

                    print("RESULT: FAILED")
                    failed += 1
                    continue

                content_type = (
                    response.headers.get(
                        "content-type",
                        ""
                    )
                )

                print(
                    "CONTENT TYPE:",
                    content_type
                )

                try:

                    data = await response.json()

                except Exception:

                    text = await response.text()

                    print(
                        "NOT JSON."
                    )

                    print(
                        "FIRST 300 CHARS:"
                    )

                    print(
                        text[:300]
                    )

                    failed += 1
                    continue

                products = data.get(
                    "products",
                    []
                )

                print(
                    "PRODUCTS:",
                    len(products)
                )

                if products:

                    successful += 1

                else:

                    print(
                        "WARNING: ZERO PRODUCTS"
                    )

                total_products += len(
                    products
                )

                for product in products:

                    product_id = str(
                        product.get(
                            "id",
                            ""
                        )
                    )

                    if product_id:
                        all_product_ids.add(
                            product_id
                        )

                # --------------------------------------------
                # SHOW FIRST PRODUCT
                # --------------------------------------------

                if products:

                    first = products[0]

                    print()
                    print("FIRST PRODUCT:")
                    print(
                        "Title:",
                        first.get(
                            "title",
                            ""
                        )
                    )

                    print(
                        "Handle:",
                        first.get(
                            "handle",
                            ""
                        )
                    )

                    print(
                        "Product ID:",
                        first.get(
                            "id",
                            ""
                        )
                    )

                    variants = first.get(
                        "variants",
                        []
                    )

                    print(
                        "Variants:",
                        len(variants)
                    )

                    if variants:

                        variant = variants[0]

                        print(
                            "Variant ID:",
                            variant.get(
                                "id",
                                ""
                            )
                        )

                        print(
                            "SKU:",
                            variant.get(
                                "sku",
                                ""
                            )
                        )

                        print(
                            "Price:",
                            variant.get(
                                "price",
                                ""
                            )
                        )

                        print(
                            "Available:",
                            variant.get(
                                "available",
                                ""
                            )
                        )

            except Exception as e:

                print(
                    "ERROR:",
                    repr(e)
                )

                failed += 1

        await browser.close()

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 70)
    print("FINAL API TEST RESULT")
    print("=" * 70)

    print(
        "Collections found       :",
        len(collections)
    )

    print(
        "Collections API success :",
        successful
    )

    print(
        "Collections API failed  :",
        failed
    )

    print(
        "Products before dedupe  :",
        total_products
    )

    print(
        "Unique Product IDs      :",
        len(all_product_ids)
    )

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
