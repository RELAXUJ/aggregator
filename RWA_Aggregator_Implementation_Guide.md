# RWA Aggregator Implementation Guide

## Block-by-Block Development Roadmap

This guide breaks down the entire RWA Liquidity Aggregator implementation into logical phases and blocks. Each block produces a working, testable increment. Follow in order—each block builds on the previous.

---

# Phase 0: Foundation & Verification (Day 1)

**Goal:** Confirm environment works, scaffold boots, basic health check passes.

---

## Block 0.1: Environment Verification

**Location:** Project root (`C:\apps\aggregator`)

**Tasks:**

1. Verify Python 3.12:
   ```powershell
   py -3.12 --version
   # Expected: Python 3.12.x
   ```

2. Create and activate virtual environment:
   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Verify pip:
   ```powershell
   pip --version
   ```

**Checkpoint:** ✅ Virtual environment active, Python 3.12 confirmed.

---

## Block 0.2: Core Dependencies Installation

**Location:** `requirements.txt` or `pyproject.toml`

**Tasks:**

1. Create `requirements.txt` with initial dependencies:
   ```
   # Web Framework
   fastapi==0.109.2
   uvicorn[standard]==0.27.1
   
   # Async HTTP Client
   httpx[http2]==0.26.0
   
   # Database
   sqlalchemy==2.0.25
   alembic==1.13.1
   psycopg[binary]==3.1.18
   
   # Redis & Celery
   redis==5.0.1
   celery[redis]==5.3.6
   
   # Configuration
   pydantic==2.6.1
   pydantic-settings==2.1.0
   
   # Templating
   jinja2==3.1.3
   
   # Testing
   pytest==8.0.0
   pytest-asyncio==0.23.4
   pytest-cov==4.1.0
   
   # Dev utilities
   python-dotenv==1.0.1
   ```

2. Install:
   ```powershell
   pip install -r requirements.txt
   ```

**Checkpoint:** ✅ All packages install without errors.

---

## Block 0.3: Minimal FastAPI Health Check

**Location:** `backend/app/main.py`

**Tasks:**

1. Create minimal FastAPI app:
   ```python
   # backend/app/main.py
   from fastapi import FastAPI
   
   def create_app() -> FastAPI:
       app = FastAPI(
           title="RWA Liquidity Aggregator",
           version="0.1.0"
       )
       
       @app.get("/health")
       async def health_check():
           return {"status": "healthy", "service": "rwa-aggregator"}
       
       return app
   
   app = create_app()
   ```

2. Run and test:
   ```powershell
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

3. Verify in browser: `http://localhost:8000/health`

**Checkpoint:** ✅ Health endpoint returns `{"status": "healthy"}`.

---

## Block 0.4: Configuration System

**Location:** `backend/app/core/config.py`

**Tasks:**

1. Create Pydantic settings:
   ```python
   # backend/app/core/config.py
   from pydantic_settings import BaseSettings
   from functools import lru_cache
   
   class Settings(BaseSettings):
       # App
       app_name: str = "RWA Aggregator"
       debug: bool = True
       
       # Database
       database_url: str = "postgresql+psycopg://user:pass@localhost:5432/rwa_aggregator"
       
       # Redis
       redis_url: str = "redis://localhost:6379/0"
       
       # Polling
       price_fetch_interval_seconds: int = 30
       alert_check_interval_seconds: int = 300
       
       # External APIs
       kraken_base_url: str = "https://api.kraken.com/0/public"
       coinbase_base_url: str = "https://api.exchange.coinbase.com"
       
       # Email
       sendgrid_api_key: str = ""
       alert_from_email: str = "alerts@rwa-aggregator.com"
       
       class Config:
           env_file = ".env"
   
   @lru_cache
   def get_settings() -> Settings:
       return Settings()
   ```

2. Create `.env.example`:
   ```
   DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/rwa_aggregator
   REDIS_URL=redis://localhost:6379/0
   SENDGRID_API_KEY=
   DEBUG=true
   ```

3. Wire into FastAPI:
   ```python
   # Update backend/app/main.py
   from app.core.config import get_settings
   
   def create_app() -> FastAPI:
       settings = get_settings()
       app = FastAPI(title=settings.app_name, debug=settings.debug)
       # ... rest of app
   ```

**Checkpoint:** ✅ Settings load from environment, app boots with config.

---

# Phase 1: Domain Layer (Day 2)

**Goal:** Pure business entities and value objects with no framework dependencies.

---

## Block 1.1: Core Value Objects

**Location:** `backend/app/rwa_aggregator/domain/value_objects/`

**Tasks:**

1. Create `price.py`:
   ```python
   # backend/app/rwa_aggregator/domain/value_objects/price.py
   from dataclasses import dataclass
   from decimal import Decimal
   from typing import Optional
   
   @dataclass(frozen=True)
   class Price:
       value: Decimal
       currency: str = "USD"
       
       def __post_init__(self):
           if self.value < 0:
               raise ValueError("Price cannot be negative")
       
       @classmethod
       def from_string(cls, value: str, currency: str = "USD") -> "Price":
           return cls(Decimal(value), currency)
   ```

2. Create `spread.py`:
   ```python
   # backend/app/rwa_aggregator/domain/value_objects/spread.py
   from dataclasses import dataclass
   from decimal import Decimal
   
   @dataclass(frozen=True)
   class Spread:
       percentage: Decimal
       
       @classmethod
       def calculate(cls, bid: Decimal, ask: Decimal) -> "Spread":
           if bid <= 0 or ask <= 0:
               raise ValueError("Bid and ask must be positive")
           mid = (bid + ask) / 2
           spread_pct = ((ask - bid) / mid) * 100
           return cls(spread_pct.quantize(Decimal("0.0001")))
       
       def is_below_threshold(self, threshold_pct: Decimal) -> bool:
           return self.percentage < threshold_pct
   ```

3. Create `email_address.py`:
   ```python
   # backend/app/rwa_aggregator/domain/value_objects/email_address.py
   from dataclasses import dataclass
   import re
   
   @dataclass(frozen=True)
   class EmailAddress:
       value: str
       
       def __post_init__(self):
           pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
           if not re.match(pattern, self.value):
               raise ValueError(f"Invalid email address: {self.value}")
   ```

**Checkpoint:** ✅ Value objects created with validation, no framework imports.

---

## Block 1.2: Core Entities

**Location:** `backend/app/rwa_aggregator/domain/entities/`

**Tasks:**

1. Create `token.py`:
   ```python
   # backend/app/rwa_aggregator/domain/entities/token.py
   from dataclasses import dataclass
   from typing import Optional
   from enum import Enum
   
   class TokenCategory(Enum):
       TBILL = "tbill"
       PRIVATE_CREDIT = "private_credit"
       REAL_ESTATE = "real_estate"
       EQUITY = "equity"
   
   @dataclass
   class Token:
       id: Optional[int]
       symbol: str
       name: str
       category: TokenCategory
       issuer: str
       chain: Optional[str] = None
       contract_address: Optional[str] = None
       is_active: bool = True
       
       def deactivate(self) -> None:
           self.is_active = False
   ```

2. Create `venue.py`:
   ```python
   # backend/app/rwa_aggregator/domain/entities/venue.py
   from dataclasses import dataclass
   from typing import Optional
   from enum import Enum
   
   class VenueType(Enum):
       CEX = "cex"
       DEX = "dex"
       ISSUER = "issuer"
   
   class ApiType(Enum):
       REST = "rest"
       WEBSOCKET = "websocket"
       SUBGRAPH = "subgraph"
   
   @dataclass
   class Venue:
       id: Optional[int]
       name: str
       venue_type: VenueType
       api_type: ApiType
       base_url: str
       trade_url_template: Optional[str] = None
       is_active: bool = True
       
       def get_trade_url(self, token_symbol: str) -> Optional[str]:
           if self.trade_url_template:
               return self.trade_url_template.format(symbol=token_symbol)
           return None
   ```

3. Create `price_snapshot.py`:
   ```python
   # backend/app/rwa_aggregator/domain/entities/price_snapshot.py
   from dataclasses import dataclass, field
   from datetime import datetime, timezone
   from decimal import Decimal
   from typing import Optional
   
   from ..value_objects.spread import Spread
   
   @dataclass
   class PriceSnapshot:
       id: Optional[int]
       token_id: int
       venue_id: int
       bid: Decimal
       ask: Decimal
       volume_24h: Optional[Decimal] = None
       fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       
       @property
       def mid(self) -> Decimal:
           return (self.bid + self.ask) / 2
       
       @property
       def spread(self) -> Spread:
           return Spread.calculate(self.bid, self.ask)
       
       def is_stale(self, max_age_seconds: int = 60) -> bool:
           age = (datetime.now(timezone.utc) - self.fetched_at).total_seconds()
           return age > max_age_seconds
   ```

4. Create `alert.py`:
   ```python
   # backend/app/rwa_aggregator/domain/entities/alert.py
   from dataclasses import dataclass, field
   from datetime import datetime, timezone, timedelta
   from decimal import Decimal
   from typing import Optional
   from enum import Enum
   
   from ..value_objects.email_address import EmailAddress
   
   class AlertType(Enum):
       SPREAD_BELOW = "spread_below"
       DAILY_SUMMARY = "daily_summary"
   
   class AlertStatus(Enum):
       ACTIVE = "active"
       PAUSED = "paused"
       DELETED = "deleted"
   
   @dataclass
   class Alert:
       id: Optional[int]
       email: EmailAddress
       token_id: int
       threshold_pct: Decimal
       alert_type: AlertType = AlertType.SPREAD_BELOW
       status: AlertStatus = AlertStatus.ACTIVE
       last_triggered_at: Optional[datetime] = None
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       cooldown_hours: int = 1
       
       def can_trigger(self) -> bool:
           if self.status != AlertStatus.ACTIVE:
               return False
           if self.last_triggered_at is None:
               return True
           cooldown_end = self.last_triggered_at + timedelta(hours=self.cooldown_hours)
           return datetime.now(timezone.utc) > cooldown_end
       
       def mark_triggered(self) -> None:
           self.last_triggered_at = datetime.now(timezone.utc)
       
       def pause(self) -> None:
           self.status = AlertStatus.PAUSED
       
       def activate(self) -> None:
           self.status = AlertStatus.ACTIVE
   ```

**Checkpoint:** ✅ All core entities created with business logic, no framework imports.

---

## Block 1.3: Repository Interfaces

**Location:** `backend/app/rwa_aggregator/domain/repositories/`

**Tasks:**

1. Create `token_repository.py`:
   ```python
   # backend/app/rwa_aggregator/domain/repositories/token_repository.py
   from abc import ABC, abstractmethod
   from typing import List, Optional
   
   from ..entities.token import Token, TokenCategory
   
   class TokenRepository(ABC):
       @abstractmethod
       async def get_by_id(self, token_id: int) -> Optional[Token]:
           pass
       
       @abstractmethod
       async def get_by_symbol(self, symbol: str) -> Optional[Token]:
           pass
       
       @abstractmethod
       async def get_all_active(self) -> List[Token]:
           pass
       
       @abstractmethod
       async def get_by_category(self, category: TokenCategory) -> List[Token]:
           pass
       
       @abstractmethod
       async def save(self, token: Token) -> Token:
           pass
   ```

2. Create `venue_repository.py`:
   ```python
   # backend/app/rwa_aggregator/domain/repositories/venue_repository.py
   from abc import ABC, abstractmethod
   from typing import List, Optional
   
   from ..entities.venue import Venue
   
   class VenueRepository(ABC):
       @abstractmethod
       async def get_by_id(self, venue_id: int) -> Optional[Venue]:
           pass
       
       @abstractmethod
       async def get_by_name(self, name: str) -> Optional[Venue]:
           pass
       
       @abstractmethod
       async def get_all_active(self) -> List[Venue]:
           pass
       
       @abstractmethod
       async def get_venues_for_token(self, token_id: int) -> List[Venue]:
           pass
       
       @abstractmethod
       async def save(self, venue: Venue) -> Venue:
           pass
   ```

3. Create `price_repository.py`:
   ```python
   # backend/app/rwa_aggregator/domain/repositories/price_repository.py
   from abc import ABC, abstractmethod
   from typing import List, Optional
   from datetime import datetime
   
   from ..entities.price_snapshot import PriceSnapshot
   
   class PriceRepository(ABC):
       @abstractmethod
       async def get_latest_for_token(self, token_id: int) -> List[PriceSnapshot]:
           """Get latest price from each venue for a token."""
           pass
       
       @abstractmethod
       async def get_latest_for_token_venue(
           self, token_id: int, venue_id: int
       ) -> Optional[PriceSnapshot]:
           pass
       
       @abstractmethod
       async def save(self, snapshot: PriceSnapshot) -> PriceSnapshot:
           pass
       
       @abstractmethod
       async def save_batch(self, snapshots: List[PriceSnapshot]) -> List[PriceSnapshot]:
           pass
       
       @abstractmethod
       async def get_history(
           self, token_id: int, venue_id: int, 
           start: datetime, end: datetime
       ) -> List[PriceSnapshot]:
           pass
   ```

4. Create `alert_repository.py`:
   ```python
   # backend/app/rwa_aggregator/domain/repositories/alert_repository.py
   from abc import ABC, abstractmethod
   from typing import List, Optional
   
   from ..entities.alert import Alert, AlertStatus
   
   class AlertRepository(ABC):
       @abstractmethod
       async def get_by_id(self, alert_id: int) -> Optional[Alert]:
           pass
       
       @abstractmethod
       async def get_active_for_token(self, token_id: int) -> List[Alert]:
           pass
       
       @abstractmethod
       async def get_by_email(self, email: str) -> List[Alert]:
           pass
       
       @abstractmethod
       async def get_all_active(self) -> List[Alert]:
           pass
       
       @abstractmethod
       async def save(self, alert: Alert) -> Alert:
           pass
       
       @abstractmethod
       async def delete(self, alert_id: int) -> bool:
           pass
   ```

**Checkpoint:** ✅ Repository interfaces defined, ready for infrastructure implementation.

---

## Block 1.4: Domain Services

**Location:** `backend/app/rwa_aggregator/domain/services/`

**Tasks:**

1. Create `price_calculator.py`:
   ```python
   # backend/app/rwa_aggregator/domain/services/price_calculator.py
   from dataclasses import dataclass
   from decimal import Decimal
   from typing import List, Optional, Tuple
   
   from ..entities.price_snapshot import PriceSnapshot
   from ..value_objects.spread import Spread
   
   @dataclass
   class BestPrices:
       best_bid: Optional[PriceSnapshot]
       best_ask: Optional[PriceSnapshot]
       effective_spread: Optional[Spread]
       venues_count: int
       
   class PriceCalculator:
       def __init__(self, max_staleness_seconds: int = 60):
           self.max_staleness_seconds = max_staleness_seconds
       
       def calculate_best_prices(
           self, snapshots: List[PriceSnapshot]
       ) -> BestPrices:
           # Filter out stale snapshots
           fresh_snapshots = [
               s for s in snapshots 
               if not s.is_stale(self.max_staleness_seconds)
           ]
           
           if not fresh_snapshots:
               return BestPrices(
                   best_bid=None,
                   best_ask=None,
                   effective_spread=None,
                   venues_count=0
               )
           
           # Find best bid (highest)
           best_bid = max(fresh_snapshots, key=lambda s: s.bid)
           
           # Find best ask (lowest)
           best_ask = min(fresh_snapshots, key=lambda s: s.ask)
           
           # Calculate effective spread across venues
           effective_spread = Spread.calculate(best_bid.bid, best_ask.ask)
           
           return BestPrices(
               best_bid=best_bid,
               best_ask=best_ask,
               effective_spread=effective_spread,
               venues_count=len(fresh_snapshots)
           )
   ```

2. Create `alert_policy.py`:
   ```python
   # backend/app/rwa_aggregator/domain/services/alert_policy.py
   from decimal import Decimal
   from typing import Optional
   
   from ..entities.alert import Alert
   from ..value_objects.spread import Spread
   
   class AlertPolicy:
       def should_trigger(
           self,
           alert: Alert,
           current_spread: Spread,
           previous_spread: Optional[Spread]
       ) -> bool:
           """
           Alert triggers when:
           1. Alert can trigger (active + cooldown passed)
           2. Current spread is below threshold
           3. Previous spread was at or above threshold (crossing condition)
           """
           if not alert.can_trigger():
               return False
           
           threshold = alert.threshold_pct
           is_below_now = current_spread.is_below_threshold(threshold)
           
           if previous_spread is None:
               # First check - only trigger if below
               return is_below_now
           
           was_at_or_above = not previous_spread.is_below_threshold(threshold)
           
           # Trigger on downward crossing
           return is_below_now and was_at_or_above
   ```

**Checkpoint:** ✅ Domain services encapsulate business rules.

---

# Phase 2: Infrastructure Layer - Database (Day 3)

**Goal:** Database models, migrations, repository implementations.

---

## Block 2.1: SQLAlchemy Models

**Location:** `backend/app/rwa_aggregator/infrastructure/db/`

**Tasks:**

1. Create `models.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/db/models.py
   from datetime import datetime
   from decimal import Decimal
   from sqlalchemy import (
       Column, Integer, String, Boolean, DateTime, 
       Numeric, ForeignKey, Enum as SQLEnum, Index
   )
   from sqlalchemy.orm import declarative_base, relationship
   
   from ...domain.entities.token import TokenCategory
   from ...domain.entities.venue import VenueType, ApiType
   from ...domain.entities.alert import AlertType, AlertStatus
   
   Base = declarative_base()
   
   class TokenModel(Base):
       __tablename__ = "tokens"
       
       id = Column(Integer, primary_key=True)
       symbol = Column(String(20), unique=True, nullable=False, index=True)
       name = Column(String(100), nullable=False)
       category = Column(SQLEnum(TokenCategory), nullable=False)
       issuer = Column(String(100))
       chain = Column(String(50))
       contract_address = Column(String(66))
       is_active = Column(Boolean, default=True)
       
       price_snapshots = relationship("PriceSnapshotModel", back_populates="token")
       alerts = relationship("AlertModel", back_populates="token")
   
   class VenueModel(Base):
       __tablename__ = "venues"
       
       id = Column(Integer, primary_key=True)
       name = Column(String(50), unique=True, nullable=False, index=True)
       venue_type = Column(SQLEnum(VenueType), nullable=False)
       api_type = Column(SQLEnum(ApiType), nullable=False)
       base_url = Column(String(255))
       trade_url_template = Column(String(255))
       is_active = Column(Boolean, default=True)
       
       price_snapshots = relationship("PriceSnapshotModel", back_populates="venue")
   
   class PriceSnapshotModel(Base):
       __tablename__ = "price_snapshots"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
       venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
       bid = Column(Numeric(20, 8), nullable=False)
       ask = Column(Numeric(20, 8), nullable=False)
       mid = Column(Numeric(20, 8), nullable=False)
       spread_pct = Column(Numeric(10, 4), nullable=False)
       volume_24h = Column(Numeric(20, 2))
       fetched_at = Column(DateTime(timezone=True), nullable=False, index=True)
       
       token = relationship("TokenModel", back_populates="price_snapshots")
       venue = relationship("VenueModel", back_populates="price_snapshots")
       
       __table_args__ = (
           Index("ix_price_snapshots_token_venue_time", "token_id", "venue_id", "fetched_at"),
       )
   
   class AlertModel(Base):
       __tablename__ = "alerts"
       
       id = Column(Integer, primary_key=True)
       email = Column(String(255), nullable=False, index=True)
       token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
       threshold_pct = Column(Numeric(5, 2), default=2.00)
       alert_type = Column(SQLEnum(AlertType), default=AlertType.SPREAD_BELOW)
       status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE)
       last_triggered_at = Column(DateTime(timezone=True))
       created_at = Column(DateTime(timezone=True), nullable=False)
       
       token = relationship("TokenModel", back_populates="alerts")
   ```

2. Create `session.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/db/session.py
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
   from app.core.config import get_settings
   
   settings = get_settings()
   
   engine = create_async_engine(
       settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
       echo=settings.debug,
       pool_size=5,
       max_overflow=10
   )
   
   AsyncSessionLocal = async_sessionmaker(
       engine,
       class_=AsyncSession,
       expire_on_commit=False
   )
   
   async def get_db_session() -> AsyncSession:
       async with AsyncSessionLocal() as session:
           try:
               yield session
           finally:
               await session.close()
   ```

**Checkpoint:** ✅ SQLAlchemy models defined matching domain entities.

---

## Block 2.2: Alembic Migrations Setup

**Location:** `backend/app/rwa_aggregator/infrastructure/db/`

**Tasks:**

1. Initialize Alembic:
   ```powershell
   cd backend
   alembic init app/rwa_aggregator/infrastructure/db/migrations
   ```

2. Update `alembic.ini`:
   ```ini
   # Update script_location
   script_location = app/rwa_aggregator/infrastructure/db/migrations
   ```

3. Update `migrations/env.py`:
   ```python
   # Add at top
   from app.rwa_aggregator.infrastructure.db.models import Base
   from app.core.config import get_settings
   
   settings = get_settings()
   config.set_main_option("sqlalchemy.url", settings.database_url)
   target_metadata = Base.metadata
   ```

4. Create initial migration:
   ```powershell
   alembic revision --autogenerate -m "initial_schema"
   ```

5. Run migration:
   ```powershell
   alembic upgrade head
   ```

**Checkpoint:** ✅ Database tables created via migration.

---

## Block 2.3: Repository Implementations

**Location:** `backend/app/rwa_aggregator/infrastructure/repositories/`

**Tasks:**

1. Create `sql_token_repository.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/repositories/sql_token_repository.py
   from typing import List, Optional
   from sqlalchemy import select
   from sqlalchemy.ext.asyncio import AsyncSession
   
   from ...domain.entities.token import Token, TokenCategory
   from ...domain.repositories.token_repository import TokenRepository
   from ..db.models import TokenModel
   
   class SqlTokenRepository(TokenRepository):
       def __init__(self, session: AsyncSession):
           self.session = session
       
       async def get_by_id(self, token_id: int) -> Optional[Token]:
           result = await self.session.get(TokenModel, token_id)
           return self._to_entity(result) if result else None
       
       async def get_by_symbol(self, symbol: str) -> Optional[Token]:
           stmt = select(TokenModel).where(TokenModel.symbol == symbol.upper())
           result = await self.session.execute(stmt)
           model = result.scalar_one_or_none()
           return self._to_entity(model) if model else None
       
       async def get_all_active(self) -> List[Token]:
           stmt = select(TokenModel).where(TokenModel.is_active == True)
           result = await self.session.execute(stmt)
           return [self._to_entity(m) for m in result.scalars().all()]
       
       async def get_by_category(self, category: TokenCategory) -> List[Token]:
           stmt = select(TokenModel).where(
               TokenModel.category == category,
               TokenModel.is_active == True
           )
           result = await self.session.execute(stmt)
           return [self._to_entity(m) for m in result.scalars().all()]
       
       async def save(self, token: Token) -> Token:
           model = self._to_model(token)
           self.session.add(model)
           await self.session.commit()
           await self.session.refresh(model)
           return self._to_entity(model)
       
       def _to_entity(self, model: TokenModel) -> Token:
           return Token(
               id=model.id,
               symbol=model.symbol,
               name=model.name,
               category=model.category,
               issuer=model.issuer,
               chain=model.chain,
               contract_address=model.contract_address,
               is_active=model.is_active
           )
       
       def _to_model(self, entity: Token) -> TokenModel:
           return TokenModel(
               id=entity.id,
               symbol=entity.symbol,
               name=entity.name,
               category=entity.category,
               issuer=entity.issuer,
               chain=entity.chain,
               contract_address=entity.contract_address,
               is_active=entity.is_active
           )
   ```

2. Create `sql_price_repository.py` (similar pattern)

3. Create `sql_alert_repository.py` (similar pattern)

**Checkpoint:** ✅ Repository implementations connect domain to database.

---

# Phase 3: Infrastructure Layer - External APIs (Day 4-5)

**Goal:** HTTP clients for CEXs, DEXs, data normalization.

---

## Block 3.1: Base Price Feed Interface

**Location:** `backend/app/rwa_aggregator/application/interfaces/`

**Tasks:**

1. Create `price_feed.py`:
   ```python
   # backend/app/rwa_aggregator/application/interfaces/price_feed.py
   from abc import ABC, abstractmethod
   from dataclasses import dataclass
   from decimal import Decimal
   from typing import Optional
   from datetime import datetime
   
   @dataclass
   class NormalizedQuote:
       venue_name: str
       token_symbol: str
       bid: Decimal
       ask: Decimal
       volume_24h: Optional[Decimal]
       timestamp: datetime
   
   class PriceFeed(ABC):
       @property
       @abstractmethod
       def venue_name(self) -> str:
           pass
       
       @abstractmethod
       async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
           pass
       
       @abstractmethod
       def supports_token(self, token_symbol: str) -> bool:
           pass
   ```

**Checkpoint:** ✅ Interface defined for all price feeds.

---

## Block 3.2: Kraken Client

**Location:** `backend/app/rwa_aggregator/infrastructure/external/`

**Tasks:**

1. Create `kraken_client.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/external/kraken_client.py
   import httpx
   from decimal import Decimal
   from datetime import datetime, timezone
   from typing import Optional, Dict
   
   from ...application.interfaces.price_feed import PriceFeed, NormalizedQuote
   from app.core.config import get_settings
   
   class KrakenClient(PriceFeed):
       # Mapping of our token symbols to Kraken pairs
       SYMBOL_MAP: Dict[str, str] = {
           "USDY": "USDYUSD",
           # Add more mappings as needed
       }
       
       def __init__(self):
           self.settings = get_settings()
           self.base_url = self.settings.kraken_base_url
       
       @property
       def venue_name(self) -> str:
           return "Kraken"
       
       def supports_token(self, token_symbol: str) -> bool:
           return token_symbol.upper() in self.SYMBOL_MAP
       
       async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
           if not self.supports_token(token_symbol):
               return None
           
           pair = self.SYMBOL_MAP[token_symbol.upper()]
           
           try:
               async with httpx.AsyncClient(timeout=10.0) as client:
                   response = await client.get(
                       f"{self.base_url}/Ticker",
                       params={"pair": pair}
                   )
                   response.raise_for_status()
                   data = response.json()
                   
                   if "error" in data and data["error"]:
                       return None
                   
                   result = data["result"][pair]
                   
                   return NormalizedQuote(
                       venue_name=self.venue_name,
                       token_symbol=token_symbol.upper(),
                       bid=Decimal(result["b"][0]),  # Best bid price
                       ask=Decimal(result["a"][0]),  # Best ask price
                       volume_24h=Decimal(result["v"][1]),  # 24h volume
                       timestamp=datetime.now(timezone.utc)
                   )
           except Exception as e:
               # Log error
               print(f"Kraken fetch error: {e}")
               return None
   ```

**Checkpoint:** ✅ Kraken client fetches and normalizes price data.

---

## Block 3.3: Coinbase Client

**Location:** `backend/app/rwa_aggregator/infrastructure/external/`

**Tasks:**

1. Create `coinbase_client.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/external/coinbase_client.py
   import httpx
   from decimal import Decimal
   from datetime import datetime, timezone
   from typing import Optional, Dict
   
   from ...application.interfaces.price_feed import PriceFeed, NormalizedQuote
   from app.core.config import get_settings
   
   class CoinbaseClient(PriceFeed):
       SYMBOL_MAP: Dict[str, str] = {
           "BENJI": "BENJI-USD",
           # Add more mappings
       }
       
       def __init__(self):
           self.settings = get_settings()
           self.base_url = self.settings.coinbase_base_url
       
       @property
       def venue_name(self) -> str:
           return "Coinbase"
       
       def supports_token(self, token_symbol: str) -> bool:
           return token_symbol.upper() in self.SYMBOL_MAP
       
       async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
           if not self.supports_token(token_symbol):
               return None
           
           product_id = self.SYMBOL_MAP[token_symbol.upper()]
           
           try:
               async with httpx.AsyncClient(timeout=10.0) as client:
                   # Get ticker
                   response = await client.get(
                       f"{self.base_url}/products/{product_id}/ticker"
                   )
                   response.raise_for_status()
                   data = response.json()
                   
                   return NormalizedQuote(
                       venue_name=self.venue_name,
                       token_symbol=token_symbol.upper(),
                       bid=Decimal(data["bid"]),
                       ask=Decimal(data["ask"]),
                       volume_24h=Decimal(data["volume"]),
                       timestamp=datetime.now(timezone.utc)
                   )
           except Exception as e:
               print(f"Coinbase fetch error: {e}")
               return None
   ```

**Checkpoint:** ✅ Coinbase client operational.

---

## Block 3.4: Uniswap Subgraph Client

**Location:** `backend/app/rwa_aggregator/infrastructure/external/`

**Tasks:**

1. Create `uniswap_client.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/external/uniswap_client.py
   import httpx
   from decimal import Decimal
   from datetime import datetime, timezone
   from typing import Optional, Dict
   
   from ...application.interfaces.price_feed import PriceFeed, NormalizedQuote
   
   class UniswapClient(PriceFeed):
       SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
       
       # Pool addresses for tokens we care about
       POOL_MAP: Dict[str, Dict] = {
           "USDY": {
               "pool_id": "0x...",  # Actual pool address
               "token_position": 0,  # 0 if USDY is token0, 1 if token1
           },
           "OUSG": {
               "pool_id": "0x...",
               "token_position": 0,
           },
       }
       
       @property
       def venue_name(self) -> str:
           return "Uniswap V3"
       
       def supports_token(self, token_symbol: str) -> bool:
           return token_symbol.upper() in self.POOL_MAP
       
       async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
           if not self.supports_token(token_symbol):
               return None
           
           pool_info = self.POOL_MAP[token_symbol.upper()]
           pool_id = pool_info["pool_id"]
           
           query = """
           query GetPool($poolId: ID!) {
               pool(id: $poolId) {
                   token0Price
                   token1Price
                   liquidity
                   volumeUSD
               }
           }
           """
           
           try:
               async with httpx.AsyncClient(timeout=10.0) as client:
                   response = await client.post(
                       self.SUBGRAPH_URL,
                       json={"query": query, "variables": {"poolId": pool_id}}
                   )
                   response.raise_for_status()
                   data = response.json()
                   
                   pool = data["data"]["pool"]
                   if not pool:
                       return None
                   
                   # Calculate bid/ask from pool price with spread estimate
                   if pool_info["token_position"] == 0:
                       mid_price = Decimal(pool["token1Price"])
                   else:
                       mid_price = Decimal(pool["token0Price"])
                   
                   # Estimate spread based on liquidity (simplified)
                   spread_estimate = Decimal("0.003")  # 0.3% typical AMM spread
                   bid = mid_price * (1 - spread_estimate / 2)
                   ask = mid_price * (1 + spread_estimate / 2)
                   
                   return NormalizedQuote(
                       venue_name=self.venue_name,
                       token_symbol=token_symbol.upper(),
                       bid=bid.quantize(Decimal("0.00000001")),
                       ask=ask.quantize(Decimal("0.00000001")),
                       volume_24h=Decimal(pool["volumeUSD"]),
                       timestamp=datetime.now(timezone.utc)
                   )
           except Exception as e:
               print(f"Uniswap fetch error: {e}")
               return None
   ```

**Checkpoint:** ✅ Uniswap subgraph client operational.

---

## Block 3.5: Price Feed Registry

**Location:** `backend/app/rwa_aggregator/infrastructure/external/`

**Tasks:**

1. Create `price_feed_registry.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/external/price_feed_registry.py
   from typing import List, Dict
   
   from ...application.interfaces.price_feed import PriceFeed, NormalizedQuote
   from .kraken_client import KrakenClient
   from .coinbase_client import CoinbaseClient
   from .uniswap_client import UniswapClient
   
   class PriceFeedRegistry:
       def __init__(self):
           self._feeds: List[PriceFeed] = [
               KrakenClient(),
               CoinbaseClient(),
               UniswapClient(),
           ]
       
       def get_feeds_for_token(self, token_symbol: str) -> List[PriceFeed]:
           return [f for f in self._feeds if f.supports_token(token_symbol)]
       
       async def fetch_all_quotes(self, token_symbol: str) -> List[NormalizedQuote]:
           feeds = self.get_feeds_for_token(token_symbol)
           quotes = []
           
           for feed in feeds:
               quote = await feed.fetch_quote(token_symbol)
               if quote:
                   quotes.append(quote)
           
           return quotes
       
       @property
       def all_venue_names(self) -> List[str]:
           return [f.venue_name for f in self._feeds]
   ```

**Checkpoint:** ✅ Registry aggregates all price feeds.

---

# Phase 4: Application Layer - Use Cases (Day 6)

**Goal:** Orchestration logic connecting domain, infrastructure, and presentation.

---

## Block 4.1: DTOs

**Location:** `backend/app/rwa_aggregator/application/dto/`

**Tasks:**

1. Create `price_dto.py`:
   ```python
   # backend/app/rwa_aggregator/application/dto/price_dto.py
   from pydantic import BaseModel
   from decimal import Decimal
   from datetime import datetime
   from typing import List, Optional
   
   class VenuePriceDTO(BaseModel):
       venue_name: str
       bid: Decimal
       ask: Decimal
       spread_pct: Decimal
       volume_24h: Optional[Decimal]
       updated_at: datetime
       status: str  # "live" | "stale"
       trade_url: Optional[str]
   
   class BestPriceDTO(BaseModel):
       price: Decimal
       venue: str
   
   class AggregatedPricesDTO(BaseModel):
       token_symbol: str
       token_name: str
       best_bid: Optional[BestPriceDTO]
       best_ask: Optional[BestPriceDTO]
       spread_pct: Optional[Decimal]
       venues: List[VenuePriceDTO]
       venues_count: int
       fetched_at: datetime
   ```

2. Create `alert_dto.py`:
   ```python
   # backend/app/rwa_aggregator/application/dto/alert_dto.py
   from pydantic import BaseModel, EmailStr
   from decimal import Decimal
   from datetime import datetime
   from typing import Optional
   
   class CreateAlertRequest(BaseModel):
       email: EmailStr
       token_symbol: str
       threshold_pct: Decimal = Decimal("2.0")
   
   class AlertDTO(BaseModel):
       id: int
       email: str
       token_symbol: str
       threshold_pct: Decimal
       status: str
       last_triggered_at: Optional[datetime]
       created_at: datetime
   ```

**Checkpoint:** ✅ DTOs defined for API contracts.

---

## Block 4.2: Get Aggregated Prices Use Case

**Location:** `backend/app/rwa_aggregator/application/use_cases/`

**Tasks:**

1. Create `get_aggregated_prices.py`:
   ```python
   # backend/app/rwa_aggregator/application/use_cases/get_aggregated_prices.py
   from datetime import datetime, timezone
   from decimal import Decimal
   from typing import Optional
   
   from ..dto.price_dto import AggregatedPricesDTO, VenuePriceDTO, BestPriceDTO
   from ...domain.repositories.token_repository import TokenRepository
   from ...domain.repositories.venue_repository import VenueRepository
   from ...domain.repositories.price_repository import PriceRepository
   from ...domain.services.price_calculator import PriceCalculator
   
   class GetAggregatedPricesUseCase:
       def __init__(
           self,
           token_repo: TokenRepository,
           venue_repo: VenueRepository,
           price_repo: PriceRepository,
           price_calculator: PriceCalculator
       ):
           self.token_repo = token_repo
           self.venue_repo = venue_repo
           self.price_repo = price_repo
           self.price_calculator = price_calculator
       
       async def execute(self, token_symbol: str) -> Optional[AggregatedPricesDTO]:
           # Get token
           token = await self.token_repo.get_by_symbol(token_symbol)
           if not token:
               return None
           
           # Get latest prices from all venues
           snapshots = await self.price_repo.get_latest_for_token(token.id)
           
           # Calculate best prices
           best_prices = self.price_calculator.calculate_best_prices(snapshots)
           
           # Build venue list
           venues = []
           for snapshot in snapshots:
               venue = await self.venue_repo.get_by_id(snapshot.venue_id)
               status = "stale" if snapshot.is_stale() else "live"
               
               venues.append(VenuePriceDTO(
                   venue_name=venue.name,
                   bid=snapshot.bid,
                   ask=snapshot.ask,
                   spread_pct=snapshot.spread.percentage,
                   volume_24h=snapshot.volume_24h,
                   updated_at=snapshot.fetched_at,
                   status=status,
                   trade_url=venue.get_trade_url(token.symbol)
               ))
           
           # Sort by spread
           venues.sort(key=lambda v: v.spread_pct)
           
           return AggregatedPricesDTO(
               token_symbol=token.symbol,
               token_name=token.name,
               best_bid=BestPriceDTO(
                   price=best_prices.best_bid.bid,
                   venue=best_prices.best_bid.venue_id  # Need venue name
               ) if best_prices.best_bid else None,
               best_ask=BestPriceDTO(
                   price=best_prices.best_ask.ask,
                   venue=best_prices.best_ask.venue_id
               ) if best_prices.best_ask else None,
               spread_pct=best_prices.effective_spread.percentage if best_prices.effective_spread else None,
               venues=venues,
               venues_count=best_prices.venues_count,
               fetched_at=datetime.now(timezone.utc)
           )
   ```

**Checkpoint:** ✅ Main use case implemented.

---

## Block 4.3: Create Alert Use Case

**Location:** `backend/app/rwa_aggregator/application/use_cases/`

**Tasks:**

1. Create `create_alert.py`:
   ```python
   # backend/app/rwa_aggregator/application/use_cases/create_alert.py
   from typing import Optional
   
   from ..dto.alert_dto import CreateAlertRequest, AlertDTO
   from ...domain.entities.alert import Alert, AlertType, AlertStatus
   from ...domain.value_objects.email_address import EmailAddress
   from ...domain.repositories.alert_repository import AlertRepository
   from ...domain.repositories.token_repository import TokenRepository
   
   class CreateAlertUseCase:
       def __init__(
           self,
           alert_repo: AlertRepository,
           token_repo: TokenRepository
       ):
           self.alert_repo = alert_repo
           self.token_repo = token_repo
       
       async def execute(self, request: CreateAlertRequest) -> Optional[AlertDTO]:
           # Validate token exists
           token = await self.token_repo.get_by_symbol(request.token_symbol)
           if not token:
               raise ValueError(f"Token {request.token_symbol} not found")
           
           # Create alert entity
           alert = Alert(
               id=None,
               email=EmailAddress(request.email),
               token_id=token.id,
               threshold_pct=request.threshold_pct,
               alert_type=AlertType.SPREAD_BELOW,
               status=AlertStatus.ACTIVE
           )
           
           # Save
           saved_alert = await self.alert_repo.save(alert)
           
           return AlertDTO(
               id=saved_alert.id,
               email=saved_alert.email.value,
               token_symbol=token.symbol,
               threshold_pct=saved_alert.threshold_pct,
               status=saved_alert.status.value,
               last_triggered_at=saved_alert.last_triggered_at,
               created_at=saved_alert.created_at
           )
   ```

**Checkpoint:** ✅ Alert creation use case complete.

---

# Phase 5: Presentation Layer - API & Web (Day 7-8)

**Goal:** FastAPI routes, HTMX endpoints, templates.

---

## Block 5.1: API Routers

**Location:** `backend/app/rwa_aggregator/presentation/api/`

**Tasks:**

1. Create `prices.py`:
   ```python
   # backend/app/rwa_aggregator/presentation/api/prices.py
   from fastapi import APIRouter, Depends, HTTPException
   from sqlalchemy.ext.asyncio import AsyncSession
   
   from ...application.dto.price_dto import AggregatedPricesDTO
   from ...application.use_cases.get_aggregated_prices import GetAggregatedPricesUseCase
   from ...infrastructure.db.session import get_db_session
   from ...infrastructure.repositories.sql_token_repository import SqlTokenRepository
   from ...infrastructure.repositories.sql_venue_repository import SqlVenueRepository
   from ...infrastructure.repositories.sql_price_repository import SqlPriceRepository
   from ...domain.services.price_calculator import PriceCalculator
   
   router = APIRouter(prefix="/api/prices", tags=["prices"])
   
   @router.get("/{token_symbol}", response_model=AggregatedPricesDTO)
   async def get_prices(
       token_symbol: str,
       session: AsyncSession = Depends(get_db_session)
   ):
       use_case = GetAggregatedPricesUseCase(
           token_repo=SqlTokenRepository(session),
           venue_repo=SqlVenueRepository(session),
           price_repo=SqlPriceRepository(session),
           price_calculator=PriceCalculator()
       )
       
       result = await use_case.execute(token_symbol)
       if not result:
           raise HTTPException(status_code=404, detail="Token not found")
       
       return result
   ```

2. Create `alerts.py`:
   ```python
   # backend/app/rwa_aggregator/presentation/api/alerts.py
   from fastapi import APIRouter, Depends, HTTPException
   from sqlalchemy.ext.asyncio import AsyncSession
   from typing import List
   
   from ...application.dto.alert_dto import CreateAlertRequest, AlertDTO
   from ...application.use_cases.create_alert import CreateAlertUseCase
   from ...infrastructure.db.session import get_db_session
   from ...infrastructure.repositories.sql_alert_repository import SqlAlertRepository
   from ...infrastructure.repositories.sql_token_repository import SqlTokenRepository
   
   router = APIRouter(prefix="/api/alerts", tags=["alerts"])
   
   @router.post("", response_model=AlertDTO, status_code=201)
   async def create_alert(
       request: CreateAlertRequest,
       session: AsyncSession = Depends(get_db_session)
   ):
       use_case = CreateAlertUseCase(
           alert_repo=SqlAlertRepository(session),
           token_repo=SqlTokenRepository(session)
       )
       
       try:
           return await use_case.execute(request)
       except ValueError as e:
           raise HTTPException(status_code=400, detail=str(e))
   ```

3. Create `tokens.py`:
   ```python
   # backend/app/rwa_aggregator/presentation/api/tokens.py
   from fastapi import APIRouter, Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from typing import List
   from pydantic import BaseModel
   
   from ...infrastructure.db.session import get_db_session
   from ...infrastructure.repositories.sql_token_repository import SqlTokenRepository
   
   router = APIRouter(prefix="/api/tokens", tags=["tokens"])
   
   class TokenListDTO(BaseModel):
       symbol: str
       name: str
       category: str
       issuer: str
   
   @router.get("", response_model=List[TokenListDTO])
   async def list_tokens(session: AsyncSession = Depends(get_db_session)):
       repo = SqlTokenRepository(session)
       tokens = await repo.get_all_active()
       
       return [
           TokenListDTO(
               symbol=t.symbol,
               name=t.name,
               category=t.category.value,
               issuer=t.issuer
           )
           for t in tokens
       ]
   ```

**Checkpoint:** ✅ API endpoints operational.

---

## Block 5.2: Web Routes (HTMX)

**Location:** `backend/app/rwa_aggregator/presentation/web/`

**Tasks:**

1. Create `dashboard.py`:
   ```python
   # backend/app/rwa_aggregator/presentation/web/dashboard.py
   from fastapi import APIRouter, Request, Depends
   from fastapi.responses import HTMLResponse
   from fastapi.templating import Jinja2Templates
   from sqlalchemy.ext.asyncio import AsyncSession
   
   from ...infrastructure.db.session import get_db_session
   from ...infrastructure.repositories.sql_token_repository import SqlTokenRepository
   from ...application.use_cases.get_aggregated_prices import GetAggregatedPricesUseCase
   # ... other imports
   
   router = APIRouter(tags=["web"])
   templates = Jinja2Templates(directory="app/rwa_aggregator/presentation/templates")
   
   @router.get("/", response_class=HTMLResponse)
   async def dashboard(
       request: Request,
       token: str = "USDY",
       session: AsyncSession = Depends(get_db_session)
   ):
       token_repo = SqlTokenRepository(session)
       tokens = await token_repo.get_all_active()
       
       # Get prices for selected token
       # ... use case call
       
       return templates.TemplateResponse(
           "dashboard.html",
           {
               "request": request,
               "tokens": tokens,
               "current_token": token,
               "prices": None,  # Populated by HTMX
           }
       )
   
   @router.get("/partials/price-table/{token_symbol}", response_class=HTMLResponse)
   async def price_table_partial(
       request: Request,
       token_symbol: str,
       session: AsyncSession = Depends(get_db_session)
   ):
       """HTMX endpoint for auto-refreshing price table."""
       use_case = GetAggregatedPricesUseCase(
           # ... dependencies
       )
       
       prices = await use_case.execute(token_symbol)
       
       return templates.TemplateResponse(
           "partials/price_table.html",
           {"request": request, "prices": prices}
       )
   ```

**Checkpoint:** ✅ Web routes serving HTMX partials.

---

## Block 5.3: Templates

**Location:** `backend/app/rwa_aggregator/presentation/templates/`

**Tasks:**

1. Create `base.html`:
   ```html
   <!-- backend/app/rwa_aggregator/presentation/templates/base.html -->
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>{% block title %}RWA Best Price{% endblock %}</title>
       <script src="https://cdn.tailwindcss.com"></script>
       <script src="https://unpkg.com/htmx.org@1.9.10"></script>
   </head>
   <body class="bg-slate-950 text-slate-100 min-h-screen">
       <div class="max-w-6xl mx-auto px-4 py-8">
           {% block content %}{% endblock %}
       </div>
   </body>
   </html>
   ```

2. Create `dashboard.html`:
   ```html
   <!-- backend/app/rwa_aggregator/presentation/templates/dashboard.html -->
   {% extends "base.html" %}
   
   {% block content %}
   <header class="flex items-center justify-between mb-8">
       <div>
           <h1 class="text-2xl font-semibold">RWA Best Price</h1>
           <p class="text-sm text-slate-400">Live best execution across venues</p>
       </div>
       <form method="get" action="/">
           <select name="token" 
                   hx-get="/partials/price-table/{{ current_token }}"
                   hx-trigger="change"
                   hx-target="#price-table"
                   class="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2">
               {% for t in tokens %}
               <option value="{{ t.symbol }}" {% if t.symbol == current_token %}selected{% endif %}>
                   {{ t.name }} ({{ t.symbol }})
               </option>
               {% endfor %}
           </select>
       </form>
   </header>
   
   <!-- KPI Cards -->
   <section class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6" id="kpi-cards">
       {% include "partials/kpi_cards.html" %}
   </section>
   
   <!-- Price Table -->
   <section class="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden">
       <div class="flex items-center justify-between px-4 py-3 border-b border-slate-800">
           <h2 class="text-sm font-semibold">Order Book Snapshot — {{ current_token }}</h2>
           <span class="text-xs text-slate-500">Auto-refreshing every 10s</span>
       </div>
       <div id="price-table"
            hx-get="/partials/price-table/{{ current_token }}"
            hx-trigger="load, every 10s"
            hx-swap="innerHTML">
           {% include "partials/price_table.html" %}
       </div>
   </section>
   
   <!-- Actions -->
   <div class="mt-4 flex gap-4">
       <button onclick="openAlertModal()" 
               class="px-4 py-2 bg-indigo-500 hover:bg-indigo-400 rounded-xl">
           🔔 Set Alert
       </button>
       <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-xl">
           📊 Export CSV
       </button>
   </div>
   {% endblock %}
   ```

3. Create `partials/price_table.html`:
   ```html
   <!-- backend/app/rwa_aggregator/presentation/templates/partials/price_table.html -->
   <table class="min-w-full text-sm">
       <thead class="bg-slate-900 border-b border-slate-800">
           <tr>
               <th class="text-left px-4 py-2 text-xs text-slate-400 uppercase">Venue</th>
               <th class="text-right px-4 py-2 text-xs text-slate-400 uppercase">Bid</th>
               <th class="text-right px-4 py-2 text-xs text-slate-400 uppercase">Ask</th>
               <th class="text-right px-4 py-2 text-xs text-slate-400 uppercase">Spread</th>
               <th class="text-right px-4 py-2 text-xs text-slate-400 uppercase">Volume 24h</th>
               <th class="text-right px-4 py-2 text-xs text-slate-400 uppercase">Updated</th>
           </tr>
       </thead>
       <tbody class="divide-y divide-slate-800">
           {% if prices and prices.venues %}
               {% for venue in prices.venues %}
               <tr class="hover:bg-slate-900/70">
                   <td class="px-4 py-2 font-medium">{{ venue.venue_name }}</td>
                   <td class="px-4 py-2 text-right tabular-nums 
                       {% if venue.bid == prices.best_bid.price %}text-green-400{% endif %}">
                       ${{ venue.bid }}
                   </td>
                   <td class="px-4 py-2 text-right tabular-nums
                       {% if venue.ask == prices.best_ask.price %}text-green-400{% endif %}">
                       ${{ venue.ask }}
                   </td>
                   <td class="px-4 py-2 text-right tabular-nums">{{ venue.spread_pct }}%</td>
                   <td class="px-4 py-2 text-right tabular-nums text-slate-500">
                       {% if venue.volume_24h %}${{ "{:,.0f}".format(venue.volume_24h) }}{% else %}-{% endif %}
                   </td>
                   <td class="px-4 py-2 text-right text-xs text-slate-500">
                       {{ venue.updated_at.strftime('%H:%M:%S') }}
                   </td>
               </tr>
               {% endfor %}
           {% else %}
               <tr>
                   <td colspan="6" class="px-4 py-6 text-center text-slate-500">
                       No price data available
                   </td>
               </tr>
           {% endif %}
       </tbody>
   </table>
   ```

**Checkpoint:** ✅ Dashboard renders with HTMX auto-refresh.

---

# Phase 6: Background Tasks - Celery (Day 9-10)

**Goal:** Price fetching and alert checking on schedule.

---

## Block 6.1: Celery Configuration

**Location:** `backend/app/rwa_aggregator/infrastructure/tasks/`

**Tasks:**

1. Create `celery_app.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/tasks/celery_app.py
   from celery import Celery
   from app.core.config import get_settings
   
   settings = get_settings()
   
   celery_app = Celery(
       "rwa_aggregator",
       broker=settings.redis_url,
       backend=settings.redis_url,
       include=[
           "app.rwa_aggregator.infrastructure.tasks.price_fetcher",
           "app.rwa_aggregator.infrastructure.tasks.alert_checker",
       ]
   )
   
   celery_app.conf.update(
       task_serializer="json",
       accept_content=["json"],
       result_serializer="json",
       timezone="UTC",
       enable_utc=True,
       beat_schedule={
           "fetch-prices-every-30s": {
               "task": "app.rwa_aggregator.infrastructure.tasks.price_fetcher.fetch_all_prices",
               "schedule": 30.0,
           },
           "check-alerts-every-5m": {
               "task": "app.rwa_aggregator.infrastructure.tasks.alert_checker.check_alerts",
               "schedule": 300.0,
           },
       }
   )
   ```

**Checkpoint:** ✅ Celery configured with beat schedule.

---

## Block 6.2: Price Fetcher Task

**Location:** `backend/app/rwa_aggregator/infrastructure/tasks/`

**Tasks:**

1. Create `price_fetcher.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/tasks/price_fetcher.py
   import asyncio
   from datetime import datetime, timezone
   
   from .celery_app import celery_app
   from ..external.price_feed_registry import PriceFeedRegistry
   from ..db.session import AsyncSessionLocal
   from ..repositories.sql_token_repository import SqlTokenRepository
   from ..repositories.sql_venue_repository import SqlVenueRepository
   from ..repositories.sql_price_repository import SqlPriceRepository
   from ...domain.entities.price_snapshot import PriceSnapshot
   
   @celery_app.task
   def fetch_all_prices():
       """Fetch prices for all active tokens from all venues."""
       asyncio.run(_fetch_all_prices_async())
   
   async def _fetch_all_prices_async():
       registry = PriceFeedRegistry()
       
       async with AsyncSessionLocal() as session:
           token_repo = SqlTokenRepository(session)
           venue_repo = SqlVenueRepository(session)
           price_repo = SqlPriceRepository(session)
           
           tokens = await token_repo.get_all_active()
           
           for token in tokens:
               quotes = await registry.fetch_all_quotes(token.symbol)
               
               for quote in quotes:
                   # Get venue by name
                   venue = await venue_repo.get_by_name(quote.venue_name)
                   if not venue:
                       continue
                   
                   # Create snapshot
                   snapshot = PriceSnapshot(
                       id=None,
                       token_id=token.id,
                       venue_id=venue.id,
                       bid=quote.bid,
                       ask=quote.ask,
                       volume_24h=quote.volume_24h,
                       fetched_at=quote.timestamp
                   )
                   
                   await price_repo.save(snapshot)
               
               await session.commit()
   ```

**Checkpoint:** ✅ Price fetcher runs on schedule.

---

## Block 6.3: Alert Checker Task

**Location:** `backend/app/rwa_aggregator/infrastructure/tasks/`

**Tasks:**

1. Create `alert_checker.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/tasks/alert_checker.py
   import asyncio
   from decimal import Decimal
   
   from .celery_app import celery_app
   from ..db.session import AsyncSessionLocal
   from ..repositories.sql_alert_repository import SqlAlertRepository
   from ..repositories.sql_price_repository import SqlPriceRepository
   from ..repositories.sql_token_repository import SqlTokenRepository
   from ..external.sendgrid_emailer import SendGridEmailer
   from ...domain.services.price_calculator import PriceCalculator
   from ...domain.services.alert_policy import AlertPolicy
   
   @celery_app.task
   def check_alerts():
       """Check all active alerts and send notifications."""
       asyncio.run(_check_alerts_async())
   
   async def _check_alerts_async():
       async with AsyncSessionLocal() as session:
           alert_repo = SqlAlertRepository(session)
           price_repo = SqlPriceRepository(session)
           token_repo = SqlTokenRepository(session)
           
           calculator = PriceCalculator()
           policy = AlertPolicy()
           emailer = SendGridEmailer()
           
           alerts = await alert_repo.get_all_active()
           
           for alert in alerts:
               # Get current prices
               snapshots = await price_repo.get_latest_for_token(alert.token_id)
               best_prices = calculator.calculate_best_prices(snapshots)
               
               if not best_prices.effective_spread:
                   continue
               
               # Check if alert should trigger
               # (simplified - would need previous spread tracking)
               if policy.should_trigger(alert, best_prices.effective_spread, None):
                   token = await token_repo.get_by_id(alert.token_id)
                   
                   # Send email
                   await emailer.send_alert(
                       to_email=alert.email.value,
                       token_symbol=token.symbol,
                       current_spread=best_prices.effective_spread.percentage,
                       best_bid_venue=best_prices.best_bid.venue_id,
                       best_bid_price=best_prices.best_bid.bid,
                       best_ask_venue=best_prices.best_ask.venue_id,
                       best_ask_price=best_prices.best_ask.ask
                   )
                   
                   # Mark triggered
                   alert.mark_triggered()
                   await alert_repo.save(alert)
               
               await session.commit()
   ```

2. Create `sendgrid_emailer.py`:
   ```python
   # backend/app/rwa_aggregator/infrastructure/external/sendgrid_emailer.py
   import httpx
   from decimal import Decimal
   from app.core.config import get_settings
   
   class SendGridEmailer:
       def __init__(self):
           self.settings = get_settings()
       
       async def send_alert(
           self,
           to_email: str,
           token_symbol: str,
           current_spread: Decimal,
           best_bid_venue: str,
           best_bid_price: Decimal,
           best_ask_venue: str,
           best_ask_price: Decimal
       ):
           if not self.settings.sendgrid_api_key:
               print(f"[DEV] Alert email to {to_email}: {token_symbol} spread {current_spread}%")
               return
           
           async with httpx.AsyncClient() as client:
               await client.post(
                   "https://api.sendgrid.com/v3/mail/send",
                   headers={
                       "Authorization": f"Bearer {self.settings.sendgrid_api_key}",
                       "Content-Type": "application/json"
                   },
                   json={
                       "personalizations": [{"to": [{"email": to_email}]}],
                       "from": {"email": self.settings.alert_from_email},
                       "subject": f"🔔 {token_symbol} Spread Alert: {current_spread}%",
                       "content": [{
                           "type": "text/html",
                           "value": f"""
                           <h2>{token_symbol} Spread Alert</h2>
                           <p>Spread has dropped to <strong>{current_spread}%</strong></p>
                           <ul>
                               <li>Best Bid: ${best_bid_price} on {best_bid_venue}</li>
                               <li>Best Ask: ${best_ask_price} on {best_ask_venue}</li>
                           </ul>
                           """
                       }]
                   }
               )
   ```

**Checkpoint:** ✅ Alerts trigger and send emails.

---

# Phase 7: Integration & Testing (Day 11-12)

**Goal:** Wire everything together, seed data, end-to-end testing.

---

## Block 7.1: Wire Routers in Main App

**Location:** `backend/app/main.py`

**Tasks:**

1. Update `main.py`:
   ```python
   # backend/app/main.py
   from fastapi import FastAPI
   from fastapi.staticfiles import StaticFiles
   
   from app.core.config import get_settings
   from app.rwa_aggregator.presentation.api import prices, alerts, tokens
   from app.rwa_aggregator.presentation.web import dashboard
   
   def create_app() -> FastAPI:
       settings = get_settings()
       
       app = FastAPI(
           title="RWA Liquidity Aggregator",
           version="0.1.0",
           debug=settings.debug
       )
       
       # API routes
       app.include_router(prices.router)
       app.include_router(alerts.router)
       app.include_router(tokens.router)
       
       # Web routes
       app.include_router(dashboard.router)
       
       # Static files
       app.mount(
           "/static",
           StaticFiles(directory="app/rwa_aggregator/presentation/static"),
           name="static"
       )
       
       @app.get("/health")
       async def health():
           return {"status": "healthy"}
       
       return app
   
   app = create_app()
   ```

**Checkpoint:** ✅ All routes wired.

---

## Block 7.2: Seed Data Script

**Location:** `scripts/`

**Tasks:**

1. Create `seed_data.py`:
   ```python
   # scripts/seed_data.py
   import asyncio
   from app.rwa_aggregator.infrastructure.db.session import AsyncSessionLocal
   from app.rwa_aggregator.infrastructure.db.models import TokenModel, VenueModel
   from app.rwa_aggregator.domain.entities.token import TokenCategory
   from app.rwa_aggregator.domain.entities.venue import VenueType, ApiType
   
   TOKENS = [
       {"symbol": "USDY", "name": "Ondo US Dollar Yield", "category": TokenCategory.TBILL, "issuer": "Ondo Finance"},
       {"symbol": "BENJI", "name": "Franklin OnChain US Gov Money Fund", "category": TokenCategory.TBILL, "issuer": "Franklin Templeton"},
       {"symbol": "OUSG", "name": "Ondo Short-Term US Gov Treasuries", "category": TokenCategory.TBILL, "issuer": "Ondo Finance"},
   ]
   
   VENUES = [
       {"name": "Kraken", "venue_type": VenueType.CEX, "api_type": ApiType.REST, "base_url": "https://api.kraken.com"},
       {"name": "Coinbase", "venue_type": VenueType.CEX, "api_type": ApiType.REST, "base_url": "https://api.exchange.coinbase.com"},
       {"name": "Uniswap V3", "venue_type": VenueType.DEX, "api_type": ApiType.SUBGRAPH, "base_url": "https://api.thegraph.com"},
   ]
   
   async def seed():
       async with AsyncSessionLocal() as session:
           for t in TOKENS:
               session.add(TokenModel(**t, is_active=True))
           for v in VENUES:
               session.add(VenueModel(**v, is_active=True))
           await session.commit()
       print("✅ Seed data inserted")
   
   if __name__ == "__main__":
       asyncio.run(seed())
   ```

**Checkpoint:** ✅ Database populated with initial tokens/venues.

---

## Block 7.3: Run Full Stack Locally

**Tasks:**

1. Start services:
   ```powershell
   # Terminal 1: Database (if using Docker)
   docker run -d --name rwa-postgres -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=rwa_aggregator -p 5432:5432 postgres:16
   
   # Terminal 2: Redis
   docker run -d --name rwa-redis -p 6379:6379 redis:7
   
   # Terminal 3: Run migrations & seed
   cd backend
   alembic upgrade head
   python ../scripts/seed_data.py
   
   # Terminal 4: FastAPI
   uvicorn app.main:app --reload --port 8000
   
   # Terminal 5: Celery worker
   celery -A app.rwa_aggregator.infrastructure.tasks.celery_app worker --loglevel=info
   
   # Terminal 6: Celery beat
   celery -A app.rwa_aggregator.infrastructure.tasks.celery_app beat --loglevel=info
   ```

2. Verify:
   - Dashboard: http://localhost:8000/
   - API: http://localhost:8000/api/tokens
   - Health: http://localhost:8000/health

**Checkpoint:** ✅ Full stack running locally.

---

## Block 7.4: Basic Tests

**Location:** `tests/`

**Tasks:**

1. Create `tests/test_domain/test_price_calculator.py`:
   ```python
   import pytest
   from decimal import Decimal
   from datetime import datetime, timezone
   
   from app.rwa_aggregator.domain.services.price_calculator import PriceCalculator
   from app.rwa_aggregator.domain.entities.price_snapshot import PriceSnapshot
   
   def test_calculate_best_prices():
       snapshots = [
           PriceSnapshot(id=1, token_id=1, venue_id=1, bid=Decimal("1.0010"), ask=Decimal("1.0020")),
           PriceSnapshot(id=2, token_id=1, venue_id=2, bid=Decimal("1.0012"), ask=Decimal("1.0018")),
       ]
       
       calculator = PriceCalculator()
       result = calculator.calculate_best_prices(snapshots)
       
       assert result.best_bid.bid == Decimal("1.0012")
       assert result.best_ask.ask == Decimal("1.0018")
       assert result.venues_count == 2
   ```

2. Run tests:
   ```powershell
   pytest tests/ -v
   ```

**Checkpoint:** ✅ Core logic tested.

---

# Summary: Day-by-Day Schedule

| Day | Phase | Blocks | Deliverable |
|-----|-------|--------|-------------|
| 1 | Phase 0 | 0.1-0.4 | Environment ready, FastAPI boots, config loads |
| 2 | Phase 1 | 1.1-1.4 | Domain layer complete (entities, value objects, services) |
| 3 | Phase 2 | 2.1-2.3 | Database models, migrations, repository implementations |
| 4-5 | Phase 3 | 3.1-3.5 | External API clients (Kraken, Coinbase, Uniswap) |
| 6 | Phase 4 | 4.1-4.3 | Application use cases (get prices, create alert) |
| 7-8 | Phase 5 | 5.1-5.3 | API routes, web routes, templates, HTMX dashboard |
| 9-10 | Phase 6 | 6.1-6.3 | Celery tasks (price fetcher, alert checker) |
| 11-12 | Phase 7 | 7.1-7.4 | Integration, seed data, testing, full stack running |

---

# Post-MVP: Next Steps

After completing Phase 7:

1. **Add more tokens/venues** - BUIDL (when Securitize MCP available), MANTRA DEX
2. **User authentication** - Simple email-based magic link auth
3. **Historical charts** - 7-day and 30-day spread history using Recharts
4. **Daily summary emails** - Celery task for morning reports
5. **Deployment** - Railway/Render with managed Postgres + Redis
6. **Monitoring** - Sentry for errors, basic metrics dashboard

---

*Document Version: 1.0 | December 2025*
