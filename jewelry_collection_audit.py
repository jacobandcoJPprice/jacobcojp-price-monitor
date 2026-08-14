import asyncio
from collections import defaultdict
from playwright.async_api import async_playwright


BASE_URL = "https://jacobandco.shop"

# Only the collections visibly listed under "All Collections"
# on https://jacobandco.shop/pages/collections
COLLECTIONS = [
    ("Jacob & Co. X PEACEMINUSONE", "g-dragon-peaceminusone-collection"),
    ("Love Lockdown", "love-lockdown"),
    ("Evil Eye", "evil-eye"),
    ("Lucky You", "lucky-you"),
    ("Infinia", "the-infinia-collection"),
    ("Jezebel", "jezebel"),
    ("Rare Touch", "rare-touch"),
    ("Securus", "securus"),
    ("Office Supplies By Virgil Abloh", "office-supplies"),
    ("Match Collection", "matchstick-collection"),
    ("Estribo", "estribo"),
    ("Cuban Link", "cuban-link"),
    ("Carabin", "carabin"),
    ("Cufflinks", "cufflinks"),
    ("Espada", "espada"),
    ("Super Arrow", "super-arrow"),
    ("Papillon", "papillon"),
    ("Hematite", "hematite"),
    ("Jacob's Code", "jacobs-code"),
    ("Sharq", "sharq"),
    ("Spread The Love", "the-spread-the-love-collection"),
    ("You Are You", "you-are-you"),
    ("Taken", "taken"),
    ("Zodiac", "zodiac-sign"),
]


async def main():
    print("=" * 78)
    print("JACOB & CO. ALL COLLECTIONS AUDIT")
    print("=" * 78)
    print("Scope: ONLY collections visibly listed on /pages/collections")
    print()

    product_to_collections = defaultdict(set)
    product_titles = {}
    product_variant_counts = {}
    collection_counts = []
    failed = []

    async with async_playwright() as p:
        request = await p.request.new_context(
            extra_http_headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/151 Safari/537.36"
                )
            }
        )

        for index, (name, handle) in enumerate(COLLECTIONS, start=1):
            api_url = (
                f"{BASE_URL}/collections/{handle}"
                "/products.json?limit=250"
            )

            try:
                response = await request.get(
                    api_url,
                    timeout=60000
                )

                if not response.ok:
                    failed.append(
                        (name, handle, response.status)
                    )
                    print(
                        f"{index:02d}. {name:<34} "
                        f"FAILED HTTP {response.status}"
                    )
                    continue

                data = await response.json()
                products = data.get("products", [])

                if not isinstance(products, list):
                    products = []

                collection_counts.append(
                    (name, handle, len(products))
                )

                print(
                    f"{index:02d}. {name:<34} "
                    f"{len(products):>3} products"
                )

                for product in products:
                    product_id = str(
                        product.get("id", "")
                    ).strip()

                    if not product_id:
                        continue

                    product_to_collections[
                        product_id
                    ].add(name)

                    product_titles[
                        product_id
                    ] = str(
                        product.get("title", "")
                    ).strip()

                    variants = product.get(
                        "variants",
                        []
                    )

                    if not isinstance(variants, list):
                        variants = []

                    product_variant_counts[
                        product_id
                    ] = len(variants)

            except Exception as e:
                failed.append(
                    (name, handle, repr(e))
                )
                print(
                    f"{index:02d}. {name:<34} ERROR {e!r}"
                )

        await request.dispose()

    total_before_dedupe = sum(
        count
        for _, _, count in collection_counts
    )

    unique_products = len(
        product_to_collections
    )

    total_variants = sum(
        product_variant_counts.values()
    )

    multi_collection_products = [
        product_id
        for product_id, names
        in product_to_collections.items()
        if len(names) > 1
    ]

    print()
    print("=" * 78)
    print("AUDIT RESULT")
    print("=" * 78)
    print(
        "Collections expected       :",
        len(COLLECTIONS)
    )
    print(
        "Collections successful     :",
        len(collection_counts)
    )
    print(
        "Collections failed         :",
        len(failed)
    )
    print(
        "Products before dedupe     :",
        total_before_dedupe
    )
    print(
        "Unique Product IDs         :",
        unique_products
    )
    print(
        "Total variants             :",
        total_variants
    )
    print(
        "Products in >1 collection  :",
        len(multi_collection_products)
    )

    if failed:
        print()
        print("FAILED COLLECTIONS")
        print("-" * 78)
        for item in failed:
            print(item)

    print()
    print("TOP DUPLICATED PRODUCTS ACROSS COLLECTIONS")
    print("-" * 78)

    duplicates = sorted(
        (
            (
                len(product_to_collections[product_id]),
                product_titles.get(product_id, ""),
                sorted(
                    product_to_collections[product_id]
                )
            )
            for product_id
            in multi_collection_products
        ),
        reverse=True
    )

    for count, title, names in duplicates[:25]:
        print(
            f"{count} collections | "
            f"{title} | "
            + " / ".join(names)
        )


if __name__ == "__main__":
    asyncio.run(main())
