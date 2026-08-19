name: Jacob & Co. USA Jewelry Monitor

permissions:
  contents: write

on:
  workflow_dispatch:

  schedule:
    - cron: "0 1 * * *"
    - cron: "0 13 * * *"

jobs:
  monitor-jewelry:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          playwright install chromium

      - name: Run jewelry monitor
        run: |
          python jewelry_monitor.py

      - name: Generate jewelry dashboard
        run: |
          python generate_jewelry_page.py

      - name: Commit jewelry data and dashboard
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add jewelry_current_prices.csv
          git add jewelry_price_history.csv
          git add jewelry_change_history.csv
          git add jewelry_missing_candidates.csv
          git add jewelry.html

          if git diff --cached --quiet; then
            echo "No jewelry changes to commit."
          else
            git commit -m "Update jewelry monitor data and dashboard"
            git push
          fi
