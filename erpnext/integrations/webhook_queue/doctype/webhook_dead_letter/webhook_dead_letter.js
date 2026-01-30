frappe.ui.form.on("Webhook Dead Letter", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Pending") {
			frm.add_custom_button(__("Retry Webhook"), () => {
				frappe.call({
					method: "erpnext.integrations.webhook_queue.dead_letter.retry_dead_letter",
					args: { name: frm.doc.name },
					callback: () => frm.reload_doc()
				});
			});
		}
	}
});
