# Mineral AI Tracker — Codebase Brief för Gemini-dialog
_Genererat: 2026-05-26 | Version: Sprint 17 (The Live Wire & God Mode Dashboard)_
_Föregående version: Sprint 13 → se CODEBASE_GEMINI_BRIEF_v4.md_

---

## 0. Snabbkarta — vad Gemini behöver förstå

```
Mineral AI Tracker är ett supply-chain intelligence-system för kritiska mineral.

Kärnan är en supply_chain_nodes/edges-graf (PostgreSQL) som visualiseras
som ett force-directed nätverksmönster (react-force-graph-2d).

Fyra nattliga AI-agenter beräknar:
  1. Quant Watchdog     → dilution_risk_score (utspädningsrisk)
  2. M&A Predictor      → buyout_probability_score (uppköpsrisk, FMP live)
  3. Chokepoint Oracle  → geopolitical_friction_cost på kanter
  4. Sentiment Crawler  → is_early_warning i labor_disputes (RSS + Gemini Flash)

Frontend visar detta i:
  /dashboard          → God Mode Panel (4 widgets) + bento-grid
  /dashboard/nexus    → Interaktiv supply-chain-graf
  /settings           → Notifikationspreferenser + alert-prenumerationer
```

---

## 1. Vad är nytt sedan v4 (Sprints 14–17)

### Sprint 15 — Claude 3.5 Sonnet Integration
- `ml/claude_client.py` (v15.0): Anthropic Claude 3.5 Sonnet som premium-LLM
- Används i SLM Debate Protocol och M&A Predictor
- `get_claude_client()` factory-funktion, keyed på `ANTHROPIC_API_KEY`

### Sprint 16 — The Omniscient Expansion (tre faser)

#### Fas 1 — Databas & Modeller (commit a6ad796)
```sql
-- Alembic 0006 (ny revision)
ALTER TABLE supply_chain_nodes
  ADD COLUMN buyout_probability_score NUMERIC(5,2) NULL;

ALTER TABLE labor_disputes
  ADD COLUMN is_early_warning BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX ix_transit_metrics_index_name ON transit_metrics(index_name);
CREATE UNIQUE INDEX ix_secondary_supply_material_name ON secondary_supply(material_name);
```
Pydantic-modeller i `backend/schemas/omniscient.py`:
`NexusNodeMeta`, `TransitMetricRead`, `SecondarySupplyRead`,
`LaborDisputeRead`, `BuyoutPrediction`, `ChokepointAlert`, `SentimentEarlyWarning`

#### Fas 2 — AI-agenter (commit a6ad796)
| Agent | Fil | Output |
|---|---|---|
| Chokepoint Oracle | `agents/chokepoint_oracle.py` | +0.15 på `geopolitical_friction_cost` för CL/PE/ZA/ID-edges |
| Secondary Supply | `agents/secondary_supply.py` | `scrap_surge`-alert när kopparspridning kollapserar |
| M&A Predictor | `agents/ma_predictor.py` | `buyout_probability_score` (0–100) via Claude + heuristik |
| Sentiment Crawler | `workers/sentiment_crawler.py` | `is_early_warning=TRUE` i `labor_disputes` |

APScheduler: `omniscient_pipeline_job` klockan 07:00 Stockholm.

#### Fas 3 — UI & Alerts (commit 944ec63)
- `/api/nexus/graph`: `buyout_probability_score` + `chokepoint_exposure` i nod-payload; `geopolitical_friction_cost` i kant-payload
- `nexus/page.tsx`: M&A Radar-toggle (amber), guld-noder, pulserande orange kanter
- `settings/page.tsx`: 6 notifikationsrader (tillägg: ma_radar, chokepoint, early_sentiment)

### Sprint 17 — The Live Wire & God Mode Dashboard (commit b713112)

**FMP Live Integration (`ma_predictor.py`)**
```python
# USE_MOCK_DATA=false → kallar fetch_fmp_fundamentals(ticker)
# market_cap, pe_ratio, debt_to_equity, fcf_margin injiceras i Claude-prompt
# Heuristik-boost:
#   micro-cap (<$500M) + hög D/E → +5 på score
#   micro-cap + negativt FCF (utan TOP) → flat 55
SMALL_CAP_THRESHOLD_USD = float(os.getenv("MA_SMALL_CAP_THRESHOLD_USD", "500_000_000"))
```

**Live Sentiment Crawler (`workers/sentiment_crawler.py`)**
```python
# Parallell RSS-hämtning med feedparser (asyncio executor)
# Pre-filtrering mot REGION_KEYWORDS (Chile, Morowali, "mining strike" m.fl.)
# Batch (max 40 rubriker) → Gemini Flash → JSON-rad per event
# SENTIMENT_RSS_FEEDS env var för konfigurerbare feeds
```

**God Mode Dashboard API (`backend/api/dashboard.py`)**
```
GET /api/dashboard/summary → {
  top_ma_targets: top 5 buyout_probability_score DESC,
  top_dilution_risks: top 5 (extracted_data#>>'{_meta,dilution_risk_score}')::float DESC,
  active_disputes: 5 nyaste is_active=TRUE labor_disputes,
  chokepoint_alerts: edges med geopolitical_friction_cost > 0
}
```

**God Mode Frontend (`frontend/app/dashboard/page.tsx`)**
- `GodModePanel`-komponent med 4 widgets ovanför befintliga bento-gridet
- Klick på ticker → `/dashboard/nexus?upstream_ticker=XXX`
- Parallell fetch av signals + summary vid mount

---

## 2. Fullständig teknikstack (post Sprint 17)

### Backend
| Komponent | Teknik | Sprint |
|---|---|---|
| Web-framework | FastAPI 0.110+ | – |
| DB | PostgreSQL 16 + pgvector | – |
| Migrationer | Alembic (7 revisioner 0000→0006) | 16: 0006 |
| Connection pool | psycopg2 ThreadedConnectionPool | 5 |
| Async broker | Celery 5 + Redis | – |
| Scheduling | APScheduler 3.10 | 9, 16 |
| Rate limiting | SlowAPI | 13 |
| AI-modeller | Ollama + Gemini Flash/Pro + Claude 3.5 | 15 |
| FMP-klient | `utils/fmp_client.py` (Redis-cachad, 1h TTL) | 9.5 |
| RSS-inläsning | feedparser>=6.0.10 | 17 |
| Auth | NextAuth JWT HS256 | – |
| Observability | Prometheus + Grafana | 11 |

### Katalogstruktur (post Sprint 17)
```
backend/
  agents/
    chokepoint_oracle.py   ← Sprint 16: friction_cost +0.15 på CL/PE/ZA/ID-kanter
    ma_predictor.py        ← Sprint 16+17: Claude + FMP live
    quant_watchdog.py      ← Sprint 10: dilution_risk_score
    secondary_supply.py    ← Sprint 16: scrap_surge alert
  alembic/versions/
    20250525_0000_baseline.py
    20250525_0001_add_take_or_pay_fields.py
    20250525_0002_add_unique_index_and_expiry_flag.py
    20250525_0003_add_notification_preferences.py
    20250525_0004_add_user_alerts_table.py
    20250525_0005_*.py                            ← (geo/trade policy fields)
    20250525_0006_omniscient_expansion.py         ← Sprint 16
  api/
    admin.py               ← force-refresh @limiter.limit("5/minute")
    dashboard.py           ← Sprint 17 NY: GET /api/dashboard/summary
    nexus.py               ← buyout_probability_score + geopolitical_friction_cost
    settings.py            ← notifications + alert subscriptions CRUD
    trade_policy.py
    [+ 16 andra routrar]
  engines/
    nexus_engine.py        ← canonical RAG/Claude + parse_and_validate_claude_response()
    quant_provider.py      ← BaseQuantProvider / LiveQuantProvider / MockQuantProvider
    rag_engine.py          ← canonical RAG (shim i ml/)
  ml/
    claude_client.py       ← v15.0: Claude 3.5 Sonnet
    gemini_client.py       ← generate_flash() + generate_pro()
    slm_orchestrator.py    ← Multi-SLM Debate Protocol
    rag_engine.py          ← SHIM (re-exporterar engines/rag_engine)
  schemas/
    omniscient.py          ← Sprint 16: BuyoutPrediction, ChokepointAlert m.fl.
  scrapers/
    scheduler.py           ← 3 jobb: 06:00, 03:00, 07:00
  utils/
    fmp_client.py          ← fetch_fmp_fundamentals() (Redis-cachad)
    database.py            ← get_db_connection / release_db_connection
  workers/
    sentiment_crawler.py   ← Sprint 16+17: mock + live RSS + Gemini Flash
    pr_whisperer.py
    black_swan_fetcher.py
  tests/
    test_slm_pipeline.py   ← 31 tester
    test_quant_watchdog.py ← 14 tester
```

---

## 3. Datamodell (post Sprint 17)

### Alembic-revisionskedja
```
0000 (baseline)
  → 0001 (take_or_pay fields på supply_chain_edges)
    → 0002 (unique index + is_expiry_estimated)
      → 0003 (notification_preferences JSONB på alert_configs)
        → 0004 (user_alerts tabell)
          → 0005 (geo/trade policy fields)
            → 0006 (buyout_probability_score + is_early_warning + unika index)
```

### `supply_chain_nodes` (nytt i 0006)
```sql
buyout_probability_score  NUMERIC(5,2)  NULL  -- sätts av ma_predictor.py
```
`extracted_data._meta` innehåller dessutom:
```json
{
  "dilution_risk_score": 62.0,
  "chokepoint_exposure": 0.3
}
```

### `supply_chain_edges` (oförändrad schema sedan Sprint 9/0005)
```sql
geopolitical_friction_cost  NUMERIC(8,2)  -- uppdateras av chokepoint_oracle.py
```

### `labor_disputes` (nytt i 0006)
```sql
is_early_warning  BOOLEAN  NOT NULL  DEFAULT FALSE  -- sätts av sentiment_crawler.py
```

### `transit_metrics` + `secondary_supply` (0006)
Fick UNIQUE INDEX för att möjliggöra ON CONFLICT upsert från Chokepoint Oracle / Secondary Supply.

---

## 4. API-yta (komplett, post Sprint 17)

| Metod | Route | Fil | Sprint |
|---|---|---|---|
| POST | `/api/intelligence/analyze` | intelligence.py | – |
| GET | `/api/intelligence/signals` | intelligence.py | – |
| GET | `/api/nexus/graph` | nexus.py | 10, 16 |
| GET | `/api/dashboard/summary` | dashboard.py | **17 NY** |
| GET | `/api/settings/notifications` | settings.py | 10 |
| PUT | `/api/settings/notifications` | settings.py | 10 |
| GET | `/api/settings/alerts/subscriptions` | settings.py | 13 |
| POST | `/api/settings/alerts/subscriptions` | settings.py | 13 |
| DELETE | `/api/settings/alerts/subscriptions/{ticker}` | settings.py | 13 |
| POST | `/api/admin/nodes/{ticker}/force-refresh` | admin.py | 10, 13 |
| GET | `/api/pulse/top-convictions` | pulse.py | – |
| GET | `/api/health` | health.py | – |

---

## 5. Kritisk analys — kända svagheter

### 🔴 Kritiska (produktionsblockerare)

**A. Admin saknar rollbaserad åtkomstkontroll**
`api/admin.py` skyddas av `get_current_user()` men ALLA inloggade användare kan
anropa admin-endpoints. En vanlig användare kan trigga force-refresh, rensa noder, etc.

**Lösning:** Lägg till `is_admin BOOLEAN DEFAULT FALSE` i users-tabellen.
Kontrollera i `api/deps.py`:
```python
async def get_admin_user(current_user = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

**B. `dilution_risk_score` distribueras inte automatiskt (Skuld B — kvarstår från v4)**
`evaluate_dilution_risk()` i `agents/quant_watchdog.py` anropas aldrig automatiskt.
`/graph` returnerar alltid `dilution_risk_score: null` tills admin force-refreshar.

**Orsak:** Steg 5 saknas i `slm_orchestrator.py`:
```
Steg 1: Manufacturer X-Ray (Claude)
Steg 2: Mining Customer Registry (Claude)
Steg 3: PRWhisperer (Gemini)
Steg 4: Phi-3 Debate
[Steg 5 saknas: Quant Watchdog → skriv dilution_risk_score till _meta]
```
**Lösning (rekommenderas):** Alt B — lägg till anrop i `slm_orchestrator.py` steg 5.

**C. Audio RAG shim är potentiellt trasig (Skuld M — kvarstår från v4)**
`worker/tasks/audio_tasks.py` importerar `chunk_text()` och `save_chunks()` från shimmen
`ml/rag_engine.py`. Dessa metoder finns **inte** i `engines/rag_engine.py` (kanonisk).
Shimmen re-exporterar bara `RAGEngine` och `get_rag_engine`.

**Lösning:** Migrera `audio_tasks.py` till `engines/rag_engine.store_document()` (Alt C från v4).

### 🟡 Viktiga (teknisk skuld)

| # | Problem | Rekommendation |
|---|---|---|
| D | `contract_volume` (legacy VARCHAR) + `contract_volume_numeric` redundanta | Migration 0007: DROP COLUMN |
| G | `is_expiry_estimated` är alltid FALSE (dead code) | Lägg till `~`-prefix i Claude-prompt → parse i `parse_and_validate_claude_response()` |
| H | `cross_reference_nexus()` och `evaluate_geopolitical_friction()` hanterar DB-anslutningar inkonsekvent | Refactor till `release_db_connection()` i finally-block |
| I | Utgångna kontrakt filtreras inte i `/graph` edge-SELECT | `AND (contract_expiry_date IS NULL OR contract_expiry_date >= CURRENT_DATE)` |
| N | `user_alerts.updated_at` uppdateras inte vid upsert | Lägg till `updated_at = NOW()` i ON CONFLICT-satsen |

### 🟢 Lösta (sedan v4, för kontext)
| # | Sprint |
|---|---|
| F: dispatch_risk_alert() saknade user-context | S13 |
| K: Dubbel RAGEngine | S13 |
| L: Rate limit saknades på force-refresh | S13 |
| Q5: Tester testade reimplementation | S13 |

---

## 6. Fork-arkitektur och signal-delning

### Isolering per nod (suveränitetsprincip)

Varje installation är **fullständigt isolerad**:
```
┌────────────────────┐    ┌────────────────────┐
│   Fork A (din)     │    │   Fork B (annan)   │
│  PostgreSQL (A)    │    │  PostgreSQL (B)     │
│  /api/admin/ (A)   │    │  /api/admin/ (B)    │
│  Användare (A)     │    │  Användare (B)      │
└────────────────────┘    └────────────────────┘
       ↑  Ingen access till B       ↑
```

### Hive Mind — enda mekanismen för delning

**Fråga:** "Får vi i huvudkoden ta del av deras sökningar?"

**Svar:** Nej, automatiskt. Ja, om de sätter `HIVE_MIND_URL`.

```
Fork B aktiverar Hive Mind:
  POST /api/hive/contribute → { ticker, signal_type, confidence_score }
       ↓ (om HIVE_MIND_URL är satt)
  POST <din_hub>/api/hive/contribute
       ↓
  Aggregeras i din hub:s hive_signals-tabell
       ↓
  GET /api/pulse/top-convictions → syns i din Global Pulse

Vad delas:    ticker, signal_type, confidence_score (anonymt)
Delas INTE:   användaridentitet, rådata, searches, API-nycklar
```

**`HIVE_MIND_URL`** är den env-variabel som kopplar ihop noder.
Just nu finns den inte implementerad i `hive.py` — det är en arkitekturdesign
som beskrivs men inte fullständigt implementerats (se Q9 nedan).

### Adminåtkomst — vad en fork-operatör FÅR och INTE FÅR

| Kan | Kan inte |
|---|---|
| Admin över sin egna instans (`/admin`) | Admin-access till original-repots instans |
| Läsa/skriva sin egna PostgreSQL | Läsa andras data |
| Konfigurera sina egna AI-nycklar | Ändra andras konfigurationer |
| Bidra anonymt till gemensam Hive Mind (opt-in) | Se vem som bidragit |

---

## 7. Öppna designfrågor för Gemini-dialog

### Q1 — `dilution_risk_score` distribueras inte automatiskt (kvarstår)
Se avsnitt 5-B ovan. Välj Alt B (SLM steg 5) eller Alt C (Celery event-driven).
**Gemini-fråga:** Är Alt B tillräckligt för en ~200-nods-graf med 24h staleness-tolerans?

### Q3 — `is_expiry_estimated` är dead code (kvarstår)
**Gemini-fråga:** Ska vi deprecate kolonnen i 0007, eller implementera `~`-prefix-parsning?

### Q6 — Webhook-kanal är stub (kvarstår)
`_dispatch_to_user()` loggar "not yet implemented". `alert_configs` har `discord_webhook_url`
och `telegram_chat_id` som parallella system.
**Gemini-rekommendation:** Unifiera under `notification_preferences` JSONB med ett
`webhook_url`-fält. Deprecate `discord_webhook_url` + `telegram_chat_id` i migration 0007.

### Q7 — `user_alerts` vs `watchlist` relationsduplicering (kvarstår från v4)
**Gemini-fråga:** Ska `risk_threshold` vara en kolumn på `watchlist`-tabellen?

### Q9 — Hive Mind är ofullständigt implementerat (NYY Sprint 17)
`hive.py` implementerar signal-aggregering internt per instans, men det finns ingen
faktisk cross-node POST till `HIVE_MIND_URL`. Hive Mind fungerar bara om alla
noder delar samma databas (ursprungsinstansen).

**Alternativ:**
- *A*: Implementera `HIVE_MIND_URL` i `hive.py` med outbound POST + HMAC-signering
- *B*: Använd en pubsub-tjänst (Redis Streams, Kafka) som nav
- *C*: Låt det vara "single-node Hive Mind" och dokumentera det ärligt

**Gemini-fråga:** Motiverar community-värdet av att koppla ihop forks implementationskostnaden
av Alt A? Eller är Alt C (ärlig dokumentation) rätt MVP-beslut?

### Q10 — Admin RBAC saknas (NY Sprint 17)
Se avsnitt 5-A. Bör vi implementera `is_admin`-fältet i migration 0007?

### Q11 — `USE_MOCK_DATA` är inkonsekvent (NY Sprint 17)
`USE_MOCK_DATA` styr nu tre separata system:
1. `QuantProvider` (styr `MockQuantProvider` vs `LiveQuantProvider`)
2. `ma_predictor.py` (styr FMP live-anrop)
3. `sentiment_crawler.py` (styr live RSS vs mock signaler)

Men kontrollerna är fristående `os.getenv()`-anrop, inte ett centraliserat config-objekt.
**Gemini-fråga:** Ska vi centralisera till `config.py` med en `settings.USE_MOCK_DATA` boolean,
eller är fristående env-anrop acceptabelt för ett open-source projekt?

---

## 8. Testsvit (post Sprint 17)

```bash
cd backend
pytest tests/ -v --tb=short
# Förväntat: 45 PASSED, 0 FAILED
```

| Testklass | Fil | Tester |
|---|---|---|
| `TestPydanticFirewall` | test_slm_pipeline.py | 8 |
| `TestParseAndValidateClaudeResponse` | test_slm_pipeline.py | 9 |
| `TestHierarchicalUpsert` | test_slm_pipeline.py | 7 |
| `TestEvaluateDilutionRisk` | test_quant_watchdog.py | 8 |
| `TestGetDilutionRiskScore` | test_quant_watchdog.py | 2 |
| `TestGetQuantProvider` | test_quant_watchdog.py | 4 |
| `TestSentimentCrawler` | (saknas, ny skuld) | 0 |
| `TestMAPredictor` | (saknas, ny skuld) | 0 |

**Testgap Sprint 16-17:** Inga tester för `ma_predictor.py` eller `sentiment_crawler.py`.
Rekommendation: Lägg till MockQuantProvider-liknande pattern för FMP-klienten.

---

## 9. Miljövariabler (komplett, post Sprint 17)

```env
# DB
POSTGRES_HOST / PORT / USER / PASSWORD / DB
DB_POOL_MIN=5
DB_POOL_MAX=20

# Auth
NEXTAUTH_SECRET=           # OBLIGATORISK (openssl rand -base64 32)
NEXTAUTH_URL=http://localhost:3000
JWT_ALGORITHM=HS256

# AI
ANTHROPIC_API_KEY=         # Claude 3.5 Sonnet (M&A Predictor)
GEMINI_API_KEY=            # Gemini Flash/Pro + Sentiment Crawler
OLLAMA_URL=http://localhost:11434

# Externa API:er
FMP_API_KEY=               # Financial Modeling Prep (obligatorisk för live)

# Sprint 16-17
USE_MOCK_DATA=false        # true → mock data, false → live FMP + RSS
MA_SMALL_CAP_THRESHOLD_USD=500000000
SENTIMENT_RSS_FEEDS=       # (valfri override)
HIVE_MIND_URL=             # (valfri, cross-node signal hub)

# QuantProvider
TAKE_OR_PAY_COVERAGE_THRESHOLD=0.50

# Infrastruktur
REDIS_URL=redis://localhost:6379/0
USE_CELERY=false
METRICS_ENABLED=true

# RAG
RAG_EMBEDDING_MODEL=nomic-embed-text
RAG_TOP_K=3
RAG_SIMILARITY_THRESHOLD=0.7
```

---

## 10. Frontend-sidor (app/, post Sprint 17)

| Route | Beskrivning | Sprint |
|---|---|---|
| `/dashboard` | God Mode Panel (4 widgets) + bento-grid | 17 |
| `/dashboard/nexus` | Supply chain-graf — M&A Radar, geo-mode, pulsande kanter | 16 |
| `/settings` | Systeminst. + 6×3 notifikationstogglar + alert-prenumerationer | 13, 16 |
| `/dashboard/black-swan` | Black Swan-monitor | – |
| `/dashboard/infrastructure-apex` | Infrastruktur-monitor | – |

**Frontend-gap:**
- `/settings` visar inte `user_alerts` CRUD i UI (backend finns, UI saknas)
- Nexus-noder är inte klickbara för "🔔 Prenumerera"-dialog

---

## 11. Nästa naturliga steg (Sprint 18)

### Kritiska
1. **Skuld B: Koppla Quant Watchdog i SLM-kedjan** — steg 5 i `slm_orchestrator.py`
2. **Skuld A+RBAC: Admin-rollskydd** — `is_admin` boolean i users + `get_admin_user()` dep
3. **Skuld M: Audio RAG shim** — migrera `audio_tasks.py` till `engines/rag_engine.store_document()`

### Viktiga
4. **Tester för Sprint 16-17 agents** — MockFMPProvider pattern för `ma_predictor.py`
5. **Alert Subscription UI** — `🔔 Notify me`-knapp på Nexus-noder → modal → POST subscriptions
6. **Filtrera utgångna kontrakt** — `AND (contract_expiry_date IS NULL OR contract_expiry_date >= CURRENT_DATE)` i `/graph`

### Arkitektur
7. **Migration 0007** — DROP `contract_volume` (Skuld D) + unifiera webhook under `notification_preferences` (Q6)
8. **Hive Mind cross-node** (Q9) — besluta Alt A/C baserat på community-intresse
9. **Centralisera `USE_MOCK_DATA`** till `config.py` (Q11)
