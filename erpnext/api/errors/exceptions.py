from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApiError(Exception):
	code: str
	message: str
	details: dict | None = field(default_factory=dict)


class ValidationError(ApiError):
	def __init__(self, message: str, details: dict | None = None):
		super().__init__(code="VALIDATION_ERROR", message=message, details=details or {})


class AuthError(ApiError):
	def __init__(self, message: str, details: dict | None = None):
		super().__init__(code="AUTH_ERROR", message=message, details=details or {})


class NotFoundError(ApiError):
	def __init__(self, message: str, details: dict | None = None):
		super().__init__(code="NOT_FOUND", message=message, details=details or {})


class RateLimitError(ApiError):
	def __init__(self, message: str, details: dict | None = None):
		super().__init__(code="RATE_LIMITED", message=message, details=details or {})
