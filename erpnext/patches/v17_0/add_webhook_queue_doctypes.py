import frappe


def execute():
	frappe.reload_doc("integrations", "doctype", "webhook_queue")
	frappe.reload_doc("integrations", "doctype", "webhook_dead_letter")
	frappe.reload_doc("integrations", "dashboard_chart_source", "failed_webhooks")
