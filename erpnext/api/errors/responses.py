from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import frappe


def _now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def get_request_id() -> str:
	request_id = getattr(frappe.local, "request_id", None)
	if request_id:
		return request_id
	request_id = str(uuid4())
	frappe.local.request_id = request_id
	return request_id


def build_error_response(code: str, message: str, details: dict | None = None) -> dict:
	return {
		"success": False,
		"error": {
			"code": code,
			"message": message,
			"details": details or {},
			"request_id": get_request_id(),
			"timestamp": _now_iso(),
		},
	}


def build_success_response(data: object) -> dict:
	return {
		"success": True,
		"data": data,
		"request_id": get_request_id(),
		"timestamp": _now_iso(),
	}
