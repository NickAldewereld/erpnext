from __future__ import annotations

from dataclasses import dataclass, field

import frappe


@dataclass
class RateLimitConfig:
	enabled: bool = False
	per_key_limit: int = 1000
	per_key_window_seconds: int = 3600
	per_ip_limit: int = 100
	per_ip_window_seconds: int = 3600
	endpoint_overrides: dict = field(default_factory=dict)


@dataclass
class CorsConfig:
	enabled: bool = False
	allowed_origins: list[str] = field(default_factory=list)
	allow_credentials: bool = True
	max_age: int = 600
	allowed_methods: list[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
	allowed_headers: list[str] = field(
		default_factory=lambda: ["Authorization", "Content-Type", "X-API-Version", "X-Requested-With"]
	)


@dataclass
class SecurityConfig:
	rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
	cors: CorsConfig = field(default_factory=CorsConfig)


def get_security_config() -> SecurityConfig:
	site_config = frappe.get_site_config(silent=True) or {}

	rate_limit = RateLimitConfig(
		enabled=bool(site_config.get("api_rate_limit_enabled", False)),
		per_key_limit=int(site_config.get("api_rate_limit_per_key", 1000)),
		per_key_window_seconds=int(site_config.get("api_rate_limit_per_key_window", 3600)),
		per_ip_limit=int(site_config.get("api_rate_limit_per_ip", 100)),
		per_ip_window_seconds=int(site_config.get("api_rate_limit_per_ip_window", 3600)),
		endpoint_overrides=site_config.get("api_rate_limit_overrides", {}) or {},
	)

	cors = CorsConfig(
		enabled=bool(site_config.get("api_cors_enabled", False)),
		allowed_origins=site_config.get("api_cors_allowed_origins", []) or [],
		allow_credentials=bool(site_config.get("api_cors_allow_credentials", True)),
		max_age=int(site_config.get("api_cors_max_age", 600)),
		allowed_methods=site_config.get(
			"api_cors_allowed_methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
		),
		allowed_headers=site_config.get(
			"api_cors_allowed_headers",
			["Authorization", "Content-Type", "X-API-Version", "X-Requested-With"],
		),
	)

	return SecurityConfig(rate_limit=rate_limit, cors=cors)
