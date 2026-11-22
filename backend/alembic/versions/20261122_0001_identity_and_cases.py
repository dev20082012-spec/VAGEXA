"""Identity, cases, and append-only audit.

Revision ID: 20261122_0001
Revises:
Create Date: 2026-11-22
"""

from alembic import op

revision = "20261122_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS citext;

        CREATE OR REPLACE FUNCTION vagexa_forbid_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'append-only table %', TG_TABLE_NAME;
        END;
        $$;

        CREATE TABLE roles (
          id smallint PRIMARY KEY,
          name text NOT NULL UNIQUE
        );

        INSERT INTO roles (id, name) VALUES
          (1, 'administrator'),
          (2, 'investigator'),
          (3, 'analyst'),
          (4, 'auditor');

        CREATE TABLE users (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          username citext NOT NULL UNIQUE,
          password_hash text NOT NULL,
          display_name text NOT NULL,
          status text NOT NULL CHECK (status IN ('active', 'disabled')),
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT users_username_len CHECK (char_length(username::text) BETWEEN 3 AND 64),
          CONSTRAINT users_username_shape CHECK (username::text ~ '^[A-Za-z0-9._-]+$'),
          CONSTRAINT users_display_name_len CHECK (char_length(display_name) BETWEEN 1 AND 120)
        );

        CREATE TABLE user_roles (
          user_id uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
          role_id smallint NOT NULL REFERENCES roles (id) ON DELETE RESTRICT,
          PRIMARY KEY (user_id, role_id)
        );

        CREATE TABLE sessions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
          token_hash text NOT NULL UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now(),
          expires_at timestamptz NOT NULL,
          revoked_at timestamptz,
          user_agent text,
          client_ip inet
        );

        CREATE TABLE synthetic_batches (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          scenario_key text NOT NULL,
          generator_version text NOT NULL,
          ground_truth_sha256 char(64) NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE cases (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          reference text NOT NULL UNIQUE,
          title text NOT NULL,
          status text NOT NULL CHECK (status IN ('open', 'closed')),
          data_classification text NOT NULL CHECK (data_classification IN ('official', 'synthetic')),
          synthetic_batch_id uuid REFERENCES synthetic_batches (id),
          opened_on date NOT NULL,
          created_by uuid NOT NULL REFERENCES users (id),
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT cases_classification_batch CHECK (
            (data_classification = 'synthetic' AND synthetic_batch_id IS NOT NULL)
            OR (data_classification <> 'synthetic' AND synthetic_batch_id IS NULL)
          ),
          CONSTRAINT cases_reference_len CHECK (char_length(reference) BETWEEN 1 AND 64),
          CONSTRAINT cases_title_len CHECK (char_length(title) BETWEEN 1 AND 200)
        );

        CREATE TABLE case_assignments (
          case_id uuid NOT NULL REFERENCES cases (id) ON DELETE RESTRICT,
          user_id uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
          case_role text NOT NULL CHECK (case_role IN ('lead', 'investigator', 'analyst', 'auditor')),
          assigned_at timestamptz NOT NULL DEFAULT now(),
          assigned_by uuid NOT NULL REFERENCES users (id),
          PRIMARY KEY (case_id, user_id)
        );

        CREATE TABLE audit_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          occurred_at timestamptz NOT NULL DEFAULT now(),
          actor_id uuid REFERENCES users (id),
          action text NOT NULL,
          case_id uuid REFERENCES cases (id),
          object_kind text NOT NULL,
          object_id text,
          request_id text,
          outcome text NOT NULL CHECK (outcome IN ('success', 'denied', 'failure')),
          detail jsonb NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE INDEX audit_events_login_failures
          ON audit_events (action, occurred_at);

        CREATE TRIGGER audit_events_append_only
          BEFORE UPDATE OR DELETE ON audit_events
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
        DROP TABLE IF EXISTS audit_events;
        DROP TABLE IF EXISTS case_assignments;
        DROP TABLE IF EXISTS cases;
        DROP TABLE IF EXISTS synthetic_batches;
        DROP TABLE IF EXISTS sessions;
        DROP TABLE IF EXISTS user_roles;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS roles;
        DROP FUNCTION IF EXISTS vagexa_forbid_mutation();
        """
    )
