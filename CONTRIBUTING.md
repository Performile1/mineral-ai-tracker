# Contributing to Mineral AI Tracker

## Innehållsförteckning

1. [Bidra med kod](#1-bidra-med-kod)
2. [Kör din egen instans (Fork-guide)](#2-kör-din-egen-instans-fork-guide)
3. [Adminåtkomst — isolering per nod](#3-adminåtkomst--isolering-per-nod)
4. [Hive Mind — hur sökningar delas](#4-hive-mind--hur-sökningar-delas)
5. [Dataintegritet och sekretess](#5-dataintegritet-och-sekretess)

---

## 1. Bidra med kod

### Workflow

```
1. Fork → GitHub: klicka "Fork" på https://github.com/Performile1/mineral-ai-tracker
2. Skapa feature-branch:  git checkout -b feat/my-feature
3. Implementera + testa:  pytest backend/tests/ -v
4. Commit med konventionellt prefix:
       feat:  ny funktionalitet
       fix:   buggfix
       chore: beroenden, build, konfiguration
       docs:  dokumentation
5. Pull Request → main-branchen
```

### Kodstandard

- **Python**: `black` + `ruff` (inga kommentarer läggs till utan anledning)
- **TypeScript**: ESLint + Prettier (konfigurerat i `frontend/.eslintrc`)
- **Tester krävs** för ny logik i `agents/`, `engines/` och `workers/`
- Kör testsviten innan PR: `pytest backend/tests/ -v --tb=short`

### Vad vi inte accepterar

- Hårdkodade API-nycklar
- Borttagning av tester utan motivering
- Direkt skrivning mot `main`-branchen

---

## 2. Kör din egen instans (Fork-guide)

En "fork" i detta sammanhang innebär en **helt separat driftsättning** med egna databaser,
egna API-nycklar och egna användare. Du delar ingenting med original-instansen per default.

### Steg-för-steg

```bash
# 1. Forka repot på GitHub (klicka "Fork")
# 2. Klona din fork lokalt
git clone https://github.com/DIN-ORG/mineral-ai-tracker.git
cd mineral-ai-tracker

# 3. Konfigurera miljövariabler
cp .env.example .env
# Redigera .env — fyll i dina egna nycklar (se .env.example)

# 4. Starta infrastrukturen
docker-compose up -d

# 5. Kör Alembic-migrationerna
cd backend
alembic upgrade head

# 6. Starta backend
uvicorn main:app --reload --port 8000

# 7. Starta frontend (i nytt terminalfönster)
cd frontend
npm install && npm run dev
```

Din instans körs nu på `http://localhost:3000` med **helt egna data**.

### Vad din fork innehåller direkt

| Komponent | Status |
|---|---|
| Full FastAPI backend (21 routrar) | ✅ |
| Next.js dashboard med God Mode | ✅ |
| Nexus supply-chain-graf | ✅ |
| M&A Radar + Chokepoint alerts | ✅ |
| APScheduler (06:00, 03:00, 07:00) | ✅ |
| Eget PostgreSQL + Alembic-schema | ✅ |
| Eget admin-panel på `/admin` | ✅ |
| Hive Mind (valfri anslutning) | Konfigurerbart |

### Håll din fork synkroniserad med upstream

```bash
# Lägg till upstream (engångssteg)
git remote add upstream https://github.com/Performile1/mineral-ai-tracker.git

# Synkronisera
git fetch upstream
git merge upstream/main
```

---

## 3. Adminåtkomst — isolering per nod

### Princip: varje nod är suverän

Varje fork/driftsättning har sin **egna** admin-panel (`/admin` i frontend,
`/api/admin/` i backend). Det finns **ingen** gemensam superadmin.

```
┌──────────────────────────┐    ┌──────────────────────────┐
│   Din instans (Fork A)   │    │   Annan instans (Fork B)  │
│                          │    │                          │
│  PostgreSQL (din)        │    │  PostgreSQL (deras)      │
│  /api/admin/ (din)       │    │  /api/admin/ (deras)     │
│  Användare (dina)        │    │  Användare (deras)       │
└──────────────────────────┘    └──────────────────────────┘
             ↑                              ↑
        Ingen access                  Ingen access
         till B                         till A
```

### Vad admin-panelen ger DIG på din instans

- Force-refresh av supply chain-noder
- Visa alla supply_chain_nodes / edges
- Köra manuella system-sweeps
- Visa Prometheus-metrics

### Vad admin INTE ger

- Access till andra instansers data
- Super-admin-funktion över Hive Mind-nätverket
- Möjlighet att ändra andra användares inställningar

### Säkerhetsnotering

`api/admin.py` skyddas av `get_current_user()` (JWT-middleware) men saknar
just nu **rollbaserad åtkomstkontroll** — dvs. alla inloggade användare
på *din* instans kan anropa admin-endpoints. Rekommendation om du öppnar
för fler användare: lägg till en `is_admin` boolean i `users`-tabellen
och kontrollera den i `api/deps.py`.

---

## 4. Hive Mind — hur sökningar delas

### Vad är Hive Mind?

Hive Mind är ett **valfritt anonymt signaldelningslager**. Idén är att
analysresultat (inte rådata, inte användardata) kan bidra till en gemensam
konsensussignal.

### Hur det fungerar tekniskt

```
Användare aktiverar "Share with Hive Mind" (toggle i UI)
          ↓
Signal skickas anonymt: { ticker, signal_type, confidence_score }
          ↓
POST /api/hive/contribute  (api/hive.py)
          ↓
Aggregeras i hive_signals-tabellen (lokal eller delad endpoint)
          ↓
GET /api/pulse/top-convictions → konsensus-ranking
```

### Tre driftslägen

| Läge | Konfiguration | Effekt |
|---|---|---|
| **Isolerat** (default) | `HIVE_MIND_URL` ej satt | Alla signaler stannar i din lokala DB |
| **Delat** | `HIVE_MIND_URL=https://hive.canonical-node.com` | Signaler postas till delad hub |
| **Hub** | Du kör din instans som hub | Tar emot andras anonyma signaler |

### Vad delas och vad delas INTE

| Delas | Delas INTE |
|---|---|
| Ticker-symbol | Användaridentitet |
| Signal-typ (bullish/bearish) | IP-adress |
| Konfidenspoäng | Rådata (pressreleaser, nyheter) |
| Consensus-score | API-nycklar, inloggningar |

### Svar på frågan "Får vi i huvudkoden ta del av deras sökningar?"

**Kort svar: Nej, inte automatiskt. Ja, om de väljer det.**

- En fork kör isolerat — ingen data flödar automatiskt tillbaka
- Om fork-operatören sätter `HIVE_MIND_URL` till din hub-URL och
  deras användare aktiverar Hive Mind-delning → ja, du ser deras
  anonyma konsensussignaler
- Du kan INTE se deras searches, supply chain-data, eller användares identiteter
- Du kan alltså **ta del av deras analysresultat** (aggregerat, anonymt)
  men INTE deras arbetsflöde

### Framtida förbättring (Sprint 18+)

En **Federated Hive Mind API** med ömsesidig TLS och per-nod API-token
skulle göra detta mer robust. Just nu är Hive Mind implementerat som en
intern service per nod.

---

## 5. Dataintegritet och sekretess

- Alla externa API-anrop görs från **din** backend — dina API-nycklar
  delas aldrig med vår infrastruktur
- PostgreSQL-data stannar i din Docker-volym eller din molninstans
- Hive Mind-delning är **opt-in** — standard är fullständig isolering
- `NEXTAUTH_SECRET` genereras per instans (`openssl rand -base64 32`)

---

## Frågor?

Öppna ett [GitHub Issue](https://github.com/Performile1/mineral-ai-tracker/issues)
eller starta en diskussion under [Discussions](https://github.com/Performile1/mineral-ai-tracker/discussions).
