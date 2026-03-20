"""Normalize ``SUPABASE_DB_URL`` for asyncpg + Supabase pooler."""

from __future__ import annotations

import os
import ssl


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


def ssl_arg_for_asyncpg() -> ssl.SSLContext | bool:
    """
    Supabase requires TLS. asyncpg is most reliable with an explicit trust store
    (certifi); some Mac/Python installs fail verification with the default bundle.

    - ``DATABASE_SSL=0`` — no TLS (local Postgres only).
    - ``DATABASE_SSL_INSECURE=1`` — TLS without cert verify (dev only, not production).
    """
    if os.environ.get("DATABASE_SSL", "").lower() in ("0", "false", "no"):
        return False
    if os.environ.get("DATABASE_SSL_INSECURE", "").lower() in ("1", "true", "yes"):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()
