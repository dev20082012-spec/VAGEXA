from typing import Any

from pydantic import BaseModel


class FieldError(BaseModel):
    field: str
    reason: str


class Problem(Exception):
    def __init__(
        self,
        status: int,
        type_slug: str,
        title: str,
        detail: str,
        errors: list[FieldError] | None = None,
    ) -> None:
        self.status = status
        self.type_slug = type_slug
        self.title = title
        self.detail = detail
        self.errors = errors or []
        super().__init__(detail)


def problem_body(problem: Problem, request_id: str, instance: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": f"https://vagexa.local/problems/{problem.type_slug}",
        "title": problem.title,
        "status": problem.status,
        "detail": problem.detail,
        "instance": instance,
        "request_id": request_id,
    }
    if problem.errors:
        body["errors"] = [item.model_dump() for item in problem.errors]
    return body
