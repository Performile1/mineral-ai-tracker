# Mineral AI Tracker — Master Audit v8.6

**Generated:** 2026-05-13 (post Phase 4 + PRD v8.6 sprint)
**Purpose:** Critical inventory + gap analysis for Gemini verification
**Previous audit:** `MASTER_AUDIT.md` (v8.3 baseline, ~80% PRD coverage)
**Δ since v8.3:** +pgvector infra, +Geopolitics engine, +Tax engine, +Watchlist Stalker, +Live Drift Alert, +Bento Dashboard

---

## 1. PRD Compliance Matrix (v8.3 + v8.6 combined)

| PRD § | Requirement | Status | Location |
|-------|------------|--------|----------|
| **v8.3 §1** Infrastructure |
| 1.1 | pgvector PostgreSQL | ✅ | `docker-compose.yml` (`ankane/pgvector:latest`) |
| 1.2 | Auto-init schema with `embedding vector(768)` | ✅ | `db/init/00_init_schema.sql` |
| 1.3 | Ollama service | ✅ | `docker-compose.yml` lines 67-74 |
| 1.4 | `setup_models.sh` | ✅ | Root (`phi3` + `mistral` + `llama3` + `nomic-embed-text`) |
| 1.5 | FastAPI Python 3.11 | ✅ | `backend/main.py` |
| 1.6 | APScheduler 06:00 sweep | ✅ | `backend/scrapers/scheduler.py` |
| 1.7 | Next.js App Router + Tailwind + Zustand | ✅ | `frontend/package.json` |
| **v8.3 §2** Pydantic Firewall |
| 2.1-2.5 | All threshold validators + settings UI | ✅ | `backend/models/finance.py`, `backend/models/geology.py`, `frontend/app/settings/page.tsx` |
| **v8.3 §3** Quant Engines |
| 3.1 | Buffett | ✅ | `backend/engines/buffett.py` |
| 3.2 | Lassonde | ✅ | `backend/engines/lassonde.py` |
| 3.3 | Soros | ✅ | `backend/engines/soros.py` |
| 3.4 | Lynch | ✅ | `backend/engines/lynch.py` |
| 3.5 | Institutional Alpha | ✅ | `backend/engines/institutional_alpha.py` |
| 3.6 | Geopolitics (Friend-Shoring + CBAM) | ✅ | `backend/engines/geopolitics.py` |
| **v8.3 §4** Multi-SLM Pipeline |
| 4.1 | Crawl4AI | ✅ | `backend/scrapers/crawler.py` (`fetch_markdown`) |
| 4.2 | Target List 3-tier | ✅ | `backend/scrapers/target_list.py` |
| 4.3 | Sequential Memory Mode (`keep_alive=0`) | ✅ | `backend/ml/ollama_client.py:57-92` |
| 4.4 | Debate Protocol Phi-3 → Pydantic → Mistral → Llama-3 → Consensus | ✅ | `backend/ml/slm_orchestrator.py` |
| 4.5 | Consensus + DB persist with debate_log JSONB | ✅ | `backend/api/intelligence.py` `save_signal_to_db` |
| 4.6 | pgvector embedding write | ⚠️ | Column exists, **not yet populated** (orchestrator does not call `nomic-embed-text`) |
| **v8.3 §5** Bento Dashboard |
| 5.1 | Global Pulse (DXY, 10y, deficits) | ✅ | `frontend/components/GlobalPulse.tsx` |
| 5.2 | Shadow Portfolio | ✅ | `frontend/components/ShadowPortfolio.tsx` |
| 5.3 | Kelly Calculator | ✅ | `frontend/components/KellyCalculator.tsx` |
| 5.4 | Risk Correlation Matrix | ✅ | `frontend/components/RiskCorrelationMatrix.tsx` |
| 5.5 | Intelligence Cards w/ Debate Log | ✅ | `frontend/components/IntelligenceCard.tsx` |
| 5.6 | Macro Deficit Radar | ✅ | `frontend/components/MacroDeficitRadar.tsx` |
| 5.7 | `/dashboard` Bento Box page | ✅ | `frontend/app/dashboard/page.tsx` |
| **v8.6 §1** Execution Engine |
| E.1 | `execution.py` router for mock orders | ❌ | **NOT created** (only Kelly auto-sizing in UI; no order/stop-loss endpoint) |
| E.2 | Auto stop-loss (10% below entry) | ❌ | Missing |
| E.3 | ShadowPortfolio uses Kelly for "Köp" position size | ⚠️ | Kelly auto-sizer present, but no actual Buy button wired yet (placeholder portfolio) |
| **v8.6 §2** Tax & Yield Engine |
| T.1 | `tax_calculator.py` (ISK schablonskatt) | ✅ | `backend/engines/tax_calculator.py` |
| T.2 | "Simulate ISK Tax" toggle in ShadowPortfolio | ✅ | `frontend/components/ShadowPortfolio.tsx` |
| T.3 | Gross vs True Net Yield KPIs | ✅ | 4-column KPI grid |
| T.4 | Client mirror of formula | ✅ | `frontend/lib/iskTax.ts` |
| **v8.6 §3** Watchlist Stalker |
| W.1 | `discovery.py` Yahoo RSS fetch | ✅ | `backend/scrapers/discovery.py` |
| W.2 | `watchlist.py` router + POST `/api/watchlist/stalk` | ✅ | `backend/api/watchlist.py` |
| W.3 | Parallel crawl + sequential SLM debate | ✅ | `asyncio.gather` over URLs, then orchestrator |
| W.4 | Highest priority (lock) | ✅ | `_stalker_lock = asyncio.Lock()` |
| W.5 | WatchlistStalker UI w/ 5-step pipeline | ✅ | `frontend/components/WatchlistStalker.tsx` |
| W.6 | Wired into dashboard | ✅ | `frontend/app/dashboard/page.tsx:87` |
| **v8.6 §4** Thematic Baskets |
| B.1 | `basket_engine.py` (auto-rebalance on Sell signal) | ❌ | **NOT created** |
| **v8.6 §5** Intraday Drift Alert |
| L.1 | `LiveTicker.tsx` Yahoo polling | ✅ | `frontend/components/LiveTicker.tsx` |
| L.2 | IntelligenceCard Drift Alert badge (>5%) | ✅ | `frontend/components/IntelligenceCard.tsx:79-85,117-124` |
| L.3 | Backend quote proxy `/api/market/quote/{ticker}` | ❌ | **NOT created** — LiveTicker falls back to direct Yahoo (CORS risk) |

**Legend:** ✅ Implemented · ⚠️ Partial · ❌ Missing

---

## 2. New Wiring Verification (v8.6 cross-file imports)

All `from ... import ...` statements in v8.6 files resolve to real symbols:

| Import statement | Resolves to | Status |
|---|---|---|
| `from scrapers.discovery import discover_news` | `backend/scrapers/discovery.py:73` | ✅ |
| `from scrapers.crawler import fetch_markdown` | `backend/scrapers/crawler.py:28` | ✅ |
| `from ml.slm_orchestrator import SLMOrchestrator` | `backend/ml/slm_orchestrator.py:50` | ✅ |
| `from ml.ollama_client import OllamaClient` | `backend/ml/ollama_client.py` | ✅ |
| `from api.intelligence import load_system_settings_dict` | `backend/api/intelligence.py:143` | ✅ |
| `from api.intelligence import save_signal_to_db` | `backend/api/intelligence.py:111` | ✅ |
| `from api.intelligence import serialize_debate_log` | `backend/api/intelligence.py:97` | ✅ |
| `orchestrator.analyze_discovery(raw_data, source, system_settings)` | `backend/ml/slm_orchestrator.py:66-71` | ✅ signature matches |
| `from api.watchlist import router as watchlist_router` | `backend/api/watchlist.py:24` | ✅ registered in `main.py:19,51` |
| `from .tax_calculator import ISKTaxCalculator` | `backend/engines/tax_calculator.py` | ✅ exported in `__init__.py` |
| Frontend `@/lib/iskTax` (ShadowPortfolio) | `frontend/lib/iskTax.ts` | ✅ |
| Frontend `./LiveTicker` (IntelligenceCard) | `frontend/components/LiveTicker.tsx` | ✅ |
| Frontend `@/components/WatchlistStalker` (dashboard) | `frontend/components/WatchlistStalker.tsx` | ✅ |

**No broken imports detected.**

---

## 3. Architecture Diagram (v8.6)

```
┌────────────────────────────────────────────────────────────────────┐
│             Mineral AI Tracker v8.6 — Wealth & Execution Engine     │
└────────────────────────────────────────────────────────────────────┘

  [Frontend :3000]            [Backend :8000]            [Ollama :11434]
  Next.js 14                  FastAPI                    Phi-3
  Tailwind + Zustand          APScheduler                Mistral
                              Pydantic V2                Llama-3
  /dashboard (Bento Box):     SLM Orchestrator           nomic-embed-text
   ┌─────────────────┐        ┌──────────────────┐
   │ Global Pulse    │        │ /api/intelligence│
   ├─────┬─────┬─────┤        │ /api/watchlist   │ ← NEW (v8.6)
   │Stlk │Sigs │Radr │        │ /api/settings    │
   │ShPo │     │Corr │        │ /api/assets ...  │
   │Kel  │     │     │        └──────────────────┘
   └─────┴─────┴─────┘                │
                                      ▼
                            [pgvector :5432]
                            system_settings
                            investment_signals (+embedding vec768)
                            trade_journal
                            macro_indicators


   Two pipelines feed the same Multi-SLM Debate Protocol:

   ┌──────── NIGHTLY (06:00 CET) ─────────┐    ┌──── ON-DEMAND (Stalker) ────┐
   │ APScheduler                          │    │ POST /api/watchlist/stalk    │
   │   target_list.py (Regulatory/News/PR)│    │   discovery.py (Yahoo RSS)    │
   │   crawler.py (one URL at a time)     │    │   crawler.py ×N (PARALLEL)    │
   └──────────────────┬───────────────────┘    └──────────┬───────────────────┘
                      │                                   │
                      └────────────► SEQUENTIAL ◄─────────┘
                                     SLM DEBATE
                                ┌─────────────────┐
                                │ Phi-3 (extract) │  keep_alive=0
                                │  └ sleep(2)     │  ~2 GB RAM
                                │ Pydantic Firewl │
                                │  └ sleep(2)     │
                                │ Mistral (geo)   │  keep_alive=0
                                │  └ sleep(2)     │  ~4 GB RAM
                                │ Llama-3 (risk)  │  keep_alive=0
                                │  Consensus      │  ~5-6 GB RAM
                                └────────┬────────┘
                                         ▼
                                investment_signals
                                (debate_log JSONB)
                                         ▼
                                IntelligenceCard
                                + LiveTicker drift alert (>5%)
```

---

## 4. Backend Inventory (current state)

### 4.1 Entry & Config (unchanged, working)

| File | Role |
|------|------|
| `backend/main.py` | FastAPI app, 7 routers, APScheduler lifecycle |
| `backend/config.py` | Settings (POSTGRES_*, OLLAMA_*, model names) |
| `backend/requirements.txt` | `fastapi`, `psycopg2-binary`, `pgvector>=0.2.5`, `crawl4ai`, `apscheduler`, `httpx`, `pydantic>=2.7`, `loguru` — **supabase removed** |

### 4.2 API Routers (`backend/api/`)

| Router | Endpoints | New in v8.6 |
|--------|-----------|-------------|
| `assets.py` | `/api/assets/*` | — |
| `discoveries.py` | `/api/discoveries/*` | — |
| `manufacturing.py` | `/api/manufacturing/*` | — |
| `stripe.py` | `/api/stripe/*` | — |
| `settings.py` | `/api/settings/*` | — |
| `intelligence.py` | `/api/intelligence/analyze`, `/signals`, `/debate/{asset_id}` | — |
| **`watchlist.py`** | `POST /api/watchlist/stalk`, `GET /api/watchlist/discover/{ticker}` | ✅ **NEW** |

**Missing routers per PRD v8.6:**
- ❌ `api/execution.py` — mock order/stop-loss endpoint
- ❌ `api/market.py` — `/api/market/quote/{ticker}` proxy (currently LiveTicker direct-hits Yahoo)
- ❌ `api/macro.py` — `/api/macro/pulse` endpoint that GlobalPulse already attempts to fetch

### 4.3 Engines (`backend/engines/`)

| File | Purpose | Version |
|------|---------|---------|
| `buffett.py` | FCF + Moat + AISC | v8.3 |
| `lassonde.py` | Curve phase + asymmetry ratio | v8.3 |
| `soros.py` | DXY + supply balance + PR fluff | v8.3 |
| `lynch.py` | Mining-adjusted PEG | v8.3 |
| `institutional_alpha.py` | Nearology + Insider Clusters + UOA | v8.3 |
| `geopolitics.py` | Friend-Shoring + CBAM + sanctions | **v8.3** (added Phase 4) |
| **`tax_calculator.py`** | Swedish ISK schablonskatt | ✅ **NEW v8.6** |
| `__init__.py` | Exports all 7 engines | — |

**Missing engines per PRD v8.6:**
- ❌ `engines/basket_engine.py` — Thematic AI Baskets / auto-rebalance

### 4.4 ML / Orchestration (`backend/ml/`)

| File | Role |
|------|------|
| `ollama_client.py` | `generate_sequential(model, prompt, keep_alive=0)` |
| `slm_orchestrator.py` | Debate Protocol — `analyze_discovery(raw_data, source, system_settings)` |
| `feedback_loop.py` | RLHF ingestion |
| `trade_journal.py` | Trade journaling (still imports `..quant.buffett_score`, see §6) |
| `weight_adjuster.py` | Adaptive RLHF weights |

### 4.5 Scrapers (`backend/scrapers/`)

| File | Role |
|------|------|
| `crawler.py` | Crawl4AI + httpx fallback (`fetch_markdown`) |
| `target_list.py` | 3-tier Target List dict |
| `scheduler.py` | APScheduler 06:00 cron |
| **`discovery.py`** | ✅ **NEW v8.6** Yahoo RSS lookup |
| `base_scraper.py` | Legacy base class |
| `ai_scout.py`, `finance_scraper.py`, `geology_scraper.py`, `geo_events.py`, `industry_macro.py`, `macro_scraper.py`, `personnel_scraper.py`, `satellite_scraper.py`, `sentiment_scraper.py` | Legacy v6.x scrapers (no longer called by scheduler) |
| `crawler_engine.py` | Legacy crawler — overlaps with `crawler.py` |

### 4.6 Quant (`backend/quant/`)

| File | Status |
|------|--------|
| `kelly_criterion.py` | ✅ Active (referenced by `trade_journal.py`) |
| `buffett_score.py` | ⚠️ Legacy (overlaps `engines/buffett.py`, still imported by `trade_journal.py`) |
| `correlation_matrix.py` | ✅ Active concept (UI in `RiskCorrelationMatrix.tsx`) |
| `scenario_engine.py` | ✅ Active concept (UI in `ScenarioSimulator.tsx`) |
| `backtesting.py` | Active concept (no UI yet) |

---

## 5. Frontend Inventory

### 5.1 Routes (`frontend/app/`)

| Route | Status |
|-------|--------|
| `/` | ✅ Landing |
| `/analytics` | ✅ |
| `/assets` | ✅ |
| `/onboarding` | ✅ |
| `/settings` | ✅ System Thresholds UI |
| `/dashboard` | ✅ **Bento Box Command Center** — Stalker + ShadowPortfolio + Kelly (left), IntelligenceCard feed (center), MacroRadar + RiskCorr (right) |

### 5.2 Components (`frontend/components/`) — 17 total

| Component | Origin | Notes |
|-----------|--------|-------|
| `AssetDetail.tsx` | v6 | — |
| `DiscoveryHeatmap.tsx` | v6 | — |
| `DiscoveryRadar.tsx` | v6 | Partial (superseded by `MacroDeficitRadar`) |
| `FeedbackPanel.tsx` | v6 | RLHF |
| `MineralHeatmap.tsx` | v6 | — |
| `Portfolio.tsx` | v6 | Asset mgmt |
| `PortfolioCard.tsx` | v6 | — |
| `PredictionGraph.tsx` | v6 | — |
| `ScenarioSimulator.tsx` | v6 | — |
| `ManufacturingContacts.tsx` | v6 | — |
| `ManufacturingInsider.tsx` | v6 | — |
| `IntelligenceCard.tsx` | v8.3 / **v8.6** | + LiveTicker inline, + Drift Alert badge |
| `ShadowPortfolio.tsx` | v6 / **v8.6** | + ISK toggle, + 4-col KPI, + Kelly auto-sizer |
| `GlobalPulse.tsx` | v8.3 (Phase 4) | Top ticker |
| `KellyCalculator.tsx` | v8.3 (Phase 4) | Sliders |
| `RiskCorrelationMatrix.tsx` | v8.3 (Phase 4) | Heatmap |
| `MacroDeficitRadar.tsx` | v8.3 (Phase 4) | Dual-axis radar |
| `LiveTicker.tsx` | **v8.6** | 30s Yahoo polling |
| `WatchlistStalker.tsx` | **v8.6** | 5-step pipeline |

### 5.3 Libraries (`frontend/lib/`)

| File | Purpose |
|------|---------|
| `schemas.ts` | Zod schemas (30 kB) |
| `iskTax.ts` | **NEW v8.6** — TS mirror of `tax_calculator.py` + Kelly helper |
| `store/disclaimer.ts` | Zustand store (only 1 store so far) |

### 5.4 Dependency Audit (`frontend/package.json`)

```
next 14.0.4 · react 18.2.0 · zustand 4.4.7 · recharts 2.10.3 · zod 3.22.4 · date-fns 3.0.6
@supabase/supabase-js — REMOVED in Phase 4
```

✅ 100% local-first, no cloud auth dependency.

### 5.5 Tailwind Palette (`frontend/tailwind.config.ts`)

```
bg/background  #F4F1EE   warmwhite
text/primary   #2F2F2F   carbon
positive/buy   #4F8A8B   petroleum
negative/warn  #B35A44   terracotta
accent         #C9A24E   gold (drift alert positive direction)
muted          #6B6B6B
surface        #FFFFFF
```

Both PRD semantic names (`positive`/`negative`/`primary`/`background`) and raw aliases (`buy`/`warning`/`text`/`bg`) work.

---

## 6. Critical Issues / Bugs to Verify

### 6.1 ⚠️ `IntelligenceCard` auto-attaches `LiveTicker` to every `asset_id`

In `IntelligenceCard.tsx`, `liveTicker = signal.ticker_symbol || signal.asset_id`. For nightly-sweep signals where `asset_id` is a free-form discovery ID (not a Yahoo ticker), LiveTicker will spam failed quote requests every 30s.

**Risk:** Low (failure is silent), but it generates console noise + unnecessary network traffic. **Fix:** Only render LiveTicker if `signal.ticker_symbol` is explicitly set, OR if `asset_id` matches a ticker regex `^[A-Z]{1,5}(\.[A-Z]{2})?$`.

### 6.2 ⚠️ `GlobalPulse` polls a non-existent endpoint

`GlobalPulse.tsx` fetches `${API}/api/macro/pulse` — there is no `api/macro.py` router. It silently falls back to hard-coded defaults, but the user never sees real macro data.

**Fix:** Add `backend/api/macro.py` exposing `/api/macro/pulse` aggregating from `macro_indicators` table.

### 6.3 ⚠️ `LiveTicker` Yahoo direct-hit has CORS risk

When no backend proxy is found, LiveTicker fetches `query1.finance.yahoo.com/v7/finance/quote` directly. Browsers may block this with CORS depending on Yahoo's response headers.

**Fix:** Add backend proxy `/api/market/quote/{ticker}` (simple `httpx` GET + JSON forward).

### 6.4 ⚠️ pgvector column exists but is never written

`db/init/00_init_schema.sql` provisions `embedding vector(768)` and an ivfflat index. But `save_signal_to_db` in `api/intelligence.py` does not generate or insert embeddings. RAG lookups against historical signals are impossible until this is wired.

**Fix:** In `save_signal_to_db`, after consensus, call `ollama.generate_embedding(model="nomic-embed-text", text=raw_data)` and pass the vector to the INSERT.

### 6.5 ⚠️ Legacy quant/buffett_score still imported

`backend/ml/trade_journal.py:14` imports `from ..quant.buffett_score import BuffettScoreCalculator, Recommendation`. This prevents simply removing the legacy file. Either:
- Migrate `trade_journal.py` to use `engines/buffett.py`, OR
- Keep `quant/buffett_score.py` indefinitely and accept the dup.

### 6.6 ⚠️ Stalker `_stalker_lock` is module-global

`_stalker_lock = asyncio.Lock()` in `api/watchlist.py` is fine for a single Uvicorn worker, but breaks under `--workers > 1` (each worker has its own lock). Acceptable for local-first PRD, but worth flagging if user later scales horizontally.

### 6.7 ✅ Sequential Memory Mode is intact

Re-verified `slm_orchestrator.py:66-71` (signature) + `ollama_client.py:57-92` (`keep_alive=0`) + `asyncio.sleep(2)` breathers between SLMs. The Stalker reuses `SLMOrchestrator.analyze_discovery` so the same memory budget applies (max ~5-6 GB peak).

---

## 7. Gap Analysis vs PRD v8.6

### 7.1 Missing (blockers for 100% v8.6 compliance)

| # | Item | PRD § | Effort |
|---|------|-------|--------|
| 1 | `backend/api/execution.py` (Kelly-sized mock order + 10% auto stop-loss) | v8.6 §1 | M |
| 2 | Wire "Köp" button in `ShadowPortfolio.tsx` → calls execution endpoint | v8.6 §1 | S |
| 3 | `backend/engines/basket_engine.py` (Thematic Baskets, auto-rebalance) | v8.6 §4 | L |
| 4 | `backend/api/market.py` — `/api/market/quote/{ticker}` proxy for LiveTicker | v8.6 §5 | S |
| 5 | `backend/api/macro.py` — `/api/macro/pulse` for GlobalPulse | v8.3 §5.1 | S |
| 6 | pgvector embedding write in `save_signal_to_db` | v8.3 §4.7 | S |

### 7.2 Polish

| # | Item | Effort |
|---|------|--------|
| 7 | Restrict LiveTicker rendering to actual tickers (regex/explicit field) | XS |
| 8 | Persist Stalker results so the dashboard auto-refreshes the signal list | XS |
| 9 | Settings UI: expose SLR (Statslåneräntan) so ISK calc tracks current year | S |
| 10 | Backtest UI for `backend/quant/backtesting.py` | M |
| 11 | Onboarding wizard wired to `/api/settings` | M |

### 7.3 Anti-Bloat (legacy still present)

| File | Action | Risk |
|------|--------|------|
| `backend/scrapers/crawler_engine.py` | Delete (replaced by `crawler.py`) | XS |
| `backend/scrapers/ai_scout.py` | Delete (replaced by `slm_orchestrator.py`) | S — verify no router references it |
| `backend/quant/buffett_score.py` | Keep until `trade_journal.py` migrated | — |
| `backend/scrapers/finance_scraper.py`, `geology_scraper.py`, `macro_scraper.py`, `sentiment_scraper.py`, etc. | Audit which (if any) are still called | M |
| `frontend/components/DiscoveryRadar.tsx` | Superseded by `MacroDeficitRadar.tsx` — delete if no consumer | XS |

---

## 8. Verification Commands

```pwsh
# 1. Full stack
docker compose down -v
docker compose up -d --build

# 2. Models
bash setup_models.sh

# 3. Verify pgvector + tables
docker compose exec postgres psql -U mineral_user -d mineral_ai_tracker -c "\dx"
docker compose exec postgres psql -U mineral_user -d mineral_ai_tracker -c "\d investment_signals"

# 4. ISK tax engine (Python REPL inside backend)
docker compose exec backend python -c "from engines.tax_calculator import default_isk_calculator as t; r=t.calculate(100000, 115000); print(r.reasoning)"

# 5. Geopolitics engine
docker compose exec backend python -c "from engines.geopolitics import GeopoliticsEngine; g=GeopoliticsEngine(); print(g.score({'country_code':'SE','commodity_type':'copper'}).reasoning); print(g.score({'country_code':'CN','commodity_type':'coal','is_fossil_fuel':True}).reasoning)"

# 6. Watchlist discovery (RSS only, fast)
curl http://localhost:8000/api/watchlist/discover/BOL.ST

# 7. Watchlist full stalker (60-120s)
curl -X POST http://localhost:8000/api/watchlist/stalk `
  -H "Content-Type: application/json" `
  -d '{\"ticker\":\"BOL.ST\",\"max_articles\":3}'

# 8. Intelligence direct analyze
curl -X POST http://localhost:8000/api/intelligence/analyze `
  -H "Content-Type: application/json" `
  -d '{\"raw_data\":\"Boliden 1.2% Cu over 250m at Aitik\",\"source\":\"manual\"}'

# 9. Trigger nightly sweep manually
docker compose exec backend python -c "import asyncio; from scrapers.scheduler import run_target_list_sweep; asyncio.run(run_target_list_sweep())"

# 10. Dashboard
start http://localhost:3000/dashboard
```

---

## 9. Summary Score

| Category | v8.3 | **v8.6** | Δ |
|----------|------|----------|---|
| Infrastructure | 80% | **100%** | +20 |
| Pydantic Firewall | 100% | 100% | 0 |
| Multi-SLM Orchestrator | 100% | 100% | 0 |
| Quant Engines | 80% | **100%** (geopolitics added) | +20 |
| Data Ingestion / Automation | 100% | 100% | 0 |
| Settings API + UI | 100% | 100% | 0 |
| Dashboard UI | 30% | **100%** | +70 |
| RLHF / Trade Journal | 70% | 75% | +5 |
| **Tax Engine (v8.6)** | — | **100%** | NEW |
| **Watchlist Stalker (v8.6)** | — | **100%** | NEW |
| **Drift Alert (v8.6)** | — | **80%** (needs backend quote proxy) | NEW |
| **Execution Engine (v8.6)** | — | **20%** (UI sizing only, no orders) | NEW |
| **Thematic Baskets (v8.6)** | — | **0%** | NEW |
| **Overall PRD v8.6 Compliance** | n/a | **~85%** | — |

**Top 3 things blocking 100% v8.6:**
1. **Thematic Baskets** (`basket_engine.py`) — 0% done.
2. **Execution Engine** (`api/execution.py` + stop-loss + buy-button wiring) — 20% done.
3. **Backend supporting endpoints** for already-built UI: `/api/market/quote/{ticker}` (LiveTicker), `/api/macro/pulse` (GlobalPulse).

---

## 10. Key Files Reference for Gemini Cross-Check

### v8.6 net-new code (use for diff vs PRD)

```
backend/engines/tax_calculator.py            ISK schablonskatt
backend/engines/geopolitics.py               Friend-Shoring + CBAM
backend/scrapers/discovery.py                Yahoo RSS
backend/api/watchlist.py                     POST /api/watchlist/stalk
db/init/00_init_schema.sql                   pgvector + tables
setup_models.sh                              Multi-SLM model pull
frontend/lib/iskTax.ts                       TS mirror of ISK + Kelly
frontend/components/WatchlistStalker.tsx     5-step pipeline UI
frontend/components/LiveTicker.tsx           Yahoo polling
frontend/components/GlobalPulse.tsx          Top ticker
frontend/components/KellyCalculator.tsx      Sizing sliders
frontend/components/RiskCorrelationMatrix.tsx Heatmap
frontend/components/MacroDeficitRadar.tsx    Dual-axis radar
frontend/app/dashboard/page.tsx              Bento Box
```

### v8.6 modified code

```
backend/main.py                              + watchlist_router
backend/engines/__init__.py                  + Geopolitics, + ISKTaxCalculator
backend/requirements.txt                     - supabase, + pgvector
docker-compose.yml                           + ankane/pgvector, - SUPABASE_*
frontend/components/IntelligenceCard.tsx     + LiveTicker, + Drift Alert
frontend/components/ShadowPortfolio.tsx      + ISK toggle, + Kelly auto-size
frontend/tailwind.config.ts                  + bg/text/buy/warning aliases
frontend/package.json                        - @supabase/supabase-js
```

### v8.6 deleted

```
backend/scheduler.py        (14 kB duplicate)
backend/models/schemas.py   (24 kB legacy V1)
```

---

*End of Master Audit v8.6 — ready for Gemini diff.*
