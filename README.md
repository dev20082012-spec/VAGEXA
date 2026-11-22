# VAGEXA

VAGEXA is a proprietary financial-crime intelligence and investigation platform.
It helps an authorised investigator reconstruct how money and supporting digital
infrastructure connect across complaints: bank statements, mule-account patterns,
multi-hop transfers, domains, DNS, IP addresses, and hosting observations.

The Rajasthan Police Hackathon 2026, run by R4C (Rajasthan Cyber Crime Control
Centre), is the first milestone. The product aim is longer than that event: a
maintainable system whose findings can be explained from source records.

This repository currently holds the engineering foundation: product intent,
architecture, data design, security and evidence rules, the licence placeholder,
and the implementation roadmap. The application itself has not been started.

## Status

| Item | State |
| --- | --- |
| Application code | Foundation and case register. See [Implementation status](docs/IMPLEMENTATION_STATUS.md). |
| Database | Identity, cases, and audit migrated. Transactions are not created yet. |
| Runnable demo | Sign-in and case create/retrieve. No fund tracing. |
| Copyright owner | `[COPYRIGHT OWNER TO BE CONFIRMED]` |
| Licence | Proprietary. All rights reserved. Not open source. |
| Data in the repository | None. No statements, complaints, or secrets. |

Investigative outputs are leads. A risk indicator, a graph cluster, or a
generated paragraph is not a determination of guilt.

## Ownership and licence

Copyright (c) 2026 `[COPYRIGHT OWNER TO BE CONFIRMED]`. All rights reserved.

- The legal owner has not been confirmed. Do not infer it from the Git remote
  `github.com/dev20082012-spec/VAGEXA`, from a commit email, or from a handle.
- `LICENSE` reserves rights as a placeholder. It does not assign ownership and
  it does not grant an open-source licence.
- `NOTICE` records third-party material. None is vendored today.
- `CONTRIBUTING.md` is the contribution policy until a written contributor
  agreement exists.
- This project does not claim ownership of third-party libraries, external
  datasets, or organiser material, including hackathon problem statements.
- Before any public release, demonstration, or hackathon submission, review the
  event's intellectual-property terms and any contributor, college, or employer
  ownership claim. Resolve a conflict before submitting.

## Documentation

| Document | Purpose |
| --- | --- |
| [Product vision](docs/PRODUCT_VISION.md) | Users, purpose, boundaries |
| [Product requirements](docs/PRODUCT_REQUIREMENTS.md) | Numbered requirements and the milestone slice |
| [System architecture](docs/SYSTEM_ARCHITECTURE.md) | Containers, modules, and main flows |
| [Database design](docs/DATABASE_DESIGN.md) | Relational system of record |
| [Graph data model](docs/GRAPH_DATA_MODEL.md) | Nodes, edges, bounds, projection |
| [Financial intelligence](docs/FINANCIAL_INTELLIGENCE.md) | Statements, layers, indicators |
| [Infrastructure intelligence](docs/INFRASTRUCTURE_INTELLIGENCE.md) | Passive domain, DNS, IP, and hosting |
| [Correlation engine](docs/CORRELATION_ENGINE.md) | How links are proposed and confirmed |
| [AI investigation copilot](docs/AI_INVESTIGATION_COPILOT.md) | Tool-grounded questions |
| [Evidence and provenance](docs/EVIDENCE_AND_PROVENANCE.md) | Classifications, immutability, reports |
| [Security threat model](docs/SECURITY_THREAT_MODEL.md) | Assets, threats, controls |
| [API specification](docs/API_SPECIFICATION.md) | HTTP contract |
| [Testing strategy](docs/TESTING_STRATEGY.md) | Ground truth and required tests |
| [Deployment architecture](docs/DEPLOYMENT_ARCHITECTURE.md) | Environments and runtime shape |
| [Implementation roadmap](docs/IMPLEMENTATION_ROADMAP.md) | Phases 1 to 5 |
| [Decisions](docs/decisions/README.md) | Architecture decision records |
| [Architecture audit](docs/ARCHITECTURE_AUDIT.md) | Findings before implementation |
| [Technology decisions](docs/TECHNOLOGY_DECISIONS.md) | Stack re-evaluation |
| [Data validation report](docs/DATA_VALIDATION_REPORT.md) | Model check and synthetic scenarios |
| [Security gap analysis](docs/SECURITY_GAP_ANALYSIS.md) | Prototype bar and pre-operational bar |
| [Phase 1 scope](docs/PHASE_1_SCOPE.md) | What may be built, and what is blocked |
| [Implementation blueprint](docs/PHASE_1_IMPLEMENTATION_BLUEPRINT.md) | Phase 1 boundary and links to the engineering specs |

Agent and contributor rules live in `.cursor/rules/`.

## Proposed stack

The stack is a decision, recorded in `docs/decisions/`, and it is still
implementable rather than deployed.

- React and TypeScript single-page application, built with Vite.
- Python 3.12 and FastAPI for the HTTP API and the worker.
- PostgreSQL 16 as the only system of record.
- NetworkX for bounded, case-scoped graph algorithms.
- A PostgreSQL job table for durable ingestion work.
- Neo4j is a later derived projection, not part of the first runtime.
- Node.js is not an application server. TypeScript stays in the frontend.
- An LLM is optional. The copilot must answer from deterministic tools when no
  model is configured.

## Data

Five classifications are enforced in the design: `official`,
`public_intelligence`, `synthetic`, `derived`, and `unverified`. A deployment
runs in `synthetic` or `operational` mode and rejects the other mode's primary
records. Real and synthetic rows are not mixed in one case.

## Development

The target database is PostgreSQL 16. This workspace uses a local PostgreSQL 18
cluster on `127.0.0.1:5433` because Docker is not installed. Trust
authentication is limited to that loopback port and is for synthetic data only.

```powershell
.\scripts\dev-postgres.ps1
copy .env.example .env
# Set VAGEXA_BOOTSTRAP_PASSWORD in .env. Do not commit .env.
cd backend
python -m pip install -e ".[dev]"
$env:VAGEXA_DATA_MODE = "synthetic"
$env:VAGEXA_DATABASE_URL = "postgresql+psycopg://vagexa@127.0.0.1:5433/vagexa"
$env:VAGEXA_COOKIE_SECURE = "false"
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head
python -m vagexa.bootstrap
python -m vagexa.demo_seed --username $env:VAGEXA_BOOTSTRAP_USERNAME
python -m uvicorn vagexa.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

`vagexa.demo_seed` loads the synthetic `SYN-DEMO` investigation for an
existing user. Running it again inserts nothing new.

In another shell:

```powershell
cd frontend
npm install
npm run dev
```

The Vite server proxies `/api` and `/health` to port 8000. Open
`http://127.0.0.1:5173`.

Checks, from `backend`:

```powershell
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m pytest
```

From `frontend`: `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, `npm run build`.

## Next engineering task

The hackathon frontend workspace for `SYN-DEMO`, then a public deployment.
See [Hackathon remaining work](docs/HACKATHON_REMAINING_WORK.md). The system
is not production-ready.
