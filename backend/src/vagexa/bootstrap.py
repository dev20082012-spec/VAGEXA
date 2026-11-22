"""Create the first local user from environment variables. Does not embed a password."""

from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.application.auth_service import create_user
from vagexa.config import load_settings


def main() -> None:
    settings = load_settings()
    if not settings.bootstrap_username or not settings.bootstrap_password:
        raise SystemExit("Set VAGEXA_BOOTSTRAP_USERNAME and VAGEXA_BOOTSTRAP_PASSWORD to create a user.")
    init_engine(settings)
    db = open_session()
    try:
        user = create_user(
            db,
            username=settings.bootstrap_username,
            display_name=settings.bootstrap_display_name,
            password=settings.bootstrap_password,
            role_names=["investigator"],
        )
        db.commit()
        print(f"created investigator {user.username} {user.id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
