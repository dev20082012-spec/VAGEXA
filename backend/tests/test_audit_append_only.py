import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError


def test_audit_events_reject_updates() -> None:
    engine = create_engine(os.environ["VAGEXA_DATABASE_URL"])
    with engine.connect() as connection:
        connection.execute(
            text(
                """
                INSERT INTO audit_events (action, object_kind, outcome, detail)
                VALUES ('case.open', 'case', 'success', '{}'::jsonb)
                """
            )
        )
        connection.commit()
        with pytest.raises(DBAPIError):
            connection.execute(text("UPDATE audit_events SET action = 'tampered'"))
            connection.commit()
    engine.dispose()
