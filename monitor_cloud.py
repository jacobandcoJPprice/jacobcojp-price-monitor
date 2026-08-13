import asyncio
import csv
import json
import os
import re
from datetime import datetime

from playwright.async_api import async_playwright


PRICE_PAGE = "https://jacobandco.com/timepiece-prices"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(
    BASE_DIR,
    "current_prices.csv"
)

HISTORY_CSV = os.path.join(
    BASE_DIR,
    "price_history_v2.csv"
)


# ============================================================
# BASIC
# ============================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_csv(path):
    if not os.path.exists(path):
        return []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, fieldnames, rows):
    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# ITEM NUMBER
# ============================================================

ITEM_NUMBER_PATTERN = re.compile(
    r"^[A-Z]{1,8}[0-9]{2,8}"
    r"(?:\.[A-Z0-9]+){2,10}$",
    re.I
)


def find_item_number(properties):
    """
    Jacob & Co. DatoCMS 的 properties 中可能同时包含：
    - Item Number
    - 尺寸
    - 限量数量
    - 其他属性

    自动寻找类似：
    BU300.22.AA.AA.B
    TT800.40.BD.AB.A
    """

    if not isinstance(properties, list):
        return ""

    for prop in properties:

        if not isinstance(prop, dict):
            continue

        value = str(
            prop.get("property", "")
        ).strip()

        if ITEM_NUMBER_PATTERN.match(value):
            return value

    return ""


# ============================================================
# PRICE
# ============================================================

def normalize_price(value):

    if value is None:
        return ""

    try:
        return float(value)

    except Exception:
        return ""


# ============================================================
# GRAPHQL RESPONSE PARSING
# ============================================================

def extract_products_from_json(data):
    """
    在 GraphQL JSON 中递归寻找 timepieceProducts。
    """

    results = []

    if isinstance(data, dict):

        for key, value in data.items():

            if (
                key == "timepieceProducts"
                and isinstance(value, list)
            ):
                results.extend(value)

            else:
                results.extend(
                    extract_products_from_json(value)
                )

    elif isinstance(data, list):

        for value in data:
            results.extend(
                extract_products_from_json(value)
            )

    return results


def convert_products_to_rows(products):

    rows = []

    seen_variant_ids = set()

    for product in products:

        if not isinstance(product, dict):
            continue

        product_name = str(
            product.get("name", "")
        ).strip()

        product_id = str(
            product.get("id", "")
        ).strip()

        variants = product.get(
            "variants",
            []
        )

        if not isinstance(variants, list):
            continue

        for variant in variants:

            if not isinstance(variant, dict):
                continue

            variant_id = str(
                variant.get("id", "")
            ).strip()

            # 防止 GraphQL response 重复
            if variant_id and variant_id in seen_variant_ids:
                continue

            if variant_id:
                seen_variant_ids.add(variant_id)

            variant_name = str(
                variant.get("name", "")
            ).strip()

            usd_price = normalize_price(
                variant.get("usdPrice")
            )

            properties = variant.get(
                "properties",
                []
            )

            item_number = find_item_number(
                properties
            )

            image_url = ""

            image = variant.get("image")

            if isinstance(image, dict):
                image_url = str(
                    image.get("url", "")
                ).strip()

            hidden = bool(
                variant.get(
                    "hideFromCollectionPages",
                    False
                )
            )

            availability = (
                "PRICE AVAILABLE"
                if usd_price != ""
                else "INQUIRE"
            )

            rows.append({

                "Collection":
                    product_name,

                "Variant":
                    variant_name,

                "Item Number":
                    item_number,

                "Price":
                    usd_price,

                "Currency":
                    "USD",

                "Availability":
                    availability,

                "Image URL":
                    image_url,

                "Product ID":
                    product_id,

                "Variant ID":
                    variant_id,

                "Hidden":
                    "YES" if hidden else "NO",

                "Source":
                    PRICE_PAGE,

                "Last Seen":
                    now()

            })

    return rows


# ============================================================
# HISTORY
# ============================================================

def build_old_map(rows):

    result = {}

    for row in rows:

        # Item Number 优先作为唯一识别码
        item_number = str(
            row.get(
                "Item Number",
                ""
            )
        ).strip()

        variant_id = str(
            row.get(
                "Variant ID",
                ""
            )
        ).strip()

        key = (
            item_number
            or variant_id
        )

        if key:
            result[key] = row

    return result


def update_history(
    old_map,
    new_rows,
    history
):

    changes = 0

    for item in new_rows:

        item_number = str(
            item.get(
                "Item Number",
                ""
            )
        ).strip()

        variant_id = str(
            item.get(
                "Variant ID",
                ""
            )
        ).strip()

        key = (
            item_number
            or variant_id
        )

        if not key:
            continue

        old = old_map.get(key)

        # 第一次进入数据库，不算价格变化
        if not old:
            continue

        old_price = str(
            old.get(
                "Price",
                ""
            )
        ).strip()

        new_price = str(
            item.get(
                "Price",
                ""
            )
        ).strip()

        if old_price == new_price:
            continue

        history.append({

            "Changed At":
                now(),

            "Collection":
                item.get(
                    "Collection",
                    ""
                ),

            "Variant":
                item.get(
                    "Variant",
                    ""
                ),

            "Item Number":
                item_number,

            "Old Price":
                old_price,

            "New Price":
                new_price,

            "Currency":
                "USD",

            "Source":
                PRICE_PAGE

        })

        changes += 1

        print()
        print("=" * 70)
        print("PRICE CHANGE DETECTED")
        print("=" * 70)
        print("Product     :", item.get("Collection", ""))
        print("Variant     :", item.get("Variant", ""))
        print("Item Number :", item_number)
        print("Old Price   :", old_price or "INQUIRE")
        print("New Price   :", new_price or "INQUIRE")

    return changes


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print("=" * 70)
    print("JACOB & CO. OFFICIAL PRICE LIST MONITOR")
    print("=" * 70)
    print("Source:", PRICE_PAGE)

    graphql_data = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            locale="en-US"
        )

        page = await context.new_page()

        async def capture_response(response):

            if "graphql.datocms.com" not in response.url:
                return

            try:

                body = await response.text()

                data = json.loads(body)

                graphql_data.append(data)

                print(
                    "Captured DatoCMS GraphQL:",
                    len(body),
                    "bytes"
                )

            except Exception as e:

                print(
                    "GraphQL capture error:",
                    e
                )

        page.on(
            "response",
            capture_response
        )

        print()
        print("Opening official price page...")

        await page.goto(
            PRICE_PAGE,
            wait_until="networkidle",
            timeout=120000
        )

        # 给页面一点时间完成所有 GraphQL 请求
        await page.wait_for_timeout(
            5000
        )

        await browser.close()

    print()
    print(
        "GraphQL responses captured:",
        len(graphql_data)
    )

    if not graphql_data:

        raise RuntimeError(
            "No DatoCMS GraphQL data captured."
        )

    # ========================================================
    # FIND PRODUCTS
    # ========================================================

    products = []

    for data in graphql_data:

        products.extend(
            extract_products_from_json(
                data
            )
        )

    # Product ID 去重
    unique_products = {}

    for product in products:

        if not isinstance(product, dict):
            continue

        product_id = str(
            product.get("id", "")
        )

        if product_id:
            unique_products[
                product_id
            ] = product

    products = list(
        unique_products.values()
    )

    print()
    print("=" * 70)
    print("OFFICIAL PRICE PAGE DATA")
    print("=" * 70)

    print(
        "Products:",
        len(products)
    )

    # ========================================================
    # CONVERT VARIANTS
    # ========================================================

    rows = convert_products_to_rows(
        products
    )

    if not rows:

        raise RuntimeError(
            "No variants found in official price page data."
        )

    with_price = sum(
        1
        for row in rows
        if row["Price"] != ""
    )

    without_price = (
        len(rows)
        -
        with_price
    )

    with_item_number = sum(
        1
        for row in rows
        if row["Item Number"]
    )

    without_item_number = (
        len(rows)
        -
        with_item_number
    )

    hidden_count = sum(
        1
        for row in rows
        if row["Hidden"] == "YES"
    )

    print(
        "Variants:",
        len(rows)
    )

    print(
        "With USD Price:",
        with_price
    )

    print(
        "Without USD Price:",
        without_price
    )

    print(
        "With Item Number:",
        with_item_number
    )

    print(
        "Without Item Number:",
        without_item_number
    )

    print(
        "Hidden Variants:",
        hidden_count
    )

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    # 防止网站/API异常导致突然写入一个明显不完整的数据库
    if len(rows) < 50:

        raise RuntimeError(
            f"Safety stop: only {len(rows)} variants found."
        )

    # ========================================================
    # OLD DATA + HISTORY
    # ========================================================

    old_rows = read_csv(
        CURRENT_CSV
    )

    history = read_csv(
        HISTORY_CSV
    )

    old_map = build_old_map(
        old_rows
    )

    changes = update_history(
        old_map,
        rows,
        history
    )

    # ========================================================
    # SORT
    # ========================================================

    rows.sort(
        key=lambda x: (
            x.get(
                "Collection",
                ""
            ).lower(),
            x.get(
                "Variant",
                ""
            ).lower(),
            x.get(
                "Item Number",
                ""
            ).lower()
        )
    )

    # ========================================================
    # SAVE CURRENT
    # ========================================================

    current_fields = [
        "Collection",
        "Variant",
        "Item Number",
        "Price",
        "Currency",
        "Availability",
        "Image URL",
        "Product ID",
        "Variant ID",
        "Hidden",
        "Source",
        "Last Seen"
    ]

    write_csv(
        CURRENT_CSV,
        current_fields,
        rows
    )

    # ========================================================
    # SAVE HISTORY
    # ========================================================

    history_fields = [
        "Changed At",
        "Collection",
        "Variant",
        "Item Number",
        "Old Price",
        "New Price",
        "Currency",
        "Source"
    ]

    write_csv(
        HISTORY_CSV,
        history_fields,
        history
    )

    print()
    print("=" * 70)
    print("MONITOR COMPLETED")
    print("=" * 70)

    print(
        "Official Products    :",
        len(products)
    )

    print(
        "Official Variants    :",
        len(rows)
    )

    print(
        "With USD Price       :",
        with_price
    )

    print(
        "Without USD Price    :",
        without_price
    )

    print(
        "With Item Number     :",
        with_item_number
    )

    print(
        "Without Item Number  :",
        without_item_number
    )

    print(
        "Price Changes        :",
        changes
    )

    print(
        "Current CSV rows     :",
        len(rows)
    )

    print(
        "History CSV rows     :",
        len(history)
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
