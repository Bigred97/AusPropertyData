"""Normalize ``SUPABASE_DB_URL`` for asyncpg + Supabase pooler."""

from __future__ import annotations

import os


def normalized_supabase_db_url(url: str | None = None) -> str:
    """
    Strip the query string (e.g. ``?options=...``) — recommended for pooler URLs.

    If ``url`` is None, uses ``SUPABASE_DB_URL`` from the environment.
    Returns empty string if unset.
    """
    raw = (url if url is not None else os.environ.get("SUPABASE_DB_URL")) or ""
    if not raw or "?" not in raw:
        return raw
    return raw.split("?")[0]


def ssl_arg_for_asyncpg() -> bool | None:
    """``False`` disables TLS (local Postgres only). Otherwise let asyncpg default apply."""
    if os.environ.get("DATABASE_SSL", "").lower() in ("0", "false", "no"):
        return False
    return None
