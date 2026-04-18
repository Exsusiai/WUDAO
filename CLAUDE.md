# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**悟道 (Wudao)** is a local-first, single-user trading workbench for Jason. It is explicitly NOT:
- a quantitative research platform
- a backtesting lab
- a strategy performance comparison center
- a fully automated trading system
- a product for anyone other than Jason

### Scope Discipline (important)

Market already has excellent general-purpose trading software (TradingView, broker apps, CCXT). Wudao does NOT compete on those. It builds **only** the pieces those tools don't do well:

1. **仓位自动计算** — given account equity + risk % + entry + stop, compute position size, risk $, R:R
2. **高级自动止盈止损** — break-even move, trailing stop, ladder TP (beyond what brokers offer)
3. **自动交易记录** — every closed trade auto-written to local DB for review
4. **交易纪律框架** — programmable pre-trade discipline checks that block non-compliant orders

Everything else (charts, indicators, backtesting, strategy management) should **reuse external tools** (TradingView via webhook, broker UIs for entry, etc.) rather than be rebuilt inside Wudao.

### Current Status

**Scaffolding only.** The base repo runs (FastAPI + Next.js + SQLite + one `AppSettings` table + `/api/health` + `/api/settings`) and can be extended milestone by milestone. No trading features implemented yet.

## Development Commands

```bash
make dev              # Start full dev environment (API port 8000 + Frontend port 3000)
make install          # Install all dependencies (Python + Node)
make api              # Start API server only
make web              # Start frontend only
make migrate          # Run Alembic migrations
make seed             # Seed database with defaults
```

Single test: `source .venv/bin/activate && pytest tests/ -k test_name`

## Architecture

Local-first Web app with frontend-backend separation:

- **Frontend**: Next.js + TypeScript + Tailwind + shadcn/ui (`apps/web/`)
- **Backend API**: FastAPI + SQLModel (`services/api/`)
- **Worker/Scheduler**: Reserved directory (`services/worker/`) — no code yet
- **Database**: SQLite at `data/wudao.db` (path from `.env` `DATABASE_URL`)
- **Migrations**: Alembic reads DB URL from `services.api.config.settings`, so alembic and the running app always hit the same file

### Current directory layout

```
wudao/
├── apps/web/                # Next.js frontend (Dashboard + Settings only for now)
├── services/
│   ├── api/                 # FastAPI main service
│   └── worker/              # (empty — future scheduler)
├── python/
│   └── core/                # DB engine, models (AppSettings only), logging, mode
├── infra/
│   ├── db/                  # Alembic migrations + seed.py
│   └── scripts/             # Dev startup scripts
├── docs/                    # Product & architecture docs
└── data/wudao.db            # SQLite DB (gitignored)
```

New domain modules (e.g. `python/risk/`, `python/journal/`) should be added only when a concrete milestone needs them.

## Key Design Constraints

1. **Database is the single source of truth** — Notion is a sync target, never the primary store
2. **Cross-platform required** — must run on macOS and Ubuntu; no hardcoded paths
3. **Live/Sandbox mode separation** — UI must clearly show current mode; sandbox must never hit production trades
4. **Minimal scope per milestone** — one feature per milestone, each independently usable
5. **External dependencies in adapter layer** — ccxt / Notion / Telegram must not pollute core models

## ExchangeAdapter Abstraction Principle

When implementing exchange connectivity (P4+), follow these rules:

1. **Domain layer must be exchange-agnostic** — no CCXT types, no MT5 structs, no broker-specific concepts in `python/domain/`
2. **Unified internal Order model** — all adapters translate to/from the same `Order`, `Position`, `Balance` domain types
3. **Internal symbol format** — use a canonical format (e.g. `BTC/USDT`) everywhere in domain; each adapter translates to exchange-native format
4. **ExchangeAdapter Protocol** — abstract interface with methods like `place_order()`, `cancel_order()`, `get_balance()`, `get_positions()`. Concrete implementations: `CcxtAdapter` (crypto), future `AlpacaAdapter` (US stocks/ETFs), future `Mt5Adapter` (CFD/forex) if needed
5. **Adapter selection at runtime** — based on asset class or user config, not hardcoded

This keeps the door open for multi-asset support without polluting the core trading logic.

## Roadmap (rewritten — small steps, user-driven)

Replaces the earlier M0–M5 plan. Each phase produces something Jason can use standalone, without depending on later phases.

- **P0 · Scaffold** *(done)* — monorepo, FastAPI, Next.js, SQLite, `AppSettings`, mode switching
- **P1 · Position Sizing Calculator** — form-only tool: inputs (equity, risk %, entry, stop) → outputs (position size, risk $, R:R). No DB write needed. Standalone utility.
- **P2 · Manual Trade Journal** — manually log trades (entry, exit, reason, P&L) into local DB; list + filter historical trades.
- **P3 · Discipline Checklist** — user-defined pre-trade rules (e.g. "stop loss set?", "risk ≤ 2%?"); simple checklist gate before manual actions.
- **P4 · TradingView Webhook + Auto SL/TP** *(requires exchange connection)* — TradingView → signal → OrderIntent → broker; break-even / trailing / ladder TP logic.
- **P5 · Review + Notion Sync** — post-trade review notes, Notion one-way sync of closed trade summaries.

Phase order may be reordered based on Jason's real-world needs — do not treat as locked.

## Task Management (Notion)

Development tasks tracked in Notion (not local todos or GitHub issues).

- **Notion page**: `https://www.notion.so/jingshengcheng/Claude-Code-3434d644686980f986b4e089af97daed`
- **Notion Page ID**: `3434d644-6869-80f9-86b4-e089af97daed`
- **Structure**: Two linked databases — **Projects** (one per phase) and **Tasks** (detailed sub-tasks per Project)
- `NOTION_API_TOKEN` is set in `~/.claude/settings.json` (global env)

**Database IDs:**
- Projects DB: `3434d644-6869-8153-9f73-ff61ed345696`
- Tasks DB: `3434d644-6869-81dc-8c1f-eb78b32b7148`

Workflow: before starting any task, query Tasks DB for the next `Not started` item in the active phase → set to `In progress` → complete work → set to `Done`.

Example API call:
```bash
curl "https://api.notion.com/v1/databases/3434d644-6869-81dc-8c1f-eb78b32b7148/query" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"filter": {"property": "Status", "status": {"equals": "Not started"}}}'
```

## Documentation

Design docs in `docs/`:
- `产品设计（最初版）.md` — **primary source of truth for feature scope** (the latest guiding document)
- `产品设计-v2.md` — earlier broader vision (kept for reference; do not treat as committed scope)
- `技术架构草案.md` — technical architecture reference
- `悟道-V1-开发规格书-Claude-Code版.md` — earlier V1 spec (superseded; kept for reference)
- `ui-design-brief.md` — UI design guidelines for future frontend work

## Prototype Reference

Existing prototype at `~/projects/trading-agent/` — `data_pipeline.py`, `analyzer.py`, `journal.py`, `backtest.py`, `alerts.py` can be adapted (not copy-pasted) when a phase needs them.
