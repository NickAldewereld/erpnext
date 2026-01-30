from __future__ import annotations

from werkzeug.wrappers import Response

import frappe

from .config import get_security_config


def _origin_allowed(origin: str, allowed: list[str]) -> bool:
	if "*" in allowed:
		return True
	return origin in allowed


def handle_preflight():
	config = get_security_config().cors
	if not config.enabled:
		return None
	request = frappe.local.request
	if request.method != "OPTIONS":
		return None
	origin = request.headers.get("Origin")
	if origin and not _origin_allowed(origin, config.allowed_origins):
		return Response("", status=403)

	response = Response("")
	apply_cors(response)
	return response


def apply_cors(response):
	config = get_security_config().cors
	if not config.enabled:
		return response
	request = getattr(frappe.local, "request", None)
	origin = request.headers.get("Origin") if request else None

	if origin and not _origin_allowed(origin, config.allowed_origins):
		return response

	response.headers["Access-Control-Allow-Origin"] = origin or "*"
	response.headers["Vary"] = "Origin"
	response.headers["Access-Control-Allow-Methods"] = ", ".join(config.allowed_methods)
	response.headers["Access-Control-Allow-Headers"] = ", ".join(config.allowed_headers)
	response.headers["Access-Control-Max-Age"] = str(config.max_age)
	if config.allow_credentials:
		response.headers["Access-Control-Allow-Credentials"] = "true"
	return response
