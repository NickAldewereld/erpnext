import frappe

from erpnext.api.errors import api_endpoint


@frappe.whitelist()
@api_endpoint
def get_greeting(name: str | None = None):
	"""Return a greeting message (v2) with breaking change."""
	display_name = name or "Guest"
	return {"greeting": f"Hello {display_name}", "display_name": display_name.upper()}
