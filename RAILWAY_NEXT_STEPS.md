# Railway Next Steps - Quick Guide

You have PostgreSQL set up! Here's exactly what to do next:

## Step 1: Connect Database to Your App Service

### Option A: Using Variable Reference (Preferred)

1. **Go to your main application service** (the one running FastAPI)
2. Click on **"Variables"** tab
3. Click **"+ New Variable"**
4. Click **"Add Reference"**
5. Select your **Postgres** service
6. Select **`DATABASE_URL`** from the dropdown
7. Click **"Add"**

**If you see "No suggestions":**
- Make sure both services are in the **same Railway project**
- Check that PostgreSQL service is **deployed/running** (green status)
- Try refreshing the page
- If still not working, use **Option B** below

### Option B: Manual DATABASE_URL (If Reference Doesn't Work)

If Variable Reference isn't working, manually copy the DATABASE_URL:

1. **Go to your PostgreSQL service** → **"Variables"** tab
2. **Copy the `DATABASE_URL` value** (it looks like: `postgresql://postgres:password@host:port/railway`)
3. **Go to your web service** → **"Variables"** tab
4. Click **"+ New Variable"**
5. Set:
   - **Variable Name:** `DATABASE_URL`
   - **Value:** Paste the copied DATABASE_URL
6. Click **"Add"**

**Important:** Make sure you're using the **internal** `DATABASE_URL` (from PostgreSQL Variables tab), not the public one. The internal one uses `postgres.railway.internal` as the host.

## Step 2: Set Required Environment Variables

In your **main application service** → **Variables** tab, add these:

### Required Variables:
```
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-random-string-here>
```

**To generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Database (already set via Variable Reference):
- `DATABASE_URL` - ✅ Automatically set when you added the reference

## Step 3: Run Database Migrations

After your app service is deployed, you need to create the tables:

### Option A: Via Railway Dashboard (Easiest)

1. Go to your **main application service**
2. Click **"Deployments"** tab
3. Click on the **latest deployment**
4. Click **"Shell"** tab (or "View Logs" → "Shell")
5. Run these commands:
   ```bash
   cd backend
   alembic upgrade head
   python scripts/seed_data.py
   ```

### Option B: Via Railway CLI

If you have Railway CLI installed:
```bash
railway link  # Link to your project
railway run --service <your-service-name> cd backend && alembic upgrade head
railway run --service <your-service-name> cd backend && python scripts/seed_data.py
```

## Step 4: Verify Database Tables

1. Go back to your **Postgres** service
2. Click **"Database"** tab
3. You should now see tables:
   - `alembic_version`
   - `tokens`
   - `venues`
   - `price_snapshots`
   - `alerts`

## Step 5: (Optional) Add Redis for Celery

If you want background tasks (price fetching, alerts):

1. In Railway dashboard, click **"+ New"** → **"Database"** → **"Add Redis"**
2. Go to your **main application service** → **Variables**
3. Add these Variable References:
   - `REDIS_URL` (from Redis service)
   - Then manually add:
     - `CELERY_BROKER_URL` = `<same-as-redis-url>/1`
     - `CELERY_RESULT_BACKEND` = `<same-as-redis-url>/2`

## Step 6: Test Your App

1. Go to your main application service
2. Click **"Settings"** tab
3. Find your **public URL** (e.g., `https://your-app.railway.app`)
4. Visit it in your browser - you should see the dashboard!

## Troubleshooting

### "No module named 'app'" error
- Make sure you're running commands from the `backend` directory
- Or use: `cd backend && alembic upgrade head`

### Database connection errors
- Verify `DATABASE_URL` Variable Reference is added correctly
- Check that both services are in the same Railway project
- Make sure PostgreSQL service is running (green status)
- If Variable Reference shows "no suggestions", manually copy `DATABASE_URL` from PostgreSQL service Variables tab

### "No suggestions" when adding Variable Reference
**Common causes:**
1. Services are in different Railway projects → Move them to the same project
2. PostgreSQL service isn't deployed yet → Wait for it to finish deploying
3. UI glitch → Try refreshing the page or using manual method (Option B above)

**Solution:** Use the manual method (Option B) - it works just as well!

### Migration errors
- Ensure `alembic.ini` is in the `backend` directory
- Check that migration files exist in `backend/app/rwa_aggregator/infrastructure/db/migrations/versions/`

## What Happens After Migrations

After running `alembic upgrade head`:
- ✅ All tables will be created
- ✅ Database schema will be ready

After running `python scripts/seed_data.py`:
- ✅ Initial tokens (PAXG, USDY, OUSG, BENJI, ETH) will be added
- ✅ Initial venues (Kraken, Coinbase, Bybit, Uniswap) will be added
- ✅ Your app will have data to display!

## Quick Checklist

- [ ] Connected PostgreSQL to app service via Variable Reference
- [ ] Set `APP_ENV=production`
- [ ] Set `DEBUG=false`
- [ ] Set `SECRET_KEY` (random string)
- [ ] Deployed app service successfully
- [ ] Ran `alembic upgrade head` in Shell
- [ ] Ran `python scripts/seed_data.py` in Shell
- [ ] Verified tables exist in Database tab
- [ ] Tested app URL in browser

Once you complete these steps, your app should be fully functional! 🚀
