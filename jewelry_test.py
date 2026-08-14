import asyncio
import csv
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"
START_URL = "https://jacobandco.shop/pages/collections"

OUTPUT_CSV = "shop_variant_test_results.csv"


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

    if not path.startswith("/collections/"):
        return ""

    if path == "/collections/all":
        return ""

    return BASE_URL + path


async def discover_collections(page):

    await page.goto(
        START_URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    await page.wait_for_timeout(
        3000
    )

    links = await page.locator(
        "a"
    ).evaluate_all(
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
            collections[url] = name

    return collections


async def fetch_collection_products(
    request_context,
    collection_url,
    collection_name
):

    parsed = urlparse(
        collection_url
    )

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

    response = await request_context.get(
        api_url,
        timeout=60000
    )

    if not response.ok:

        print(
            "FAILED:",
            response.status,
            collection_name,
            api_url
        )

        return []

    data = await response.json()

    products = data.get(
        "products",
        []
    )

    if not isinstance(
        products,
        list
    ):
        return []

    return products


def normalize_price(value):

    if value is None:
        return ""

    value = str(
        value
    ).strip()

    if not value:
        return ""

    try:
        return round(
            float(value),
            2
        )

    except Exception:
        return value


async def main():

    print("=" * 70)
    print("JACOB & CO. SHOP VARIANT FINAL TEST")
    print("=" * 70)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            locale="en-US"
        )

        page = await context.new_page()

        collections = await discover_collections(
            page
        )

        print()
        print(
            "Collections found:",
            len(collections)
        )

        # ----------------------------------------------------
        # Product ID -> product data + collections
        # ----------------------------------------------------

        product_map = {}

        successful_collections = 0
        failed_collections = 0

        for collection_url, collection_name in sorted(
            collections.items()
        ):

            try:

                products = await fetch_collection_products(
                    context.request,
                    collection_url,
                    collection_name
                )

                successful_collections += 1

            except Exception as e:

                print(
                    "COLLECTION ERROR:",
                    collection_name,
                    repr(e)
                )

                failed_collections += 1
                continue

            print(
                collection_name or collection_url,
                ":",
                len(products)
            )

            for product in products:

                product_id = str(
                    product.get(
                        "id",
                        ""
                    )
                ).strip()

                if not product_id:
                    continue

                if product_id not in product_map:

                    product_map[
                        product_id
                    ] = {
                        "product":
                            product,
                        "collections":
                            set()
                    }

                product_map[
                    product_id
                ][
                    "collections"
                ].add(
                    collection_name
                    or collection_url
                )

        await browser.close()

    # ========================================================
    # BUILD VARIANT ROWS
    # ========================================================

    rows = []

    for product_id, info in product_map.items():

        product = info[
            "product"
        ]

        collections_text = " | ".join(
            sorted(
                info[
                    "collections"
                ]
            )
        )

        title = str(
            product.get(
                "title",
                ""
            )
        ).strip()

        handle = str(
            product.get(
                "handle",
                ""
            )
        ).strip()

        vendor = str(
            product.get(
                "vendor",
                ""
            )
        ).strip()

        product_type = str(
            product.get(
                "product_type",
                product.get(
                    "type",
                    ""
                )
            )
        ).strip()

        product_url = (
            BASE_URL
            + "/products/"
            + handle
        )

        variants = product.get(
            "variants",
            []
        )

        if not isinstance(
            variants,
            list
        ):
            variants = []

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

            price = normalize_price(
                variant.get(
                    "price"
                )
            )

            compare_at_price = normalize_price(
                variant.get(
                    "compare_at_price"
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
                    title,

                "Variant":
                    variant_title,

                "Product Type":
                    product_type,

                "Vendor":
                    vendor,

                "Collections":
                    collections_text,

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

    # ========================================================
    # DEDUPE BY UNIQUE KEY
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
    # STATISTICS
    # ========================================================

    unique_products = len(
        product_map
    )

    total_variants = len(
        rows
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

    available = sum(
        1
        for row in rows
        if row[
            "Available"
        ] == "YES"
    )

    sold_out = (
        total_variants
        - available
    )

    sku_list = [
        row[
            "SKU"
        ]
        for row in rows
        if row[
            "SKU"
        ]
    ]

    duplicate_skus = (
        len(sku_list)
        - len(
            set(
                sku_list
            )
        )
    )

    # ========================================================
    # CSV
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
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("FINAL VARIANT RESULT")
    print("=" * 70)

    print(
        "Collections found       :",
        len(collections)
    )

    print(
        "Collections success     :",
        successful_collections
    )

    print(
        "Collections failed      :",
        failed_collections
    )

    print(
        "Unique Products         :",
        unique_products
    )

    print(
        "Total Variants          :",
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
        duplicate_skus
    )

    print(
        "With USD Price          :",
        with_price
    )

    print(
        "Without Price           :",
        without_price
    )

    print(
        "Available               :",
        available
    )

    print(
        "Sold Out / Unavailable  :",
        sold_out
    )

    print(
        "Output CSV              :",
        OUTPUT_CSV
    )

    print("=" * 70)

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
