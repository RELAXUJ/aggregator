# Railway Deployment Guide

## Quick Start

Railway should now detect your FastAPI app and start it correctly with the configuration files provided.

## Configuration Files Created

1. **`railway.json`** - Railway-specific configuration
2. **`Procfile`** - Fallback start command (Railway will use this if railway.json doesn't work)
3. **`runtime.txt`** - Python version specification

## Required Setup Steps

### 1. Add PostgreSQL Database

In Railway dashboard:
1. Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway will automatically set the `DATABASE_URL` environment variable
3. Your app will use this automatically via `database_url` config

### 2. Add Redis

In Railway dashboard:
1. Click **"+ New"** → **"Database"** → **"Add Redis"**
2. Railway will set `REDIS_URL` environment variable
3. Update your app's environment variables:
   - `REDIS_URL` (from Railway Redis service)
   - `CELERY_BROKER_URL` (same as REDIS_URL but with `/1` suffix)
   - `CELERY_RESULT_BACKEND` (same as REDIS_URL but with `/2` suffix)

### 3. Set Environment Variables

In your Railway service settings, add these environment variables:

#### Required:
```bash
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-a-random-secret-key>
```

#### Database (auto-set by Railway PostgreSQL):
```bash
DATABASE_URL=<auto-set-by-railway>
```

#### Redis (set manually from Railway Redis service):
```bash
REDIS_URL=<from-railway-redis-service>
CELERY_BROKER_URL=<redis-url>/1
CELERY_RESULT_BACKEND=<redis-url>/2
```

#### Optional (for email alerts):
```bash
POSTMARK_API_TOKEN=<your-postmark-server-token>
ALERT_FROM_EMAIL=alerts@yourdomain.com
```

#### Optional (for API integrations):
```bash
KRAKEN_API_KEY=<your-key>
KRAKEN_API_SECRET=<your-secret>
COINBASE_API_KEY=<your-key>
COINBASE_API_SECRET=<your-secret>
THEGRAPH_API_KEY=<your-key>
ETH_RPC_URL=<your-ethereum-rpc-url>
```

### 4. Run Database Migrations

After deployment, you need to run migrations. In Railway:

**Option A: Via Railway CLI**
```bash
railway run alembic upgrade head
```

**Option B: Via Railway Shell**
1. Open Railway dashboard → Your service → "Deployments" → Click on latest deployment
2. Click "Shell" tab
3. Run:
```bash
cd backend
alembic upgrade head
python scripts/seed_data.py
```

### 5. Start Celery Worker (Separate Service)

Railway needs a separate service for Celery workers:

1. **Duplicate your service** (or create new service from same repo)
2. **Change the start command** to:
   ```bash
   cd backend && celery -A app.rwa_aggregator.infrastructure.tasks.celery_app worker --loglevel=info
   ```
3. **Share environment variables** from main service (especially Redis URLs)

### 6. Start Celery Beat (Optional - for scheduled tasks)

If you want scheduled alert checks:

1. Create another service
2. Start command:
   ```bash
   cd backend && celery -A app.rwa_aggregator.infrastructure.tasks.celery_app beat --loglevel=info
   ```

## Service Architecture on Railway

You'll need **3-4 services**:

1. **Web Service** (FastAPI) - Handles HTTP requests
   - Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   
2. **Celery Worker** - Processes background tasks
   - Start: `cd backend && celery -A app.rwa_aggregator.infrastructure.tasks.celery_app worker --loglevel=info`
   
3. **Celery Beat** (Optional) - Schedules periodic tasks
   - Start: `cd backend && celery -A app.rwa_aggregator.infrastructure.tasks.celery_app beat --loglevel=info`

4. **PostgreSQL** - Database (Railway managed)

5. **Redis** - Cache & message broker (Railway managed)

## Troubleshooting

### Build fails with "No start command found"
- Make sure `railway.json` and `Procfile` are in the **root** directory
- Check that Railway is detecting Python correctly

### Database connection errors
- Verify `DATABASE_URL` is set correctly
- Check PostgreSQL service is running
- Run migrations: `alembic upgrade head`

### Redis connection errors
- Verify `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` are set
- Check Redis service is running
- Ensure Redis URLs include the database number (`/0`, `/1`, `/2`)

### Port binding errors
- Railway sets `$PORT` automatically - don't hardcode port 8000
- The start command uses `--port $PORT` which Railway provides

## Notes

- Railway automatically provides `$PORT` environment variable
- The `railway.json` uses `NIXPACKS` builder (Railway's default)
- If Railpack detection fails, Railway will fall back to `Procfile`
- Make sure `requirements.txt` is in the root directory (it is)
