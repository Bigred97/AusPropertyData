import asyncio
import os
import ssl

import asyncpg

_pool = None
_pool_lock = asyncio.Lock()


def _dsn() -> str:
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. Add it in Railway / hosting env (or `.env` locally)."
        )
    return url


def _connect_ssl():
    """Supabase requires TLS; pooler and direct both expect SSL."""
    if os.environ.get("DATABASE_SSL", "").lower() in ("0", "false", "no"):
        return False
    # Nixpacks/Railway images often ship an incomplete CA bundle; certifi matches
    # public roots asyncpg needs for *.pooler.supabase.com / *.supabase.co.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


async def get_pool():
    """
    Lazy pool + one-time column probe. Keeps startup (and /health) fast so platform
    healthchecks succeed before Postgres is contacted.
    """
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is not None:
            return _pool
        from api.column_probe import load_column_flags

        _pool = await asyncpg.create_pool(
            _dsn(),
            min_size=1,
            max_size=10,
            statement_cache_size=0,  # required for Supabase transaction-mode pooler
            ssl=_connect_ssl(),
        )
        async with _pool.acquire() as conn:
            await load_column_flags(conn)
        return _pool


async def get_conn():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
