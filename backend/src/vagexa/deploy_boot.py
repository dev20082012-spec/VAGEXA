"""Prepare the synthetic demonstration after migrations. Does not erase data.

Usage, after `alembic upgrade head`:
    python -m vagexa.deploy_boot

The bootstrap password is read from the environment and is not printed.
An existing user is left in place. SYN-DEMO is loaded again only as an
idempotent insert.
"""

from sqlalchemy import select

from vagexa.adapters.persistence.models import User
from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.api.errors import Problem
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings
from vagexa.demo_seed import seed_demo


def main() -> None:
    settings = load_settings()
    if settings.data_mode != "synthetic":
        raise SystemExit("Demonstration boot refuses operational mode.")
    if not settings.bootstrap_username or not settings.bootstrap_password:
        raise SystemExit("Set VAGEXA_BOOTSTRAP_USERNAME and VAGEXA_BOOTSTRAP_PASSWORD.")
    init_engine(settings)
    db = open_session()
    try:
        existing = db.scalar(select(User).where(User.username == settings.bootstrap_username))
        if existing is None:
            create_user(
                db,
                username=settings.bootstrap_username,
                display_name=settings.bootstrap_display_name,
                password=settings.bootstrap_password,
                role_names=["investigator"],
            )
            db.commit()
            print("created investigator")
        else:
            print("investigator exists")
        result = seed_demo(db, settings, settings.bootstrap_username)
        db.commit()
    except Problem as exc:
        db.rollback()
        raise SystemExit(exc.detail) from exc
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"{result['reference']} {result['case_id']}")


if __name__ == "__main__":
    main()
