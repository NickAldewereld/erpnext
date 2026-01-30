from __future__ import annotations

import ast
from pathlib import Path

import frappe


ROOT = Path(__file__).resolve().parents[2]


def _is_whitelisted(node: ast.FunctionDef) -> bool:
	for decorator in node.decorator_list:
		if isinstance(decorator, ast.Call):
			decorator = decorator.func
		if isinstance(decorator, ast.Attribute):
			if decorator.attr == "whitelist":
				return True
		if isinstance(decorator, ast.Name) and decorator.id == "whitelist":
			return True
	return False


def _get_annotation(annotation) -> str | None:
	if annotation is None:
		return None
	if isinstance(annotation, ast.Name):
		return annotation.id
	if isinstance(annotation, ast.Subscript):
		return ast.unparse(annotation)
	return ast.unparse(annotation)


def _extract_functions(path: Path) -> list[dict]:
	module = "erpnext." + ".".join(path.relative_to(ROOT).with_suffix("").parts)
	tree = ast.parse(path.read_text(encoding="utf-8"))
	results = []
	for node in tree.body:
		if isinstance(node, ast.FunctionDef) and _is_whitelisted(node):
			params = []
			for arg in node.args.args:
				if arg.arg == "self":
					continue
				params.append(
					{
						"name": arg.arg,
						"type": _get_annotation(arg.annotation),
					}
				)
			results.append(
				{
					"name": node.name,
					"module": module,
					"doc": ast.get_docstring(node) or "",
					"params": params,
					"return_type": _get_annotation(node.returns),
				}
			)
	return results


def _collect_whitelisted_methods() -> list[dict]:
	results = []
	for path in ROOT.rglob("*.py"):
		if "/api/openapi/" in str(path):
			continue
		results.extend(_extract_functions(path))
	return results


def _dump_yaml(data: dict, indent: int = 0) -> str:
	lines = []
	space = " " * indent
	if isinstance(data, dict):
		for key, value in data.items():
			if isinstance(value, (dict, list)):
				lines.append(f"{space}{key}:")
				lines.append(_dump_yaml(value, indent + 2))
			else:
				lines.append(f"{space}{key}: {value}")
	elif isinstance(data, list):
		for item in data:
			if isinstance(item, (dict, list)):
				lines.append(f"{space}-")
				lines.append(_dump_yaml(item, indent + 2))
			else:
				lines.append(f"{space}- {item}")
	return "\n".join(lines)


def generate_spec() -> dict:
	methods = _collect_whitelisted_methods()
	paths = {}
	for method in methods:
		endpoint = f"/api/method/{method['module']}.{method['name']}"
		paths[endpoint] = {
			"post": {
				"summary": method["doc"] or method["name"],
				"parameters": [
					{
						"name": param["name"],
						"in": "query",
						"schema": {"type": param["type"] or "string"},
					}
					for param in method["params"]
				],
				"responses": {
					"200": {"description": "Success"},
					"400": {"description": "Validation Error"},
					"401": {"description": "Auth Error"},
					"404": {"description": "Not Found"},
					"429": {"description": "Rate Limited"},
					"500": {"description": "Internal Error"},
				},
			}
		}

	return {
		"openapi": "3.0.0",
		"info": {"title": "ERPNext API", "version": "1.0.0"},
		"paths": paths,
	}


def write_spec(path: Path | None = None):
	spec = generate_spec()
	content = _dump_yaml(spec)
	path = path or Path(__file__).with_name("spec.yaml")
	path.write_text(content + "\n", encoding="utf-8")
	return path


def main():
	write_spec()
	frappe.msgprint("OpenAPI spec generated.")


if __name__ == "__main__":
	main()
