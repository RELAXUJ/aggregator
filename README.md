# RWA Liquidity Aggregator

Real-time price aggregation for RWA (Real World Asset) tokens across multiple venues including centralized exchanges (CEX), decentralized exchanges (DEX), and token issuers.

## Features

- **Price Aggregation (F-001)**: Fetch real-time prices from multiple venues
- **Best Price Calculation (F-002)**: Calculate best bid/ask, mid-price, and spread
- **Alert System (F-003)**: User-configurable price alerts with email notifications
- **Dashboard (F-004)**: Real-time price display with HTMX-powered updates

## Tech Stack

- **Runtime**: Python 3.12+
- **Web Framework**: FastAPI with Uvicorn
- **Background Tasks**: Celery with Redis broker
- **Database**: PostgreSQL with SQLAlchemy 2.x
- **Cache**: Redis
- **Templates**: Jinja2 with HTMX
- **Styling**: Tailwind CSS

## Project Structure

```
aggregator/
├── backend/
│   └── app/
│       ├── core/                    # Cross-cutting concerns
│       │   ├── config.py            # Pydantic settings
│       │   └── logging.py           # Logging setup
│       ├── main.py                  # FastAPI app factory
│       └── rwa_aggregator/          # Main bounded context
│           ├── domain/              # Pure business logic
│           │   ├── entities/        # Token, Venue, PriceSnapshot, Alert
│           │   ├── value_objects/   # Price, Spread, VenueType
│           │   ├── repositories/    # Abstract interfaces
│           │   └── services/        # PriceCalculator, AlertPolicy
│           ├── application/         # Use cases & orchestration
│           │   ├── use_cases/       # GetAggregatedPrices, CreateAlert
│           │   ├── dto/             # Request/response DTOs
│           │   └── interfaces/      # Ports for external systems
│           ├── infrastructure/      # Frameworks & adapters
│           │   ├── db/              # SQLAlchemy models, migrations
│           │   ├── redis/           # Cache client
│           │   ├── external/        # Kraken, Coinbase, Uniswap clients
│           │   ├── repositories/    # SQL implementations
│           │   └── tasks/           # Celery tasks
│           └── presentation/        # API & web layer
│               ├── api/             # FastAPI routers
│               ├── web/             # HTMX endpoints
│               ├── templates/       # Jinja2 templates
│               └── static/          # CSS, assets
├── frontend/                        # Tailwind build pipeline
├── infra/                           # Docker, deployment configs
├── scripts/                         # Dev/maintenance scripts
├── tests/                           # Test suite by layer
├── .cursorrules                     # AI coding guidelines
├── pyproject.toml                   # Project metadata & dependencies
├── requirements.txt                 # Pip dependencies
└── .env.example                     # Environment template
```

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+

### Setup

1. **Create virtual environment**:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database and API credentials
   ```

4. **Run the application**:
   ```bash
   # Start FastAPI server
   cd backend
   uvicorn app.main:app --reload

   # In another terminal, start Celery worker
   celery -A app.rwa_aggregator.infrastructure.tasks.celery_app worker --loglevel=info

   # In another terminal, start Celery beat (scheduler)
   celery -A app.rwa_aggregator.infrastructure.tasks.celery_app beat --loglevel=info
   ```

5. **Access the application**:
   - API docs: http://localhost:8000/api/docs
   - Health check: http://localhost:8000/api/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/ready` | Readiness check |
| GET | `/api/prices/{token}` | Get aggregated prices for a token |
| GET | `/api/prices` | Get prices for all tracked tokens |

## Architecture

This project follows **Domain-Driven Design (DDD)** with strict layering:

- **Domain Layer**: Pure business logic, no framework dependencies
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: Database, cache, external API adapters
- **Presentation Layer**: HTTP endpoints and templates

See `.cursorrules` for detailed architecture guidelines.

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Linting
ruff check backend/

# Type checking
mypy backend/
```

## License

MIT
