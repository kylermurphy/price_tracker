"""
price_tracker.py
----------------
A standalone price tracker using Playwright, with optional Discord webhook alerts.

Run directly
------------
    python price_tracker.py                        # uses tracked.json in same folder
    python price_tracker.py --config my_tracked.json

Jupyter / import
----------------
    from price_tracker import PriceTracker, run_from_config

    # Single product
    tracker = PriceTracker(
        url="https://www.sportchek.ca/...",
        discord_webhook="https://discord.com/api/webhooks/...",
        alert_threshold=299.99,
        product_name="Helly Hansen Jacket",
    )
    await tracker.check()

    # All products from a config file
    await run_from_config("tracked.json")

Config file format (tracked.json)
---------------------------------
    {
      "discord_webhook": "https://discord.com/api/webhooks/...",  // shared default
      "products": [
        {
          "name": "Helly Hansen Jacket",
          "url": "https://www.sportchek.ca/...",
          "threshold": 299.99,
          "selectors": [".price__regular-price"],   // optional override
          "discord_webhook": "https://..."           // optional per-product override
        }
      ]
    }

Install
-------
    pip install playwright aiohttp
    playwright install chromium --with-deps
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import aiohttp
from playwright.async_api import async_playwright

# ── Default selectors (most specific first) ───────────────────────────────────

DEFAULT_SELECTORS = [
    "[data-testid='price-display']",
    ".price__regular-price",
    ".price__sale-price",
    ".price__regular",
    ".price__sale",
    ".selling-price",
    "[class*='price']",
]

# ── PriceTracker ──────────────────────────────────────────────────────────────

class PriceTracker:
    """
    Async price tracker for a single product URL.

    Parameters
    ----------
    url : str
        Full product page URL to track.
    history_file : str or Path, optional
        Where to persist price history (default: price_history.json).
    selectors : list[str], optional
        CSS selectors to try in order. Falls back to DEFAULT_SELECTORS.
    headless : bool
        Run browser headlessly (default: True).
    discord_webhook : str, optional
        Discord webhook URL to send alerts to.
    alert_threshold : float, optional
        Send a Discord alert when price drops to or below this value.
        If None, an alert is sent on every successful price check.
    product_name : str, optional
        Human-readable product name used in Discord messages.
    """

    def __init__(
        self,
        url: str,
        history_file: str | Path = "price_history.json",
        selectors: list[str] | None = None,
        headless: bool = True,
        discord_webhook: str | None = None,
        alert_threshold: float | None = None,
        product_name: str = "Product",
    ):
        self.url = url
        self.history_file = Path(history_file)
        self.selectors = selectors.extend(DEFAULT_SELECTORS)
        self.headless = headless
        self.discord_webhook = discord_webhook
        self.alert_threshold = alert_threshold
        self.product_name = product_name

    # ── History ───────────────────────────────────────────────────────────────

    def load_history(self) -> list[dict]:
        if self.history_file.exists():
            return json.loads(self.history_file.read_text())
        return []

    def save_history(self, history: list[dict]) -> None:
        self.history_file.write_text(json.dumps(history[:30], indent=2))

    def clear_history(self) -> None:
        if self.history_file.exists():
            self.history_file.unlink()
            print(f"  [{self.product_name}] History cleared.")
        else:
            print(f"  [{self.product_name}] No history file found.")

    def show_history(self) -> None:
        history = self.load_history()
        if not history:
            print(f"  [{self.product_name}] No history yet.")
            return
        prices = [h["price"] for h in history]
        print(f"\nHistory — {self.product_name}")
        print("─" * 60)
        print(f"  Current : ${history[0]['price']:.2f}")
        print(f"  Lowest  : ${min(prices):.2f}")
        print(f"  Highest : ${max(prices):.2f}")
        print(f"  Checks  : {len(history)}\n")
        for h in history:
            ts = datetime.fromisoformat(h["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {ts}  →  ${h['price']:.2f}  (via {h.get('selector', '?')})")
        print()

    # ── Discord ───────────────────────────────────────────────────────────────

    async def _send_discord(self, payload: dict) -> None:
        if not self.discord_webhook:
            return
        async with aiohttp.ClientSession() as session:
            async with session.post(self.discord_webhook, json=payload) as resp:
                if resp.status not in (200, 204):
                    text = await resp.text()
                    print(f"  Discord error {resp.status}: {text}")
                else:
                    print(f"  [{self.product_name}] Discord alert sent.")

    async def test_webhook(self) -> None:
        if not self.discord_webhook:
            print("No discord_webhook set.")
            return
        await self._send_discord({
            "embeds": [{
                "title": "Price Tracker — webhook test",
                "description": f"Connected! Tracking: **{self.product_name}**\n{self.url}",
                "color": 0x5865F2,
                "footer": {"text": "price_tracker.py"},
                "timestamp": datetime.utcnow().isoformat(),
            }]
        })

    async def _maybe_alert(self, entry: dict, history: list[dict]) -> None:
        if not self.discord_webhook:
            return
        price = entry["price"]
        prev_price = history[1]["price"] if len(history) > 1 else None

        if self.alert_threshold is not None:
            if price > self.alert_threshold:
                return
            title = f"Price alert — {self.product_name} dropped to ${price:.2f}!"
            color = 0x57F287
        else:
            title = f"Price check — {self.product_name}: ${price:.2f}"
            color = 0x5865F2

        lines = [f"**Current price:** ${price:.2f} CAD"]
        if prev_price:
            diff = price - prev_price
            arrow = "▼" if diff < 0 else "▲" if diff > 0 else "—"
            lines.append(f"**Previous price:** ${prev_price:.2f} CAD  {arrow} ${abs(diff):.2f}")
        if self.alert_threshold:
            lines.append(f"**Your threshold:** ${self.alert_threshold:.2f} CAD")
        lines.append(f"\n[View product]({self.url})")

        await self._send_discord({
            "embeds": [{
                "title": title,
                "description": "\n".join(lines),
                "color": color,
                "footer": {"text": f"via {entry.get('selector', '?')}"},
                "timestamp": datetime.utcnow().isoformat(),
            }]
        })

    # ── Browser ───────────────────────────────────────────────────────────────

    async def _make_page(self, pw):
        browser = await pw.chromium.launch(headless=self.headless)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        return browser, page

    async def _load_page(self, page):
        await page.goto(self.url, wait_until="domcontentloaded", timeout=30_000)
        combined = ", ".join(self.selectors)
        try:
            await page.wait_for_selector(combined, timeout=15_000)
        except Exception:
            raise ValueError(
                "No price selector appeared after 15s. "
                "Run debug() to find the right selector."
            )

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape(self) -> dict:
        async with async_playwright() as pw:
            browser, page = await self._make_page(pw)
            try:
                await self._load_page(page)
                raw = None
                matched_selector = None
                for sel in self.selectors:
                    el = await page.query_selector(sel)
                    if el:
                        text = (await el.inner_text()).strip()
                        if re.search(r"\d", text):
                            raw = text
                            matched_selector = sel
                            break
            finally:
                await browser.close()

        if not raw:
            raise ValueError("Selector matched but contained no numeric price.")

        price = float(re.sub(r"[^\d.]", "", raw))
        return {"price": price, "raw": raw, "selector": matched_selector}

    async def check(self) -> dict:
        print(f"  [{self.product_name}] Checking...")
        result = await self.scrape()
        entry = {
            "price":     result["price"],
            "raw":       result["raw"],
            "selector":  result["selector"],
            "timestamp": datetime.now().isoformat(),
        }
        history = self.load_history()
        history.insert(0, entry)
        self.save_history(history)
        print(f"  [{self.product_name}] ${entry['price']:.2f} CAD  (via {entry['selector']})")
        await self._maybe_alert(entry, history)
        return entry

    async def debug(self) -> list[dict]:
        async with async_playwright() as pw:
            browser, page = await self._make_page(pw)
            try:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(4_000)
                results = await page.evaluate("""() => {
                    const hits = [];
                    for (const el of document.querySelectorAll('*')) {
                        const cls   = el.className?.toString() || '';
                        const attrs = Array.from(el.attributes)
                            .map(a => a.name + '=' + a.value).join(' ');
                        const text  = el.innerText?.trim();
                        if ((cls.toLowerCase().includes('price') ||
                             attrs.toLowerCase().includes('price')) && text) {
                            hits.push({
                                tag:   el.tagName.toLowerCase(),
                                cls:   cls,
                                attrs: attrs,
                                text:  text.slice(0, 80)
                            });
                        }
                    }
                    return hits;
                }""")
            finally:
                await browser.close()

        print(f"\nFound {len(results)} price-related elements on:\n{self.url}\n")
        for r in results:
            print(f"  <{r['tag']}>  class='{r['cls'][:60]}'  →  '{r['text']}'")
        print(
            "\nPrefix the class with '.' to use as a selector, e.g.\n"
            "  class='price__regular-price'  →  '.price__regular-price'"
        )
        return results


# ── Config runner ─────────────────────────────────────────────────────────────

def load_config(config_path: str | Path = "tracked.json") -> dict:
    """Load and validate a config file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Create a tracked.json file — see tracked.example.json for the format."
        )
    return json.loads(path.read_text())


def _tracker_from_config_entry(entry: dict, default_webhook: str | None) -> PriceTracker:
    """Build a PriceTracker from a single products[] entry."""
    name = entry.get("name", "Product")
    # Derive a safe filename from the product name
    safe_name = re.sub(r"[^\w\-]", "_", name.lower())
    history_file = entry.get("history_file", f"history_{safe_name}.json")

    return PriceTracker(
        url=entry["url"],
        product_name=name,
        history_file=history_file,
        selectors=entry.get("selectors") or DEFAULT_SELECTORS,
        discord_webhook=entry.get("discord_webhook") or default_webhook,
        alert_threshold=entry.get("threshold"),
    )


async def run_from_config(config_path: str | Path = "tracked.json") -> list[dict]:
    """
    Load tracked.json and run check() on every product in sequence.

    Returns a list of result dicts (one per product).
    The DISCORD_WEBHOOK environment variable is used as a fallback webhook
    when none is set in the config file.
    """
    import os
    config = load_config(config_path)
    products = config.get("products", [])
    # Prefer webhook from config, fall back to environment variable
    default_webhook = config.get("discord_webhook") or os.environ.get("DISCORD_WEBHOOK")

    if not products:
        print("No products found in config.")
        return []

    print(f"Running price checks for {len(products)} product(s)...\n")
    results = []
    for entry in products:
        tracker = _tracker_from_config_entry(entry, default_webhook)
        try:
            result = await tracker.check()
            results.append({"name": tracker.product_name, "result": result})
        except Exception as e:
            print(f"  [{tracker.product_name}] ERROR: {e}")
            results.append({"name": tracker.product_name, "error": str(e)})

    print(f"\nDone. Checked {len(products)} product(s).")
    return results


# ── CLI entry point ───────────────────────────────────────────────────────────

def _cli():
    usage = (
        "Usage:\n"
        "  python price_tracker.py                        # run all products from tracked.json\n"
        "  python price_tracker.py --config <file>        # use a different config file\n"
    )

    config_path = "tracked.json"
    args = sys.argv[1:]

    it = iter(args)
    for arg in it:
        if arg in ("--config", "-c"):
            config_path = next(it, "tracked.json")
        elif arg in ("--help", "-h"):
            print(usage)
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}\n")
            print(usage)
            sys.exit(1)

    asyncio.run(run_from_config(config_path))


if __name__ == "__main__":
    _cli()
