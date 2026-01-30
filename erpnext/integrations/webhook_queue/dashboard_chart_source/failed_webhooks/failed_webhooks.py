from __future__ import annotations

from datetime import datetime, timedelta

import frappe


def get(filters=None):
	filters = filters or {}
	days = int(filters.get("days", 7))
	start_date = datetime.utcnow() - timedelta(days=days)

	data = frappe.db.get_all(
		"Webhook Dead Letter",
		filters={"creation": [">=", start_date.isoformat()]},
		fields=["creation"],
	)

	counts = {}
	for row in data:
		date_key = row.creation.date().isoformat()
		counts[date_key] = counts.get(date_key, 0) + 1

	labels = sorted(counts.keys())
	values = [counts[label] for label in labels]

	return {
		"labels": labels,
		"datasets": [{"name": "Failed Webhooks", "values": values}],
	}
