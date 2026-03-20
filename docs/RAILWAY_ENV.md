# Railway environment variables (common mistakes)

## `CORS_ORIGINS`

Must be a **comma-separated list of full origins** (scheme + host, no path). Each Lovable URL is its **own** origin — do not join two hostnames into one.

**Wrong** (two domains merged — invalid host, CORS and healthchecks can fail):

```text
https://aussiepropertydata.lovable.e185-4a1e-aecf-4e7c4d6e163b.lovableproject.com
```

**Right** (two entries):

```text
http://localhost:5173,https://aussiepropertydata.lovable.app,https://9d387518-e185-4a1e-aecf-4e7c4d6e163b.lovableproject.com
```

Add `http://127.0.0.1:5173` if you open the app via 127.0.0.1. Regex in the API still allows other `*.lovable.app` / `*.lovableproject.com` previews when the request sends a matching `Origin` header.

## `SUPABASE_DB_URL`

Must be a valid PostgreSQL URI: **`postgresql://USER:PASSWORD@HOST:PORT/DATABASE`**

- There must be an **`@`** between the password and the hostname.
- Do not paste a placeholder like `your_strong_password` and accidentally delete characters so the host gets glued to the password.

**Pooler — use the exact URI from Supabase (ports differ by mode):**

- **Transaction pooler** (PgBouncer transaction mode): port **`6543`**, user **`postgres.YOUR_PROJECT_REF`**
- **Session pooler**: port **`5432`** on the **pooler** host, same user style — only valid if the dashboard string says so

Do **not** mix a pooler hostname with the wrong port; copy the **Session** or **Transaction** string as given.

**Direct (often simpler with asyncpg):**

```text
postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

Special characters in the password must be **URL-encoded** in the URI (`#` → `%23`, `$` → `%24`, `@` → `%40`, etc.).

Copy the string from **Supabase → Project Settings → Database** and paste it whole into Railway.

## CLI quick fix

From the repo root (logged in with `railway link`):

```bash
railway variable set 'CORS_ORIGINS=http://localhost:5173,https://aussiepropertydata.lovable.app,https://9d387518-e185-4a1e-aecf-4e7c4d6e163b.lovableproject.com'
```

Set `SUPABASE_DB_URL` in the Railway dashboard, or pipe from a local `.env` (value not echoed):

```bash
python3 -c "from pathlib import Path; from dotenv import load_dotenv; import os,sys; load_dotenv(Path('.')/'.env'); sys.stdout.write(os.environ['SUPABASE_DB_URL'])" | railway variable set SUPABASE_DB_URL --stdin
```
