from __future__ import annotations

import functools

import frappe
from frappe import _

from .exceptions import ApiError
from .responses import build_error_response, build_success_response


def standard_errors_enabled() -> bool:
	site_config = frappe.get_site_config(silent=True) or {}
	return bool(site_config.get("api_standardized_errors", False))


def _log_error(exc: Exception) -> None:
	request = getattr(frappe.local, "request", None)
	context = {
		"request_id": getattr(frappe.local, "request_id", None),
		"path": request.path if request else None,
		"method": request.method if request else None,
		"user": frappe.session.user if hasattr(frappe, "session") else None,
	}
	message = f"{exc}\n\nContext: {frappe.as_json(context, indent=2)}"
	frappe.log_error(message=message, title="API Error")


def api_endpoint(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		if not standard_errors_enabled():
			return func(*args, **kwargs)

		try:
			result = func(*args, **kwargs)
			return build_success_response(result)
		except ApiError as exc:
			_log_error(exc)
			return build_error_response(exc.code, exc.message, exc.details)
		except frappe.DoesNotExistError as exc:
			_log_error(exc)
			return build_error_response("NOT_FOUND", str(exc))
		except frappe.PermissionError as exc:
			_log_error(exc)
			return build_error_response("AUTH_ERROR", str(exc))
		except frappe.ValidationError as exc:
			_log_error(exc)
			return build_error_response("VALIDATION_ERROR", str(exc))
		except Exception as exc:
			_log_error(exc)
			return build_error_response("INTERNAL_ERROR", _("Internal Server Error"))

	return wrapper
