"""Live, read-only diagnostic for the jewelry USD monitor."""

from jewelry_monitor import (
    MIN_COLLECTIONS,
    MIN_PRODUCTS,
    MIN_VARIANTS,
    TARGET_CURRENCY,
    scrape_current_state,
)


def main():
    product_map, rows, collections = scrape_current_state()
    currencies = {
        str(row.get("Currency", "")).strip().upper()
        for row in rows
    }

    assert len(collections) >= MIN_COLLECTIONS
    assert len(product_map) >= MIN_PRODUCTS
    assert len(rows) >= MIN_VARIANTS
    assert currencies == {TARGET_CURRENCY}
    assert all(row.get("Price") for row in rows)

    print()
    print("=" * 70)
    print("JEWELRY USD DIAGNOSTIC PASSED")
    print("=" * 70)
    print("Collections      :", len(collections))
    print("Unique products  :", len(product_map))
    print("Variants         :", len(rows))
    print("Currency         :", TARGET_CURRENCY)
    print("All prices filled: YES")


if __name__ == "__main__":
    main()
