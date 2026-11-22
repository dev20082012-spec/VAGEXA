"""Permission catalog and session CSRF hashes.

Revision ID: 20261122_0002
Revises: 20261122_0001
"""

from alembic import op

revision = "20261122_0002"
down_revision = "20261122_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sessions ADD COLUMN csrf_token_hash text;

        CREATE TABLE permissions (
          id smallint PRIMARY KEY,
          name text NOT NULL UNIQUE
        );

        CREATE TABLE role_permissions (
          role_id smallint NOT NULL REFERENCES roles (id) ON DELETE RESTRICT,
          permission_id smallint NOT NULL REFERENCES permissions (id) ON DELETE RESTRICT,
          PRIMARY KEY (role_id, permission_id)
        );

        INSERT INTO permissions (id, name) VALUES
          (1, 'users.manage'),
          (2, 'cases.create'),
          (3, 'cases.assign');

        INSERT INTO role_permissions (role_id, permission_id) VALUES
          (1, 1),
          (1, 2),
          (1, 3),
          (2, 2);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS role_permissions;
        DROP TABLE IF EXISTS permissions;
        ALTER TABLE sessions DROP COLUMN IF EXISTS csrf_token_hash;
        """
    )
