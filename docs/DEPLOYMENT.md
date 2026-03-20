# Deployment reference

_Generated: 2026-03-20 00:49 UTC — run `python3 scripts/update_deployment_docs.py` to refresh._

## Railway (`railway status`)

```
Project: AusPropertyData
Environment: production
Service: AusPropertyData
```

### Railway variables (sanitized)

| Variable | Value |
|----------|-------|
| `RAILWAY_PROJECT_NAME` | `AusPropertyData` |
| `RAILWAY_PROJECT_ID` | `03156c1b-4312-4227-a615-4a27688db610` |
| `RAILWAY_SERVICE_NAME` | `AusPropertyData` |
| `RAILWAY_SERVICE_ID` | `330ed819-cbf4-4621-b2d0-eaa6e8bd578f` |
| `RAILWAY_PUBLIC_DOMAIN` | `auspropertydata-production.up.railway.app` |
| `ENV` | `production` |
| `CORS_ORIGINS` | `http://localhost:5173,https://aussiepropertydata.lovable.app` |
| `SUPABASE_DB_URL` | `postgresql://postgres.ksmumnnyioxcxutodiax:***@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres` |

### API

- **Base URL:** `https://auspropertydata-production.up.railway.app`
- **Health:** `https://auspropertydata-production.up.railway.app/health`


### Supabase (from `supabase projects list`)

| Field | Value |
|-------|-------|
| Project name | `aussiepropertydata` |
| Project ref | `ksmumnnyioxcxutodiax` |
| Region | Oceania (Sydney) |
| Dashboard | [Open project](https://supabase.com/dashboard/project/ksmumnnyioxcxutodiax) |
| DB pooler (typical host) | `aws-1-ap-southeast-2.pooler.supabase.com` |

Connection strings (password **never** committed):

- **Direct** (asyncpg / local scripts): `postgresql://postgres:***@db.ksmumnnyioxcxutodiax.supabase.co:5432/postgres`
- **Transaction pooler** (6543): `postgresql://postgres.ksmumnnyioxcxutodiax:***@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres`

See `.env.example` for when to prefer each.


## Security

- Do **not** commit real `SUPABASE_DB_URL` passwords or Supabase **service_role** / **anon** keys.
- Set secrets in **Railway** → service → Variables and (if used) **GitHub** → repository secrets for Actions.
