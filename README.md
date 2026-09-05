# Jacob & Co. USA Price Monitor

Jacob & Co.公式サイトの米国価格をGitHub Actionsで定期監視し、GitHub Pagesに表示する社内用モニターです。

## Jewelry monitor

- 公式の `/pages/collections` に表示される全ジュエリーコレクションを毎回自動検出
- Shopifyの市場をUnited Statesに設定
- 同一セッションの `/cart.js` が `USD` を返すことを取得前後に確認
- USDを確認できない場合はCSVを更新せず、安全停止
- 各コレクションの全商品・全バリエーションを取得し、価格・追加・削除・在庫状態を比較
- 日本時間の毎日09:15と21:15に自動実行

公開ダッシュボード: <https://jacobandcojpprice.github.io/jacobcojp-price-monitor/jewelry.html>

### Manual diagnostic

```bash
pip install -r requirements.txt
python jewelry_test.py
```

診断はデータを書き換えず、コレクション数、商品数、バリエーション数、全価格の有無、通貨がUSDだけであることを確認します。
