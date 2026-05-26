# Mineral AI Tracker — Sovereign Supply-Chain Intelligence

**Sprint 17 · Live Wire & God Mode Dashboard**

---

## Vad är det här?

Mineral AI Tracker är ett **supply-chain intelligence-system för kritiska mineral** (koppar, nickel, litium, uran m.fl.). Det kombinerar ett nätverks-visualiseringsverktyg (Nexus-graf), AI-agenter för M&A-prediktering och geopolitisk riskbedömning, samt ett aggregerat "God Mode"-kommandocenter.

Varje installation är **suverän** — all data stannar i din egna PostgreSQL. Du kan valfritt bidra med anonyma konsensussignaler till en gemensam Hive Mind.

### Kärnprinciper

- **Data Sovereignty**: Din data lämnar aldrig din infrastruktur.
- **Model Agnosticism**: Lokala SLM-swarms (Ollama) eller molnmodeller (Gemini, Claude).
- **Hive Mind Consensus**: Valfri anonym signal-delning till ett distribuerat konsensus-lager.
- **Transaction Safety**: Atomära kredit-transaktioner med automatisk återbetalning vid fel.

---

## Arkitektur

### Backend

| Komponent | Teknik |
|---|---|
| Web-framework | FastAPI (Python 3.10+) |
| Databas | PostgreSQL 16 + pgvector |
| Schemamigrationer | Alembic (7 revisioner, 0000→0006) |
| Connection pool | psycopg2 ThreadedConnectionPool |
| Schemaläggare | APScheduler 3.10 (3 nattliga jobb) |
| Async broker | Celery 5 + Redis (valfritt) |
| AI-modeller | Ollama (Phi-3/Llama-3) + Gemini Flash/Pro + Claude 3.5 Sonnet |
| Auth | NextAuth JWT (HS256) |
| Rate limiting | SlowAPI |
| Observability | Prometheus + Grafana |

### Frontend

| Komponent | Teknik |
|---|---|
| Framework | Next.js 14 App Router + TypeScript |
| Styling | Tailwind CSS |
| Graf-visualisering | react-force-graph-2d (canvas, animerad) |
| Auth | NextAuth.js |
| Charts | Recharts |

### AI-modeller

| Modell | Kostnad | Användning |
|---|---|---|
| Local Swarm (Ollama) | 1 kredit | Phi-3 → Mistral → Llama-3 debate |
| Gemini Flash | 2 krediter | Sentimentklassificering, snabbanalys |
| Gemini Pro | 5 krediter | Djupanalys, 1M-token kontext |
| Claude 3.5 Sonnet | 5 krediter | M&A-prediktering, strukturerad extraktion |

### Schemalagda jobb

| Tid | Jobb | Vad det gör |
|---|---|---|
| 06:00 | `target_list_sweep` | Scraper + SLM-debate per bevakad nod |
| 03:00 | `contract_decay_job` | Markerar utgångna kontrakt |
| 07:00 | `omniscient_pipeline` | Chokepoint Oracle → Secondary Supply → M&A Predictor → Sentiment Crawler |

---

## Funktioner (Sprint 17)

- **Nexus-graf** — supply-chain-nätverk med M&A Radar-läge, geo-friktionsvisning, kantdisputemarkering
- **God Mode Dashboard** — 4 aggregerade kort: Top M&A Targets, Critical Dilution Risks, Active Disputes, Chokepoint Alerts
- **M&A Predictor** — Claude + FMP live-fundamentals beräknar `buyout_probability_score` per PRODUCER-nod
- **Chokepoint Oracle** — spårar Panama/Suez-korridorer och påverkar `geopolitical_friction_cost` på edges
- **Live Sentiment Crawler** — parallell RSS-hämtning + Gemini Flash batch-klassificering av arbetsmarknadskonflikter
- **Alert Subscriptions** — prenumerera på risktrösklar per ticker, routing via email/in-app/webhook
- **Multi-SLM Debate** — Phi-3 → Mistral → Llama-3 → Quant Watchdog för daglig nod-sweep

---

## Kom igång

### Förutsättningar

- Docker Desktop 4.0+
- `FMP_API_KEY` (Financial Modeling Prep — obligatorisk för live-data)
- `GEMINI_API_KEY` (valfri, för Gemini-modeller och sentiment-crawlern)
- `ANTHROPIC_API_KEY` (valfri, för Claude-baserad M&A-prediktering)

### Installation

```bash
# 1. Klona repot
git clone https://github.com/Performile1/mineral-ai-tracker.git
cd mineral-ai-tracker

# 2. Kopiera miljömall
cp .env.example .env
# Redigera .env — fyll minst i FMP_API_KEY och NEXTAUTH_SECRET

# 3. Starta Docker-tjänster
docker-compose up -d

# 4. Kör Alembic-migrationer
cd backend && alembic upgrade head

# 5. Starta backend (port 8000) + frontend (port 3000)
# Backend: uvicorn main:app --reload
# Frontend: cd frontend && npm install && npm run dev
# Frontend nås på http://localhost:3000
```

### Docker-tjänster

| Tjänst | Port | Beskrivning |
|---|---|---|
| `frontend` | 3000 | Next.js dashboard |
| `backend` | 8000 | FastAPI API |
| `postgres` | 5432 | PostgreSQL + pgvector |
| `redis` | 6379 | Cache + Celery broker |
| `ollama` | 11434 | Lokal SLM-inference (Phi-3, Llama-3) |
| `celery_worker` | — | Async task-processing |
| `prometheus` | 9090 | Metrics-insamling |
| `grafana` | 3001 | Metrics-visualisering (admin/admin) |

---

## Konfiguration

### Miljövariabler

All konfiguration hanteras via miljövariabler. Se `.env.example` för komplett mall.

**Obligatoriska:**
- `FMP_API_KEY` — Financial Modeling Prep (live-fundamentals för M&A Predictor)
- `POSTGRES_PASSWORD` — Databaslösenord (byt från default i produktion)
- `NEXTAUTH_SECRET` — JWT-hemlighet (`openssl rand -base64 32`)

**Viktiga valfria (AI-modeller):**
- `GEMINI_API_KEY` — Gemini Flash/Pro + live sentiment-klassificering
- `ANTHROPIC_API_KEY` — Claude 3.5 Sonnet för M&A-prediktering

**Sprint 16-17 specifika:**
- `USE_MOCK_DATA=false` — Aktiverar live FMP + live RSS (default: false)
- `SENTIMENT_RSS_FEEDS` — Komma-separerade RSS-URL:er (har standardvärde)
- `MA_SMALL_CAP_THRESHOLD_USD` — Micro-cap-gräns för M&A heuristik (default: 500000000)

### Databasinitialisering

Kör `alembic upgrade head` i `backend/` för att applicera alla 7 Alembic-revisioner:

```
0000 → baseline
0001 → take_or_pay fields
0002 → unique index + expiry flag
0003 → notification_preferences JSONB
0004 → user_alerts table
0005 → trade policy + geo fields
0006 → omniscient expansion (buyout_probability_score, is_early_warning)
```

---

## AI-system

### Modellval

Användare väljer AI-modell i frontend. Dynamisk prissättning:

| Modell | Krediter | Beskrivning |
|---|---|---|
| Local Swarm | 1 | Ollama-pipeline (Phi-3 → Mistral → Llama-3) |
| Gemini Flash | 2 | Snabbanalys, sentiment-batch |
| Gemini Pro | 5 | Djupanalys, 1M-token |
| Claude 3.5 | 5 | M&A-prediktering, JSON-extraktion |

### Transaktionssäkerhet

1. **Pre-auth**: Krediter kontrolleras innan analys startar
2. **Atomic deduction**: Dras omedelbart, förhindrar race conditions
3. **Auto-refund**: Full återbetalning om analysen misslyckas
4. **Clear messaging**: Användaren notifieras explicit vid återbetalning

---

## Hive Mind Protocol

### Anonym signaldelning

Noder kan valfritt bidra anonyma signaler:

1. Användare aktiverar "Share with Hive Mind" i UI
2. Signal anonymiseras — inga användaridentifierare
3. Aggregeras med andra noders signaler
4. Konsensusscore beräknas
5. Global Pulse visar top-conviction-signaler

### Dataintegritet

- Ingen användardata delas
- Endast aggregerad metadata: ticker, signal_type, confidence_score
- Valfritt — kan stängas av för fullständig isolering

**Se `CONTRIBUTING.md` avsnitt 4 för fullständig Hive Mind-arkitektur och fork-guide.**

---

## API-endpoints (urval)

| Metod | Route | Beskrivning |
|---|---|---|
| POST | `/api/intelligence/analyze` | Kör multi-SLM debate |
| GET | `/api/intelligence/signals` | Lista analyser |
| GET | `/api/nexus/graph` | Supply-chain-graf (noder + kanter) |
| GET | `/api/dashboard/summary` | God Mode aggregerad snapshot |
| GET | `/api/settings/alerts/subscriptions` | Lista alert-prenumerationer |
| POST | `/api/settings/alerts/subscriptions` | Upsert prenumeration |
| GET | `/api/pulse/top-convictions` | Hive Mind konsensus-ranking |
| GET | `/api/health` | Systemhälsa |

---

## Utveckling

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tester

```bash
cd backend
pytest tests/ -v --tb=short
# Förväntad output: 45 PASSED, 0 FAILED
```

---

## Security

### Authentication

- JWT-based session management via NextAuth.js
- User authentication required for all API endpoints
- Row-level security (RLS) in PostgreSQL for data isolation

### Secrets Management

- All secrets stored in environment variables
- `.gitignore` configured to prevent secret leakage
- Service role keys restricted to backend infrastructure

### Rate Limiting

- API rate limiting configured via slowapi
- Configurable requests per minute/hour

---

## Monitoring

### Prometheus Metrics

The system exposes Prometheus metrics on port 9090:
- Request latency
- Error rates
- Credit transactions
- Task queue depth

### Grafana Dashboards

Access Grafana at http://localhost:3001 (default: admin/admin)
- Pre-configured dashboards for system health
- Custom dashboards can be added

---

## Bidra / Fork

Se [`CONTRIBUTING.md`](CONTRIBUTING.md) för:
- Hur du bidrar med kod (PR-workflow)
- **Komplett fork-guide** (steg-för-steg, egna API-nycklar)
- Adminåtkomst och isolering per nod
- Hive Mind-arkitektur och signaldelning

---

## Licens

MIT — se [`LICENSE`](LICENSE)

---

## Disclaimer

**This is a data analysis and visualization tool, NOT financial advice.**

Users are solely responsible for their investment decisions. The system provides intelligence signals based on available data but cannot guarantee accuracy or profitability. Past performance does not indicate future results.

---

## Support

- **Issues**: Rapportera buggar via [GitHub Issues](https://github.com/Performile1/mineral-ai-tracker/issues)
- **Discussions**: Frågor och idéer via [GitHub Discussions](https://github.com/Performile1/mineral-ai-tracker/discussions)
- **Gemini-analys**: Se `CODEBASE_GEMINI_BRIEF_v5.md` för arkitekturgenomgång

---

**Byggd för suverän finansiell intelligens inom kritiska mineraler**
