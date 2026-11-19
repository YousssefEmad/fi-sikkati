# Fi Sikkati — Vercel + Neon + Upstash (no card demo)

Same pattern as Nexora: web on Vercel, API on Vercel, data on Neon, Redis on Upstash.

## 1) Neon (Postgres + PostGIS)

1. https://console.neon.tech → Sign up / Log in (GitHub OK, no card on Free)
2. Create project `fi-sikkati`
3. Open SQL Editor and run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

4. Copy the connection string (pooled is fine). Convert to asyncpg:

```
postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require
```

Use the **same** URL for `DATABASE_URL` and `MIGRATION_DATABASE_URL` on Neon.

## 2) Upstash Redis

1. https://console.upstash.com → Redis → Create database (Free)
2. Copy the Redis URL (`rediss://...`)

## 3) Migrate (from your PC)

```bash
cd apps/api
# set DATABASE_URL + MIGRATION_DATABASE_URL to the Neon asyncpg URL in the shell
uv run alembic upgrade head
```

## 4) Deploy API on Vercel

```bash
cd apps/api
vercel link   # new project: fi-sikkati-api, root = apps/api
vercel env add ...
vercel --prod
```

Required env (Production):

- `APP_ENV=staging`
- `DATABASE_URL` / `MIGRATION_DATABASE_URL` (Neon asyncpg)
- `REDIS_URL` (Upstash)
- `PUBLIC_WEB_URL=https://fi-sikkati.vercel.app`
- `CORS_ORIGINS=https://fi-sikkati.vercel.app`
- `AUTH_JWT_ACTIVE_KID`, `AUTH_JWT_PRIVATE_KEY`, `AUTH_PASSWORD_PEPPER`, `AUTH_CSRF_SECRET`, `AUTH_HASH_SECRET`
- `EMAIL_FROM_ADDRESS=no-reply@fisikkati.app`
- `SMTP_HOST=127.0.0.1`
- `BOOTSTRAP_ADMIN_EMAILS` / `BOOTSTRAP_SUPER_ADMIN_EMAILS`

## 5) Point the web app

In the existing `fi-sikkati` Vercel project:

- `API_INTERNAL_URL=https://fi-sikkati-api.vercel.app`

Redeploy web.

## 6) Smoke test

- `https://fi-sikkati-api.vercel.app/health/ready`
- Register / sign-in on `https://fi-sikkati.vercel.app`
- Create trip + join + admin
