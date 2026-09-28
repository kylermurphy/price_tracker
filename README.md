# Price Tracker

A Playwright-based product price tracker with optional Discord webhook alerts. Works as a standalone script, an importable Python package, or inside a Jupyter notebook.

## Setup

**1. Clone the repo and install** (requires Python 3.11+):
```bash
git clone https://github.com/kylermurphy/price_tracker.git
cd price_tracker
pip install -e .
playwright install chromium --with-deps
```

**2. Copy `tracked.example.json` to `tracked.json` and add your products:**
```bash
cp tracked.example.json tracked.json
```
```json
{
  "products": [
    {
      "name": "Helly Hansen Jacket",
      "url": "https://www.sportchek.ca/en/pdp/...",
      "threshold": 299.99,
      "selectors": [".price__regular-price"]
    }
  ]
}
```

See `tracked.example.json` for the full documented example, including every optional key and the Discord webhook options.

**3. Run:**
```bash
price-tracker                          # uses tracked.json
price-tracker --config other.json      # use a different file
```

## Config options

| Field | Required | Description |
|---|---|---|
| `name` | yes | Product name shown in Discord alerts |
| `url` | yes | Full product page URL |
| `threshold` | no | Alert when price drops to or below this value. If omitted, alerts on every check |
| `selectors` | no | CSS selectors to try first, in order; the built-in defaults are tried after them |
| `discord_webhook` | no | Per-product webhook. Overrides the top-level default |
| `history_file` | no | Where this product's price history is saved. Defaults to `history_<name>.json` (product name lowercased, with non-letter/digit/`_`/`-` characters replaced by `_`) |

Webhook precedence, most specific first: a product's own `discord_webhook` → the top-level `discord_webhook` → the `DISCORD_WEBHOOK` environment variable. An empty string (`""`) counts as unset at each level, so it falls through to the next one.

## Jupyter usage

```python
import os
from tracker import PriceTracker, run_from_config

# Check all products from tracked.json
await run_from_config("tracked.json")

# Single product
tracker = PriceTracker(
    url="https://www.sportchek.ca/...",
    product_name="Helly Hansen Jacket",
    discord_webhook=os.environ.get("DISCORD_WEBHOOK"),
    alert_threshold=299.99,
)
await tracker.check()

# Test your Discord webhook
await tracker.test_webhook()

# Find the right CSS selector for a page
await tracker.debug()

# View price history
tracker.show_history()
```

## Finding the right selector

If the tracker can't find the price on a page, run the debug helper:

```python
tracker = PriceTracker(url="https://...")
await tracker.debug()
```

This prints every element whose class or attributes contain the word "price". Take the `class` value from the output, prefix it with `.`, and add it to the `selectors` list in `tracked.json`:

```
<div>  class='price__regular-price'  →  '$349.99'
```
```json
"selectors": [".price__regular-price"]
```

## Price history

Each product's history is saved to a separate JSON file (e.g. `history_helly_hansen_jacket.json`) in the working directory, keeping the last 30 price checks. The files aren't git-ignored: the scheduled GitHub Actions workflow commits its updated `history_*.json` files back to the repo after each run (see **Scheduled runs** below).

## Discord alerts

To get a Discord webhook URL:
1. Open your server → channel settings → **Integrations** → **Webhooks**
2. Click **New Webhook**, give it a name, copy the URL
3. Set it as the `DISCORD_WEBHOOK` environment variable when running locally, or as a repo secret named `DISCORD_WEBHOOK` for the scheduled workflow (Settings → Secrets and variables → Actions). Don't paste it into `tracked.json`: that file is committed to the repo, so a webhook stored there becomes public in a public repo.

Alert appearance:
- **Green embed** — price dropped to or below your threshold
- **Blue embed** — regular check-in (no threshold set)

Both show the current price, previous price with a ▼/▲ arrow, and a direct link to the product.

## Scheduled runs (GitHub Actions)

`.github/workflows/price_tracker.yml` runs price checks on a schedule, with no local machine required:

- **When:** daily at 10:00 and 21:00 UTC, plus on demand from the repo's **Actions** tab (`workflow_dispatch`).
- **Secret:** set a repo secret named `DISCORD_WEBHOOK` (Settings → Secrets and variables → Actions) with your webhook URL. The workflow passes it through as the `DISCORD_WEBHOOK` environment variable when it runs `price-tracker --config tracked.json`.
- **History:** after each run, it commits any updated `history_*.json` files back to the repo.
