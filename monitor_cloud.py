import asyncio
import csv
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(
    BASE_DIR,
    "current_prices.csv"
)

HISTORY_CSV = os.path.join(
    BASE_DIR,
    "price_history_v2.csv"
)

SITE_URL = "https://jacobandco.com/timepieces"

VARIANT_SITEMAP = (
    "https://jacobandco.com/sitemap-variants.xml"
)

REQUEST_DELAY = 1.2


# ============================================================
# BASIC
# ============================================================

def now():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def normalize_url(url):
    if not url:
        return ""

    url = url.strip()
    url = url.split("#")[0]

    # 修复 sitemap 中可能出现的 mojibake
    try:
        if "Ã" in url:
            url = (
                url
                .encode("latin1")
                .decode("utf-8")
            )
    except Exception:
        pass

    if url.endswith("/"):
        url = url[:-1]

    return url


def read_csv(path):
    if not os.path.exists(path):
        return []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def write_csv(
    path,
    fieldnames,
    rows
):
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
# OFFICIAL SITEMAP
# ============================================================

def get_official_variant_urls():

    print()
    print("=" * 70)
    print("Reading official Variant Sitemap...")
    print("=" * 70)

    try:
        response = requests.get(
            VARIANT_SITEMAP,
            timeout=60,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
            }
        )

        response.raise_for_status()

        # 强制 UTF-8，避免 pavé -> pavÃ©
        text = response.content.decode(
            "utf-8",
            errors="replace"
        )

        urls = re.findall(
            r"<loc>(.*?)</loc>",
            text,
            flags=re.I | re.S
        )

        cleaned = set()

        for url in urls:

            url = normalize_url(url)

            if "/timepieces/" not in url.lower():
                continue

            cleaned.add(url)

        print(
            "Official Variant URLs:",
            len(cleaned)
        )

        return cleaned

    except Exception as e:

        print(
            "ERROR reading Variant Sitemap:",
            e
        )

        return set()


# ============================================================
# SCHEMA DATA
# ============================================================

def get_item_number(variant):

    candidates = [
        "sku",
        "itemNumber",
        "item_number",
        "mpn",
        "productID"
    ]

    for key in candidates:

        value = variant.get(key)

        if value:
            return str(value).strip()

    return ""


def get_variant_name(variant):

    for key in [
        "name",
        "model",
        "title"
    ]:

        value = variant.get(key)

        if value:
            return str(value).strip()

    url = variant.get(
        "url",
        ""
    )

    if url:

        slug = (
            urlparse(url)
            .path
            .rstrip("/")
            .split("/")[-1]
        )

        return (
            slug
            .replace("-", " ")
            .title()
        )

    return ""


def extract_offer(variant):

    offers = variant.get(
        "offers"
    )

    if not offers:
        return None, "", ""

    if isinstance(
        offers,
        list
    ):

        if not offers:
            return None, "", ""

        offers = offers[0]

    if not isinstance(
        offers,
        dict
    ):
        return None, "", ""

    price = offers.get(
        "price"
    )

    currency = offers.get(
        "priceCurrency",
        ""
    )

    availability = offers.get(
        "availability",
        ""
    )

    if price is not None:

        try:
            price = float(
                str(price).replace(
                    ",",
                    ""
                )
            )

        except Exception:
            price = None

    return (
        price,
        currency,
        availability
    )


def walk_for_schema_product(obj):

    results = []

    if isinstance(
        obj,
        dict
    ):

        if "schemaOrgProduct" in obj:

            results.append(
                obj[
                    "schemaOrgProduct"
                ]
            )

        for value in obj.values():

            results.extend(
                walk_for_schema_product(
                    value
                )
            )

    elif isinstance(
        obj,
        list
    ):

        for value in obj:

            results.extend(
                walk_for_schema_product(
                    value
                )
            )

    return results


# ============================================================
# EXTRACT VARIANTS FROM PAGE
# ============================================================

async def extract_variants(page):

    scripts = await page.locator(
        "script"
    ).all()

    found = []

    for script in scripts:

        try:
            text = (
                await script.text_content()
            )

            if not text:
                continue

            if (
                "schemaOrgProduct"
                not in text
            ):
                continue

            try:
                data = json.loads(text)

            except Exception:
                continue

            products = (
                walk_for_schema_product(
                    data
                )
            )

            for product in products:

                if not isinstance(
                    product,
                    dict
                ):
                    continue

                collection_name = str(
                    product.get(
                        "name",
                        ""
                    )
                ).strip()

                variants = product.get(
                    "hasVariant",
                    []
                )

                if isinstance(
                    variants,
                    dict
                ):
                    variants = [
                        variants
                    ]

                if not isinstance(
                    variants,
                    list
                ):
                    continue

                for variant in variants:

                    if not isinstance(
                        variant,
                        dict
                    ):
                        continue

                    (
                        price,
                        currency,
                        availability
                    ) = extract_offer(
                        variant
                    )

                    variant_url = normalize_url(
                        variant.get(
                            "url",
                            ""
                        )
                    )

                    if not variant_url:

                        offers = variant.get(
                            "offers"
                        )

                        if isinstance(
                            offers,
                            dict
                        ):

                            variant_url = normalize_url(
                                offers.get(
                                    "url",
                                    ""
                                )
                            )

                    if not variant_url:
                        continue

                    found.append({

                        "Collection":
                            collection_name,

                        "Variant":
                            get_variant_name(
                                variant
                            ),

                        "Item Number":
                            get_item_number(
                                variant
                            ),

                        "Price":
                            (
                                ""
                                if price is None
                                else price
                            ),

                        "Currency":
                            currency,

                        "Availability":
                            availability,

                        "URL":
                            variant_url,

                        "Last Seen":
                            now()

                    })

        except Exception:
            pass

    unique = {}

    for item in found:

        unique[
            normalize_url(
                item["URL"]
            )
        ] = item

    return list(
        unique.values()
    )


# ============================================================
# COLLECTION DISCOVERY
# ============================================================

async def get_collection_links(
    page
):

    print()
    print("=" * 70)
    print("Scanning collection pages...")
    print("=" * 70)

    await page.goto(
        SITE_URL,
        wait_until="domcontentloaded",
        timeout=90000
    )

    await page.wait_for_timeout(
        5000
    )

    for _ in range(10):

        await page.evaluate(
            "window.scrollTo("
            "0, document.body.scrollHeight)"
        )

        await page.wait_for_timeout(
            1000
        )

    links = await page.locator(
        'a[href^="/timepieces/"]'
    ).evaluate_all(
        """
        els => els.map(e => e.href)
        """
    )

    cleaned = set()

    for url in links:

        if not url:
            continue

        parsed = urlparse(url)

        path = (
            parsed.path
            .rstrip("/")
        )

        parts = [
            p
            for p
            in path.split("/")
            if p
        ]

        # Collection 页面：
        # /timepieces/collection-name

        if len(parts) != 2:
            continue

        if parts[0] != "timepieces":
            continue

        cleaned.add(
            normalize_url(url)
        )

    links = sorted(
        cleaned
    )

    print(
        "Collection pages:",
        len(links)
    )

    return links


# ============================================================
# FALLBACK DIRECT VARIANT PAGE
# ============================================================

async def scrape_missing_variant(
    page,
    target_url
):

    print()
    print(
        "Fallback Variant:",
        target_url
    )

    try:

        await page.goto(
            target_url,
            wait_until="networkidle",
            timeout=90000
        )

        await page.wait_for_timeout(
            1800
        )

        variants = await extract_variants(
            page
        )

        # 优先精确 URL 匹配
        for item in variants:

            if (
                normalize_url(
                    item["URL"]
                )
                ==
                normalize_url(
                    target_url
                )
            ):

                print(
                    "  MATCH:",
                    item["Variant"],
                    item["Price"]
                )

                return item

        # 如果 schema 没有返回自己，
        # 至少创建一条无价格监控记录

        html = await page.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        page_text = " ".join(
            soup.stripped_strings
        )

        # 名称
        name = ""

        h1 = soup.find("h1")

        if h1:
            name = h1.get_text(
                " ",
                strip=True
            )

        if not name:

            slug = (
                urlparse(
                    target_url
                )
                .path
                .rstrip("/")
                .split("/")[-1]
            )

            name = (
                slug
                .replace("-", " ")
                .title()
            )

        # Item Number
        item_number = ""

        patterns = [
            (
                r"ITEM\s*NUMBER"
                r"\s*[:#]?\s*"
                r"([A-Za-z0-9.\-]+)"
            ),
            (
                r"ITEM\s*NO\.?"
                r"\s*[:#]?\s*"
                r"([A-Za-z0-9.\-]+)"
            ),
            (
                r"SKU"
                r"\s*[:#]?\s*"
                r"([A-Za-z0-9.\-]+)"
            )
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                page_text,
                flags=re.I
            )

            if match:

                item_number = (
                    match
                    .group(1)
                    .strip()
                )

                break

        # Collection 从 URL 提取
        parts = [
            p
            for p in
            urlparse(
                target_url
            ).path.split("/")
            if p
        ]

        collection = ""

        if len(parts) >= 2:

            collection = (
                parts[1]
                .replace("-", " ")
                .title()
            )

        print(
            "  NO PUBLIC PRICE / FALLBACK"
        )

        return {

            "Collection":
                collection,

            "Variant":
                name,

            "Item Number":
                item_number,

            "Price":
                "",

            "Currency":
                "USD",

            "Availability":
                "INQUIRE",

            "URL":
                normalize_url(
                    target_url
                ),

            "Last Seen":
                now()

        }

    except Exception as e:

        print(
            "Fallback ERROR:",
            e
        )

        return None


# ============================================================
# HISTORY
# ============================================================

def build_old_map(rows):

    result = {}

    for row in rows:

        url = normalize_url(
            row.get(
                "URL",
                ""
            )
        )

        if url:
            result[url] = row

    return result


def update_history(
    old_map,
    new_rows,
    history
):

    for item in new_rows:

        url = normalize_url(
            item.get(
                "URL",
                ""
            )
        )

        old = old_map.get(
            url
        )

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

        # ======================================
        # 普通价格变化
        # ======================================

        if (
            old_price
            and new_price
            and old_price != new_price
        ):

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
                    item.get(
                        "Item Number",
                        ""
                    ),

                "Old Price":
                    old_price,

                "New Price":
                    new_price,

                "Currency":
                    item.get(
                        "Currency",
                        ""
                    ),

                "URL":
                    url

            })

            print()
            print(
                "PRICE CHANGE:"
            )

            print(
                item.get(
                    "Variant",
                    ""
                )
            )

            print(
                old_price,
                "->",
                new_price
            )

        # ======================================
        # INQUIRE -> PRICE
        # ======================================

        elif (
            not old_price
            and new_price
        ):

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
                    item.get(
                        "Item Number",
                        ""
                    ),

                "Old Price":
                    "",

                "New Price":
                    new_price,

                "Currency":
                    item.get(
                        "Currency",
                        ""
                    ),

                "URL":
                    url

            })

            print()
            print(
                "NEW PRICE PUBLISHED:"
            )

            print(
                item.get(
                    "Variant",
                    ""
                )
            )

            print(
                "INQUIRE ->",
                new_price
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print("=" * 70)
    print(
        "JACOB & CO. USA "
        "FULL VARIANT PRICE MONITOR"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # 1. 官方 Variant 基准
    # --------------------------------------------------------

    official_variant_urls = (
        get_official_variant_urls()
    )

    if not official_variant_urls:

        raise RuntimeError(
            "Official Variant Sitemap "
            "could not be loaded."
        )

    # --------------------------------------------------------
    # 2. 旧数据
    # --------------------------------------------------------

    old_rows = read_csv(
        CURRENT_CSV
    )

    history = read_csv(
        HISTORY_CSV
    )

    old_map = build_old_map(
        old_rows
    )

    all_rows = []

    # --------------------------------------------------------
    # 3. 浏览器扫描
    # --------------------------------------------------------

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            locale="en-US"
        )

        page = await context.new_page()

        collection_links = (
            await get_collection_links(
                page
            )
        )

        total = len(
            collection_links
        )

        print()
        print(
            "Scanning collections:",
            total
        )

        for index, url in enumerate(
            collection_links,
            start=1
        ):

            print(
                f"[{index}/{total}] {url}"
            )

            try:

                await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=90000
                )

                await page.wait_for_timeout(
                    1800
                )

                variants = (
                    await extract_variants(
                        page
                    )
                )

                print(
                    "Variants:",
                    len(variants)
                )

                all_rows.extend(
                    variants
                )

            except Exception as e:

                print(
                    "Collection ERROR:",
                    e
                )

            await asyncio.sleep(
                REQUEST_DELAY
            )

        # ----------------------------------------------------
        # 4. 去重
        # ----------------------------------------------------

        unique = {}

        for row in all_rows:

            url = normalize_url(
                row["URL"]
            )

            row["URL"] = url

            unique[url] = row

        # ----------------------------------------------------
        # 5. 只保留官方 Sitemap Variant
        # ----------------------------------------------------

        unique = {

            url: row

            for url, row
            in unique.items()

            if url
            in official_variant_urls
        }

        print()
        print("=" * 70)
        print("PRIMARY SCAN RESULT")
        print("=" * 70)

        print(
            "Official Variants:",
            len(
                official_variant_urls
            )
        )

        print(
            "Primary matched:",
            len(unique)
        )

        # ----------------------------------------------------
        # 6. 找遗漏
        # ----------------------------------------------------

        missing_urls = (
            official_variant_urls
            -
            set(
                unique.keys()
            )
        )

        print(
            "Need fallback:",
            len(
                missing_urls
            )
        )

        # ----------------------------------------------------
        # 7. 补抓遗漏
        # ----------------------------------------------------

        for index, url in enumerate(
            sorted(missing_urls),
            start=1
        ):

            print()
            print(
                f"[Fallback "
                f"{index}/"
                f"{len(missing_urls)}]"
            )

            item = (
                await scrape_missing_variant(
                    page,
                    url
                )
            )

            if item:

                unique[
                    normalize_url(
                        item["URL"]
                    )
                ] = item

            await asyncio.sleep(
                REQUEST_DELAY
            )

        await browser.close()

    # --------------------------------------------------------
    # 8. 最终结果
    # --------------------------------------------------------

    all_rows = list(
        unique.values()
    )

    all_rows.sort(
        key=lambda x: (
            x.get(
                "Collection",
                ""
            ),
            x.get(
                "Variant",
                ""
            )
        )
    )

    final_urls = {
        normalize_url(
            row["URL"]
        )
        for row
        in all_rows
    }

    remaining_missing = (
        official_variant_urls
        -
        final_urls
    )

    priced_count = sum(
        1
        for row in all_rows
        if str(
            row.get(
                "Price",
                ""
            )
        ).strip()
    )

    no_price_count = (
        len(all_rows)
        -
        priced_count
    )

    print()
    print("=" * 70)
    print("FINAL COVERAGE")
    print("=" * 70)

    print(
        "Official Variant URLs:",
        len(
            official_variant_urls
        )
    )

    print(
        "Monitored Variant URLs:",
        len(
            final_urls
        )
    )

    print(
        "With Price:",
        priced_count
    )

    print(
        "No Price / INQUIRE:",
        no_price_count
    )

    print(
        "Still Missing:",
        len(
            remaining_missing
        )
    )

    if official_variant_urls:

        coverage = (
            len(
                official_variant_urls
                &
                final_urls
            )
            /
            len(
                official_variant_urls
            )
            *
            100
        )

        print(
            f"Coverage: "
            f"{coverage:.2f}%"
        )

    if remaining_missing:

        print()
        print(
            "STILL MISSING:"
        )

        for url in sorted(
            remaining_missing
        ):

            print(url)

    # --------------------------------------------------------
    # 9. PRICE HISTORY
    # --------------------------------------------------------

    update_history(
        old_map,
        all_rows,
        history
    )

    # --------------------------------------------------------
    # 10. 保存
    # --------------------------------------------------------

    product_fields = [
        "Collection",
        "Variant",
        "Item Number",
        "Price",
        "Currency",
        "Availability",
        "URL",
        "Last Seen"
    ]

    history_fields = [
        "Changed At",
        "Collection",
        "Variant",
        "Item Number",
        "Old Price",
        "New Price",
        "Currency",
        "URL"
    ]

    write_csv(
        CURRENT_CSV,
        product_fields,
        all_rows
    )

    write_csv(
        HISTORY_CSV,
        history_fields,
        history
    )

    print()
    print("=" * 70)
    print(
        "FULL VARIANT SCAN COMPLETED"
    )
    print("=" * 70)

    print(
        "Current rows:",
        len(all_rows)
    )

    print(
        "History rows:",
        len(history)
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
