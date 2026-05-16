# Mineral AI Tracker - The Decentralized Financial Intelligence Protocol

**Version 13.2 | Production-Ready Open Source Protocol**

---

## The Sovereign Protocol

Mineral AI Tracker is a decentralized financial intelligence protocol that enables sovereign data analysis through multi-model AI orchestration. Each node in the network operates independently, running local AI models (Ollama) or cloud models (Gemini) to analyze financial intelligence, then optionally contributes anonymous signals to a distributed Hive Mind consensus layer.

### Core Philosophy

- **Data Sovereignty**: Your data never leaves your infrastructure. Analysis runs locally or on your cloud infrastructure.
- **Model Agnosticism**: Choose between local SLM swarms (Phi-3, Mistral, Llama-3) or cloud models (Gemini Flash/Pro) with dynamic pricing.
- **Hive Mind Consensus**: Optional anonymous contribution to a distributed intelligence layer that aggregates signals across nodes.
- **Transaction Safety**: Enterprise-grade credit management with atomic transactions and automatic refunds on failure.

---

## Architecture

### Backend Stack

- **Framework**: FastAPI (Python 3.10+) with async/await
- **Database**: PostgreSQL 14+ with pgvector extension for semantic search
- **Task Queue**: Celery with Redis for async job processing
- **AI Orchestration**: Multi-SLM Debate Protocol (Phi-3 → Mistral → Llama-3)
- **Cloud Integration**: Google Gemini API (optional, with dynamic pricing)
- **Monitoring**: Prometheus + Grafana for observability

### Frontend Stack

- **Framework**: Next.js 14 with App Router and TypeScript
- **Styling**: Tailwind CSS with custom design tokens
- **State Management**: React hooks with server components
- **Authentication**: NextAuth.js with JWT session management
- **Charts**: Recharts for financial visualization

### Multi-Model AI Engine

- **Local Swarm**: Phi-3 (extraction) → Mistral (geology) → Llama-3 (risk) - 1 Credit
- **Cloud Engine**: Gemini Flash (fast analysis) - 2 Credits
- **Deep Cloud**: Gemini Pro (1M token context) - 5 Credits

---

## Quick Start for Node Runners

### Prerequisites

- Docker Desktop 4.0+
- Ollama (for local SLM swarm, optional)
- Financial Modeling Prep API key (required for institutional data)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/mineral-ai-tracker.git
cd mineral-ai-tracker

# 2. Copy environment template
cp .env.example .env

# 3. Configure your environment
# Edit .env and add your FMP_API_KEY
# For Gemini models, add GEMINI_API_KEY (optional)

# 4. Start the infrastructure
docker-compose up -d

# 5. Initialize the database
# Database migrations run automatically on first startup
# Access the frontend at http://localhost:3000
```

### Docker Services

The `docker-compose.yml` orchestrates the following services:

- **frontend**: Next.js application (port 3000)
- **backend**: FastAPI API server (port 8000)
- **postgres**: PostgreSQL with pgvector (port 5432)
- **redis**: Redis for Celery task queue (port 6379)
- **ollama**: Local SLM inference (port 11434)
- **celery_worker**: Async task processing
- **prometheus**: Metrics collection (port 9090)
- **grafana**: Metrics visualization (port 3001)

---

## Configuration

### Environment Variables

All configuration is managed through environment variables. See `.env.example` for the complete structure.

**Required Variables:**
- `FMP_API_KEY`: Financial Modeling Prep API key for institutional data
- `POSTGRES_PASSWORD`: Database password (change from default for production)

**Optional Variables:**
- `GEMINI_API_KEY`: Google Gemini API key for cloud models
- `USE_CELERY`: Enable async task processing (default: True)
- `USE_PROXIES`: Enable proxy rotation for web scraping

### Database Initialization

The database schema is initialized automatically on first startup. Migration files in `db/init/` are executed in order:

- `00_init_schema.sql`: Core tables and pgvector extension
- `01_*.sql` through `14_*.sql`: Feature-specific migrations

---

## Multi-Model AI System

### Model Selection

Users select their preferred AI model through the frontend:

- **Local Swarm**: Runs entirely on your infrastructure using Ollama
- **Cloud Engine**: Fast analysis via Google Gemini Flash
- **Deep Cloud**: Deep analysis via Google Gemini Pro

### Dynamic Pricing

Credit costs vary by model:
- Local Swarm: 1 credit per analysis
- Gemini Flash: 2 credits per analysis
- Gemini Pro: 5 credits per analysis

### Transaction Safety

The credit system implements enterprise-grade transaction safety:

1. **Pre-authorization**: Credits verified before analysis starts
2. **Atomic Deduction**: Credits deducted immediately to prevent race conditions
3. **Automatic Refund**: Full refund if analysis fails (no automatic fallback)
4. **Clear Messaging**: Users receive explicit notification when credits are refunded

---

## Hive Mind Protocol

### Anonymous Signal Contribution

Nodes can optionally contribute anonymous signals to the Hive Mind:

1. User enables "Share with Hive Mind" in the UI
2. Signal is anonymized (no user identifiers)
3. Signal is aggregated with other nodes' signals
4. Consensus score is calculated across the network
5. Global Pulse ranking displays top conviction signals

### Data Privacy

- No user data is ever shared with the Hive Mind
- Only aggregated signal metadata (ticker, signal_type, confidence_score, consensus_score)
- Optional feature - can be disabled for complete privacy

---

## API Endpoints

### Intelligence API

- `POST /api/intelligence/analyze`: Run multi-SLM debate protocol
- `GET /api/intelligence/models/available`: Get available AI models
- `GET /api/intelligence/signals`: List intelligence signals

### Watchlist API

- `POST /api/watchlist/stalk`: On-demand analysis of a ticker
- `GET /api/watchlist/status/{task_id}`: Check Celery task status

### User API

- `GET /api/pulse/credits`: Get user credit balance
- `GET /api/pulse/top-convictions`: Get Hive Mind top convictions

---

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
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

## Contributing

We welcome contributions from the community. Please see `CONTRIBUTING.md` for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

---

## License

MIT License - See `LICENSE` file for details

---

## Disclaimer

**This is a data analysis and visualization tool, NOT financial advice.**

Users are solely responsible for their investment decisions. The system provides intelligence signals based on available data but cannot guarantee accuracy or profitability. Past performance does not indicate future results.

---

## Support

- **Documentation**: See `docs/` directory for detailed documentation
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and ideas

---

**Built with ❤️ for the decentralized financial intelligence community**
