# Environment Configuration Example

Copy the content below to a `.env` file in the backend directory.

```bash
# RWA Liquidity Aggregator - Environment Configuration
# Copy this to .env and fill in your values

# Application
APP_ENV=development
DEBUG=true
SECRET_KEY=change-this-to-a-secure-random-string

# Database (PostgreSQL)
# Port 5433 to avoid conflict with local PostgreSQL
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/rwa_aggregator

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Price Feed Polling
PRICE_POLL_INTERVAL_SECONDS=30
STALENESS_THRESHOLD_SECONDS=300

# Alert System
ALERT_COOLDOWN_MINUTES=60
ALERT_CHECK_INTERVAL_SECONDS=300

# ============================================
# EXCHANGE API KEYS
# ============================================

# Kraken API (Public endpoints work without keys)
# For higher rate limits, get keys from https://www.kraken.com/u/security/api
KRAKEN_API_KEY=0n4zuNkwhr5XrUTSdAwFhzfMLZ+N5qPJ9U9xWKGYxtqvJ3I5ZS3BTa5J
KRAKEN_API_SECRET=u3h7e8Fmjt4k9ug9tkth463gtORTWBwjhKAMbFeAUdI25bscA0JUQjlsKJw5SKf5MKMv2SkwfkpQpi6B5ktfJA==

# Coinbase CDP API (for Coinbase Advanced Trade)
# Get keys from https://www.coinbase.com/settings/api
# Uses CDP (Coinbase Developer Platform) format
COINBASE_API_KEY=4fbb5921-3b61-4189-8d16-7ebe035e520f
COINBASE_API_SECRET=2ruLTEUbEzD1J0Y0GUd+gtq4lum/IESt5SN+nQWZ+WJ6IFf5eirfgdkSGDmoXcAd0RHGxSVTj6Rp2Qlo9SZsXA==

# ============================================
# BLOCKCHAIN / DEX CONFIGURATION
# ============================================

# Ethereum RPC URL (for direct contract calls if needed)
# Use Infura, Alchemy, or other provider
ETH_RPC_URL=https://mainnet.infura.io/v3/your_project_id

# The Graph API Key (required for Uniswap V3 subgraph)
# Get free tier (100k queries/month) from https://thegraph.com/studio/
THEGRAPH_API_KEY=37c26010270315607fc2333c3dbabe1b

# ============================================
# EMAIL ALERTS (SendGrid)
# ============================================

SENDGRID_API_KEY=
ALERT_FROM_EMAIL=alerts@yourdomain.com
```

## API Key Setup

### Kraken
1. Go to https://www.kraken.com/u/security/api
2. Create a new API key with "Query Funds" and "Query Open Orders & Trades" permissions
3. Copy the API Key and Private Key to your `.env` file

### Coinbase (CDP)
1. Go to https://portal.cdp.coinbase.com/
2. Create a new CDP API key
3. Save the JSON file - it contains `id` (key) and `privateKey` (secret)
4. Copy values to your `.env` file:
   - `COINBASE_API_KEY` = the `id` field
   - `COINBASE_API_SECRET` = the `privateKey` field

### Uniswap (via The Graph)
1. Go to https://thegraph.com/studio/
2. Sign in and create a free account
3. Get your API key from the dashboard (free tier: 100k queries/month)
4. Set `THEGRAPH_API_KEY` in your `.env` file

**Note:** Without the API key, Uniswap price feeds will not work (The Graph deprecated their free hosted service).
