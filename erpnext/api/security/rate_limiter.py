from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import frappe

from erpnext.api.errors import RateLimitError
from .config import get_security_config


_lock = threading.Lock()
_local_store: dict[str, tuple[int, float]] = {}


@dataclass
class RateLimitResult:
	limit: int
	remaining: int
	reset: int


def _get_cache_backend():
	try:
		return frappe.cache()
	except Exception:
		return None


def _get_count(cache, key: str) -> int | None:
	if not cache:
		return None
	try:
		return cache.get_value(key)
	except Exception:
		return None


def _set_count(cache, key: str, value: int, expires_in: int) -> None:
	if not cache:
		return
	try:
		cache.set_value(key, value, expires_in=expires_in)
	except Exception:
		return


def _increment_count(key: str, window: int) -> int:
	cache = _get_cache_backend()
	if cache:
		current = _get_count(cache, key) or 0
		next_value = int(current) + 1
		_set_count(cache, key, next_value, window)
		return next_value

	with _lock:
		count, expires_at = _local_store.get(key, (0, 0))
		now = time.time()
		if now >= expires_at:
			count = 0
			expires_at = now + window
		count += 1
		_local_store[key] = (count, expires_at)
		return count


def _get_reset_time(key: str, window: int) -> int:
	cache = _get_cache_backend()
	if cache:
		ttl_fn = getattr(cache, "get_ttl", None)
		if ttl_fn:
			ttl = ttl_fn(key)
			if ttl is not None:
				return int(time.time() + ttl)
	with _lock:
		_, expires_at = _local_store.get(key, (0, time.time() + window))
		return int(expires_at)


def enforce_rate_limit(endpoint: str) -> RateLimitResult | None:
	config = get_security_config().rate_limit
	if not config.enabled:
		return None

	user = frappe.session.user if hasattr(frappe, "session") else "Guest"
	is_guest = user == "Guest"
	api_key = frappe.get_request_header("Authorization") or frappe.get_request_header("X-API-Key")
	api_key = api_key.split(" ", 1)[-1] if api_key else None
	client_ip = getattr(frappe.local, "request_ip", None) or frappe.get_request_header("X-Forwarded-For")

	override = config.endpoint_overrides.get(endpoint, {}) if config.endpoint_overrides else {}
	if is_guest:
		limit = int(override.get("per_ip_limit", config.per_ip_limit))
		window = int(override.get("per_ip_window_seconds", config.per_ip_window_seconds))
		identity = client_ip or "unknown"
		key = f"api_rate_limit:ip:{identity}:{endpoint}"
	else:
		limit = int(override.get("per_key_limit", config.per_key_limit))
		window = int(override.get("per_key_window_seconds", config.per_key_window_seconds))
		identity = api_key or user
		key = f"api_rate_limit:key:{identity}:{endpoint}"

	count = _increment_count(key, window)
	reset = _get_reset_time(key, window)
	remaining = max(limit - count, 0)

	result = RateLimitResult(limit=limit, remaining=remaining, reset=reset)
	frappe.local.rate_limit_headers = {
		"X-RateLimit-Limit": str(limit),
		"X-RateLimit-Remaining": str(remaining),
		"X-RateLimit-Reset": str(reset),
	}

	if count > limit:
		raise RateLimitError(
			"Rate limit exceeded",
			details={"limit": limit, "reset": reset},
		)

	return result
