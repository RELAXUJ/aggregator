# RWA Secondary Market Liquidity Aggregator

## MVP Specification Document

**User Stories • UX Definitions • Technical Architecture**
**Functional Specifications • Data Acquisition Strategy**

**Version 1.0**
**December 2025**

---

# Table of Contents

1. [Executive Summary](#executive-summary)
2. [User Stories](#user-stories)
3. [UX Definitions](#ux-definitions)
4. [Technical Architecture](#technical-architecture)
5. [Data Acquisition Strategy](#data-acquisition-strategy)
6. [Functional Specifications](#functional-specifications)
7. [API Specifications](#api-specifications)
8. [Implementation Roadmap](#implementation-roadmap)
9. [Risks and Mitigations](#risks-and-mitigations)
10. [Appendix A: Glossary](#appendix-a-glossary)
11. [Appendix B: Reference Links](#appendix-b-reference-links)

---

# Executive Summary

The RWA Secondary Market Liquidity Aggregator addresses the critical liquidity fragmentation problem in tokenized Real-World Assets. Currently, investors face a landscape of 'liquidity islands' where each platform (Ondo, Securitize, MANTRA, Franklin Templeton) operates independently with no unified view of market depth or best execution.

This MVP delivers a price comparison dashboard with real-time aggregation across 3-5 RWA platforms, enabling institutional investors to identify best execution venues and receive alerts when trading opportunities emerge. The architecture leverages public APIs, DEX subgraphs, and documented issuer APIs—avoiding risky scraping of authenticated portals.

## Problem Statement

- Tokenized RWAs have $2.42B+ in TVL but only 85 holders on flagship products (BUIDL)
- Bid-ask spreads on private credit tokens reach 10-20%
- No unified view across platforms—investors manually check 5+ interfaces
- Real estate tokens (RealT) trade once per year on average

## MVP Value Proposition

- Single dashboard showing best bid/ask across all venues
- Email alerts when spreads narrow below configurable threshold (default 2%)
- Click-through to execute on best venue
- 2-week delivery timeline for functional MVP

---

# User Stories

The following user stories define the core functionality of the MVP. Each story follows the format: As a [persona], I want [action], so that [outcome]. Acceptance criteria specify the conditions for story completion.

## Primary Personas

| Persona | Description | Primary Goals |
|---------|-------------|---------------|
| Treasury Manager | Corporate treasury professional managing cash reserves and yield-bearing instruments | Maximize yield on idle cash while maintaining liquidity access |
| PE Fund CFO | Chief Financial Officer at private equity firm with allocation to tokenized assets | Best execution on large trades, minimize slippage |
| RIA/Wealth Manager | Registered Investment Advisor allocating client funds to tokenized securities | Demonstrate best execution compliance to clients |

## Epic 1: Price Discovery

### US-001: View Aggregated Prices

*As a Treasury Manager, I want to see real-time prices for a tokenized asset across all available venues, so that I can identify the best execution opportunity without manually checking each platform.*

**Acceptance Criteria:**

1. Dashboard displays bid price, ask price, spread, and volume for each venue
2. Best bid is highlighted in green, best ask is highlighted in green
3. Prices refresh automatically every 10-30 seconds
4. Last update timestamp visible for each venue
5. Token selector dropdown allows switching between supported assets

### US-002: Compare Market Depth

*As a PE Fund CFO, I want to see available liquidity depth at each venue, so that I can assess whether a venue can handle my trade size without significant slippage.*

**Acceptance Criteria:**

1. Display available volume at best bid/ask where API provides it
2. Show estimated slippage for user-entered trade sizes ($10K, $100K, $1M)
3. Indicate 'Depth Unavailable' if API doesn't provide order book data

### US-003: Filter by Asset Type

*As a Wealth Manager, I want to filter the dashboard by asset category (T-Bills, Private Credit, Real Estate), so that I can focus on asset classes relevant to my client portfolios.*

**Acceptance Criteria:**

1. Category filter buttons: All, T-Bills/Money Market, Private Credit, Real Estate, Equities
2. Selected filter persists during session
3. Token count shown per category

## Epic 2: Alerts & Notifications

### US-004: Set Spread Alert

*As a Treasury Manager, I want to receive an email alert when the bid-ask spread for a specific token narrows below my threshold, so that I can execute trades at optimal times without constant monitoring.*

**Acceptance Criteria:**

1. Alert subscription form: email, token, spread threshold (default 2%)
2. Alert triggers when spread crosses from above to below threshold
3. Email includes: token name, current spread, best bid venue, best ask venue, direct links
4. Cooldown period of 1 hour to prevent alert spam
5. User can manage (view/delete) active alerts

### US-005: Daily Summary Report

*As a PE Fund CFO, I want to receive a daily email summary of spread trends for my watched tokens, so that I can identify patterns and plan trade timing.*

**Acceptance Criteria:**

1. Daily email sent at configurable time (default 8:00 AM user timezone)
2. Includes: average spread, min spread, max spread, best execution window
3. User can select which tokens to include in summary

---

# UX Definitions

## Design Philosophy

The interface follows a 'professional trading terminal' aesthetic without the complexity. Target users are finance professionals who value clarity, information density, and fast decision-making. The design prioritizes: data visibility over decoration, clear visual hierarchy highlighting actionable information, and minimal clicks to key actions.

## Color Palette

| Element | Color Code | Usage |
|---------|------------|-------|
| Background | #0F172A (Slate 950) | Main page background—dark theme for reduced eye strain |
| Card Background | #1E293B (Slate 800) | Cards, panels, table containers |
| Best Price Highlight | #22C55E (Green 500) | Best bid/ask indicators, positive spreads |
| Warning | #F59E0B (Amber 500) | Stale data warnings, moderate spreads |
| Primary Action | #6366F1 (Indigo 500) | Buttons, links, selected state |

## Screen Definitions

### Screen 1: Main Dashboard

**Layout Structure:**

- Header Bar: Logo/title left, token selector dropdown center, settings icon right
- KPI Cards Row: Three cards showing Best Bid (price + venue), Best Ask (price + venue), Current Spread (%)
- Price Table: Full-width table with columns: Venue, Bid, Ask, Spread, Volume, Last Updated
- Action Row: 'Set Alert' button, 'Export CSV' button

**Interaction Behaviors:**

- Token selector: On change, table refreshes with new token data (no page reload via HTMX)
- Auto-refresh: Price table polls every 10 seconds, timestamp updates
- Row hover: Subtle highlight, shows 'Trade on [Venue]' button
- Click 'Trade on [Venue]': Opens venue's trading page in new tab

### Screen 2: Alert Configuration

**Modal Dialog Contents:**

- Email input field (pre-filled if user previously subscribed)
- Token selector (pre-selected with current dashboard token)
- Spread threshold slider: 0.5% to 10%, step 0.5%
- Alert type: 'Spread crosses below threshold' (checked), 'Daily summary' (optional)
- Submit button: 'Create Alert'

### Screen 3: My Alerts

**Table Columns:**

- Token, Threshold, Created Date, Last Triggered, Status (Active/Paused), Actions (Edit/Delete)

## Wireframe: Main Dashboard

The following ASCII wireframe illustrates the main dashboard layout:

```
┌─────────────────────────────────────────────────────────────────┐
│  RWA Best Price    [ Select Token ▼ ]              ⚙️ Settings │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │ BEST BID     │ │ BEST ASK     │ │ SPREAD       │            │
│ │ $1.0012      │ │ $1.0018      │ │ 0.06%        │            │
│ │ Kraken       │ │ Ondo Markets │ │ 3 venues     │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│ Order Book Snapshot — USDY              Auto-refresh: 10s      │
├──────────┬──────────┬──────────┬────────┬──────────────────────┤
│ Venue    │ Bid      │ Ask      │ Spread │ Last Updated         │
├──────────┼──────────┼──────────┼────────┼──────────────────────┤
│ Kraken   │ $1.0012* │ $1.0020  │ 0.08%  │ 2 seconds ago        │
│ Ondo GM  │ $1.0008  │ $1.0018* │ 0.10%  │ 5 seconds ago        │
│ Uniswap  │ $1.0005  │ $1.0025  │ 0.20%  │ 12 seconds ago       │
└──────────┴──────────┴──────────┴────────┴──────────────────────┘
│                    [🔔 Set Alert]    [📊 Export CSV]           │
└─────────────────────────────────────────────────────────────────┘
```

*\* indicates best price in column*

---

# Technical Architecture

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Backend Framework | FastAPI (Python) | Async-native, excellent for I/O-bound data fetching |
| Database | PostgreSQL + Redis | Postgres for persistence, Redis for real-time price cache |
| Frontend | Django Templates + HTMX + Tailwind | Server-rendered, minimal JS, modern look |
| Task Queue | Celery + Redis | Background price fetching, alert checking |
| Email Service | SendGrid API | Reliable transactional email, good free tier |
| Hosting | Railway / Render | Fast deployment, managed Postgres + Redis included |

## System Architecture Diagram

The system follows a data aggregation pipeline pattern:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                 │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐        │
│  │ Kraken │  │Coinbase│  │Uniswap │  │  Ondo  │  │ MANTRA │        │
│  │  API   │  │  API   │  │Subgraph│  │  API   │  │  DEX   │        │
│  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘        │
│      │          │          │          │          │                │
│      └──────────┴────┬─────┴──────────┴──────────┘                │
│                      ▼                                            │
│            ┌─────────────────────┐                                │
│            │   PRICE FETCHER     │  ← Celery Beat (every 10-30s)  │
│            │   (Async Workers)   │                                │
│            └─────────┬───────────┘                                │
│                      │                                            │
│         ┌────────────┼────────────┐                               │
│         ▼            ▼            ▼                               │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐                          │
│    │  Redis  │  │Postgres │  │  Alert  │                          │
│    │ (Cache) │  │(History)│  │ Checker │→ SendGrid → Email        │
│    └────┬────┘  └─────────┘  └─────────┘                          │
│         │                                                         │
│         ▼                                                         │
│    ┌─────────────────────┐                                        │
│    │    FastAPI/Django   │                                        │
│    │    Web Application  │                                        │
│    └─────────┬───────────┘                                        │
│              │ HTMX partial updates                               │
│              ▼                                                    │
│    ┌─────────────────────┐                                        │
│    │   User's Browser    │                                        │
│    └─────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Database Schema

Core tables for MVP:

```sql
-- tokens: Master list of supported RWA tokens
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50), -- 'tbill', 'private_credit', 'real_estate'
    issuer VARCHAR(100),
    chain VARCHAR(50),
    contract_address VARCHAR(66),
    is_active BOOLEAN DEFAULT true
);

-- venues: Trading platforms/exchanges
CREATE TABLE venues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    venue_type VARCHAR(20), -- 'cex', 'dex', 'issuer'
    api_type VARCHAR(20), -- 'rest', 'websocket', 'subgraph'
    base_url VARCHAR(255),
    trade_url_template VARCHAR(255) -- for click-through
);

-- price_snapshots: Historical price records
CREATE TABLE price_snapshots (
    id BIGSERIAL PRIMARY KEY,
    token_id INTEGER REFERENCES tokens(id),
    venue_id INTEGER REFERENCES venues(id),
    bid DECIMAL(20, 8),
    ask DECIMAL(20, 8),
    mid DECIMAL(20, 8),
    spread_pct DECIMAL(10, 4),
    volume_24h DECIMAL(20, 2),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- alerts: User alert subscriptions
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    token_id INTEGER REFERENCES tokens(id),
    threshold_pct DECIMAL(5, 2) DEFAULT 2.00,
    alert_type VARCHAR(20) DEFAULT 'spread_below',
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

# Data Acquisition Strategy

This section outlines the safe, compliant approach to obtaining price data from RWA platforms. The strategy prioritizes official APIs and on-chain data over web scraping, ensuring legal compliance and system stability.

## Data Source Hierarchy

Always pursue data sources in this order of preference:

- **Tier 1 (Preferred):** Official REST/WebSocket APIs with documented endpoints
- **Tier 2 (Good):** On-chain data via subgraphs (The Graph) or direct RPC calls
- **Tier 3 (Acceptable):** Aggregator APIs (CoinGecko, RWA.xyz) for supplementary data
- **Tier 4 (Last Resort):** Public webpage JSON endpoints (network tab inspection)
- **AVOID:** Scraping HTML, bypassing authentication, violating ToS

## Venue-by-Venue Analysis

### 1. Centralized Exchanges (CEXs)

| Exchange | API Availability | Data Accessible | Implementation Notes |
|----------|------------------|-----------------|----------------------|
| Kraken | Public REST API, no auth required for market data | Bid/Ask, 24h volume, order book depth | Rate limit: 1 req/sec. USDY listed. |
| Coinbase | Public REST API (Coinbase Exchange) | Ticker, order book, trades | Check BENJI/Franklin availability. |
| Gate.io | Public REST API | Full order book, ticker data | Lists several RWA tokens. |

**Implementation Pattern (Kraken example):**

```python
import httpx

async def fetch_kraken_price(pair: str = 'USDYUSD'):
    async with httpx.AsyncClient() as client:
        r = await client.get(f'https://api.kraken.com/0/public/Ticker?pair={pair}')
        data = r.json()['result'][pair]
        return {'bid': data['b'][0], 'ask': data['a'][0], 'volume': data['v'][1]}
```

### 2. Decentralized Exchanges (DEXs)

| DEX | Data Access Method | Data Accessible | Implementation Notes |
|-----|-------------------|-----------------|----------------------|
| Uniswap V3 | The Graph Subgraph (hosted or decentralized) | Pool prices, liquidity, TVL, swap history | Query pool by token addresses. Calculate implied price from sqrtPriceX96. |
| Curve | Subgraph + direct RPC | Pool balances, virtual prices | Good for stablecoin RWAs. |
| MANTRA DEX | Chain RPC + likely subgraph | Order book, pool data | RWA-focused chain; check docs at mantrachain.io |

**Implementation Pattern (Uniswap Subgraph):**

```python
UNISWAP_SUBGRAPH = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3'

query = '''
{ pool(id: "0x...") { token0Price token1Price liquidity sqrtPrice } }
'''
```

### 3. RWA Issuer Platforms

| Platform | API Status | Access Strategy | Legal Considerations |
|----------|------------|-----------------|----------------------|
| Ondo Finance | Ondo Global Markets advertises API access | Request API access via business development contact | May require partnership agreement |
| Securitize | Building MCP server for programmatic access (announced Oct 2025) | Monitor for public MCP release; contact BD for early access | Securities platform—prices likely KYC-gated |
| Franklin Templeton | BENJI on-chain; app likely internal | Use CEX/DEX prices for BENJI token; NAV from public filings | NAV publicly disclosed; secondary market via exchanges |

## Compliance & Legal Framework

### Mandatory Checks Before Adding Data Source

- **Review Terms of Service:** Search for 'automated access', 'scraping', 'data use'
- **Check robots.txt:** Respect disallow directives
- **Verify authentication requirements:** Never bypass login/KYC walls
- **Document API usage rights:** Save evidence of public API documentation
- **Rate limit compliance:** Implement exponential backoff, respect stated limits

### Red Lines (Never Cross)

- Do NOT access data behind authentication without explicit API credentials
- Do NOT scrape KYC-gated securities platforms (Securitize, etc.)
- Do NOT redistribute raw data as your own product
- Do NOT circumvent rate limits with rotating proxies/IPs
- Do NOT store personal data from platforms without consent

## MVP Token Selection

Start with 3-5 tokens that have verified public API availability:

| Token | Issuer | Category | Primary Venue | API Confidence |
|-------|--------|----------|---------------|----------------|
| USDY | Ondo Finance | T-Bill Yield Token | Kraken, DEXs | HIGH |
| BENJI | Franklin Templeton | Gov Money Fund | Coinbase, DEXs | HIGH |
| OUSG | Ondo Finance | Short-term Treasuries | Uniswap, Curve | HIGH |
| BUIDL | BlackRock/Securitize | Tokenized Fund | Securitize (KYC) | LOW (Phase 2) |

---

# Functional Specifications

## F-001: Price Aggregation Engine

**Description:**

The price aggregation engine fetches, normalizes, and stores price data from multiple venues on a configurable schedule.

**Functional Requirements:**

- **F-001.1:** System shall fetch prices from all configured venues every 10-30 seconds
- **F-001.2:** System shall normalize all prices to a common schema: {token, venue, bid, ask, mid, spread_pct, volume, timestamp}
- **F-001.3:** System shall store latest snapshot in Redis (TTL: 60 seconds)
- **F-001.4:** System shall persist all snapshots to PostgreSQL for historical analysis
- **F-001.5:** System shall handle venue API failures gracefully (mark venue as 'stale' after 3 consecutive failures)
- **F-001.6:** System shall calculate spread as: (ask - bid) / mid * 100

## F-002: Best Price Calculation

**Functional Requirements:**

- **F-002.1:** System shall identify best bid as highest bid across all venues with data < 60 seconds old
- **F-002.2:** System shall identify best ask as lowest ask across all venues with data < 60 seconds old
- **F-002.3:** System shall calculate effective spread as: (best_ask - best_bid) / ((best_ask + best_bid) / 2) * 100
- **F-002.4:** System shall exclude venues with 'stale' status from best price calculation

## F-003: Alert System

**Functional Requirements:**

- **F-003.1:** User shall be able to create alert with: email, token, spread threshold (0.5%-10%)
- **F-003.2:** System shall check alert conditions every 5 minutes via background job
- **F-003.3:** Alert triggers when: current_spread < threshold AND previous_spread >= threshold
- **F-003.4:** System shall enforce 1-hour cooldown between alerts for same token/email
- **F-003.5:** Alert email shall include: token, current spread, best bid venue/price, best ask venue/price, links to trade
- **F-003.6:** User shall be able to view, pause, and delete their alerts

## F-004: Dashboard Display

**Functional Requirements:**

- **F-004.1:** Dashboard shall display token selector dropdown with all active tokens
- **F-004.2:** Dashboard shall display KPI cards: Best Bid (price + venue), Best Ask (price + venue), Spread %
- **F-004.3:** Dashboard shall display venue table with columns: Venue, Bid, Ask, Spread, Volume, Last Updated
- **F-004.4:** Best prices in table shall be highlighted with green background
- **F-004.5:** Table shall auto-refresh every 10 seconds via HTMX without full page reload
- **F-004.6:** Venue rows shall include click-through link to trading platform

---

# API Specifications

## Internal API Endpoints

### GET /api/prices/{token_symbol}

Returns aggregated price data for a specific token.

**Response Schema:**

```json
{
  "token": "USDY",
  "best_bid": { "price": "1.0012", "venue": "Kraken" },
  "best_ask": { "price": "1.0018", "venue": "Ondo" },
  "spread_pct": "0.06",
  "venues": [
    {
      "name": "Kraken",
      "bid": "1.0012",
      "ask": "1.0020",
      "spread_pct": "0.08",
      "volume_24h": "1250000",
      "updated_at": "2025-12-07T10:30:00Z",
      "status": "live"
    }
  ],
  "fetched_at": "2025-12-07T10:30:05Z"
}
```

### POST /api/alerts

Creates a new price alert subscription.

**Request Body:**

```json
{
  "email": "user@example.com",
  "token": "USDY",
  "threshold_pct": 2.0
}
```

**Response:**

```json
{
  "id": 123,
  "status": "active",
  "created_at": "2025-12-07T10:35:00Z"
}
```

### GET /api/tokens

Returns list of all supported tokens.

**Response:**

```json
[
  {
    "symbol": "USDY",
    "name": "Ondo US Dollar Yield",
    "category": "tbill",
    "issuer": "Ondo Finance"
  },
  {
    "symbol": "BENJI",
    "name": "Franklin OnChain US Gov Money Fund",
    "category": "tbill",
    "issuer": "Franklin Templeton"
  }
]
```

---

# Implementation Roadmap

## Phase 1: MVP (Weeks 1-2)

| Day | Tasks | Deliverable | Owner |
|-----|-------|-------------|-------|
| 1-2 | Setup project structure, database schema, deploy to Railway | Dev environment ready | Developer |
| 3-4 | Implement Kraken + Coinbase API fetchers, normalize schema | 2 CEX integrations | Developer |
| 5-6 | Implement Uniswap subgraph integration, add USDY + OUSG pools | DEX integration | Developer |
| 7-8 | Build dashboard UI with HTMX auto-refresh, token selector | Working dashboard | Developer |
| 9-10 | Implement alert system: subscription form, Celery checker, SendGrid | Email alerts live | Developer |
| 11-12 | Testing, bug fixes, UI polish, documentation | MVP ready for demo | Developer |

## Phase 2: Expansion (Weeks 3-6)

- Add 5+ additional tokens (BUIDL pending Securitize MCP, real estate tokens)
- Implement MANTRA DEX integration
- Add user accounts (simple email-based auth)
- Historical spread charts (7-day, 30-day)
- Daily summary emails

## Phase 3: Monetization (Weeks 7-12)

- API access tier for institutional clients
- Partnership discussions with Ondo, Securitize for official data feeds
- Order routing integration (requires brokerage/compliance work)
- Revenue model: 2-5 bps per routed trade

---

# Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API access revoked by venue | Medium | Loss of price data for that venue | Maintain 5+ data sources; build relationships with issuers |
| Legal challenge on data aggregation | Low | Cease and desist, potential shutdown | Only use documented public APIs; document ToS compliance |
| Stale/inaccurate price data | Medium | User makes bad trade decision | Clear staleness indicators; disclaimers; multiple source validation |
| Low user adoption | Medium | No revenue; wasted effort | Validate demand with 10 treasury desk interviews before Phase 2 |
| Regulatory classification as broker/advisor | Low | Compliance burden; registration required | Phase 1 is information only; consult securities attorney before order routing |

---

# Appendix A: Glossary

| Term | Definition |
|------|------------|
| RWA | Real-World Asset – a tokenized representation of physical or financial assets on blockchain |
| Bid-Ask Spread | Difference between highest buy price (bid) and lowest sell price (ask); measure of liquidity |
| CEX | Centralized Exchange – traditional exchange with order book (Kraken, Coinbase) |
| DEX | Decentralized Exchange – blockchain-native exchange using AMM or order book (Uniswap, Curve) |
| Subgraph | Indexed blockchain data accessible via GraphQL (The Graph protocol) |
| MCP | Model Context Protocol – Anthropic's standard for AI-to-service integration; Securitize building one |
| HTMX | JavaScript library for AJAX requests via HTML attributes; enables SPA-like UX without React |

---

# Appendix B: Reference Links

- Ondo Finance: https://ondo.finance/
- Securitize MCP Announcement: https://www.coindesk.com/tech/2025/10/22/securitize-unveils-mcp-server
- MANTRA Chain: https://mantrachain.io/
- RWA.xyz Analytics: https://app.rwa.xyz/
- Kraken API Docs: https://docs.kraken.com/rest/
- Uniswap V3 Subgraph: https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3
- HTMX Documentation: https://htmx.org/docs/
- Tailwind CSS: https://tailwindcss.com/

---

*— End of Document —*
