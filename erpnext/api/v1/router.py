import frappe

from erpnext.api.errors import api_endpoint


@frappe.whitelist()
@api_endpoint
def get_greeting(name: str | None = None):
	"""Return a greeting message (v1)."""
	display_name = name or "Guest"
	return {"message": f"Hello {display_name}"}
