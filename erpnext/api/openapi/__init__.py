from __future__ import annotations

from pathlib import Path

import frappe


@frappe.whitelist(allow_guest=True)
def get_spec():
	spec_path = Path(__file__).with_name("spec.yaml")
	if not spec_path.exists():
		frappe.throw("OpenAPI spec not generated")
	return spec_path.read_text(encoding="utf-8")
