import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from api.routers import suburbs, market, calculators

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """DB pool and schema probe run lazily on first request (see api.db.get_pool)."""
    yield


# ENV=production (explicit) or Railway’s built-in flag (CLI vars sometimes omit ENV)
_is_production = (
    os.environ.get("ENV") == "production"
    or os.environ.get("RAILWAY_ENVIRONMENT") == "production"
)

app = FastAPI(
    title="AussiePropertyData API",
    description="Victorian suburb property analytics",
    version="1.0.0",
    docs_url="/docs" if not _is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=500)

# Comma-separated list; override in Railway with your Lovable URL(s).
_default_cors = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "http://localhost:3000,"
    "http://127.0.0.1:3000,"
    "http://localhost:4173,"
    "http://127.0.0.1:4173,"
    "https://aussiepropertydata.lovable.app,"
    "https://9d387518-e185-4a1e-aecf-4e7c4d6e163b.lovableproject.com"
)
_cors_raw = os.environ.get("CORS_ORIGINS", _default_cors)
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

_lovable_host_regex = (
    r"https://[^/]+\.lovable\.app$"
    r"|https://[^/]+\.lovableproject\.com$"
)


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    """Mirror CORSMiddleware rules so 4xx/5xx JSON responses still carry ACAO (avoids bogus browser CORS errors)."""
    origin = request.headers.get("origin")
    if not origin:
        return {}
    o = origin.strip()
    if o in _cors_origins:
        return {"Access-Control-Allow-Origin": o, "Vary": "Origin"}
    try:
        if re.fullmatch(_lovable_host_regex, o):
            return {"Access-Control-Allow-Origin": o, "Vary": "Origin"}
    except re.error:
        pass
    return {}


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_lovable_host_regex,
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(suburbs.router, prefix="/suburbs", tags=["suburbs"])
app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(calculators.router, prefix="/calculators", tags=["calculators"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def _validation_cors(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers=_cors_headers_for_request(request),
    )


@app.exception_handler(HTTPException)
async def _http_cors(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={**_cors_headers_for_request(request), **dict(exc.headers or {})},
    )


@app.exception_handler(Exception)
async def _unhandled_cors(request: Request, exc: Exception):
    if not _is_production:
        logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=_cors_headers_for_request(request),
    )
