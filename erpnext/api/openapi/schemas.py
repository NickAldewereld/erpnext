from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SuccessResponse:
	success: bool = True
	data: Any = None


@dataclass
class ErrorDetail:
	code: str
	message: str
	details: dict = field(default_factory=dict)
	request_id: str | None = None
	timestamp: str | None = None


@dataclass
class ErrorResponse:
	success: bool = False
	error: ErrorDetail | None = None


@dataclass
class PaginatedResponse:
	success: bool = True
	data: list[Any] = field(default_factory=list)
	page: int = 1
	page_size: int = 20
	total: int = 0
