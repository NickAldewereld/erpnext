from __future__ import annotations

from uuid import uuid4

import frappe
from werkzeug.wrappers import Response

from erpnext.api.errors import RateLimitError
from erpnext.api.errors.responses import build_error_response, get_request_id
from erpnext.api.security import apply_cors, enforce_rate_limit, handle_preflight


def _set_request_id():
	if not getattr(frappe.local, "request_id", None):
		frappe.local.request_id = str(uuid4())
	return frappe.local.request_id


def _set_api_version(version: str | None):
	frappe.local.api_version = version or "1"


def _sanitize_cmd(cmd: str | None) -> str | None:
	if not cmd:
		return None
	if ".." in cmd or "/" in cmd or " " in cmd:
		return None
	return cmd


def _rewrite_endpoint(path: str, version: str):
	if not path.startswith("/api/v"):
		return
	version_prefix = f"/api/v{version}/method/"
	if not path.startswith(version_prefix):
		return
	original = path[len(version_prefix) :]
	if original.startswith("erpnext.api.") and ".v1." not in original and ".v2." not in original:
		module_path = original.replace("erpnext.api.", f"erpnext.api.v{version}.router.")
	else:
		module_path = original
	frappe.local.request.environ["PATH_INFO"] = f"/api/method/{module_path}"
	frappe.local.rewritten_endpoint = module_path


def _resolve_version():
	request = frappe.local.request
	path = request.path
	header_version = request.headers.get("X-API-Version")
	version = None

	if path.startswith("/api/v1/"):
		version = "1"
	elif path.startswith("/api/v2/"):
		version = "2"
	elif header_version:
		candidate = header_version.strip()
		version = candidate if candidate in {"1", "2"} else "1"
	else:
		version = "1"

	_set_api_version(version)
	if path.startswith("/api/v") and "/method/" in path:
		_rewrite_endpoint(path, version)
	elif header_version and path.startswith("/api/method/"):
		cmd = _sanitize_cmd(frappe.form_dict.get("cmd"))
		if cmd and cmd.startswith("erpnext.api.") and ".v1." not in cmd and ".v2." not in cmd:
			module_path = cmd.replace("erpnext.api.", f"erpnext.api.v{version}.router.")
			frappe.local.request.environ["PATH_INFO"] = f"/api/method/{module_path}"
			frappe.form_dict["cmd"] = module_path
			frappe.local.rewritten_endpoint = module_path


def before_request():
	_set_request_id()
	_resolve_version()

	preflight_response = handle_preflight()
	if preflight_response:
		frappe.local.response = preflight_response
		return preflight_response

	request = frappe.local.request
	if request.path.startswith("/api/"):
		endpoint = _sanitize_cmd(frappe.form_dict.get("cmd")) or getattr(
			frappe.local, "rewritten_endpoint", None
		)
		if not endpoint and request.path.startswith("/api/method/"):
			endpoint = _sanitize_cmd(request.path.removeprefix("/api/method/"))
		if endpoint:
			try:
				enforce_rate_limit(endpoint)
			except RateLimitError as exc:
				return handle_rate_limit_error(exc)


def after_request(response: Response):
	response.headers["X-Request-ID"] = get_request_id()
	api_version = getattr(frappe.local, "api_version", "1")
	if api_version == "1":
		response.headers["Deprecation"] = "true"
		response.headers["Link"] = '</api/v2/method/>; rel="successor-version"'

	rate_limit_headers = getattr(frappe.local, "rate_limit_headers", None) or {}
	for key, value in rate_limit_headers.items():
		response.headers[key] = value

	apply_cors(response)
	return response


def handle_rate_limit_error(exc: RateLimitError):
	frappe.local.response = Response(
		frappe.as_json(build_error_response(exc.code, exc.message, exc.details)),
		status=429,
		content_type="application/json",
	)
	return frappe.local.response
