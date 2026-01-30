from __future__ import annotations

import frappe

from .dispatcher import enqueue_webhook


@frappe.whitelist()
def retry_dead_letter(name: str):
	dead_letter = frappe.get_doc("Webhook Dead Letter", name)
	enqueue_webhook(
		target_url=dead_letter.target_url,
		payload=frappe.parse_json(dead_letter.payload or "{}"),
		headers=frappe.parse_json(dead_letter.headers or "{}"),
		event=dead_letter.event,
	)
	dead_letter.status = "Retried"
	dead_letter.save(ignore_permissions=True)
