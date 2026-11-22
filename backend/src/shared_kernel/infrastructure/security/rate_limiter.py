"""Distributed atomic Redis-backed rate limiter core (AUD-HIGH-05).

Provides:
- Atomic Redis Lua fixed-window rate limiting with bounded TTLs (`RedisRateLimiter`).
- Centralized, configurable policy matrix (`RateLimitPolicy`, `DEFAULT_RATE_LIMIT_POLICIES`).
- Trusted-proxy-aware client IP extraction (`extract_client_ip`) resistant to
  `X-Forwarded-For` / `X-Real-IP` spoofing.
- Privacy-preserving identifier hashing (`hash_email`, `hash_token`, `hash_identifier`).
- Explicit failure semantics (`fail_closed=True` -> 503 `RateLimiterUnavailableError`,
  `fail_closed=False` -> degraded fail-open with structured warning log).
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

import redis.asyncio as aioredis
import redis.exceptions
import structlog

from src.shared_kernel.config import get_settings

logger = structlog.get_logger(__name__)

# Atomic fixed-window counter with millisecond-precision TTL.
# Guarantees:
# 1. Zero race conditions across concurrent coroutines or backend replicas.
# 2. Bounded TTL on every key (never unbounded growth); defensive PTTL check heals
#    any key missing a TTL without resetting active windows on excess requests.
_LUA_FIXED_WINDOW_LIMIT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])

local current = redis.call("INCR", key)
if current == 1 then
    redis.call("PEXPIRE", key, window_ms)
end

local pttl = redis.call("PTTL", key)
if pttl < 0 then
    redis.call("PEXPIRE", key, window_ms)
    pttl = window_ms
end

local allowed = 0
if current <= limit then
    allowed = 1
end

local remaining = limit - current
if remaining < 0 then
    remaining = 0
end

return {allowed, current, remaining, pttl}
"""

DEFAULT_TRUSTED_PROXIES: tuple[str, ...] = ("127.0.0.1/32", "::1/128")

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


class _ClientAddressLike(Protocol):
    @property
    def host(self) -> str: ...


class RequestLike(Protocol):
    """Minimal protocol satisfied by FastAPI/Starlette Request and test doubles."""

    @property
    def client(self) -> _ClientAddressLike | None: ...

    @property
    def headers(self) -> Mapping[str, str]: ...


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Outcome of a single rate limit evaluation."""

    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    degraded: bool = False

    def to_headers(self) -> dict[str, str]:
        """Return standard HTTP rate-limit response headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
        }
        if not self.allowed and self.retry_after_seconds > 0:
            headers["Retry-After"] = str(self.retry_after_seconds)
        return headers


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """Named rate-limit policy definition."""

    name: str
    limit: int
    window_seconds: int
    fail_closed: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("RateLimitPolicy.name must be a non-empty string")
        if self.limit < 1:
            raise ValueError(f"RateLimitPolicy.limit must be >= 1 (got {self.limit})")
        if self.window_seconds < 1:
            raise ValueError(
                f"RateLimitPolicy.window_seconds must be >= 1 (got {self.window_seconds})"
            )


class RateLimitExceededError(Exception):
    """Raised when a caller exceeds its configured rate-limit policy (HTTP 429)."""

    status_code: int = 429

    def __init__(
        self,
        *,
        policy_name: str,
        decision: RateLimitDecision,
        detail: str = "Too many requests. Please try again later.",
    ) -> None:
        super().__init__(detail)
        self.policy_name = policy_name
        self.decision = decision
        self.detail = detail
        self.headers = decision.to_headers()


class RateLimiterUnavailableError(Exception):
    """Raised when Redis is unreachable for a fail-closed policy (HTTP 503)."""

    status_code: int = 503

    def __init__(
        self,
        *,
        policy_name: str,
        detail: str = "Rate limiting service is temporarily unavailable. Please retry shortly.",
    ) -> None:
        super().__init__(detail)
        self.policy_name = policy_name
        self.detail = detail


_DEFAULT_POLICIES_DICT: dict[str, RateLimitPolicy] = {
    # Authentication — dual IP + account-hash layers prevent shared-NAT lockout
    # while blocking targeted credential stuffing and OTP brute-force.
    "auth_login_ip": RateLimitPolicy(
        name="auth_login_ip",
        limit=60,
        window_seconds=60,
        fail_closed=False,
        description="Per-IP login burst limit calibrated for shared campus/NAT; fails open on transient Redis blip while account guard & Argon2id remain active.",
    ),
    "auth_login_account": RateLimitPolicy(
        name="auth_login_account",
        limit=10,
        window_seconds=300,
        fail_closed=True,
        description="Per-account (normalized email hash) login limit; fails closed to block credential stuffing.",
    ),
    "auth_register_otp_ip": RateLimitPolicy(
        name="auth_register_otp_ip",
        limit=60,
        window_seconds=300,
        fail_closed=True,
        description="Per-IP registration OTP dispatch limit calibrated for shared campus/NAT; fails closed to prevent SMTP abuse.",
    ),
    "auth_verify_otp_ip": RateLimitPolicy(
        name="auth_verify_otp_ip",
        limit=60,
        window_seconds=300,
        fail_closed=True,
        description="Per-IP OTP verification limit calibrated for shared campus/NAT; fails closed due to high brute-force risk.",
    ),
    "auth_verify_otp_account": RateLimitPolicy(
        name="auth_verify_otp_account",
        limit=8,
        window_seconds=300,
        fail_closed=True,
        description="Per-account (email hash) OTP verification limit; fails closed due to high brute-force risk.",
    ),
    "auth_password_reset_ip": RateLimitPolicy(
        name="auth_password_reset_ip",
        limit=60,
        window_seconds=300,
        fail_closed=True,
        description="Per-IP password reset limit calibrated for shared campus/NAT; returns uniform 429 without leaking account existence.",
    ),
    "auth_password_reset_account": RateLimitPolicy(
        name="auth_password_reset_account",
        limit=5,
        window_seconds=300,
        fail_closed=True,
        description="Per-account (email hash) password reset limit; fails closed with uniform 429.",
    ),
    "auth_refresh_ip": RateLimitPolicy(
        name="auth_refresh_ip",
        limit=120,
        window_seconds=60,
        fail_closed=False,
        description="Per-IP JWT refresh limit calibrated for shared campus/NAT; fails open on Redis blip to avoid mass session drops.",
    ),
    "auth_google_ip": RateLimitPolicy(
        name="auth_google_ip",
        limit=60,
        window_seconds=60,
        fail_closed=False,
        description="Per-IP Google OAuth login limit calibrated for shared campus/NAT; fails open on transient Redis blip.",
    ),
    # Authenticated user resource guards
    "account_export_user": RateLimitPolicy(
        name="account_export_user",
        limit=5,
        window_seconds=3600,
        fail_closed=False,
        description="Per-user account data export limit (heavy payload).",
    ),
    "webcal_feed_token": RateLimitPolicy(
        name="webcal_feed_token",
        limit=60,
        window_seconds=300,
        fail_closed=False,
        description="Per-token-hash WebCal feed limit; replaces unbounded in-memory dict.",
    ),
    "calendar_oauth_init_user": RateLimitPolicy(
        name="calendar_oauth_init_user",
        limit=15,
        window_seconds=300,
        fail_closed=False,
        description="Per-user calendar OAuth initiation limit.",
    ),
    "knowledge_upload_user": RateLimitPolicy(
        name="knowledge_upload_user",
        limit=20,
        window_seconds=300,
        fail_closed=False,
        description="Per-user RAG knowledge upload limit.",
    ),
    # External provider webhooks — generous burst & fail-open so legitimate
    # provider callbacks are not dropped on a transient Redis outage.
    "billing_webhook_ip": RateLimitPolicy(
        name="billing_webhook_ip",
        limit=120,
        window_seconds=60,
        fail_closed=False,
        description="Per-IP payment webhook burst limit; fails open to avoid dropping provider callbacks.",
    ),
    "calendar_webhook_ip": RateLimitPolicy(
        name="calendar_webhook_ip",
        limit=120,
        window_seconds=60,
        fail_closed=False,
        description="Per-IP calendar push-notification webhook burst limit; fails open.",
    ),
}

DEFAULT_RATE_LIMIT_POLICIES: Mapping[str, RateLimitPolicy] = MappingProxyType(
    _DEFAULT_POLICIES_DICT
)


def load_rate_limit_policies(
    *,
    overrides: Mapping[str, RateLimitPolicy] | None = None,
    env_overrides_json: str | None = None,
) -> dict[str, RateLimitPolicy]:
    """Build a policy registry starting from defaults and applying JSON & mapping overrides."""
    merged: dict[str, RateLimitPolicy] = dict(DEFAULT_RATE_LIMIT_POLICIES)

    if env_overrides_json and env_overrides_json.strip():
        raw_obj = json.loads(env_overrides_json)
        if not isinstance(raw_obj, dict):
            raise ValueError("Rate limit env_overrides_json must decode to a JSON object")
        for policy_name, cfg in raw_obj.items():
            if not isinstance(policy_name, str) or not isinstance(cfg, dict):
                raise ValueError(f"Invalid rate limit policy override entry for {policy_name!r}")
            base = merged.get(policy_name)
            limit_val = int(cfg["limit"]) if "limit" in cfg else (base.limit if base else 0)
            window_val = (
                int(cfg["window_seconds"])
                if "window_seconds" in cfg
                else (base.window_seconds if base else 0)
            )
            fail_closed_val = (
                bool(cfg["fail_closed"])
                if "fail_closed" in cfg
                else (base.fail_closed if base else False)
            )
            description_val = (
                str(cfg["description"])
                if "description" in cfg
                else (base.description if base else "")
            )
            merged[policy_name] = RateLimitPolicy(
                name=policy_name,
                limit=limit_val,
                window_seconds=window_val,
                fail_closed=fail_closed_val,
                description=description_val,
            )

    if overrides:
        for policy_name, policy in overrides.items():
            merged[policy_name] = policy

    return merged


def hash_identifier(value: str, *, normalize_lower: bool = False) -> str:
    """Return a 32-char SHA-256 hex digest suitable for Redis keys and logs."""
    cleaned = value.strip()
    if normalize_lower:
        cleaned = cleaned.lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:32]


def hash_email(email: str) -> str:
    """Hash a normalized (trimmed + lowercased) email address for privacy-safe keying."""
    return hash_identifier(email, normalize_lower=True)


def hash_token(raw_token: str) -> str:
    """Hash a raw bearer/WebCal token so secrets never appear in Redis keys or logs."""
    return hash_identifier(raw_token, normalize_lower=False)


def _parse_trusted_networks(
    trusted_proxies: Iterable[str] | str | None,
) -> tuple[IPNetwork, ...]:
    if trusted_proxies is None:
        raw_entries: Iterable[str] = DEFAULT_TRUSTED_PROXIES
    elif isinstance(trusted_proxies, str):
        raw_entries = [part.strip() for part in trusted_proxies.split(",") if part.strip()]
    else:
        raw_entries = trusted_proxies

    networks: list[IPNetwork] = []
    for entry in raw_entries:
        cleaned = entry.strip()
        if not cleaned:
            continue
        networks.append(ipaddress.ip_network(cleaned, strict=False))
    return tuple(networks)


def _parse_ip(raw: str | None) -> IPAddress | None:
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return ipaddress.ip_address(cleaned)
    except ValueError:
        return None


def _is_trusted_ip(ip: IPAddress, trusted_networks: tuple[IPNetwork, ...]) -> bool:
    return any(ip in net for net in trusted_networks)


def extract_client_ip(
    request: RequestLike,
    trusted_proxies: Iterable[str] | str | None = DEFAULT_TRUSTED_PROXIES,
) -> str:
    """Extract the effective client IP without blindly trusting forwarded headers.

    - If `request.client.host` is NOT inside `trusted_proxies`, `X-Forwarded-For`
      and `X-Real-IP` are completely ignored and `request.client.host` is returned.
    - If `request.client.host` IS a trusted proxy, `X-Forwarded-For` is walked
      right-to-left, skipping trusted proxy hops, returning the first untrusted IP.
      Falls back to `X-Real-IP` (when valid), then `request.client.host`.
    """
    peer_host = request.client.host if request.client is not None else None
    peer_ip = _parse_ip(peer_host)
    if peer_ip is None:
        return "unknown"

    trusted_networks = _parse_trusted_networks(trusted_proxies)
    if not _is_trusted_ip(peer_ip, trusted_networks):
        return str(peer_ip)

    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        hops = [part.strip() for part in xff.split(",") if part.strip()]
        leftmost_valid: IPAddress | None = None
        for hop in reversed(hops):
            hop_ip = _parse_ip(hop)
            if hop_ip is None:
                # Malformed hop in XFF chain: do not trust anything further left.
                return str(peer_ip)
            leftmost_valid = hop_ip
            if not _is_trusted_ip(hop_ip, trusted_networks):
                return str(hop_ip)
        if leftmost_valid is not None:
            return str(leftmost_valid)

    x_real_ip_raw = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    x_real_ip = _parse_ip(x_real_ip_raw)
    if x_real_ip is not None:
        return str(x_real_ip)

    return str(peer_ip)


class RedisRateLimiter:
    """Distributed atomic Redis rate limiter using an embedded Lua script."""

    def __init__(
        self,
        *,
        redis_client: aioredis.Redis | None = None,
        redis_url: str | None = None,
        policies: Mapping[str, RateLimitPolicy] | None = None,
        key_prefix: str = "ff:rl",
        socket_connect_timeout: float = 0.5,
        socket_timeout: float = 1.0,
    ) -> None:
        self._client: aioredis.Redis | None = redis_client
        self._owns_client: bool = redis_client is None
        self._redis_url: str = redis_url or get_settings().redis_url
        self._policies: dict[str, RateLimitPolicy] = (
            dict(policies) if policies is not None else dict(DEFAULT_RATE_LIMIT_POLICIES)
        )
        self._key_prefix: str = key_prefix.strip(":") or "ff:rl"
        self._socket_connect_timeout = socket_connect_timeout
        self._socket_timeout = socket_timeout

    def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=self._socket_connect_timeout,
                socket_timeout=self._socket_timeout,
            )
            self._owns_client = True
        return self._client

    def get_policy(self, policy_name: str) -> RateLimitPolicy:
        """Look up a registered policy by name."""
        if policy_name not in self._policies:
            raise KeyError(f"Unknown rate limit policy: {policy_name!r}")
        return self._policies[policy_name]

    def build_key(self, policy_name: str, identifier: str) -> str:
        """Build the bounded-TTL Redis key for a policy and pre-normalized/hashed identifier."""
        cleaned_id = identifier.strip() or "unknown"
        return f"{self._key_prefix}:{policy_name}:{cleaned_id}"

    async def check(
        self,
        policy: str | RateLimitPolicy,
        identifier: str,
    ) -> RateLimitDecision:
        """Atomically evaluate and record a single hit against Redis."""
        resolved = self.get_policy(policy) if isinstance(policy, str) else policy
        redis_key = self.build_key(resolved.name, identifier)
        window_ms = resolved.window_seconds * 1000

        try:
            client = self._get_client()
            raw_result = await client.eval(
                _LUA_FIXED_WINDOW_LIMIT,
                1,
                redis_key,
                resolved.limit,
                window_ms,
            )
        except (redis.exceptions.RedisError, OSError, TimeoutError) as exc:
            logger.warning(
                "rate_limiter_redis_unavailable",
                policy=resolved.name,
                fail_closed=resolved.fail_closed,
                error_type=type(exc).__name__,
            )
            if resolved.fail_closed:
                raise RateLimiterUnavailableError(policy_name=resolved.name) from exc
            return RateLimitDecision(
                allowed=True,
                limit=resolved.limit,
                remaining=resolved.limit,
                retry_after_seconds=0,
                degraded=True,
            )

        allowed = bool(int(raw_result[0]))
        remaining = max(0, int(raw_result[2]))
        pttl_ms = max(0, int(raw_result[3]))
        retry_after = 0 if allowed else max(1, math.ceil(pttl_ms / 1000))

        return RateLimitDecision(
            allowed=allowed,
            limit=resolved.limit,
            remaining=remaining,
            retry_after_seconds=retry_after,
            degraded=False,
        )

    async def enforce(
        self,
        policy: str | RateLimitPolicy,
        identifier: str,
    ) -> RateLimitDecision:
        """Check rate limit and raise `RateLimitExceededError` (429) if denied."""
        resolved = self.get_policy(policy) if isinstance(policy, str) else policy
        decision = await self.check(resolved, identifier)
        if not decision.allowed:
            raise RateLimitExceededError(policy_name=resolved.name, decision=decision)
        return decision

    async def aclose(self) -> None:
        """Close the underlying Redis client if owned by this limiter."""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None


_rate_limiters_by_loop: dict[tuple[int, str, str], RedisRateLimiter] = {}


def get_rate_limiter() -> RedisRateLimiter:
    """Return an event-loop-scoped RedisRateLimiter configured from current settings."""
    settings = get_settings()
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = 0

    overrides_json = (settings.rate_limit_overrides_json or "").strip()
    cache_key = (loop_id, settings.redis_url, overrides_json)
    limiter = _rate_limiters_by_loop.get(cache_key)
    if limiter is None:
        policies = load_rate_limit_policies(env_overrides_json=overrides_json or None)
        limiter = RedisRateLimiter(
            redis_url=settings.redis_url,
            policies=policies,
        )
        _rate_limiters_by_loop[cache_key] = limiter
    return limiter


def reset_rate_limiter_cache() -> None:
    """Clear cached per-loop RedisRateLimiter instances (used in tests)."""
    _rate_limiters_by_loop.clear()


async def enforce_rate_limit(
    request: RequestLike | None,
    policy_name: str,
    *,
    identifier: str | None = None,
    limiter: RedisRateLimiter | None = None,
) -> RateLimitDecision | None:
    """Enforce a named rate-limit policy for an incoming HTTP request.

    - Respects ``settings.rate_limit_enabled`` (no-op when disabled).
    - When ``identifier`` is omitted, extracts client IP from ``request`` using
      ``settings.rate_limit_trusted_proxies``.
    - Raises ``RateLimitExceededError`` (429) or ``RateLimiterUnavailableError`` (503).
    """
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return None

    effective_limiter = limiter if limiter is not None else get_rate_limiter()
    if identifier is not None:
        resolved_id = identifier
    elif request is not None:
        resolved_id = extract_client_ip(
            request,
            trusted_proxies=settings.rate_limit_trusted_proxies,
        )
    else:
        resolved_id = "unknown"

    return await effective_limiter.enforce(policy_name, resolved_id)


__all__ = [
    "DEFAULT_RATE_LIMIT_POLICIES",
    "DEFAULT_TRUSTED_PROXIES",
    "RateLimitDecision",
    "RateLimitExceededError",
    "RateLimitPolicy",
    "RateLimiterUnavailableError",
    "RedisRateLimiter",
    "RequestLike",
    "enforce_rate_limit",
    "extract_client_ip",
    "get_rate_limiter",
    "hash_email",
    "hash_identifier",
    "hash_token",
    "load_rate_limit_policies",
    "reset_rate_limiter_cache",
]
