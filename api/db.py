import asyncio

import asyncpg

from api.db_url import normalized_supabase_db_url, ssl_arg_for_asyncpg

_pool_url = normalized_supabase_db_url() or None

pool = None
_pool_lock = asyncio.Lock()


async def get_pool():
    global pool
    if pool is not None:
        return pool
    async with _pool_lock:
        if pool is not None:
            return pool
        if not _pool_url:
            raise RuntimeError(
                "SUPABASE_DB_URL environment variable not set. Add it in Railway or `.env`."
            )
        ssl_kw = {}
        sa = ssl_arg_for_asyncpg()
        if sa is not False:
            ssl_kw["ssl"] = sa
        pool = await asyncpg.create_pool(
            _pool_url,
            min_size=1,
            max_size=5,
            statement_cache_size=0,  # required for Supabase pooler / transaction mode
            max_inactive_connection_lifetime=300,
            command_timeout=60,
            **ssl_kw,
        )
        from api.column_probe import load_column_flags

        async with pool.acquire() as conn:
            await load_column_flags(conn)
        return pool


async def get_conn():
    """FastAPI Depends: yields a connection and returns it to the pool after the request."""
    p = await get_pool()
    async with p.acquire() as conn:
        yield conn
