from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe
import requests
from frappe import _

from .models import create_dead_letter


def _get_retry_schedule() -> list[int]:
	site_config = frappe.get_site_config(silent=True) or {}
	return site_config.get("webhook_retry_schedule_seconds", [1, 5, 30, 120, 600, 3600])


def _get_max_retries() -> int:
	site_config = frappe.get_site_config(silent=True) or {}
	return int(site_config.get("webhook_max_retries", 6))


def enqueue_webhook(
	target_url: str,
	payload: dict[str, Any],
	headers: dict[str, str] | None = None,
	event: str | None = None,
):
	queue_doc = frappe.new_doc("Webhook Queue")
	queue_doc.target_url = target_url
	queue_doc.payload = frappe.as_json(payload)
	queue_doc.headers = frappe.as_json(headers or {})
	queue_doc.event = event
	queue_doc.status = "Queued"
	queue_doc.retry_count = 0
	queue_doc.save(ignore_permissions=True)
	frappe.enqueue("erpnext.integrations.webhook_queue.dispatcher.process_webhook", name=queue_doc.name)
	return queue_doc.name


def process_due_webhooks():
	due_jobs = frappe.get_all(
		"Webhook Queue",
		filters={
			"status": "Queued",
			"next_retry_at": ["<=", datetime.utcnow().isoformat()],
		},
		pluck="name",
	)
	for name in due_jobs:
		process_webhook(name)


def process_webhook(name: str):
	queue_doc = frappe.get_doc("Webhook Queue", name)
	if queue_doc.status != "Queued":
		return

	headers = frappe.parse_json(queue_doc.headers or "{}")
	payload = frappe.parse_json(queue_doc.payload or "{}")

	try:
		response = requests.post(queue_doc.target_url, json=payload, headers=headers, timeout=10)
		queue_doc.last_response = response.text
		if response.status_code >= 400:
			raise Exception(_("Webhook failed with status {0}").format(response.status_code))
		queue_doc.status = "Delivered"
		queue_doc.save(ignore_permissions=True)
	except Exception as exc:
		_handle_failure(queue_doc, str(exc))


def _handle_failure(queue_doc, error_message: str):
	queue_doc.retry_count = (queue_doc.retry_count or 0) + 1
	queue_doc.last_error = error_message

	retry_schedule = _get_retry_schedule()
	max_retries = _get_max_retries()
	if queue_doc.retry_count >= max_retries:
		queue_doc.status = "Dead Letter"
		queue_doc.save(ignore_permissions=True)
		create_dead_letter(
			{
				"target_url": queue_doc.target_url,
				"payload": queue_doc.payload,
				"headers": queue_doc.headers,
				"event": queue_doc.event,
				"retry_count": queue_doc.retry_count,
				"last_error": queue_doc.last_error,
				"last_response": queue_doc.last_response,
			}
		)
		return

	delay = retry_schedule[min(queue_doc.retry_count - 1, len(retry_schedule) - 1)]
	queue_doc.next_retry_at = (datetime.utcnow() + timedelta(seconds=delay)).isoformat()
	queue_doc.status = "Queued"
	queue_doc.save(ignore_permissions=True)
