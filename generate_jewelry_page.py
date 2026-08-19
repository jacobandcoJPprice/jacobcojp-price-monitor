import csv
import html
import os
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(
    BASE_DIR,
    "jewelry_current_prices.csv"
)

HISTORY_CSV = os.path.join(
    BASE_DIR,
    "jewelry_price_history.csv"
)

PRODUCT_HISTORY_CSV = os.path.join(
    BASE_DIR,
    "jewelry_change_history.csv"
)

OUTPUT_HTML = os.path.join(
    BASE_DIR,
    "jewelry.html"
)

CONFIRM_API_URL = "https://script.google.com/macros/s/AKfycbzSYIw5g1YSVdh6-pAgrKoCf0MFh4TwWjwNIJzudhnZuYyTFwx6QYwXM19gUOQs28-q-A/exec"
STRUCTURE_CONFIRM_API_URL = "https://script.google.com/macros/s/AKfycby_kPhxICq5kzM-5FnoXQ7pn83bXshujxw8M-egP3r88G2wNbN6o_BdIgY4_Lg_GTG9OQ/exec"


# ============================================================
# BASIC
# ============================================================

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


def esc(value):

    return html.escape(
        str(value or ""),
        quote=True
    )


def format_price(value):

    if value is None:
        return "—"

    value = str(value).strip()

    if not value:
        return "—"

    try:

        number = float(
            value.replace(",", "")
        )

        return "${:,.0f}".format(
            number
        )

    except Exception:

        return esc(value)


# ============================================================
# LOAD DATA
# ============================================================

current_rows = read_csv(
    CURRENT_CSV
)

history_rows = read_csv(
    HISTORY_CSV
)

product_history_rows = read_csv(
    PRODUCT_HISTORY_CSV
)


# Sort current prices
current_rows.sort(
    key=lambda x: (
        str(
            x.get("Collections", "")
        ).lower(),
        str(
            x.get("SKU", "")
        ).lower()
    )
)


# Latest changes first
history_rows = list(
    reversed(
        history_rows
    )
)


product_history_rows = list(
    reversed(
        product_history_rows
    )
)


# ============================================================
# CURRENT PRICE CARDS
# ============================================================

current_cards = []

for row in current_rows:

    collection = esc(
        row.get(
            "Collections",
            ""
        )
    )

    variant = esc(
        row.get(
            "Variant",
            ""
        )
    )

    item_number = esc(
        row.get(
            "SKU",
            ""
        )
    )

    price = format_price(
        row.get(
            "Price",
            ""
        )
    )

    url = esc(
        row.get(
            "URL",
            ""
        )
    )

    search_text = esc(
        " ".join([
            str(
                row.get(
                    "Collections",
                    ""
                )
            ),
            str(
                row.get(
                    "Product",
                    ""
                )
            ),
            str(
                row.get(
                    "Variant",
                    ""
                )
            ),
            str(
                row.get(
                    "SKU",
                    ""
                )
            )
        ]).lower()
    )

    if not variant:
        variant = collection

    current_cards.append(
        f"""
        <a
            class="price-card"
            href="{url}"
            target="_blank"
            rel="noopener noreferrer"
            data-search="{search_text}"
        >
            <div class="card-top">

                <div class="collection">
                    {collection}
                </div>

                <div class="price">
                    {price}
                </div>

            </div>

            <div class="variant">
                {variant}
            </div>

            <div class="item-label">
                SKU
            </div>

            <div class="item-number">
                {item_number}
            </div>

            <div class="official-link">
                JACOB &amp; CO. USA ↗
            </div>

        </a>
        """
    )


current_cards_html = "\n".join(
    current_cards
)


# ============================================================
# PRICE HISTORY
# ============================================================

history_cards = []

for row in history_rows:

    collection = esc(
        row.get(
            "Collections",
            ""
        )
    )

    variant = esc(
        row.get(
            "Variant",
            ""
        )
    )

    item_number_raw = str(
        row.get(
            "SKU",
            ""
        )
    ).strip()

    old_price_raw = str(
        row.get(
            "Old Price",
            ""
        )
    ).strip()

    new_price_raw = str(
        row.get(
            "New Price",
            ""
        )
    ).strip()

    item_number = esc(
        item_number_raw
    )

    old_price = format_price(
        old_price_raw
    )

    new_price = format_price(
        new_price_raw
    )

    changed_at = esc(
        row.get(
            "Changed At",
            ""
        )
    )

    url = esc(
        row.get(
            "URL",
            ""
        )
    )

    history_cards.append(
        f"""
        <div
            class="change-card"
            data-item-number="{esc(item_number_raw)}"
            data-old-price="{esc(old_price_raw)}"
            data-new-price="{esc(new_price_raw)}"
        >

            <a
                class="change-main-link"
                href="{url}"
                target="_blank"
                rel="noopener noreferrer"
            >

                <div class="change-info">

                    <div class="change-collection">
                        {collection}
                    </div>

                    <div class="change-variant">
                        {variant}
                    </div>

                    <div class="change-item">
                        {item_number}
                    </div>

                    <div class="change-date">
                        {changed_at}
                    </div>

                </div>

                <div class="change-prices">

                    <span class="old-price">
                        {old_price}
                    </span>

                    <span class="arrow">
                        →
                    </span>

                    <span class="new-price">
                        {new_price}
                    </span>

                </div>

            </a>

            <div class="confirm-area">

                <button
                    type="button"
                    class="confirm-button"
                >
                    確認済みにする
                </button>

                <div class="confirm-status">
                    未確認
                </div>

            </div>

        </div>
        """
    )


if history_cards:

    history_html = "\n".join(
        history_cards
    )

else:

    history_html = """
        <div class="no-changes">
            現在、記録されている価格変更はありません。
        </div>
    """


# ============================================================
# PRODUCT STRUCTURE CHANGES
# ============================================================

product_change_cards = []

for row in product_history_rows[:100]:

    change_type_raw = str(
        row.get(
            "Change Type",
            ""
        )
    ).strip()

    unique_key_raw = str(
        row.get(
            "Unique Key",
            ""
        )
    ).strip()

    item_number_raw = str(
        row.get(
            "SKU",
            ""
        )
    ).strip()

    product_raw = str(
        row.get(
            "Product",
            ""
        )
    ).strip()

    collection_raw = str(
        row.get(
            "Collections",
            ""
        )
    ).strip()

    variant_raw = str(
        row.get(
            "Variant",
            ""
        )
    ).strip()

    old_status_raw = str(
        row.get(
            "Old Status",
            ""
        )
    ).strip()

    new_status_raw = str(
        row.get(
            "New Status",
            ""
        )
    ).strip()

    price_raw = str(
        row.get(
            "Price",
            ""
        )
    ).strip()

    changed_at_raw = str(
        row.get(
            "Changed At",
            ""
        )
    ).strip()

    url_raw = str(
        row.get(
            "URL",
            ""
        )
    ).strip()

    event_key_raw = "||".join([
        change_type_raw,
        unique_key_raw,
        changed_at_raw
    ])

    display_title_raw = (
        product_raw
        or (
            variant_raw
            if variant_raw.lower() != "default title"
            else ""
        )
        or collection_raw
        or item_number_raw
        or "名称未取得"
    )

    variant_detail_raw = (
        variant_raw
        if (
            variant_raw
            and variant_raw.lower() != "default title"
            and variant_raw != display_title_raw
        )
        else ""
    )

    change_type = esc(change_type_raw)
    item_number = esc(item_number_raw)
    collection = esc(collection_raw)
    old_status = esc(old_status_raw)
    new_status = esc(new_status_raw)
    price = format_price(price_raw)
    changed_at = esc(changed_at_raw)
    url = esc(url_raw)
    display_title = esc(display_title_raw)
    variant_detail = esc(variant_detail_raw)

    product_change_cards.append(
        f"""
        <div
            class="product-change-card structure-change-card"
            data-event-key="{esc(event_key_raw)}"
            data-change-type="{esc(change_type_raw)}"
            data-sku="{esc(item_number_raw)}"
            data-product="{esc(product_raw)}"
            data-variant="{esc(variant_raw)}"
            data-changed-at="{esc(changed_at_raw)}"
            data-url="{esc(url_raw)}"
            data-old-status="{esc(old_status_raw)}"
            data-new-status="{esc(new_status_raw)}"
            data-price="{esc(price_raw)}"
        >
            <div class="product-change-type">
                {change_type}
            </div>

            <div class="product-change-info">
                <a
                    class="product-change-main-link"
                    href="{url}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <div class="change-collection">
                        {collection}
                    </div>

                    <div class="change-variant">
                        {display_title}
                    </div>

                    {
                        f'<div class="product-variant-detail">{variant_detail}</div>'
                        if variant_detail
                        else ''
                    }

                    <div class="change-item">
                        {item_number}
                    </div>

                    <div class="change-date">
                        {changed_at}
                    </div>
                </a>
            </div>

            <div class="product-change-status">
                <div>
                    {old_status or "—"}
                    →
                    {new_status or "—"}
                </div>

                <strong>
                    {price}
                </strong>
            </div>

            <div class="confirm-area structure-confirm-area">

                <button
                    type="button"
                    class="confirm-button structure-confirm-button"
                >
                    確認済みにする
                </button>

                <div class="confirm-status">
                    未確認
                </div>

            </div>
        </div>
        """
    )


if product_change_cards:

    product_changes_html = "\n".join(
        product_change_cards
    )

else:

    product_changes_html = """
        <div class="no-changes">
            商品構成の変更履歴はありません。
        </div>
    """


# ============================================================

# UPDATED TIME
# ============================================================

updated_at = datetime.now().strftime(
    "%Y-%m-%d %H:%M"
)


last_seen_values = [
    str(
        row.get(
            "Last Seen",
            ""
        )
    ).strip()
    for row in current_rows
    if str(
        row.get(
            "Last Seen",
            ""
        )
    ).strip()
]

last_successful_scan = (
    max(last_seen_values)
    if last_seen_values
    else ""
)


# ============================================================
# HTML
# ============================================================

page = f"""<!DOCTYPE html>

<html lang="ja">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
Jacob & Co. USA Jewelry Price Monitor
</title>

<style>

* {{
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{
    margin: 0;
    background: #f5f5f3;
    color: #111;
    font-family:
        Arial,
        Helvetica,
        sans-serif;
}}

.header {{
    background: #000;
    color: #fff;
    padding: 42px 24px 38px;
}}

.header-inner {{
    width: min(1400px, 94%);
    margin: 0 auto;
}}

.brand {{
    font-size: 13px;
    letter-spacing: 4px;
    opacity: 0.72;
    margin-bottom: 14px;
}}

h1 {{
    margin: 0;
    font-size: clamp(
        28px,
        4vw,
        52px
    );
    font-weight: 500;
    letter-spacing: -1px;
}}

.subtitle {{
    margin-top: 15px;
    color: #aaa;
    font-size: 14px;
}}

.stats {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 28px;
}}

.stat {{
    border: 1px solid #333;
    padding: 11px 16px;
    font-size: 13px;
}}

.stat-button {{
    color: #fff;
    background: transparent;
    font-family: inherit;
    cursor: pointer;
}}

.stat-button:hover {{
    border-color: #777;
    background: #111;
}}

.change-card.is-confirmed {{
    display: none;
}}

.confirm-modal {{
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: none;
}}

.confirm-modal.is-open {{
    display: block;
}}

.confirm-modal-backdrop {{
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,.55);
}}

.confirm-modal-panel {{
    position: relative;
    width: min(1100px, 92vw);
    max-height: 82vh;
    overflow: auto;
    margin: 7vh auto 0;
    background: #f5f5f3;
    border: 1px solid #ccc;
    padding: 26px;
    box-shadow: 0 18px 60px rgba(0,0,0,.3);
}}

.confirm-modal-header {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 22px;
}}

.confirm-modal-title {{
    margin: 0;
    font-size: 24px;
    font-weight: 500;
}}

.confirm-modal-subtitle {{
    margin-top: 6px;
    color: #777;
    font-size: 12px;
}}

.confirm-modal-close {{
    border: 0;
    background: transparent;
    color: #111;
    font-size: 32px;
    line-height: 1;
    cursor: pointer;
}}

.confirmed-history-list {{
    display: grid;
    gap: 10px;
}}

.confirmed-record {{
    background: #fff;
    border: 1px solid #ddd;
    padding: 18px 20px;
}}

.confirmed-record-main {{
    color: inherit;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
}}

.confirmed-record-meta {{
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #eee;
    color: #555;
    font-size: 12px;
}}

.confirmed-record-meta strong {{
    color: #111;
}}

.main {{
    width: min(1400px, 94%);
    margin: 0 auto;
    padding: 45px 0 80px;
}}

.section {{
    margin-bottom: 60px;
}}

.section-header {{
    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 20px;
    margin-bottom: 20px;
}}

.section-title {{
    margin: 0;
    font-size: 26px;
    font-weight: 500;
}}

.section-description {{
    color: #777;
    font-size: 13px;
}}

.change-list {{
    display: grid;
    gap: 10px;
}}

.change-card {{
    background: #fff;
    color: inherit;
    border: 1px solid #ddd;
    padding: 20px 22px;

    display: flex;
    align-items: center;
    gap: 22px;

    transition:
        transform .15s ease,
        border-color .15s ease;
}}

.change-card:hover {{
    transform: translateY(-1px);
    border-color: #888;
}}

.change-main-link {{
    color: inherit;
    text-decoration: none;

    flex: 1;
    min-width: 0;

    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 25px;
}}

.confirm-area {{
    width: 210px;
    flex: 0 0 210px;
    text-align: right;
}}

.confirm-button {{
    border: 1px solid #111;
    background: #111;
    color: #fff;

    padding: 10px 14px;

    font-size: 12px;
    font-weight: 600;

    cursor: pointer;
}}

.confirm-button:hover {{
    opacity: .82;
}}

.confirm-button:disabled {{
    cursor: default;
}}

.confirm-status {{
    margin-top: 7px;
    color: #888;
    font-size: 11px;
    line-height: 1.5;
}}

.confirm-area.is-confirmed .confirm-button {{
    background: #fff;
    color: #111;
    border-color: #111;
}}

.confirm-area.is-confirmed .confirm-status {{
    color: #111;
}}

.change-collection {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #888;
}}

.change-variant {{
    margin-top: 5px;
    font-size: 16px;
}}

.change-item {{
    margin-top: 7px;
    font-family: monospace;
    font-size: 13px;
    font-weight: bold;
}}

.change-date {{
    margin-top: 5px;
    color: #999;
    font-size: 11px;
}}

.change-prices {{
    white-space: nowrap;
    font-size: 18px;
}}

.old-price {{
    color: #999;
    text-decoration: line-through;
}}

.arrow {{
    padding: 0 12px;
    color: #999;
}}

.new-price {{
    font-weight: bold;
}}

.no-changes {{
    background: #fff;
    border: 1px solid #ddd;
    padding: 26px;
    color: #777;
}}

.health-stat.is-ok {{
    border-color: #2b7a3d;
}}

.health-stat.is-warning {{
    border-color: #b77a00;
}}

.health-stat.is-error {{
    border-color: #b83333;
}}

.product-change-list {{
    display: grid;
    gap: 10px;
}}

.product-change-card {{
    background: #fff;
    color: inherit;
    border: 1px solid #ddd;
    padding: 18px 20px;
    display: grid;
    grid-template-columns: 150px minmax(0, 1fr) auto 210px;
    gap: 20px;
    align-items: center;
}}

.product-change-card:hover {{
    border-color: #888;
}}

.product-change-card.is-confirmed {{
    display: none;
}}

.product-change-main-link {{
    color: inherit;
    text-decoration: none;
    display: block;
}}

.product-variant-detail {{
    margin-top: 4px;
    color: #777;
    font-size: 12px;
}}

.product-change-type {{
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 1px;
}}

.product-change-status {{
    text-align: right;
    color: #555;
    font-size: 12px;
}}

.product-change-status strong {{
    display: block;
    margin-top: 5px;
    color: #111;
    font-size: 15px;
}}

.search-wrap {{
    position: sticky;
    top: 0;
    z-index: 20;

    background:
        rgba(245,245,243,.95);

    backdrop-filter:
        blur(12px);

    padding: 14px 0;
    margin-bottom: 15px;
}}

.search {{
    width: 100%;
    border: 1px solid #bbb;
    background: #fff;
    padding: 16px 18px;
    font-size: 15px;
    outline: none;
}}

.search:focus {{
    border-color: #111;
}}

.result-info {{
    color: #777;
    font-size: 12px;
    margin: 12px 0 18px;
}}

.grid {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fill,
            minmax(260px, 1fr)
        );

    gap: 12px;
}}

.price-card {{
    min-height: 220px;

    background: #fff;
    color: inherit;
    text-decoration: none;

    border: 1px solid #ddd;

    padding: 20px;

    display: flex;
    flex-direction: column;

    transition:
        transform .15s ease,
        border-color .15s ease,
        box-shadow .15s ease;
}}

.price-card:hover {{
    transform: translateY(-2px);
    border-color: #999;

    box-shadow:
        0 8px 25px
        rgba(0,0,0,.06);
}}

.card-top {{
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 15px;
}}

.collection {{
    font-size: 11px;
    line-height: 1.4;
    color: #777;
    text-transform: uppercase;
    letter-spacing: 1.2px;
}}

.price {{
    font-size: 18px;
    font-weight: bold;
    white-space: nowrap;
}}

.variant {{
    margin-top: 24px;

    font-size: 17px;
    line-height: 1.35;

    min-height: 45px;
}}

.item-label {{
    margin-top: 22px;

    font-size: 9px;
    letter-spacing: 1.6px;

    color: #999;
}}

.item-number {{
    margin-top: 5px;

    font-family:
        Consolas,
        Monaco,
        monospace;

    font-size: 14px;
    font-weight: bold;

    word-break: break-all;
}}

.official-link {{
    margin-top: auto;
    padding-top: 20px;

    font-size: 10px;
    letter-spacing: 1px;

    color: #999;
}}

.empty {{
    display: none;

    padding: 50px 20px;

    text-align: center;
    color: #777;
}}

.footer {{
    border-top: 1px solid #ddd;

    padding: 30px 0;

    text-align: center;

    color: #999;
    font-size: 11px;
}}

@media (
    max-width: 700px
) {{

    .header {{
        padding:
            30px 18px;
    }}

    .main {{
        width: 92%;
        padding-top: 30px;
    }}

    .section-header {{
        display: block;
    }}

    .section-description {{
        margin-top: 8px;
    }}

    .change-card {{
        display: block;
    }}

    .change-prices {{
        margin-top: 16px;
    }}

    .change-main-link {{
        display: block;
    }}

    .confirm-area {{
        width: 100%;
        margin-top: 18px;
        text-align: left;
    }}

    .confirmed-record-main {{
        display: block;
    }}

    .confirm-modal-panel {{
        width: 94vw;
        margin-top: 3vh;
        max-height: 92vh;
        padding: 18px;
    }}

    .grid {{
        grid-template-columns:
            1fr;
    }}

    .product-change-card {{
        grid-template-columns: 1fr;
    }}

    .structure-confirm-area {{
        width: 100%;
        text-align: left;
    }}

    .product-change-status {{
        text-align: left;
    }}

}}

</style>

</head>


<body>


<header class="header">

    <div class="header-inner">

        <div class="brand">
            JACOB &amp; CO. JAPAN
        </div>

        <h1>
            USA Official Jewelry Price Monitor
        </h1>

        <div class="subtitle">
            Jacob &amp; Co. 米国公式ジュエリー価格監視
        </div>


        <div style="margin-top:24px; display:flex; gap:12px;">
    <a href="index.html" style="color:#aaa; text-decoration:none; border:1px solid #444; padding:14px 26px; font-size:14px; font-weight:600; letter-spacing:0.5px;">
        WATCHES
    </a>
    <a href="jewelry.html" style="color:#fff; text-decoration:none; border:1px solid #777; background:#111; padding:14px 26px; font-size:14px; font-weight:600; letter-spacing:0.5px;">
        JEWELRY
    </a>
</div>

        <div class="stats">

            <div class="stat">
                現在の登録数：
                <strong>
                    {len(current_rows)}
                </strong>
            </div>

            <div
                class="stat health-stat"
                id="healthStat"
                data-current-rows="{len(current_rows)}"
                data-last-seen="{esc(last_successful_scan)}"
            >
                監視状態：
                <strong id="healthStatus">
                    確認中…
                </strong>
            </div>

            <div class="stat">
                価格変更履歴：
                <strong>
                    {len(history_rows)}
                </strong>
            </div>

            <button
                type="button"
                class="stat stat-button"
                id="confirmedHistoryButton"
            >
                確認済み：
                <strong id="confirmedCount">
                    0
                </strong>
            </button>

            <div class="stat">
                商品構成変更：
                <strong>
                    {len(product_history_rows)}
                </strong>
            </div>

            <div class="stat">
                最終更新：
                <strong>
                    {updated_at}
                </strong>
            </div>

        </div>

    </div>

</header>


<main class="main">


    <!-- ================================================ -->
    <!-- PRICE CHANGES FIRST -->
    <!-- ================================================ -->

    <section class="section">

        <div class="section-header">

            <div>

                <h2 class="section-title">
                    最近の価格変更
                </h2>

                <div class="section-description">
                    Jacob &amp; Co. 米国公式ジュエリー価格の変更履歴
                </div>

            </div>

        </div>


        <div
            class="change-list"
            id="unconfirmedChangeList"
        >

            {history_html}

        </div>

        <div
            class="no-changes"
            id="unconfirmedEmpty"
            style="display:none;"
        >
            未確認の価格変更はありません。
        </div>

    </section>


    <!-- ================================================ -->
    <!-- PRODUCT STRUCTURE CHANGES -->
    <!-- ================================================ -->

    <section class="section">

        <div class="section-header">

            <div>

                <h2 class="section-title">
                    商品構成の変更
                </h2>

                <div class="section-description">
                    NEW ITEM / REMOVED ITEM / STATUS CHANGE
                </div>

            </div>

        </div>

        <div
            class="product-change-list"
            id="unconfirmedProductChangeList"
        >
            {product_changes_html}
        </div>

        <div
            class="no-changes"
            id="unconfirmedProductEmpty"
            style="display:none;"
        >
            未確認の商品構成変更はありません。
        </div>

    </section>


    <!-- ================================================ -->
    <!-- CURRENT OFFICIAL PRICES -->
    <!-- ================================================ -->

    <section class="section">

        <div class="section-header">

            <div>

                <h2 class="section-title">
                    現在の米国公式価格
                </h2>

                <div class="section-description">
                    SKU・Collection・Variant から検索できます
                </div>

            </div>

        </div>


        <div class="search-wrap">

            <input
                id="search"
                class="search"
                type="text"
                placeholder="SKU / COLLECTION / VARIANT を検索..."
                autocomplete="off"
            >

        </div>


        <div
            id="resultInfo"
            class="result-info"
        >
            {len(current_rows)} 件を表示
        </div>


        <div
            id="priceGrid"
            class="grid"
        >

            {current_cards_html}

        </div>


        <div
            id="empty"
            class="empty"
        >
            該当する商品が見つかりません。
        </div>

    </section>


</main>


<div
    class="confirm-modal"
    id="confirmedHistoryModal"
    aria-hidden="true"
>
    <div
        class="confirm-modal-backdrop"
        data-close-confirmed-modal
    ></div>

    <div
        class="confirm-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirmedModalTitle"
    >
        <div class="confirm-modal-header">
            <div>
                <h2
                    class="confirm-modal-title"
                    id="confirmedModalTitle"
                >
                    確認済みの価格変更
                </h2>
                <div class="confirm-modal-subtitle">
                    確認済みの記録を最新順で表示します
                </div>
            </div>

            <button
                type="button"
                class="confirm-modal-close"
                data-close-confirmed-modal
                aria-label="閉じる"
            >
                ×
            </button>
        </div>

        <div
            class="confirmed-history-list"
            id="confirmedHistoryList"
        ></div>

        <div
            class="no-changes"
            id="confirmedHistoryEmpty"
        >
            確認済みの価格変更はありません。
        </div>
    </div>
</div>


<footer class="footer">

    <div>
        Data source:
        Jacob &amp; Co. USA Official Timepiece Prices
    </div>

    <div style="margin-top:18px; opacity:0.65; line-height:1.8;">
        Syun was here. — 2026<br>
        このシステムがまだ動いているなら、そっとそのままにしておいてください。<br>
        壊れているなら……AIに聞いてください。笑
    </div>

</footer>


<script>

const search =
    document.getElementById(
        "search"
    );

const cards =
    Array.from(
        document.querySelectorAll(
            ".price-card"
        )
    );

const resultInfo =
    document.getElementById(
        "resultInfo"
    );

const empty =
    document.getElementById(
        "empty"
    );


function filterCards() {{

    const query =
        search.value
        .trim()
        .toLowerCase();

    let visible = 0;

    cards.forEach(card => {{

        const text =
            (
                card.dataset.search
                || ""
            ).toLowerCase();

        const match =
            !query
            ||
            text.includes(query);

        card.style.display =
            match
            ? ""
            : "none";

        if (match) {{
            visible++;
        }}

    }});


    resultInfo.textContent =
        visible
        + " 件を表示";


    empty.style.display =
        visible === 0
        ? "block"
        : "none";

}}


search.addEventListener(
    "input",
    filterCards
);


// ============================================================
// SHARED CONFIRMATION STATUS
// Google Apps Script / Google Sheet
// ============================================================

const CONFIRM_API_URL =
    "{CONFIRM_API_URL}";

const STRUCTURE_CONFIRM_API_URL =
    "{STRUCTURE_CONFIRM_API_URL}";

const changeCards =
    Array.from(
        document.querySelectorAll(
            ".change-card"
        )
    );


function confirmationKey(
    itemNumber,
    oldPrice,
    newPrice
) {{

    return [
        String(
            itemNumber || ""
        ).trim(),

        String(
            oldPrice || ""
        ).trim(),

        String(
            newPrice || ""
        ).trim()

    ].join("||");
}}


function jsonpRequest(params) {{

    return new Promise(
        (resolve, reject) => {{

            const callbackName =
                "__jacobConfirm_"
                + Date.now()
                + "_"
                + Math.random()
                    .toString(36)
                    .slice(2);

            const timeout =
                setTimeout(
                    () => {{

                        cleanup();

                        reject(
                            new Error(
                                "Request timeout"
                            )
                        );

                    }},
                    15000
                );

            const script =
                document.createElement(
                    "script"
                );


            function cleanup() {{

                clearTimeout(
                    timeout
                );

                if (
                    script.parentNode
                ) {{
                    script.parentNode
                        .removeChild(
                            script
                        );
                }}

                try {{
                    delete window[
                        callbackName
                    ];
                }} catch (e) {{
                    window[
                        callbackName
                    ] = undefined;
                }}
            }}


            window[
                callbackName
            ] = data => {{

                cleanup();

                resolve(
                    data
                );
            }};


            const url =
                new URL(
                    CONFIRM_API_URL
                );

            Object.entries(
                params || {{}}
            ).forEach(
                ([key, value]) => {{

                    url.searchParams.set(
                        key,
                        String(
                            value ?? ""
                        )
                    );
                }}
            );

            url.searchParams.set(
                "callback",
                callbackName
            );

            url.searchParams.set(
                "_",
                Date.now()
            );

            script.src =
                url.toString();

            script.onerror =
                () => {{

                    cleanup();

                    reject(
                        new Error(
                            "Request failed"
                        )
                    );
                }};

            document.body
                .appendChild(
                    script
                );
        }}
    );
}}


const confirmedRecords = new Map();


function escapeHtml(value) {{
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}}


function refreshUnconfirmedEmpty() {{
    const visibleUnconfirmed =
        changeCards.filter(
            card =>
                !card.classList.contains(
                    "is-confirmed"
                )
        );

    const empty =
        document.getElementById(
            "unconfirmedEmpty"
        );

    if (empty) {{
        empty.style.display =
            visibleUnconfirmed.length === 0
            ? "block"
            : "none";
    }}
}}


function formatJapanTime(value) {{
    const raw =
        String(value || "").trim();

    if (!raw) {{
        return "";
    }}

    const date =
        new Date(raw);

    if (
        raw.includes("T")
        &&
        !Number.isNaN(
            date.getTime()
        )
    ) {{
        const parts =
            new Intl.DateTimeFormat(
                "ja-JP",
                {{
                    timeZone:
                        "Asia/Tokyo",
                    year:
                        "numeric",
                    month:
                        "2-digit",
                    day:
                        "2-digit",
                    hour:
                        "2-digit",
                    minute:
                        "2-digit",
                    second:
                        "2-digit",
                    hour12:
                        false
                }}
            ).formatToParts(
                date
            );

        const values = {{}};

        parts.forEach(part => {{
            if (
                part.type !== "literal"
            ) {{
                values[part.type] =
                    part.value;
            }}
        }});

        return (
            values.year
            + "-"
            + values.month
            + "-"
            + values.day
            + " "
            + values.hour
            + ":"
            + values.minute
            + ":"
            + values.second
        );
    }}

    return raw
        .replace(
            /\s+JST$/i,
            ""
        );
}}


function renderConfirmedHistory() {{
    const list =
        document.getElementById(
            "confirmedHistoryList"
        );

    const empty =
        document.getElementById(
            "confirmedHistoryEmpty"
        );

    const count =
        document.getElementById(
            "confirmedCount"
        );

    const records =
        Array.from(
            confirmedRecords.values()
        ).sort(
            (a, b) =>
                String(
                    b.confirmedAt || ""
                ).localeCompare(
                    String(
                        a.confirmedAt || ""
                    )
                )
        );

    if (count) {{
        count.textContent =
            records.length;
    }}

    if (!list || !empty) {{
        return;
    }}

    if (records.length === 0) {{
        list.innerHTML = "";
        empty.style.display = "block";
        return;
    }}

    empty.style.display = "none";

    list.innerHTML =
        records.map(record => `
            <div class="confirmed-record">
                <a
                    class="confirmed-record-main"
                    href="${{escapeHtml(record.url)}}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <div class="change-info">
                        <div class="change-collection">
                            ${{escapeHtml(record.collection)}}
                        </div>
                        <div class="change-variant">
                            ${{escapeHtml(record.variant)}}
                        </div>
                        <div class="change-item">
                            ${{escapeHtml(record.itemNumber)}}
                        </div>
                        <div class="change-date">
                            ${{escapeHtml(record.changedAt)}}
                        </div>
                    </div>

                    <div class="change-prices">
                        <span class="old-price">
                            ${{escapeHtml(record.oldPriceDisplay)}}
                        </span>
                        <span class="arrow">→</span>
                        <span class="new-price">
                            ${{escapeHtml(record.newPriceDisplay)}}
                        </span>
                    </div>
                </a>

                <div class="confirmed-record-meta">
                    <strong>✓ 確認済み</strong>
                    &nbsp;&nbsp;
                    確認者：${{escapeHtml(record.confirmedBy)}}
                    &nbsp;/&nbsp;
                    ${{escapeHtml(formatJapanTime(record.confirmedAt))}} JST
                </div>
            </div>
        `).join("");
}}


function showConfirmed(
    card,
    confirmedBy,
    confirmedAt
) {{
    const key =
        confirmationKey(
            card.dataset.itemNumber,
            card.dataset.oldPrice,
            card.dataset.newPrice
        );

    const record = {{
        key: key,
        itemNumber:
            card.dataset.itemNumber || "",
        oldPrice:
            card.dataset.oldPrice || "",
        newPrice:
            card.dataset.newPrice || "",
        oldPriceDisplay:
            card.querySelector(
                ".old-price"
            )?.textContent?.trim() || "",
        newPriceDisplay:
            card.querySelector(
                ".new-price"
            )?.textContent?.trim() || "",
        collection:
            card.querySelector(
                ".change-collection"
            )?.textContent?.trim() || "",
        variant:
            card.querySelector(
                ".change-variant"
            )?.textContent?.trim() || "",
        changedAt:
            card.querySelector(
                ".change-date"
            )?.textContent?.trim() || "",
        url:
            card.querySelector(
                ".change-main-link"
            )?.getAttribute("href") || "",
        confirmedBy:
            String(
                confirmedBy || ""
            ).trim(),
        confirmedAt:
            String(
                confirmedAt || ""
            ).trim()
    }};

    confirmedRecords.set(
        key,
        record
    );

    card.classList.add(
        "is-confirmed"
    );

    renderConfirmedHistory();
    refreshUnconfirmedEmpty();
}}


async function loadConfirmations() {{

    if (
        changeCards.length === 0
    ) {{
        return;
    }}

    try {{

        const result =
            await jsonpRequest({{
                action: "list"
            }});

        const rows =
            Array.isArray(
                result
            )
            ? result
            : (
                result.rows
                || []
            );

        const confirmedMap =
            new Map();


        rows.forEach(row => {{

            const confirmed =
                row.confirmed === true
                ||
                String(
                    row.confirmed
                )
                .toLowerCase()
                === "true";


            if (!confirmed) {{
                return;
            }}


            const key =
                confirmationKey(
                    row.itemNumber,
                    row.oldPrice,
                    row.newPrice
                );


            confirmedMap.set(
                key,
                row
            );
        }});


        changeCards.forEach(card => {{

            const key =
                confirmationKey(
                    card.dataset.itemNumber,
                    card.dataset.oldPrice,
                    card.dataset.newPrice
                );

            const row =
                confirmedMap.get(
                    key
                );

            if (row) {{

                showConfirmed(
                    card,
                    row.confirmedBy,
                    row.confirmedAt
                );
            }}
        }});


    }} catch (error) {{

        console.error(
            "Confirmation load failed:",
            error
        );
    }}
}}


changeCards.forEach(card => {{

    const button =
        card.querySelector(
            ".confirm-button"
        );


    button.addEventListener(
        "click",
        async event => {{

            event.preventDefault();
            event.stopPropagation();


            const name =
                window.prompt(
                    "確認者の名前を入力してください"
                );


            if (
                name === null
                ||
                !name.trim()
            ) {{
                return;
            }}


            const originalText =
                button.textContent;


            button.disabled =
                true;

            button.textContent =
                "登録中...";


            try {{

                const result =
                    await jsonpRequest({{

                        action:
                            "confirm",

                        itemNumber:
                            card.dataset.itemNumber,

                        oldPrice:
                            card.dataset.oldPrice,

                        newPrice:
                            card.dataset.newPrice,

                        confirmedBy:
                            name.trim()
                    }});


                if (
                    !result
                    ||
                    result.ok !== true
                ) {{

                    throw new Error(
                        (
                            result
                            &&
                            result.error
                        )
                        ||
                        "Save failed"
                    );
                }}


                showConfirmed(
                    card,
                    result.confirmedBy
                        || name.trim(),
                    result.confirmedAt
                        || ""
                );


            }} catch (error) {{

                console.error(
                    "Confirmation save failed:",
                    error
                );


                alert(
                    "確認状態を保存できませんでした。"
                    + "\\n"
                    + "もう一度お試しください。"
                );


                button.disabled =
                    false;

                button.textContent =
                    originalText;
            }}
        }}
    );
}});



// ============================================================
// JEWELRY STRUCTURE CONFIRMATION
// Separate Apps Script endpoint; WATCHES is untouched.
// ============================================================

const structureCards =
    Array.from(
        document.querySelectorAll(
            ".structure-change-card"
        )
    );

const confirmedStructureRecords =
    new Map();


function structureConfirmationKey(
    eventKey
) {{
    return String(
        eventKey || ""
    ).trim();
}}


function structureJsonpRequest(params) {{

    return new Promise(
        (resolve, reject) => {{

            const callbackName =
                "__jacobJewelryStructure_"
                + Date.now()
                + "_"
                + Math.random()
                    .toString(36)
                    .slice(2);

            const timeout =
                setTimeout(
                    () => {{
                        cleanup();
                        reject(
                            new Error(
                                "Request timeout"
                            )
                        );
                    }},
                    15000
                );

            const script =
                document.createElement(
                    "script"
                );

            function cleanup() {{
                clearTimeout(
                    timeout
                );

                if (
                    script.parentNode
                ) {{
                    script.parentNode
                        .removeChild(
                            script
                        );
                }}

                try {{
                    delete window[
                        callbackName
                    ];
                }} catch (e) {{
                    window[
                        callbackName
                    ] = undefined;
                }}
            }}

            window[
                callbackName
            ] = data => {{
                cleanup();
                resolve(
                    data
                );
            }};

            const url =
                new URL(
                    STRUCTURE_CONFIRM_API_URL
                );

            Object.entries(
                params || {{}}
            ).forEach(
                ([key, value]) => {{
                    url.searchParams.set(
                        key,
                        String(
                            value ?? ""
                        )
                    );
                }}
            );

            url.searchParams.set(
                "callback",
                callbackName
            );

            url.searchParams.set(
                "_",
                Date.now()
            );

            script.src =
                url.toString();

            script.onerror =
                () => {{
                    cleanup();
                    reject(
                        new Error(
                            "Request failed"
                        )
                    );
                }};

            document.body
                .appendChild(
                    script
                );
        }}
    );
}}


function refreshStructureEmpty() {{
    const visible =
        structureCards.filter(
            card =>
                !card.classList.contains(
                    "is-confirmed"
                )
        );

    const empty =
        document.getElementById(
            "unconfirmedProductEmpty"
        );

    if (empty) {{
        empty.style.display =
            visible.length === 0
            ? "block"
            : "none";
    }}
}}


function showStructureConfirmed(
    card,
    confirmedBy,
    confirmedAt
) {{
    const key =
        structureConfirmationKey(
            card.dataset.eventKey
        );

    confirmedStructureRecords.set(
        key,
        {{
            confirmedBy:
                String(
                    confirmedBy || ""
                ).trim(),
            confirmedAt:
                String(
                    confirmedAt || ""
                ).trim()
        }}
    );

    card.classList.add(
        "is-confirmed"
    );

    refreshStructureEmpty();
}}


async function loadStructureConfirmations() {{

    if (
        structureCards.length === 0
    ) {{
        refreshStructureEmpty();
        return;
    }}

    try {{
        const result =
            await structureJsonpRequest({{
                action: "list"
            }});

        const rows =
            Array.isArray(
                result
            )
            ? result
            : (
                result.rows
                || []
            );

        const confirmedMap =
            new Map();

        rows.forEach(row => {{
            const confirmed =
                row.confirmed === true
                ||
                String(
                    row.confirmed
                )
                .toLowerCase()
                === "true";

            if (!confirmed) {{
                return;
            }}

            const key =
                structureConfirmationKey(
                    row.eventKey
                );

            if (key) {{
                confirmedMap.set(
                    key,
                    row
                );
            }}
        }});

        structureCards.forEach(card => {{
            const key =
                structureConfirmationKey(
                    card.dataset.eventKey
                );

            const row =
                confirmedMap.get(
                    key
                );

            if (row) {{
                showStructureConfirmed(
                    card,
                    row.confirmedBy,
                    row.confirmedAt
                );
            }}
        }});

    }} catch (error) {{
        console.error(
            "Jewelry structure confirmation load failed:",
            error
        );
    }} finally {{
        refreshStructureEmpty();
    }}
}}


structureCards.forEach(card => {{

    const button =
        card.querySelector(
            ".structure-confirm-button"
        );

    if (!button) {{
        return;
    }}

    button.addEventListener(
        "click",
        async event => {{

            event.preventDefault();
            event.stopPropagation();

            const name =
                window.prompt(
                    "確認者の名前を入力してください"
                );

            if (
                name === null
                ||
                !name.trim()
            ) {{
                return;
            }}

            const originalText =
                button.textContent;

            button.disabled =
                true;

            button.textContent =
                "登録中...";

            try {{
                const result =
                    await structureJsonpRequest({{
                        action:
                            "confirm",
                        eventKey:
                            card.dataset.eventKey,
                        changeType:
                            card.dataset.changeType,
                        sku:
                            card.dataset.sku,
                        product:
                            card.dataset.product,
                        variant:
                            card.dataset.variant,
                        changedAt:
                            card.dataset.changedAt,
                        url:
                            card.dataset.url,
                        oldStatus:
                            card.dataset.oldStatus,
                        newStatus:
                            card.dataset.newStatus,
                        price:
                            card.dataset.price,
                        confirmedBy:
                            name.trim()
                    }});

                if (
                    !result
                    ||
                    result.ok !== true
                ) {{
                    throw new Error(
                        (
                            result
                            &&
                            result.error
                        )
                        ||
                        "Save failed"
                    );
                }}

                showStructureConfirmed(
                    card,
                    result.confirmedBy
                        || name.trim(),
                    result.confirmedAt
                        || ""
                );

            }} catch (error) {{
                console.error(
                    "Jewelry structure confirmation save failed:",
                    error
                );

                alert(
                    "確認状態を保存できませんでした。"
                    + "\\n"
                    + "もう一度お試しください。"
                );

                button.disabled =
                    false;

                button.textContent =
                    originalText;
            }}
        }}
    );
}});


loadStructureConfirmations();


const confirmedHistoryButton =
    document.getElementById(
        "confirmedHistoryButton"
    );

const confirmedHistoryModal =
    document.getElementById(
        "confirmedHistoryModal"
    );


function openConfirmedModal() {{
    if (!confirmedHistoryModal) {{
        return;
    }}

    confirmedHistoryModal.classList.add(
        "is-open"
    );

    confirmedHistoryModal.setAttribute(
        "aria-hidden",
        "false"
    );

    document.body.style.overflow =
        "hidden";
}}


function closeConfirmedModal() {{
    if (!confirmedHistoryModal) {{
        return;
    }}

    confirmedHistoryModal.classList.remove(
        "is-open"
    );

    confirmedHistoryModal.setAttribute(
        "aria-hidden",
        "true"
    );

    document.body.style.overflow =
        "";
}}


if (confirmedHistoryButton) {{
    confirmedHistoryButton.addEventListener(
        "click",
        openConfirmedModal
    );
}}


document.querySelectorAll(
    "[data-close-confirmed-modal]"
).forEach(element => {{
    element.addEventListener(
        "click",
        closeConfirmedModal
    );
}});


document.addEventListener(
    "keydown",
    event => {{
        if (
            event.key === "Escape"
            &&
            confirmedHistoryModal
            &&
            confirmedHistoryModal.classList.contains(
                "is-open"
            )
        ) {{
            closeConfirmedModal();
        }}
    }}
);


renderConfirmedHistory();
refreshUnconfirmedEmpty();
loadConfirmations();


function updateHealthStatus() {{
    const stat =
        document.getElementById(
            "healthStat"
        );

    const label =
        document.getElementById(
            "healthStatus"
        );

    if (!stat || !label) {{
        return;
    }}

    const rowCount =
        Number(
            stat.dataset.currentRows || 0
        );

    const lastSeenRaw =
        String(
            stat.dataset.lastSeen || ""
        ).trim();

    let ageHours = null;

    if (lastSeenRaw) {{
        const parsed =
            new Date(
                lastSeenRaw.replace(
                    " ",
                    "T"
                ) + "Z"
            );

        if (
            !Number.isNaN(
                parsed.getTime()
            )
        ) {{
            ageHours =
                (
                    Date.now()
                    - parsed.getTime()
                )
                / 3600000;
        }}
    }}

    stat.classList.remove(
        "is-ok",
        "is-warning",
        "is-error"
    );

    if (
        rowCount < 490
        ||
        !lastSeenRaw
        ||
        ageHours === null
        ||
        ageHours > 30
    ) {{
        stat.classList.add(
            "is-error"
        );

        label.textContent =
            "要確認 ⚠";

        return;
    }}

    if (
        rowCount < 510
        ||
        ageHours > 18
    ) {{
        stat.classList.add(
            "is-warning"
        );

        label.textContent =
            "注意 △";

        return;
    }}

    stat.classList.add(
        "is-ok"
    );

    label.textContent =
        "正常 ✓";
}}


updateHealthStatus();

setInterval(
    updateHealthStatus,
    60000
);

</script>


</body>

</html>
"""


# ============================================================
# WRITE
# ============================================================

with open(
    OUTPUT_HTML,
    "w",
    encoding="utf-8"
) as f:

    f.write(page)


print("=" * 70)
print("PAGE GENERATED")
print("=" * 70)

print(
    "Current products:",
    len(current_rows)
)

print(
    "Price history:",
    len(history_rows)
)


print(
    "Product history:",
    len(product_history_rows)
)

print(
    "Output:",
    OUTPUT_HTML
)
