"""
Shared helpers for ingestion scripts.
"""
import os

import asyncpg

from api.db_url import normalized_supabase_db_url, ssl_arg_for_asyncpg


async def asyncpg_connect_supabase(
    dsn: str | None = None, *, statement_cache_size: int = 0
) -> asyncpg.Connection:
    """Single-shot connect using the same DSN rules as the API pool."""
    url = normalized_supabase_db_url(dsn)
    if not url:
        raise RuntimeError("SUPABASE_DB_URL is not set")
    ssl_kw = {}
    sa = ssl_arg_for_asyncpg()
    if sa is not None:
        ssl_kw["ssl"] = sa
    return await asyncpg.connect(
        url, statement_cache_size=statement_cache_size, **ssl_kw
    )
