import os

os.environ["VAGEXA_DATA_MODE"] = "synthetic"
os.environ["VAGEXA_DATABASE_URL"] = "postgresql+psycopg://vagexa@127.0.0.1:5433/vagexa_test"
os.environ["VAGEXA_COOKIE_SECURE"] = "false"
os.environ["VAGEXA_LOG_LEVEL"] = "warning"

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from vagexa.api.main import create_app
from vagexa.config import load_settings


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def clean_rows() -> Iterator[None]:
    yield
    engine = create_engine(os.environ["VAGEXA_DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE relationship_reviews, relationship_support, relationships, gateway_records,
                         dns_observations, hosting_observations, domain_names, ip_addresses,
                         finding_support, findings, evidence_records, account_indicators,
                         trace_residuals, trace_flows, trace_seeds, analytical_runs,
                         ingestion_issues, account_observations, transactions, statements,
                         source_files, jobs, accounts, provenance_records, audit_events,
                         case_assignments, cases, synthetic_batches, sessions, user_roles,
                         users RESTART IDENTITY CASCADE
                """
            )
        )
    engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(load_settings())
    with TestClient(app) as test_client:
        yield test_client
