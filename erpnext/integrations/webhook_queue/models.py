from __future__ import annotations

import frappe
from frappe.model.document import Document


class WebhookQueue(Document):
	pass


class WebhookDeadLetter(Document):
	def retry(self):
		from .dead_letter import retry_dead_letter

		retry_dead_letter(self.name)


def create_dead_letter(payload: dict):
	dead_letter = frappe.new_doc("Webhook Dead Letter")
	for key, value in payload.items():
		if key in dead_letter.as_dict():
			dead_letter.set(key, value)
	dead_letter.insert(ignore_permissions=True)
	return dead_letter
