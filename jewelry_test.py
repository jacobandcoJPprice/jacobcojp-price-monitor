import asyncio
import csv
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"
START_URL = "https://jacobandco.shop/pages/collections"

OUTPUT_CSV = "jewelry_test_results.csv"

MAX_CONCURRENT = 6


# ============================================================
# URL
# ============================================================

def normalize_product_url(url):

    if not url:
        return ""

    url = urljoin(
        BASE_URL,
        url
    )

    parsed = urlparse(url)

    path = parsed.path.rstrip("/")

    if "/products/" not in path:
        return ""

    # 只保留 /products/handle
    parts = path.split("/products/")

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
# DISCOVER PRODUCTS
# ============================================================

async def discover_product_urls(page):

    print()
    print("=" * 70)
    print("DISCOVERING JEWELRY PRODUCTS")
    print("=" * 70)

    await page.goto(
        START_URL,
        wait_until="networkidle",
        timeout=120000
    )

    await page.wait_for_timeout(
        5000
    )

    # 页面往下滚，确保商品卡片加载出来
    last_height = 0
    stable_count = 0

    for i in range(80):

        await page.evaluate(
            """
            window.scrollTo(
                0,
                document.body.scrollHeight
            )
            """
        )

        await page.wait_for_timeout(
            700
        )

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

    await page.wait_for_timeout(
        2500
    )

    links = await page.locator(
        'a[href*="/products/"]'
    ).evaluate_all(
        """
        els => els.map(
            e => e.href
        )
        """
    )

    product_urls = set()

    for url in links:

        clean = normalize_product_url(
            url
        )

        if clean:
            product_urls.add(
                clean
            )

    product_urls = sorted(
        product_urls
    )

    print(
        "Unique product URLs found:",
        len(product_urls)
    )

    return product_urls


# ============================================================
# SHOPIFY PRODUCT JSON
# ============================================================

async def fetch_product(
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
                    "FAILED:",
                    response.status,
                    json_url
                )

                return None

            data = await response.json()

            return data

        except Exception as e:

            print(
                "ERROR:",
                product_url,
                e
            )

            return None


# ============================================================
# CONVERT PRODUCT → VARIANTS
# ============================================================

def product_to_rows(
    data,
    product_url
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
    )

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

        variant_title = str(
            variant.get(
                "title",
                ""
            )
        ).strip()

        sku = str(
            variant.get(
                "sku",
                ""
            )
        ).strip()

        price_raw = variant.get(
            "price"
        )

        price = ""

        if price_raw is not None:

            try:
                # Shopify .js price 一般是 cents
                price = (
                    float(price_raw)
                    / 100
                )

            except Exception:
                price = ""

        compare_at_raw = variant.get(
            "compare_at_price"
        )

        compare_at_price = ""

        if compare_at_raw is not None:

            try:
                compare_at_price = (
                    float(compare_at_raw)
                    / 100
                )

            except Exception:
                compare_at_price = ""

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

        # SKU 最理想。
        # 如果 SKU 为空，则 Shopify Variant ID 仍可作为稳定唯一键。
        unique_key = (
            sku
            if sku
            else variant_id
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

            "Price":
                price,

            "Compare At Price":
                compare_at_price,

            "Currency":
                "USD",

            "Available":
                "YES"
                if available
                else "NO",

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
        "JACOB & CO. JEWELRY "
        "SHOPIFY TEST"
    )
    print("=" * 70)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            locale="en-US"
        )

        page = await context.new_page()

        # ----------------------------------------------------
        # 1. Discover all visible product URLs
        # ----------------------------------------------------

        product_urls = (
            await discover_product_urls(
                page
            )
        )

        if not product_urls:

            raise RuntimeError(
                "No jewelry product URLs found."
            )

        # ----------------------------------------------------
        # 2. Fetch Shopify product JSON
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("READING SHOPIFY PRODUCT DATA")
        print("=" * 70)

        semaphore = asyncio.Semaphore(
            MAX_CONCURRENT
        )

        tasks = [

            fetch_product(
                context.request,
                url,
                semaphore
            )

            for url in product_urls
        ]

        results = await asyncio.gather(
            *tasks
        )

        await browser.close()

    # --------------------------------------------------------
    # 3. Convert products / variants
    # --------------------------------------------------------

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

        product_rows = (
            product_to_rows(
                data,
                product_url
            )
        )

        if product_rows:

            successful_products += 1

            rows.extend(
                product_rows
            )

        else:

            failed_products += 1

    # --------------------------------------------------------
    # 4. Variant ID dedupe
    # --------------------------------------------------------

    unique_rows = {}

    for row in rows:

        key = row[
            "Unique Key"
        ]

        if not key:
            continue

        unique_rows[
            key
        ] = row

    rows = list(
        unique_rows.values()
    )

    rows.sort(
        key=lambda x: (
            x[
                "Product"
            ].lower(),
            x[
                "Variant"
            ].lower(),
            x[
                "SKU"
            ].lower()
        )
    )

    # --------------------------------------------------------
    # 5. Statistics
    # --------------------------------------------------------

    with_price = sum(
        1
        for row in rows
        if row[
            "Price"
        ] != ""
    )

    without_price = (
        len(rows)
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
        len(rows)
        - with_sku
    )

    available = sum(
        1
        for row in rows
        if row[
            "Available"
        ] == "YES"
    )

    sold_out = (
        len(rows)
        - available
    )

    unique_skus = {
        row["SKU"]
        for row in rows
        if row["SKU"]
    }

    duplicate_sku_count = (
        with_sku
        - len(
            unique_skus
        )
    )

    # --------------------------------------------------------
    # 6. Save CSV
    # --------------------------------------------------------

    fields = [
        "Unique Key",
        "Product ID",
        "Variant ID",
        "SKU",
        "Product",
        "Variant",
        "Product Type",
        "Vendor",
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
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(
            rows
        )

    # --------------------------------------------------------
    # 7. Final report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("JEWELRY TEST RESULT")
    print("=" * 70)

    print(
        "Product URLs discovered :",
        len(product_urls)
    )

    print(
        "Products successfully read:",
        successful_products
    )

    print(
        "Products failed          :",
        failed_products
    )

    print(
        "Total variants           :",
        len(rows)
    )

    print(
        "With USD price           :",
        with_price
    )

    print(
        "Without price            :",
        without_price
    )

    print(
        "With SKU                 :",
        with_sku
    )

    print(
        "Without SKU              :",
        without_sku
    )

    print(
        "Duplicate SKU count      :",
        duplicate_sku_count
    )

    print(
        "Available                :",
        available
    )

    print(
        "Sold out / unavailable   :",
        sold_out
    )

    print(
        "Output file              :",
        OUTPUT_CSV
    )

    print("=" * 70)

    print()
    print("FIRST 15 VARIANTS")
    print("-" * 70)

    for row in rows[:15]:

        print(
            row["SKU"]
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
