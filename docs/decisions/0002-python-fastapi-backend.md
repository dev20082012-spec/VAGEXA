# 0002. Python and FastAPI form the application backend

- Status: accepted
- Date: 2026-11-22

## Context

The hard part of VAGEXA is statement normalisation, decimal allocation,
graph algorithms, and testable evidence rules. The API is a thin authorised
door onto those rules. The team should not implement the rules twice.

Node.js and TypeScript are a coherent API choice and share types with a React
client. The financial and graph libraries the design relies on, starting with
NetworkX and a direct decimal type, live more naturally in Python. A second
Node service would exist to forward calls.

Django would provide an admin and an ORM. A general admin is a liability on
evidence tables. FastAPI gives typed requests and an OpenAPI document without
that admin surface.

## Decision

The API and the worker are one Python 3.12 package. FastAPI serves HTTP.
Pydantic v2 validates boundaries. SQLAlchemy 2 and Alembic handle persistence.
Domain code uses `Decimal` and does not import FastAPI.

OpenAPI generated from the app is the type source for the frontend once the
app exists. Hand-written types may precede that generator and must follow
[API specification](../API_SPECIFICATION.md).

## Consequences

- One language for rules, jobs, and HTTP.
- The frontend does not import Python. The contract is HTTP.
- Pandas is not a dependency of the core path. It can be reconsidered for a
  batch report if a use case needs it. It must not become the place where
  money rules hide.

## Alternatives

- Node.js API with a Python worker. Rejected for Phase 1 as two deployable
  application codebases and two auth implementations.
- Django. Rejected because the admin and framework surface are larger than the
  problem.
- A notebook as the product. Rejected because it cannot hold authorisation or
  audit.
