"""OpenAPI document customisation (api.md §6).

* FastAPI documents an automatic ``422`` for every operation with parameters; our validation
  handler returns ``400 VALIDATION_ERROR`` instead (ADR-0010), so the ``422`` entries are removed.
* Every operation gets a ``default`` ``application/problem+json`` response so the generated client
  knows the error shape.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.errors import PROBLEM_CONTENT_TYPE, Problem

_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def build_openapi_schema(app: FastAPI) -> dict[str, Any]:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components["Problem"] = Problem.model_json_schema(
        ref_template="#/components/schemas/{model}", by_alias=True
    )
    # Pydantic nests referenced models under $defs; hoist them into components.
    for name, definition in components["Problem"].pop("$defs", {}).items():
        components.setdefault(name, definition)

    problem_response = {
        "description": "Error (RFC 9457 Problem Details with machine-readable `code`)",
        "content": {PROBLEM_CONTENT_TYPE: {"schema": {"$ref": "#/components/schemas/Problem"}}},
    }
    for path_item in schema.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in _HTTP_METHODS:
                continue
            responses = operation.setdefault("responses", {})
            responses.pop("422", None)
            responses.setdefault("default", problem_response)
    return schema


def install_custom_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = build_openapi_schema(app)
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
