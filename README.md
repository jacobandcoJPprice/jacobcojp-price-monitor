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

## Notifications

時計・ジュエリーの定期監視は、次の場合にGitHub Issue
`Jacob & Co. 価格監視通知`へ1回の実行につき1件だけ通知を追加します。

- 価格変更を1件以上検知した場合
- 商品の追加・削除・在庫状態など、商品構成変更を1件以上検知した場合
- 取得件数不足、USD確認失敗、生成・保存・公開処理などでエラーが発生した場合

通常の最終取得時刻の更新だけでは通知しません。複数の変更を同時に検知した場合も、
価格変更件数と商品構成変更件数をまとめて1件の通知にします。

通知先はリポジトリ所有者 `jacobandcoJPprice` です。GitHubの通知設定で
`Participating` の `Email` を有効にすると、登録済みメールアドレスでも受信できます。
