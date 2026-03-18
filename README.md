# Price Tracker

A Playwright-based product price tracker with optional Discord webhook alerts. Works as a standalone script, an importable Python package, or inside a Jupyter notebook.

## Setup

**1. Clone the repo and install:**
```bash
git clone https://github.com/your-username/price_tracker.git
cd price_tracker
pip install -e .
playwright install chromium --with-deps
```

**2. Edit `tracked.json` with your products:**
```json
{
  "discord_webhook": "https://discord.com/api/webhooks/YOUR/WEBHOOK",
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
| `selectors` | no | CSS selectors to find the price element. Falls back to built-in defaults |
| `discord_webhook` | no | Per-product webhook. Overrides the top-level default |

The top-level `discord_webhook` is a shared default used by all products that don't define their own.

## Jupyter usage

```python
from tracker import PriceTracker, run_from_config

# Check all products from tracked.json
await run_from_config("tracked.json")

# Single product
tracker = PriceTracker(
    url="https://www.sportchek.ca/...",
    product_name="Helly Hansen Jacket",
    discord_webhook="https://discord.com/api/webhooks/...",
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

Each product's history is saved to a separate JSON file (e.g. `history_helly_hansen_jacket.json`) in the working directory. These are excluded from git via `.gitignore`. Each file keeps the last 30 price checks.

## Discord alerts

To get a Discord webhook URL:
1. Open your server → channel settings → **Integrations** → **Webhooks**
2. Click **New Webhook**, give it a name, copy the URL
3. Paste it into `tracked.json`

Alert appearance:
- **Green embed** — price dropped to or below your threshold
- **Blue embed** — regular check-in (no threshold set)

Both show the current price, previous price with a ▼/▲ arrow, and a direct link to the product.
