#!/usr/bin/env bash

set -euo pipefail

issue_title="Jacob & Co. 価格監視通知"
issue_number="$(
  gh issue list \
    --repo "$GITHUB_REPOSITORY" \
    --state open \
    --limit 100 \
    --json number,title \
    --jq '[.[] | select(.title == "Jacob & Co. 価格監視通知")][0].number // empty'
)"

if [ "$JOB_STATUS" != "success" ]; then
  body="$(cat <<EOF
@${GITHUB_REPOSITORY_OWNER}

## ${MONITOR_NAME}：監視エラー

監視処理が正常に完了しませんでした。

- [監視ページを確認](${DASHBOARD_URL})
- [エラー内容を確認](${RUN_URL})
EOF
)"
elif [ "$HEALTHY" != "true" ]; then
  body="$(cat <<EOF
@${GITHUB_REPOSITORY_OWNER}

## ${MONITOR_NAME}：監視状態に注意

処理は完了しましたが、監視状態が正常基準を満たしていません。

- 登録数：${CURRENT_ROWS}件
- 監視通貨：${CURRENCIES}
- 最終取得から：${DATA_AGE_HOURS}時間
- 価格変更：${PRICE_CHANGES}件
- 商品構成変更：${STRUCTURE_CHANGES}件
- [監視ページを確認](${DASHBOARD_URL})
- [今回の監視処理を確認](${RUN_URL})
EOF
)"
else
  body="$(cat <<EOF
@${GITHUB_REPOSITORY_OWNER}

## ${MONITOR_NAME}：変更を検知

- 価格変更：${PRICE_CHANGES}件
- 商品構成変更：${STRUCTURE_CHANGES}件
- [監視ページを確認](${DASHBOARD_URL})
- [今回の監視処理を確認](${RUN_URL})
EOF
)"
fi

if [ -n "$issue_number" ]; then
  gh issue comment "$issue_number" \
    --repo "$GITHUB_REPOSITORY" \
    --body "$body"
else
  gh issue create \
    --repo "$GITHUB_REPOSITORY" \
    --title "$issue_title" \
    --body "$body" \
    --assignee "$GITHUB_REPOSITORY_OWNER"
fi
