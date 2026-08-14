import asyncio
import csv
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"
START_URL = "https://jacobandco.shop/pages/collections"

OUTPUT_CSV = "jewelry_test_results.csv"

MAX_CONCURRENT = 6


# ============================================================
# URL HELPERS
# ============================================================

def normalize_collection_url(url):

    if not url:
        return ""

    url = urljoin(
        BASE_URL,
        url
    )

    parsed = urlparse(url)

    if parsed.netloc != "jacobandco.shop":
        return ""

    path = parsed.path.rstrip("/")

    if not path.startswith(
        "/collections/"
    ):
        return ""

    if path == "/collections/all":
        return ""

    return BASE_URL + path


def normalize_product_url(url):

    if not url:
        return ""

    url = urljoin(
        BASE_URL,
        url
    )

    parsed = urlparse(url)

    if parsed.netloc != "jacobandco.shop":
        return ""

    path = parsed.path.rstrip("/")

    if "/products/" not in path:
        return ""

    parts = path.split(
        "/products/"
    )

    if len(parts) != 2:
        return ""

    handle = (
        parts[1]
        .split("/")[0]
        .strip()
    )

    if not handle:
        return ""

    return (
        BASE_URL
        + "/products/"
        + handle
    )


# ============================================================
# COLLECTION DISCOVERY
# ============================================================

async def discover_collections(page):

    print()
    print("=" * 70)
    print("DISCOVERING COLLECTIONS")
    print("=" * 70)

    response = await page.goto(
        START_URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    if response:

        print(
            "HTTP status:",
            response.status
        )

    await page.wait_for_timeout(
        5000
    )

    links = await page.locator(
        "a"
    ).evaluate_all(
        """
        elements => elements.map(
            a => ({
                href: a.href || "",
                text:
                    (a.innerText || "")
                    .trim()
            })
        )
        """
    )

    collections = {}

    for link in links:

        url = normalize_collection_url(
            link.get(
                "href",
                ""
            )
        )

        if not url:
            continue

        name = (
            link.get(
                "text",
                ""
            )
            .replace("\n", " ")
            .strip()
        )

        if url not in collections:

            collections[
                url
            ] = name

    print(
        "Collection URLs found:",
        len(collections)
    )

    return collections


# ============================================================
# PRODUCT DISCOVERY
# ============================================================

async def discover_products_from_collection(
    page,
    collection_url,
    collection_name
):

    print()
    print(
        "Collection:",
        collection_name
        or collection_url
    )

    try:

        response = await page.goto(
            collection_url,
            wait_until="domcontentloaded",
            timeout=120000
        )

        if not response:

            print(
                "  No response"
            )

            return []

        if response.status >= 400:

            print(
                "  HTTP:",
                response.status
            )

            return []

        await page.wait_for_timeout(
            2500
        )

        # --------------------------------------------
        # Scroll collection page
        # --------------------------------------------

        last_height = 0
        stable_count = 0

        for _ in range(60):

            await page.evaluate(
                """
                window.scrollTo(
                    0,
                    document.body.scrollHeight
                )
                """
            )

            await page.wait_for_timeout(
                500
            )

            new_height = (
                await page.evaluate(
                    "document.body.scrollHeight"
                )
            )

            if new_height == last_height:

                stable_count += 1

            else:

                stable_count = 0

            last_height = new_height

            if stable_count >= 3:
                break

        # --------------------------------------------
        # Product links
        # --------------------------------------------

        links = await page.locator(
            'a[href*="/products/"]'
        ).evaluate_all(
            """
            elements => elements.map(
                a => a.href || ""
            )
            """
        )

        products = set()

        for link in links:

            clean = normalize_product_url(
                link
            )

            if clean:

                products.add(
                    clean
                )

        print(
            "  Products found:",
            len(products)
        )

        return sorted(
            products
        )

    except Exception as e:

        print(
            "  ERROR:",
            e
        )

        return []


# ============================================================
# SHOPIFY PRODUCT DATA
# ============================================================

async def fetch_product_data(
    request_context,
    product_url,
    semaphore
):

    async with semaphore:

        json_url = (
            product_url
            + ".js"
        )

        try:

            response = (
                await request_context.get(
                    json_url,
                    timeout=60000
                )
            )

            if not response.ok:

                print(
                    "PRODUCT FAILED:",
                    response.status,
                    product_url
                )

                return None

            return await response.json()

        except Exception as e:

            print(
                "PRODUCT ERROR:",
                product_url,
                e
            )

            return None


# ============================================================
# PRICE
# ============================================================

def convert_shopify_price(
    value
):

    if value is None:
        return ""

    try:

        number = float(
            value
        )

        return round(
            number / 100,
            2
        )

    except Exception:

        return ""


# ============================================================
# PRODUCT → VARIANTS
# ============================================================

def product_to_rows(
    data,
    product_url,
    collections
):

    rows = []

    if not isinstance(
        data,
        dict
    ):
        return rows

    product_id = str(
        data.get(
            "id",
            ""
        )
    ).strip()

    product_title = str(
        data.get(
            "title",
            ""
        )
    ).strip()

    handle = str(
        data.get(
            "handle",
            ""
        )
    ).strip()

    vendor = str(
        data.get(
            "vendor",
            ""
        )
    ).strip()

    product_type = str(
        data.get(
            "type",
            ""
        )
    ).strip()

    variants = data.get(
        "variants",
        []
    )

    if not isinstance(
        variants,
        list
    ):

        return rows

    collection_text = " | ".join(
        sorted(
            collections
        )
    )

    for variant in variants:

        if not isinstance(
            variant,
            dict
        ):
            continue

        variant_id = str(
            variant.get(
                "id",
                ""
            )
        ).strip()

        sku = str(
            variant.get(
                "sku",
                ""
            )
            or ""
        ).strip()

        variant_title = str(
            variant.get(
                "title",
                ""
            )
            or ""
        ).strip()

        price = convert_shopify_price(
            variant.get(
                "price"
            )
        )

        compare_at_price = (
            convert_shopify_price(
                variant.get(
                    "compare_at_price"
                )
            )
        )

        available = variant.get(
            "available",
            False
        )

        option1 = str(
            variant.get(
                "option1",
                ""
            )
            or ""
        ).strip()

        option2 = str(
            variant.get(
                "option2",
                ""
            )
            or ""
        ).strip()

        option3 = str(
            variant.get(
                "option3",
                ""
            )
            or ""
        ).strip()

        # --------------------------------------------
        # Stable unique key
        # --------------------------------------------

        if sku:

            unique_key = (
                "SKU:"
                + sku
            )

        elif variant_id:

            unique_key = (
                "VARIANT:"
                + variant_id
            )

        else:

            unique_key = (
                "PRODUCT:"
                + product_id
                + ":"
                + variant_title
            )

        rows.append({

            "Unique Key":
                unique_key,

            "Product ID":
                product_id,

            "Variant ID":
                variant_id,

            "SKU":
                sku,

            "Product":
                product_title,

            "Variant":
                variant_title,

            "Product Type":
                product_type,

            "Vendor":
                vendor,

            "Collections":
                collection_text,

            "Price":
                price,

            "Compare At Price":
                compare_at_price,

            "Currency":
                "USD",

            "Available":
                (
                    "YES"
                    if available
                    else "NO"
                ),

            "Option 1":
                option1,

            "Option 2":
                option2,

            "Option 3":
                option3,

            "Handle":
                handle,

            "URL":
                product_url

        })

    return rows


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print("=" * 70)
    print(
        "JACOB & CO. "
        "COLLECTION PRODUCT TEST"
    )
    print("=" * 70)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            locale="en-US",
            viewport={
                "width": 1920,
                "height": 1080
            }
        )

        page = await context.new_page()

        # ====================================================
        # 1. COLLECTIONS
        # ====================================================

        collections = (
            await discover_collections(
                page
            )
        )

        if not collections:

            raise RuntimeError(
                "No collections found."
            )

        # ====================================================
        # 2. PRODUCTS
        # ====================================================

        print()
        print("=" * 70)
        print("DISCOVERING PRODUCTS")
        print("=" * 70)

        product_collections = {}

        for (
            collection_url,
            collection_name
        ) in sorted(
            collections.items()
        ):

            products = (
                await discover_products_from_collection(
                    page,
                    collection_url,
                    collection_name
                )
            )

            for product_url in products:

                if (
                    product_url
                    not in product_collections
                ):

                    product_collections[
                        product_url
                    ] = set()

                product_collections[
                    product_url
                ].add(
                    collection_name
                    or collection_url
                )

        product_urls = sorted(
            product_collections.keys()
        )

        print()
        print(
            "Unique product URLs:",
            len(product_urls)
        )

        if not product_urls:

            raise RuntimeError(
                "No product URLs found "
                "inside collections."
            )

        # ====================================================
        # 3. SHOPIFY PRODUCT DATA
        # ====================================================

        print()
        print("=" * 70)
        print(
            "READING SHOPIFY "
            "PRODUCT DATA"
        )
        print("=" * 70)

        semaphore = (
            asyncio.Semaphore(
                MAX_CONCURRENT
            )
        )

        tasks = [

            fetch_product_data(
                context.request,
                product_url,
                semaphore
            )

            for product_url
            in product_urls
        ]

        results = await asyncio.gather(
            *tasks
        )

        await browser.close()

    # ========================================================
    # 4. BUILD VARIANT ROWS
    # ========================================================

    rows = []

    successful_products = 0
    failed_products = 0

    for product_url, data in zip(
        product_urls,
        results
    ):

        if not data:

            failed_products += 1
            continue

        product_rows = product_to_rows(
            data,
            product_url,
            product_collections[
                product_url
            ]
        )

        if product_rows:

            successful_products += 1

            rows.extend(
                product_rows
            )

        else:

            failed_products += 1

    # ========================================================
    # 5. DEDUPE
    # ========================================================

    unique_rows = {}

    for row in rows:

        key = row.get(
            "Unique Key",
            ""
        )

        if not key:
            continue

        unique_rows[
            key
        ] = row

    rows = list(
        unique_rows.values()
    )

    rows.sort(
        key=lambda row: (
            row.get(
                "Product",
                ""
            ).lower(),

            row.get(
                "Variant",
                ""
            ).lower()
        )
    )

    # ========================================================
    # 6. STATISTICS
    # ========================================================

    total_variants = len(
        rows
    )

    with_price = sum(
        1
        for row in rows
        if row[
            "Price"
        ] != ""
    )

    without_price = (
        total_variants
        - with_price
    )

    with_sku = sum(
        1
        for row in rows
        if row[
            "SKU"
        ]
    )

    without_sku = (
        total_variants
        - with_sku
    )

    available = sum(
        1
        for row in rows
        if row[
            "Available"
        ] == "YES"
    )

    unavailable = (
        total_variants
        - available
    )

    sku_values = [
        row[
            "SKU"
        ]
        for row in rows
        if row[
            "SKU"
        ]
    ]

    duplicate_sku_count = (
        len(sku_values)
        - len(
            set(
                sku_values
            )
        )
    )

    # ========================================================
    # 7. CSV
    # ========================================================

    fields = [
        "Unique Key",
        "Product ID",
        "Variant ID",
        "SKU",
        "Product",
        "Variant",
        "Product Type",
        "Vendor",
        "Collections",
        "Price",
        "Compare At Price",
        "Currency",
        "Available",
        "Option 1",
        "Option 2",
        "Option 3",
        "Handle",
        "URL"
    ]

    with open(
        OUTPUT_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )

        writer.writeheader()

        writer.writerows(
            rows
        )

    # ========================================================
    # 8. FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        "Collections found       :",
        len(collections)
    )

    print(
        "Product URLs found      :",
        len(product_urls)
    )

    print(
        "Products read           :",
        successful_products
    )

    print(
        "Products failed         :",
        failed_products
    )

    print(
        "Total variants          :",
        total_variants
    )

    print(
        "With SKU                :",
        with_sku
    )

    print(
        "Without SKU             :",
        without_sku
    )

    print(
        "Duplicate SKU count     :",
        duplicate_sku_count
    )

    print(
        "With price              :",
        with_price
    )

    print(
        "Without price           :",
        without_price
    )

    print(
        "Available               :",
        available
    )

    print(
        "Sold out / unavailable  :",
        unavailable
    )

    print(
        "Output CSV              :",
        OUTPUT_CSV
    )

    print("=" * 70)

    # ========================================================
    # SAMPLE
    # ========================================================

    print()
    print("FIRST 20 VARIANTS")
    print("-" * 70)

    for row in rows[:20]:

        print(
            row[
                "SKU"
            ]
            or (
                "VariantID:"
                + row[
                    "Variant ID"
                ]
            ),
            "|",
            row[
                "Product"
            ],
            "|",
            row[
                "Variant"
            ],
            "| $",
            row[
                "Price"
            ],
            "|",
            row[
                "Available"
            ]
        )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
