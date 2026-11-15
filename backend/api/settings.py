"""Runtime settings, read from the environment once.

No secret has a default and no value is ever logged. The service does not read
`.env` files: in production the variables come from the Cloud Run configuration.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

API_DIR = Path(__file__).resolve().parent
DEFAULT_ORIGIN = "http://localhost:3000"
DEFAULT_FIXTURES_DIR = API_DIR.parents[1] / "frontend" / "fixtures"
DEFAULT_DEMO_DIR = API_DIR / "demo_data"

# Which entry of X-Forwarded-For is the client. Cloud Run appends the address it saw, so the
# last entry cannot be forged by the caller; "first" is for a proxy that adds its own after it.
ForwardedHop = Literal["first", "last"]


@dataclass(frozen=True)
class Settings:
    frontend_origins: tuple[str, ...] = (DEFAULT_ORIGIN,)
    use_fixtures: bool = False
    fixtures_dir: Path = DEFAULT_FIXTURES_DIR
    demo_dir: Path = DEFAULT_DEMO_DIR
    gemini_key_present: bool = False
    rate_limit_per_minute: int = 60
    rate_limit_heavy_per_minute: int = 10
    forwarded_ip_hop: ForwardedHop = "last"
    cache_ttl_seconds: float = 6 * 60 * 60
    cache_max_entries: int = 256
    max_body_bytes: int = 16 * 1024
    request_timeout_seconds: float = 90.0
    log_level: str = "INFO"


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _number[T: (int, float)](env: Mapping[str, str], name: str, default: T, kind: type[T]) -> T:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = kind(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number.") from exc
    if value < 0:
        raise ValueError(f"Environment variable {name} must not be negative.")
    return value


def _origins(env: Mapping[str, str]) -> tuple[str, ...]:
    raw = env.get("FRONTEND_ORIGIN", DEFAULT_ORIGIN)
    origins = tuple(o.strip().rstrip("/") for o in raw.split(",") if o.strip())
    return origins or (DEFAULT_ORIGIN,)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build the settings from `env` (the process environment by default)."""
    env = os.environ if env is None else env
    defaults = Settings()
    hop: ForwardedHop = (
        "first" if env.get("FORWARDED_IP_HOP", "").strip().lower() == "first" else "last"
    )
    return Settings(
        frontend_origins=_origins(env),
        use_fixtures=_flag(env, "USE_FIXTURES"),
        fixtures_dir=Path(env.get("FIXTURES_DIR") or defaults.fixtures_dir),
        demo_dir=Path(env.get("DEMO_DATA_DIR") or defaults.demo_dir),
        gemini_key_present=bool(env.get("GEMINI_API_KEY", "").strip()),
        rate_limit_per_minute=_number(
            env, "RATE_LIMIT_PER_MINUTE", defaults.rate_limit_per_minute, int
        ),
        rate_limit_heavy_per_minute=_number(
            env, "RATE_LIMIT_HEAVY_PER_MINUTE", defaults.rate_limit_heavy_per_minute, int
        ),
        forwarded_ip_hop=hop,
        cache_ttl_seconds=_number(env, "CACHE_TTL_SECONDS", defaults.cache_ttl_seconds, float),
        cache_max_entries=_number(env, "CACHE_MAX_ENTRIES", defaults.cache_max_entries, int),
        max_body_bytes=_number(env, "MAX_BODY_BYTES", defaults.max_body_bytes, int),
        request_timeout_seconds=_number(
            env, "REQUEST_TIMEOUT_SECONDS", defaults.request_timeout_seconds, float
        ),
        log_level=(env.get("LOG_LEVEL") or defaults.log_level).upper(),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
