import csv
import html
import os
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(
    BASE_DIR,
    "current_prices.csv"
)

HISTORY_CSV = os.path.join(
    BASE_DIR,
    "price_history_v2.csv"
)

OUTPUT_HTML = os.path.join(
    BASE_DIR,
    "index.html"
)


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


# Sort current prices
current_rows.sort(
    key=lambda x: (
        str(
            x.get("Collection", "")
        ).lower(),
        str(
            x.get("Item Number", "")
        ).lower()
    )
)


# Latest changes first
history_rows = list(
    reversed(
        history_rows
    )
)


# ============================================================
# CURRENT PRICE CARDS
# ============================================================

current_cards = []

for row in current_rows:

    collection = esc(
        row.get(
            "Collection",
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
            "Item Number",
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
                    "Collection",
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
                    "Item Number",
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
                ITEM NUMBER
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

for row in history_rows[:50]:

    collection = esc(
        row.get(
            "Collection",
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
            "Item Number",
            ""
        )
    )

    old_price = format_price(
        row.get(
            "Old Price",
            ""
        )
    )

    new_price = format_price(
        row.get(
            "New Price",
            ""
        )
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
        <a
            class="change-card"
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
# UPDATED TIME
# ============================================================

updated_at = datetime.now().strftime(
    "%Y-%m-%d %H:%M"
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
Jacob & Co. USA Price Monitor
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
    text-decoration: none;
    border: 1px solid #ddd;
    padding: 20px 22px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 25px;

    transition:
        transform .15s ease,
        border-color .15s ease;
}}

.change-card:hover {{
    transform: translateY(-1px);
    border-color: #888;
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

    .grid {{
        grid-template-columns:
            1fr;
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
            USA Official Price Monitor
        </h1>

        <div class="subtitle">
            Jacob &amp; Co. 米国公式価格ページ監視
        </div>

        <div class="stats">

            <div class="stat">
                現在の登録数：
                <strong>
                    {len(current_rows)}
                </strong>
            </div>

            <div class="stat">
                価格変更履歴：
                <strong>
                    {len(history_rows)}
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
                    Jacob &amp; Co. 米国公式価格の変更履歴
                </div>

            </div>

        </div>


        <div class="change-list">

            {history_html}

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
                    Item Number・Collection・Variant から検索できます
                </div>

            </div>

        </div>


        <div class="search-wrap">

            <input
                id="search"
                class="search"
                type="text"
                placeholder="ITEM NUMBER / COLLECTION / VARIANT を検索..."
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


<footer class="footer">

    Data source:
    Jacob &amp; Co. USA Official Timepiece Prices

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
    "Output:",
    OUTPUT_HTML
)
