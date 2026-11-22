"""Authorization policy. Frontend visibility is not an input."""

CASE_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "lead": frozenset({"cases.read", "cases.mutate", "audit.read", "analysis.run"}),
    "investigator": frozenset({"cases.read", "cases.mutate", "audit.read", "analysis.run"}),
    "analyst": frozenset({"cases.read", "audit.read", "analysis.run"}),
    "auditor": frozenset({"cases.read", "audit.read"}),
}


def case_role_allows(case_role: str, permission: str) -> bool:
    return permission in CASE_ROLE_PERMISSIONS.get(case_role, frozenset())
