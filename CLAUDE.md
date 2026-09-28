# CLAUDE.md — price_tracker

Instructions for Claude Code **and** claude.ai/code (cloud) sessions working in this repo.
Both read this file. Edit it in dev-hub (`repos/price_tracker/CLAUDE.md`), not
here: this copy is replaced from the master at the start of each task.

## What this is
A Playwright-based product price tracker with optional Discord webhook alerts. Runs as a
standalone script, an importable Python package, or inside a Jupyter notebook. A GitHub
Actions workflow runs it on a schedule (twice daily) and commits updated price-history files
back to the repo.

## Environment & install
- Python **>= 3.11**.
- Install: `pip install -e .` then `playwright install chromium --with-deps`.
- CLI entry point: `price-tracker` (`--config <file>`, defaults to `tracked.json`).

## Commands
- No test suite yet (PRICE-2).
- Manual run: `price-tracker --config tracked.json`.
- Debug a broken selector: `PriceTracker(url=...).debug()` — prints every element whose
  class/attributes contain "price".

## Layout
- `tracker/price_tracker.py` — everything: `PriceTracker` class (scrape/check/history/Discord
  alert), `load_config`/`run_from_config`, the `_cli` entry point.
- `tracked.json` — the user's real product list (webhook, URL, threshold, selectors per
  product); not example data.
- `history_*.json` — one per product, last 30 checks each, written by the scheduled run.
- `.github/workflows/` — the scheduled price-check workflow (not a test/lint CI).

## Conventions & gotchas
- Most of the repo's commit history is the scheduled Actions workflow committing updated
  `history_*.json` files (`github-actions[bot]`, ~195 of 212 commits as of 2026-09-26) —
  don't read the raw commit count as development activity.
- `DEFAULT_SELECTORS` in `price_tracker.py` is meant as a fallback list tried in order, but
  `_tracker_from_config_entry` picks a product's own `selectors` **instead of** the defaults
  (`entry.get("selectors") or DEFAULT_SELECTORS`), not in addition to them. Since most
  `tracked.json` entries give a single site-specific selector, `scrape()`'s loop has nothing
  else to fall through to if that one selector stops matching (PRICE-6).
- `run_from_config` already catches per-product exceptions so one broken selector doesn't
  stop the rest of the run — keep that when touching it.
- `load_config`'s `FileNotFoundError` message points readers at `tracked.example.json`, which
  doesn't exist yet (PRICE-3).
- The README's clone command still has the template placeholder `your-username` (PRICE-1).
- Today `check()` calls `_maybe_alert()` per product, so a run with 5 tracked products sends
  5 separate Discord messages (and none at all for a product above its `alert_threshold`).
  PRICE-7 replaces this with one combined message per run.
- `pyproject.toml` has no `authors`/`license`/`readme`/classifiers, despite a real MIT
  `LICENSE` file in the repo (PRICE-5).

## Learnings

Durable facts from past tasks, promoted from `log/<ID>.md` by `mark-done` (max ~15).

_None yet._

## Task protocol (dev-hub tasks)

Tasks come from **dev-hub** (`kylermurphy/dev-hub`). Its `CLAUDE.md` → **Task protocol** is the
full, authoritative version; this is the summary. Each task is self-contained: start from its
board row alone.

- **Branch** `task/<ID>-<slug>` off the default branch; never commit to `main`.
- **First commit:** sync this file from its dev-hub master
  (`repos/price_tracker/CLAUDE.md`). Edit instructions in the master, never here.
- **Plan** saved to dev-hub `log/<ID>.md` before heavy work (`plan-task <ID>`); a `plan <ID>`
  dry run saves nothing. **Draft PR** following dev-hub's `templates/PULL_REQUEST_TEMPLATE.md`
  (not copied here): ID, what, why, how tested, DoD check.
- **Bookkeeping** (`log/<ID>.md`, `TASK_LOG.md` row, board Status → `WIP`) goes straight to
  dev-hub `main`. In a branch-restricted session it goes to the designated branch with an
  open PR instead (say so in chat; never merge it yourself). Only `mark-done <ID>` sets `Done`.
- **Stop states:** `Blocked` (fill `## Blocked / open questions`) or `Usage-stopped`; keep
  `Next step` current and resume with `pickup-task <ID>`.
- **Batches** (`multi-task`, or `plan-task` with several IDs): one branch
  `task/<ID>+<ID>+…-<slug>` and one PR for up to 5 simple tasks; each keeps its own log, and
  commits are prefixed with their ID. A `Blocked` task is dropped from the batch; the rest
  ship. Rules: dev-hub `CLAUDE.md` → Batches.
- **Learnings:** mark lasting findings as `Learning:` lines in the log; `mark-done` promotes
  them into `## Learnings` above (via the master).
- **Subagents:** delegate only broad/mechanical work to cheaper models, per dev-hub
  `CLAUDE.md` → Subagents; the main session does all commits and pushes.
- Definition of done = the task's row on dev-hub `TASK_BOARD.md`.

## Task board
This repo's backlog IDs use the **`PRICE-`** prefix.
