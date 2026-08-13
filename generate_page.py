import csv
import html
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRENT_CSV = os.path.join(BASE_DIR, "current_prices.csv")
HISTORY_CSV = os.path.join(BASE_DIR, "price_history_v2.csv")
OUTPUT_HTML = os.path.join(BASE_DIR, "index.html")


def read_csv(path):
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def esc(value):
    return html.escape(str(value or ""))


def money(value):
    try:
        if value is None or str(value).strip() == "":
            return "-"
        return "${:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return esc(value)


def number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0


def get_last_scan(products):
    values = []

    for product in products:
        value = product.get("Last Seen", "")
        if value:
            values.append(value)

    if values:
        return max(values)

    return "-"


def availability_text(value):
    value = str(value or "")

    if "InStock" in value:
        return "在庫あり"

    if "OutOfStock" in value:
        return "在庫なし"

    if value:
        return esc(value)

    return "-"


products = read_csv(CURRENT_CSV)
history = read_csv(HISTORY_CSV)

products.sort(
    key=lambda x: number(x.get("Price")),
    reverse=True
)

history.reverse()

collections = sorted(
    {
        p.get("Collection", "").strip()
        for p in products
        if p.get("Collection", "").strip()
    }
)

last_scan = get_last_scan(products)


product_rows = []

for p in products:

    collection = esc(p.get("Collection", ""))
    variant = esc(p.get("Variant", ""))
    item_number = esc(p.get("Item Number", "")) or "-"
    price = money(p.get("Price"))
    availability = availability_text(p.get("Availability", ""))
    last_seen = esc(p.get("Last Seen", ""))
    url = esc(p.get("URL", ""))

    if url:
        link = (
            f'<a class="official-link" href="{url}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'公式サイトを見る →</a>'
        )
    else:
        link = "-"

    product_rows.append(
        f"""
        <tr data-collection="{collection}">
            <td>{collection}</td>
            <td>{variant}</td>
            <td class="item-number">{item_number}</td>
            <td class="price">{price}</td>
            <td><span class="status">{availability}</span></td>
            <td>{last_seen}</td>
            <td>{link}</td>
        </tr>
        """
    )


history_rows = []

for h in history[:100]:

    old_price = number(h.get("Old Price"))
    new_price = number(h.get("New Price"))
    difference = new_price - old_price

    if difference > 0:
        diff_html = (
            f'<span class="price-up">'
            f'↑ +${difference:,.0f}</span>'
        )

    elif difference < 0:
        diff_html = (
            f'<span class="price-down">'
            f'↓ -${abs(difference):,.0f}</span>'
        )

    else:
        diff_html = "—"

    url = esc(h.get("URL", ""))

    if url:
        link = (
            f'<a class="official-link" href="{url}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'公式サイトを見る →</a>'
        )
    else:
        link = "-"

    history_rows.append(
        f"""
        <tr>
            <td>{esc(h.get("Changed At", ""))}</td>
            <td>{esc(h.get("Collection", ""))}</td>
            <td>{esc(h.get("Variant", ""))}</td>
            <td class="item-number">
                {esc(h.get("Item Number", "")) or "-"}
            </td>
            <td>{money(h.get("Old Price"))}</td>
            <td class="price">{money(h.get("New Price"))}</td>
            <td>{diff_html}</td>
            <td>{link}</td>
        </tr>
        """
    )


collection_options = "".join(
    f'<option value="{esc(c)}">{esc(c)}</option>'
    for c in collections
)


if history_rows:

    history_content = f"""
    <div class="table-wrap">

        <table>

            <thead>
                <tr>
                    <th>変更日時</th>
                    <th>コレクション</th>
                    <th>モデル</th>
                    <th>Item Number</th>
                    <th>旧価格</th>
                    <th>新価格</th>
                    <th>変更額</th>
                    <th>公式商品ページ</th>
                </tr>
            </thead>

            <tbody>
                {''.join(history_rows)}
            </tbody>

        </table>

    </div>
    """

else:

    history_content = """
    <div class="empty">
        現在、価格変更は検出されていません。
    </div>
    """


page = f"""<!DOCTYPE html>

<html lang="ja">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<meta
    http-equiv="refresh"
    content="300"
>

<title>
Jacob & Co. Japan | 米国公式サイト価格モニター
</title>


<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family:
        Arial,
        "Yu Gothic",
        "YuGothic",
        "Meiryo",
        sans-serif;

    background: #f5f5f5;
    color: #171717;
}}


.header {{
    background: #080808;
    color: #ffffff;
    padding: 34px 4%;
}}

.header-inner {{
    max-width: 1700px;
    margin: auto;
}}

.brand {{
    font-size: 30px;
    font-weight: 600;
    letter-spacing: 2px;
}}

.subtitle {{
    margin-top: 9px;
    color: #c4c4c4;
    font-size: 15px;
    letter-spacing: 1px;
}}

.internal {{
    margin-top: 13px;
    display: inline-block;
    padding: 6px 11px;
    border-radius: 20px;
    background: #242424;
    color: #d0d0d0;
    font-size: 11px;
}}


.container {{
    width: 94%;
    max-width: 1700px;
    margin: 28px auto 50px;
}}


.stats {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin-bottom: 22px;
}}

.stat-card {{
    background: #ffffff;
    padding: 23px;
    border-radius: 11px;
    box-shadow: 0 2px 10px rgba(0,0,0,.055);
}}

.stat-label {{
    color: #777;
    font-size: 12px;
    letter-spacing: .5px;
}}

.stat-number {{
    margin-top: 9px;
    font-size: 29px;
    font-weight: 700;
}}


.guide {{
    background: #ffffff;
    padding: 20px 22px;
    border-radius: 11px;
    margin-bottom: 22px;
    box-shadow: 0 2px 10px rgba(0,0,0,.055);
    font-size: 13px;
    line-height: 1.9;
}}

.guide-title {{
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 5px;
}}


.controls {{
    display: flex;
    gap: 12px;
    padding: 18px;
    background: #ffffff;
    border-radius: 11px;
    margin-bottom: 22px;
    box-shadow: 0 2px 10px rgba(0,0,0,.055);
}}

.search {{
    flex: 1;
    border: 1px solid #dddddd;
    border-radius: 7px;
    padding: 14px 15px;
    font-size: 14px;
    outline: none;
}}

.search:focus {{
    border-color: #777777;
}}

select {{
    border: 1px solid #dddddd;
    border-radius: 7px;
    padding: 0 14px;
    background: #ffffff;
    min-width: 240px;
    font-size: 13px;
}}


.section {{
    background: #ffffff;
    border-radius: 11px;
    margin-bottom: 25px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,.055);
}}

.section-header {{
    padding: 21px 22px;
    border-bottom: 1px solid #eeeeee;
    font-size: 18px;
    font-weight: 700;
}}


.table-wrap {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    text-align: left;
    padding: 13px 14px;
    background: #f8f8f8;
    color: #666666;
    font-size: 11px;
    letter-spacing: .4px;
    border-bottom: 1px solid #dddddd;
    white-space: nowrap;
}}

td {{
    padding: 14px;
    border-bottom: 1px solid #eeeeee;
    font-size: 13px;
    vertical-align: middle;
}}

tbody tr:hover {{
    background: #fafafa;
}}

.price {{
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
}}

.item-number {{
    font-family: Consolas, monospace;
    white-space: nowrap;
}}

.status {{
    display: inline-block;
    padding: 5px 9px;
    background: #efefef;
    border-radius: 20px;
    font-size: 11px;
    white-space: nowrap;
}}

.official-link {{
    color: #111111;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
}}

.official-link:hover {{
    text-decoration: underline;
}}

.price-up {{
    font-weight: 700;
}}

.price-down {{
    font-weight: 700;
}}

.empty {{
    padding: 38px;
    text-align: center;
    color: #888888;
    font-size: 13px;
}}


.result-info {{
    margin-left: auto;
    padding: 14px 4px;
    color: #777777;
    font-size: 12px;
    white-space: nowrap;
}}


.footer {{
    text-align: center;
    padding: 30px;
    color: #999999;
    font-size: 12px;
    line-height: 1.8;
}}


@media(max-width: 850px) {{

    .stats {{
        grid-template-columns: 1fr;
    }}

    .controls {{
        flex-direction: column;
    }}

    select {{
        width: 100%;
        padding: 14px;
    }}

    .result-info {{
        margin-left: 0;
    }}

}}

</style>

</head>


<body>


<header class="header">

    <div class="header-inner">

        <div class="brand">
            JACOB & CO. JAPAN
        </div>

        <div class="subtitle">
            米国公式サイト価格モニター
        </div>

        <div class="internal">
            社内利用限定
        </div>

    </div>

</header>


<main class="container">


<div class="stats">

    <div class="stat-card">

        <div class="stat-label">
            バリエーション総数
        </div>

        <div class="stat-number">
            {len(products)}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-label">
            価格変更履歴
        </div>

        <div class="stat-number">
            {len(history)}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-label">
            最終価格確認
        </div>

        <div
            class="stat-number"
            style="font-size:18px;"
        >
            {esc(last_scan)}
        </div>

    </div>

</div>


<div class="guide">

    <div class="guide-title">
        ご利用案内
    </div>

    コレクション名、モデル名、Item Numberから
    商品を検索できます。

    <br>

    表示価格は Jacob & Co. 米国公式サイトの情報をもとに、
    システムが定期的に自動確認しています。

</div>


<div class="controls">

    <input
        id="search"
        class="search"
        type="text"
        placeholder="コレクション・モデル・Item Numberを検索"
        oninput="filterProducts()"
    >

    <select
        id="collectionFilter"
        onchange="filterProducts()"
    >

        <option value="">
            すべてのコレクション
        </option>

        {collection_options}

    </select>

    <div
        id="resultInfo"
        class="result-info"
    >
    </div>

</div>


<section class="section">

    <div class="section-header">
        現在の米国公式価格
    </div>

    <div class="table-wrap">

        <table id="productTable">

            <thead>

                <tr>

                    <th>コレクション</th>

                    <th>モデル</th>

                    <th>Item Number</th>

                    <th>米国公式価格</th>

                    <th>在庫状況</th>

                    <th>最終確認</th>

                    <th>公式商品ページ</th>

                </tr>

            </thead>


            <tbody>

                {''.join(product_rows)}

            </tbody>

        </table>

    </div>

</section>


<section class="section">

    <div class="section-header">
        最近の価格変更
    </div>

    {history_content}

</section>


</main>


<footer class="footer">

    Jacob & Co. Japan

    <br>

    米国公式サイト価格モニター

    <br>

    社内利用限定

</footer>


<script>

function filterProducts() {{

    const search =
        document
        .getElementById("search")
        .value
        .toLowerCase()
        .trim();

    const collection =
        document
        .getElementById("collectionFilter")
        .value;

    const rows =
        document
        .querySelectorAll(
            "#productTable tbody tr"
        );

    let visible = 0;

    rows.forEach(row => {{

        const text =
            row.innerText
            .toLowerCase();

        const rowCollection =
            row.dataset.collection;

        const matchesSearch =
            text.includes(search);

        const matchesCollection =
            collection === "" ||
            rowCollection === collection;

        if (
            matchesSearch &&
            matchesCollection
        ) {{

            row.style.display = "";
            visible++;

        }}

        else {{

            row.style.display = "none";

        }}

    }});


    document
    .getElementById("resultInfo")
    .textContent =
        visible + " 件を表示";

}}


filterProducts();

</script>


</body>

</html>
"""


with open(
    OUTPUT_HTML,
    "w",
    encoding="utf-8"
) as f:

    f.write(page)


print("=" * 60)

print(
    "Jacob & Co. Japan "
    "価格モニターページを生成しました。"
)

print("=" * 60)

print(
    f"商品数: {len(products)}"
)

print(
    f"価格変更履歴: {len(history)}"
)

print(
    f"最終価格確認: {last_scan}"
)

print(
    f"出力先: {OUTPUT_HTML}"
)
