import csv
import json
import re
import time
from collections import Counter
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://jacobandco.com"
CURRENT_CSV = "current_prices.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def load_current_monitor():
    """读取现在正在监控的 current_prices.csv。"""
    urls = set()
    rows = []

    try:
        with open(CURRENT_CSV, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

                url = (
                    row.get("URL")
                    or row.get("Url")
                    or row.get("url")
                    or ""
                ).strip()

                if url:
                    urls.add(url.rstrip("/"))

    except FileNotFoundError:
        print("WARNING: current_prices.csv not found")

    return rows, urls


def get_text(url):
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"ERROR requesting {url}: {e}")
        return ""


def extract_sitemap_urls(xml_text):
    if not xml_text:
        return []

    return [
        x.strip()
        for x in re.findall(r"<loc>(.*?)</loc>", xml_text, flags=re.I | re.S)
        if x.strip()
    ]


def discover_sitemaps():
    """从 robots.txt 和常见 sitemap 地址寻找 sitemap。"""
    found = set()

    robots = get_text(BASE_URL + "/robots.txt")

    for line in robots.splitlines():
        if line.lower().startswith("sitemap:"):
            url = line.split(":", 1)[1].strip()
            if url:
                found.add(url)

    common = [
        BASE_URL + "/sitemap.xml",
        BASE_URL + "/sitemap_index.xml",
        BASE_URL + "/sitemap-index.xml",
    ]

    found.update(common)

    return sorted(found)


def crawl_sitemaps():
    """
    递归读取 sitemap。
    返回所有 sitemap 中发现的 URL。
    """
    queue = discover_sitemaps()
    visited = set()
    pages = set()

    while queue:
        sitemap = queue.pop(0)

        if sitemap in visited:
            continue

        visited.add(sitemap)

        print("Reading sitemap:", sitemap)

        text = get_text(sitemap)

        if not text:
            continue

        urls = extract_sitemap_urls(text)

        for url in urls:
            lower = url.lower()

            if lower.endswith(".xml") or "sitemap" in lower:
                if url not in visited:
                    queue.append(url)
            else:
                pages.add(url.rstrip("/"))

        time.sleep(0.2)

    return pages, visited
def get_official_variant_urls():
    """
    直接读取 Jacob & Co. 官方 sitemap-variants.xml。
    用它作为 Variant URL 的独立基准。
    """
    sitemap_url = BASE_URL + "/sitemap-variants.xml"

    print()
    print("Reading official variant sitemap:", sitemap_url)

    text = get_text(sitemap_url)

    if not text:
        print("WARNING: Could not read sitemap-variants.xml")
        return set()

    urls = extract_sitemap_urls(text)

    variant_urls = {
        url.rstrip("/")
        for url in urls
        if "/timepieces/" in url.lower()
    }

    print("Official variant URLs found:", len(variant_urls))

    return variant_urls

def looks_like_product_url(url):
    """
    Jacob & Co. 商品页面通常位于产品/系列路径下。
    这里先宽松筛选，宁可多抓，后面再判断。
    """
    u = url.lower()

    bad = [
        "/blog",
        "/news",
        "/boutique",
        "/contact",
        "/about",
        "/privacy",
        "/terms",
        "/press",
        "/careers",
    ]

    if any(x in u for x in bad):
        return False

    good = [
        "/timepieces/",
        "/high-jewelry/",
        "/fine-jewelry/",
        "/jewelry/",
    ]

    return any(x in u for x in good)


def analyze_product_page(url):
    """
    检查页面：
    - 是否像商品页
    - 是否存在美元价格
    - 是否存在询价类文字
    - 尝试提取名称 / SKU / Item Number
    """

    html_text = get_text(url)

    if not html_text:
        return None

    soup = BeautifulSoup(html_text, "html.parser")

    text = " ".join(soup.stripped_strings)

    title = ""

    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)

    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)

    # 美元价格
    prices = re.findall(
        r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        text
    )

    # 常见询价/无公开价格文字
    inquire_words = [
        "inquire",
        "enquire",
        "request price",
        "price upon request",
        "contact us",
    ]

    lower_text = text.lower()

    inquire = any(word in lower_text for word in inquire_words)

    # 尝试找 Item Number / SKU
    item_number = ""

    patterns = [
        r"Item\s*Number\s*[:#]?\s*([A-Za-z0-9._/-]+)",
        r"\bSKU\s*[:#]?\s*([A-Za-z0-9._/-]+)",
        r"Reference\s*[:#]?\s*([A-Za-z0-9._/-]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            item_number = m.group(1).strip()
            break

    # JSON-LD 中再检查 Product
    json_product = False

    for tag in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    ):
        raw = tag.string or tag.get_text()

        if not raw:
            continue

        try:
            data = json.loads(raw)

            stack = data if isinstance(data, list) else [data]

            for obj in stack:
                if not isinstance(obj, dict):
                    continue

                obj_type = obj.get("@type", "")

                if obj_type == "Product" or (
                    isinstance(obj_type, list)
                    and "Product" in obj_type
                ):
                    json_product = True

                    if not title:
                        title = str(obj.get("name", ""))

                    if not item_number:
                        item_number = str(
                            obj.get("sku")
                            or obj.get("mpn")
                            or ""
                        )

        except Exception:
            pass

    has_price = len(prices) > 0

    # sitemap 路径 + Product JSON-LD + 页面特征综合判断
    likely_product = (
        json_product
        or has_price
        or inquire
        or bool(item_number)
    )

    if not likely_product:
        return None

    return {
        "url": url,
        "title": title,
        "item_number": item_number,
        "has_price": has_price,
        "prices_found": prices,
        "inquire": inquire,
    }


def main():
    print("=" * 70)
    print("JACOB & CO. USA WEBSITE COVERAGE CHECK")
    print("=" * 70)

    current_rows, monitored_urls = load_current_monitor()
    official_variant_urls = get_official_variant_urls()
    
    matched_variant_urls = official_variant_urls & monitored_urls
    missing_variant_urls = official_variant_urls - monitored_urls
    extra_monitored_urls = monitored_urls - official_variant_urls
    
    print()
    print("=" * 70)
    print("OFFICIAL VARIANT SITEMAP CHECK")
    print("=" * 70)
    print("Official variant URLs :", len(official_variant_urls))
    print("Current monitored URLs:", len(monitored_urls))
    print("Matched URLs          :", len(matched_variant_urls))
    print("Missing from monitor  :", len(missing_variant_urls))
    print("Extra monitored URLs  :", len(extra_monitored_urls))
    
    if official_variant_urls:
        variant_coverage = (
            len(matched_variant_urls)
            / len(official_variant_urls)
            * 100
        )
        print(f"Variant URL coverage  : {variant_coverage:.2f}%")
    
    print()
    print("MISSING VARIANT URLS")
    print("-" * 70)
    
    if missing_variant_urls:
        for url in sorted(missing_variant_urls):
            print(url)
    else:
        print("NONE")
    
    print()
    print("EXTRA MONITORED URLS")
    print("-" * 70)
    
    if extra_monitored_urls:
        for url in sorted(extra_monitored_urls):
            print(url)
    else:
        print("NONE")
        print()
        print("Current monitor rows:", len(current_rows))
        print("Current monitor unique URLs:", len(monitored_urls))
        print()
    
        all_urls, sitemaps = crawl_sitemaps()
    
        print()
        print("Sitemaps checked:", len(sitemaps))
        print("Total URLs found in sitemaps:", len(all_urls))
    
        candidates = sorted(
            url for url in all_urls
            if looks_like_product_url(url)
        )
    
        print("Potential product URLs:", len(candidates))
        print()
        print("Now checking candidate product pages...")
        print()
    
        products = []
    
        for i, url in enumerate(candidates, 1):
            print(f"[{i}/{len(candidates)}] {url}")
    
            result = analyze_product_page(url)
    
            if result:
                products.append(result)
    
            time.sleep(0.15)
    
        official_urls = {
            p["url"].rstrip("/")
            for p in products
        }
    
        priced = [
            p for p in products
            if p["has_price"]
        ]
    
        no_public_price = [
            p for p in products
            if not p["has_price"]
        ]
    
        inquire = [
            p for p in products
            if p["inquire"] and not p["has_price"]
        ]
    
        missing_from_monitor = sorted(
            official_urls - monitored_urls
        )
    
        monitored_not_found = sorted(
            monitored_urls - official_urls
        )
    
        print()
        print("=" * 70)
        print("COVERAGE REPORT")
        print("=" * 70)
    
        print("Official product pages detected :", len(products))
        print("Pages with public USD price     :", len(priced))
        print("Pages without public USD price  :", len(no_public_price))
        print("Inquire-type pages              :", len(inquire))
        print("Current monitored rows          :", len(current_rows))
        print("Current monitored unique URLs   :", len(monitored_urls))
        print("Official URLs missing monitor   :", len(missing_from_monitor))
        print("Monitor URLs not found official :", len(monitored_not_found))
    
        if official_urls:
            coverage = (
                len(official_urls & monitored_urls)
                / len(official_urls)
                * 100
            )
    
            print(f"URL coverage                    : {coverage:.2f}%")
    
        print()
        print("=" * 70)
        print("OFFICIAL PAGES MISSING FROM CURRENT MONITOR")
        print("=" * 70)
    
        if not missing_from_monitor:
            print("NONE")
        else:
            for url in missing_from_monitor:
                print(url)
    
        print()
        print("=" * 70)
        print("NO PUBLIC PRICE / INQUIRE PAGES")
        print("=" * 70)
    
        for p in no_public_price:
            print(
                p["title"],
                "|",
                p["item_number"],
                "|",
                p["url"]
            )
    
        # 保存详细报告
        with open(
            "coverage_report.csv",
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as f:
    
            writer = csv.writer(f)
    
            writer.writerow([
                "Title",
                "Item Number",
                "Has Public Price",
                "Inquire",
                "Prices Found",
                "Currently Monitored",
                "URL",
            ])
    
            for p in products:
                writer.writerow([
                    p["title"],
                    p["item_number"],
                    "YES" if p["has_price"] else "NO",
                    "YES" if p["inquire"] else "NO",
                    " | ".join(p["prices_found"]),
                    "YES" if p["url"].rstrip("/") in monitored_urls else "NO",
                    p["url"],
                ])
    
        print()
        print("Detailed report saved as coverage_report.csv")
        print("=" * 70)
    

if __name__ == "__main__":
    main()
