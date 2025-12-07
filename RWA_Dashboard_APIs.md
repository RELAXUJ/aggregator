# RWA Tokenization Dashboard - API Integration Guide

**December 7, 2025 | For Solo Founder MicroSaaS**

This document consolidates API documentation for building a **Secondary Market Liquidity Aggregator for Tokenized Assets** across multiple platforms and data sources.

---

## 📊 Architecture Overview

Your dashboard will aggregate pricing and liquidity data from:

1. **Centralized Exchanges**: Kraken, Coinbase (for native crypto pairs)
2. **DEX Protocols**: Uniswap Subgraph (liquidity pools)
3. **RWA Platforms**: Ondo, Mantra DEX (tokenized asset pools)
4. **Data Layer**: The Graph (on-chain data via GraphQL)

---

## 1. KRAKEN REST API

### Base URL
```
https://api.kraken.com/0/
```

### Authentication
- **Public endpoints**: No authentication required
- **Private endpoints**: HMAC-SHA256 signature required
- **Rate Limits**: 
  - Public: 1 request/second
  - Private: 15-20 requests/minute

### Key Market Data Endpoints

#### Get Ticker Information
```
GET /0/public/Ticker?pair=XXBTZUSD

Response:
{
  "error": [],
  "result": {
    "XXBTZUSD": {
      "a": ["50000.00", "0"],
      "b": ["49999.00", "1"],
      "c": ["49999.50", "1.5"],
      "v": ["1234.5678", "5678.1234"],
      "p": ["49900.00", "49900.00"],
      "t": [123, 456],
      "l": ["49500.00", "49600.00"],
      "h": ["50200.00", "50300.00"],
      "o": "49800.00"
    }
  }
}
```

**Key fields for dashboard:**
- `a`: Ask (best offer to sell) [price, lot volume]
- `b`: Bid (best offer to buy) [price, lot volume]
- `c`: Last trade close [price, lot volume]
- `v`: Volume [today, 24h]
- `p`: VWAP (volume-weighted avg price) [today, 24h]
- `l`: Low [today, 24h]
- `h`: High [today, 24h]

#### Get Order Book
```
GET /0/public/Depth?pair=XXBTZUSD&count=20

Response:
{
  "error": [],
  "result": {
    "XXBTZUSD": {
      "asks": [
        ["50000.00", "1.5"],
        ["50001.00", "2.0"]
      ],
      "bids": [
        ["49999.00", "1.0"],
        ["49998.00", "1.5"]
      ]
    }
  }
}
```

#### Get OHLC (Candlestick) Data
```
GET /0/public/OHLC?pair=XXBTZUSD&interval=60

Response:
{
  "error": [],
  "result": {
    "XXBTZUSD": [
      [1641801600, "49000.00", "50000.00", "49500.00", "49800.00", "50000.00", "100.5678", 50],
      // [time, open, high, low, close, vwap, volume, count]
    ]
  }
}
```

#### Get Recent Trades
```
GET /0/public/Trades?pair=XXBTZUSD

Response:
{
  "error": [],
  "result": {
    "XXBTZUSD": [
      ["49999.50", "1.5", 1641801605, "b", "m"],
      // [price, volume, time, side, type]
    ],
    "last": "1641801605"
  }
}
```

### Supported Asset Pairs for RWA Integration
- Bitcoin/USD: `XXBTZUSD` or `XBTUSD`
- Ethereum/USD: `XETHZUSD` or `ETHUSD`
- Stablecoins: `USDTZUSD`, `USDCUSD`, `EURZUSD`

---

## 2. COINBASE ADVANCED TRADE API

### Base URLs
```
Production: https://api.exchange.coinbase.com
Sandbox: https://api-public.sandbox.exchange.coinbase.com
```

### Authentication
- **Method**: HMAC-SHA256 signature + timestamp
- **Headers**:
  ```
  CB-ACCESS-KEY: your_api_key
  CB-ACCESS-SIGN: signature_base64
  CB-ACCESS-TIMESTAMP: unix_timestamp
  CB-ACCESS-PASSPHRASE: your_passphrase
  Content-Type: application/json
  ```
- **Rate Limits**: 
  - Public: 3-10 requests/second per IP
  - Private: Higher limits per API key

### Key Market Data Endpoints

#### Get All Products (Trading Pairs)
```
GET /api/v3/brokerage/products

Response:
[
  {
    "product_id": "BTC-USD",
    "price": "50000.00",
    "price_percentage_change_24h": "2.5",
    "volume_24h": "1234567890.50",
    "volume_percentage_change_24h": "5.3",
    "base_increment": "0.00000001",
    "quote_increment": "0.01",
    "display_name": "BTC/USD",
    "status": "open",
    "base_currency": "BTC",
    "quote_currency": "USD",
    "base_max_size": "10000",
    "base_min_size": "0.001",
    "quote_max_size": "500000",
    "quote_min_size": "1"
  }
]
```

#### Get Single Product
```
GET /api/v3/brokerage/products/BTC-USD

Response:
{
  "product_id": "BTC-USD",
  "price": "50000.00",
  "time": "2025-12-07T12:00:00Z",
  "trade_id": "12345",
  "bid": "49999.50",
  "ask": "50000.50",
  "volume": "1234.5678"
}
```

#### Get Product Candles (OHLCV)
```
GET /api/v3/brokerage/products/BTC-USD/candles?start=1641801600&end=1641888000&granularity=3600

Response:
{
  "candles": [
    {
      "time": "1641801600",
      "low": "49500.00",
      "high": "50200.00",
      "open": "49800.00",
      "close": "50000.00",
      "volume": "100.5678"
    }
  ]
}
```

#### Get Product Ticker (Real-time Price)
```
GET /api/v3/brokerage/products/BTC-USD/ticker

Response:
{
  "product_id": "BTC-USD",
  "price": "50000.00",
  "volume_24h": "1234567890.50",
  "volume_30d": "5000000000.00",
  "low_24h": "49500.00",
  "high_24h": "50500.00",
  "low_52w": "30000.00",
  "high_52w": "68000.00",
  "price_percent_chg_24h": "2.5"
}
```

#### Get Product Book (Order Book)
```
GET /api/v3/brokerage/products/BTC-USD/book?limit=20

Response:
{
  "pricebook": {
    "product_id": "BTC-USD",
    "bids": [
      ["49999.50", "1.5"],
      ["49999.00", "2.0"]
    ],
    "asks": [
      ["50000.00", "1.0"],
      ["50001.00", "1.5"]
    ],
    "time": "2025-12-07T12:00:00Z",
    "sequence": "12345"
  }
}
```

#### Get Trades (Recent Transactions)
```
GET /api/v3/brokerage/products/BTC-USD/trades?limit=100&before=cursor

Response:
{
  "trades": [
    {
      "trade_id": "123456",
      "product_id": "BTC-USD",
      "order_id": "order-123",
      "user_id": "user-123",
      "profile_id": "profile-123",
      "liquidity": "T",
      "price": "50000.00",
      "size": "0.001",
      "fee": "5.00",
      "created_at": "2025-12-07T12:00:00Z",
      "side": "buy"
    }
  ],
  "pagination": {
    "after": "cursor_after",
    "before": "cursor_before",
    "limit": 100
  }
}
```

### Best Practices
- Use `/api/v3` endpoints (v2 is deprecated)
- Implement exponential backoff for rate limiting
- Cache product data (~24 hours)
- Use WebSocket for real-time price feeds instead of polling

---

## 3. UNISWAP SUBGRAPH (GRAPHQL)

### Endpoints
```
Mainnet: https://api.studio.thegraph.com/query/48211/uniswap-v3/latest
Arbitrum: https://api.studio.thegraph.com/query/48211/uniswap-v3-arbitrum/latest
Polygon: https://api.studio.thegraph.com/query/48211/uniswap-v3-polygon/latest
Optimism: https://api.studio.thegraph.com/query/48211/uniswap-v3-optimism/latest
```

### Authentication
- None required (public queries)
- Rate Limits: ~1000 queries/minute

### Core Entities

#### Get All Pools
```graphql
query {
  pools(first: 100, orderBy: totalValueLockedUSD, orderDirection: desc) {
    id
    token0 {
      id
      symbol
      name
      decimals
    }
    token1 {
      id
      symbol
      name
      decimals
    }
    feeTier
    liquidity
    sqrtPrice
    tick
    txCount
    totalValueLockedToken0
    totalValueLockedToken1
    totalValueLockedUSD
    volumeUSD
    feesUSD
  }
}
```

#### Get Pool Details (for specific token pair)
```graphql
query {
  pools(where: {
    token0: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"  # USDC
    token1: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"  # WETH
  }) {
    id
    feeTier
    tick
    sqrtPrice
    liquidity
    volumeUSD
    feesUSD
    totalValueLockedUSD
    token0Price
    token1Price
  }
}
```

#### Get Recent Swaps (Track volume/liquidity)
```graphql
query {
  swaps(
    first: 100
    orderBy: timestamp
    orderDirection: desc
    where: {
      pool: "0x8ad599c3a0ff1de082011efddc58f1908762f2f7"  # USDC/ETH pool
    }
  ) {
    id
    transaction {
      id
      timestamp
    }
    timestamp
    pool {
      token0 { symbol }
      token1 { symbol }
    }
    origin
    amount0
    amount1
    amountUSD
    tick
    sqrtPriceX96
    logIndex
  }
}
```

#### Get Liquidity Providers (Track LP positions)
```graphql
query {
  positions(
    first: 100
    orderBy: liquidity
    orderDirection: desc
    where: {
      pool: "0x8ad599c3a0ff1de082011efddc58f1908762f2f7"
    }
  ) {
    id
    owner
    pool {
      token0 { symbol }
      token1 { symbol }
    }
    tickLower
    tickUpper
    liquidity
    feeGrowthInside0LastX128
    feeGrowthInside1LastX128
    tokensOwed0
    tokensOwed1
    transaction {
      timestamp
    }
  }
}
```

#### Get Hourly Pool Stats
```graphql
query {
  poolHourDatas(
    first: 100
    orderBy: periodStartUnix
    orderDirection: desc
    where: {
      pool: "0x8ad599c3a0ff1de082011efddc58f1908762f2f7"
    }
  ) {
    periodStartUnix
    pool {
      token0 { symbol }
      token1 { symbol }
    }
    high
    low
    open
    close
    volumeToken0
    volumeToken1
    volumeUSD
    feesUSD
    tvlUSD
    txCount
  }
}
```

### Response Format (Example: Pool Data)
```json
{
  "data": {
    "pools": [
      {
        "id": "0x8ad599c3a0ff1de082011efddc58f1908762f2f7",
        "token0": {
          "id": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
          "symbol": "USDC",
          "decimals": "6"
        },
        "token1": {
          "id": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
          "symbol": "WETH",
          "decimals": "18"
        },
        "feeTier": "3000",
        "totalValueLockedUSD": "1234567890.50",
        "volumeUSD": "567890123.45",
        "feesUSD": "1234567.89"
      }
    ]
  }
}
```

---

## 4. ONDO FINANCE API

### Base URL
```
https://api.ondo.finance/
```

### Key Data Points

#### Get Fund Information
```
GET /api/funds

Response:
{
  "funds": [
    {
      "id": "buidl",
      "name": "ONDO USD Institutional Digital Liquidity Fund",
      "symbol": "BUIDL",
      "chainId": 1,
      "tokenAddress": "0x...",
      "issuedShares": "2900000000",
      "nav": "2900000000.00",
      "navPerShare": "1.00",
      "totalAUM": "2900000000.00",
      "inception_date": "2024-03-01",
      "status": "active",
      "description": "Short-term US Treasury holdings"
    }
  ]
}
```

#### Get Fund Performance
```
GET /api/funds/{fund_id}/performance

Response:
{
  "fund_id": "buidl",
  "yields": {
    "apy": "5.25",
    "ytd": "4.80",
    "month_1": "0.45",
    "month_3": "1.35"
  },
  "aum_history": [
    { "date": "2025-12-07", "aum": "2900000000.00" },
    { "date": "2025-12-06", "aum": "2895000000.00" }
  ]
}
```

#### Get Fund Holdings
```
GET /api/funds/{fund_id}/holdings

Response:
{
  "fund_id": "buidl",
  "holdings": [
    {
      "asset": "US Treasury 3M",
      "quantity": "1000000000",
      "weight": "35%",
      "yieldPercent": "5.25"
    },
    {
      "asset": "US Treasury 6M",
      "quantity": "1200000000",
      "weight": "42%",
      "yieldPercent": "5.35"
    },
    {
      "asset": "Cash",
      "quantity": "700000000",
      "weight": "23%",
      "yieldPercent": "5.20"
    }
  ]
}
```

#### Get Fund Holders / Token Distribution
```
GET /api/funds/{fund_id}/holders?limit=100

Response:
{
  "fund_id": "buidl",
  "total_holders": 85,
  "top_holders": [
    {
      "address": "0x...",
      "shares": "500000000",
      "percentage": "17.24%"
    }
  ]
}
```

#### Get Fund Redemptions/Subscriptions
```
GET /api/funds/{fund_id}/transactions?type=redemption&limit=50

Response:
{
  "transactions": [
    {
      "type": "redemption",
      "timestamp": "2025-12-07T10:30:00Z",
      "investor": "0x...",
      "amount": "1000000",
      "nav_per_share": "1.00",
      "status": "pending"
    }
  ]
}
```

### Dashboard Integration Points
- **Nav Per Share**: Real-time valuation
- **Total AUM**: Market size per fund
- **Yields**: APY for comparison
- **Holdings**: Asset breakdown (transparency)
- **Holders**: Concentration analysis

---

## 5. MANTRA DEX API (RWA-focused)

### Base URL / Network
```
Chain ID: Mantra Chain
RPC: https://mantra-mainnet.rpc.allthatnode.com:8545
```

### Pool Manager Contract Interactions

#### Query All Pools
```
Smart Contract Query: Pool Manager
Method: pools

Response (Simulation):
{
  "pools": [
    {
      "pool_identifier": "om-usdc-1",
      "asset_denoms": ["uom", "uusdc"],
      "lp_denom": "uom_uusdc_lp",
      "assets": [
        { "denom": "uom", "amount": "1000000" },
        { "denom": "uusdc", "amount": "1000000" }
      ],
      "pool_type": "constant_product",
      "pool_fees": {
        "protocol_fee": "0.001",
        "swap_fee": "0.002",
        "burn_fee": "0"
      },
      "total_share": { "denom": "uom_uusdc_lp", "amount": "1000000" }
    }
  ]
}
```

#### Simulate Swap (Price Discovery)
```
Smart Contract Query: Pool Manager
Method: simulation
Params: {
  "offer_asset": { "denom": "uom", "amount": "1000000" },
  "ask_asset_denom": "uusdc",
  "pool_identifier": "om-usdc-1"
}

Response:
{
  "return_amount": "990000",
  "spread_amount": "5000",
  "swap_fee_amount": "3000",
  "protocol_fee_amount": "2000"
}
```

#### Query Pool TVL/Liquidity
```
Smart Contract Query: Pool Manager
Method: pools
Param: pool_identifier = "om-usdc-1"

Response:
{
  "pool_identifier": "om-usdc-1",
  "assets": [
    { "denom": "uom", "amount": "5000000000" },
    { "denom": "uusdc", "amount": "4950000000" }
  ],
  "total_value_usd": "9950000000",  # Calculated from prices
  "total_share": { "amount": "4975000000" }
}
```

### Dashboard Integration
- **Pool Liquidity**: TVL across pools
- **Bid-Ask Spreads**: From swap simulation
- **Trading Fees**: Protocol + swap fees comparison
- **LP APY**: Estimated returns (fees / TVL)

---

## 6. THE GRAPH - SUBGRAPH DATA QUERIES (Generic)

### Generic Pattern for Any Subgraph
```graphql
# Example: Query any token/pool data
query {
  tokens(first: 100, orderBy: volumeUSD, orderDirection: desc) {
    id
    symbol
    name
    decimals
    totalSupply
    volumeUSD
    txCount
  }
}

# Example: Get transactions with timestamps
query {
  transactions(
    first: 100
    orderBy: timestamp
    orderDirection: desc
  ) {
    id
    timestamp
    blockNumber
    gasUsed
    gasPrice
  }
}
```

---

## 7. IMPLEMENTATION PATTERNS FOR YOUR DASHBOARD

### Pattern 1: Real-time Price Aggregation
```
1. Query Kraken Ticker (1 req/sec)
   ↓ Extract bid/ask
2. Query Coinbase Product (parallel)
   ↓ Extract bid/ask
3. Query Uniswap Subgraph (parallel)
   ↓ Calculate mid-price from liquidity
4. Aggregate into single data structure
   ↓
5. Calculate best execution prices
   ↓
6. Alert if spreads narrow <2%
```

### Pattern 2: Liquidity Aggregation
```
1. Query Kraken Depth (get order book)
   ↓ Extract bids/asks at levels
2. Query Coinbase Book (parallel)
3. Query Uniswap Pool Data (parallel)
4. Query Mantra DEX Pools (parallel)
   ↓
5. Merge order books by price level
   ↓
6. Calculate cumulative liquidity at each price
   ↓
7. Display liquidity islands + fragmentation analysis
```

### Pattern 3: Volume Tracking (for liquidity analysis)
```
1. Query Kraken recent trades (1000/call)
   ↓ Sum volume by pair
2. Query Coinbase trades (parallel)
3. Query Uniswap swaps via subgraph
4. Query Mantra DEX swap simulations
   ↓
5. Normalize by asset decimals
   ↓
6. Calculate 24h volume across venues
   ↓
7. Identify which venue has best liquidity
```

### Pattern 4: Yield/Return Calculation
```
For Ondo/RWA funds:
1. Get Fund NAV + APY
2. Get Holdings breakdown
3. Get Historical NAV (30 days)
   ↓
4. Calculate:
   - Daily yield realized
   - Annualized return
   - Performance vs benchmark (3M Treasury)
   ↓
5. Compare across multiple funds
```

---

## 8. RATE LIMITS & OPTIMIZATION STRATEGIES

| Source | Limit | Strategy |
|--------|-------|----------|
| **Kraken** | 1/sec public, 15-20/min private | Queue with 1-sec delay |
| **Coinbase** | 3-10/sec public | Batch requests, cache |
| **Uniswap Subgraph** | ~1000/min | Batch GraphQL queries |
| **Ondo API** | Not public | Cache fund data 1hr |
| **Mantra RPC** | Typical node limits | Use public RPC, cache |

### Caching Strategy
```
- Ticker data: 5-15 sec cache
- Order book: 2-5 sec cache
- Historical OHLC: 1 hour cache
- Fund holdings: 24 hour cache
- Pool liquidity: 30 sec cache
```

### Batch Query Pattern (GraphQL)
```graphql
# Query multiple entities in single request
query {
  pools1: pools(first: 100, where: { id: "id1" }) { ... }
  pools2: pools(first: 100, where: { id: "id2" }) { ... }
  swaps: swaps(first: 50, orderBy: timestamp) { ... }
}
```

---

## 9. ERROR HANDLING & FALLBACK LOGIC

```javascript
// Pseudo-code for robust aggregation

async function getPrices() {
  try {
    // Attempt primary source
    const krakenPrice = await krakenAPI.getTicker();
    return krakenPrice;
  } catch (err) {
    // Fallback to secondary
    try {
      const cbPrice = await coinbaseAPI.getTicker();
      return cbPrice;
    } catch (err2) {
      // Fallback to subgraph
      const uniPrice = await uniswapSubgraph.getPrice();
      return uniPrice;
    }
  }
}
```

---

## 10. QUICK REFERENCE: Key Data Points for Dashboard

| Metric | Source | Update Freq | Purpose |
|--------|--------|-------------|---------|
| **Best Bid/Ask** | Kraken, Coinbase, Uniswap | 1-5 sec | Execution pricing |
| **Order Book Depth** | Kraken, Coinbase | 2-5 sec | Liquidity analysis |
| **24h Volume** | Kraken, Coinbase, Uniswap | 1 min | Market activity |
| **Fund NAV** | Ondo | 1 hour | Valuation |
| **Pool Liquidity** | Mantra, Uniswap | 30 sec | Trading impact |
| **Spread Analysis** | All sources | Real-time | Best execution |
| **APY/Yields** | Ondo, Mantra LP rewards | 1 hour | Return comparison |

---

## 11. EXAMPLE DASHBOARD DATA STRUCTURE

```json
{
  "aggregated_prices": {
    "BTC-USD": {
      "kraken": { "bid": 49999.50, "ask": 50000.50 },
      "coinbase": { "bid": 49999.00, "ask": 50001.00 },
      "uniswap": { "mid": 50000.25 }
    },
    "BUIDL": {
      "nav_per_share": 1.00,
      "ondo_market": { "bid": 0.999, "ask": 1.001 },
      "uniswap_if_tradable": null
    }
  },
  "liquidity_aggregation": {
    "order_book": {
      "bids": [
        { "price": 50000.00, "size": 10, "venue": "kraken" },
        { "price": 49999.50, "size": 15, "venue": "uniswap_pool" }
      ],
      "asks": [
        { "price": 50001.00, "size": 8, "venue": "coinbase" },
        { "price": 50000.50, "size": 12, "venue": "kraken" }
      ]
    }
  },
  "market_stats": {
    "spread_bps": 10,  # bid-ask in basis points
    "best_execution": {
      "buy_at": { "price": 50000.00, "venue": "kraken" },
      "sell_at": { "price": 50001.00, "venue": "coinbase" }
    }
  }
}
```

---

## 12. NEXT STEPS FOR MVP

1. **Week 1**: Set up Kraken + Coinbase API clients
2. **Week 2**: Integrate Uniswap Subgraph queries
3. **Week 3**: Add Ondo fund data layer
4. **Week 4**: Build aggregation logic + dashboard UI
5. **Week 5**: Add Mantra DEX integration
6. **Week 6**: Deploy, test, launch MVP

---

**Last Updated**: December 7, 2025  
**Status**: Ready for integration  
**Estimated MVP Build Time**: 4-6 weeks solo  
**Technology Stack**: Node.js + Express + React + GraphQL client
