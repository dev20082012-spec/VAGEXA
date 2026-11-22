"""Reviewable correlation proposals. Sources stay append-only.

Revision ID: 20261122_0006
Revises: 20261122_0005
"""

from alembic import op

revision = "20261122_0006"
down_revision = "20261122_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE analytical_runs DROP CONSTRAINT analytical_runs_run_kind_check;
        ALTER TABLE analytical_runs ADD CONSTRAINT analytical_runs_run_kind_check
          CHECK (run_kind IN ('trace', 'indicators', 'statement_walk', 'correlation'));

        CREATE TABLE relationships (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          analytical_run_id uuid NOT NULL REFERENCES analytical_runs (id),
          pair_key text NOT NULL,
          from_kind text NOT NULL CHECK (from_kind IN ('account', 'domain', 'ip')),
          from_id uuid NOT NULL,
          to_kind text NOT NULL CHECK (to_kind IN ('account', 'domain', 'ip')),
          to_id uuid NOT NULL,
          rel_type text NOT NULL CHECK (rel_type IN (
            'mentioned_in', 'infrastructure_overlap', 'same_payment'
          )),
          assertion_kind text NOT NULL CHECK (assertion_kind IN ('verified', 'inferred', 'hypothesis')),
          method_name text NOT NULL,
          method_version text NOT NULL,
          status text NOT NULL CHECK (status IN ('proposed', 'confirmed', 'rejected')),
          limitation text NOT NULL CHECK (length(limitation) > 0),
          explanation text NOT NULL,
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          created_by uuid NOT NULL REFERENCES users (id),
          created_at timestamptz NOT NULL DEFAULT now(),
          decided_by uuid REFERENCES users (id),
          decided_at timestamptz,
          UNIQUE (case_id, pair_key)
        );
        CREATE INDEX relationships_case_status ON relationships (case_id, status);

        CREATE OR REPLACE FUNCTION vagexa_relationship_decision() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status <> 'proposed' THEN
            RAISE EXCEPTION 'relationship decision is final';
          END IF;
          IF NEW.status NOT IN ('confirmed', 'rejected') THEN
            RAISE EXCEPTION 'invalid relationship status';
          END IF;
          IF NEW.assertion_kind IS DISTINCT FROM OLD.assertion_kind
             OR NEW.rel_type IS DISTINCT FROM OLD.rel_type
             OR NEW.from_id IS DISTINCT FROM OLD.from_id
             OR NEW.to_id IS DISTINCT FROM OLD.to_id
             OR NEW.limitation IS DISTINCT FROM OLD.limitation
             OR NEW.explanation IS DISTINCT FROM OLD.explanation
             OR NEW.pair_key IS DISTINCT FROM OLD.pair_key THEN
            RAISE EXCEPTION 'relationship evidence columns are fixed';
          END IF;
          RETURN NEW;
        END;
        $$;
        CREATE TRIGGER relationships_decision
          BEFORE UPDATE ON relationships
          FOR EACH ROW EXECUTE FUNCTION vagexa_relationship_decision();

        CREATE TABLE relationship_support (
          relationship_id uuid NOT NULL REFERENCES relationships (id),
          object_kind text NOT NULL CHECK (object_kind IN ('transaction', 'dns_observation', 'hosting_observation')),
          object_id uuid NOT NULL,
          PRIMARY KEY (relationship_id, object_kind, object_id)
        );
        CREATE TRIGGER relationship_support_append_only
          BEFORE UPDATE OR DELETE ON relationship_support
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE relationship_reviews (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          relationship_id uuid NOT NULL REFERENCES relationships (id),
          case_id uuid NOT NULL REFERENCES cases (id),
          decision text NOT NULL CHECK (decision IN ('confirmed', 'rejected')),
          reason text NOT NULL,
          decided_by uuid NOT NULL REFERENCES users (id),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER relationship_reviews_append_only
          BEFORE UPDATE OR DELETE ON relationship_reviews
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS relationship_reviews;
        DROP TABLE IF EXISTS relationship_support;
        DROP TABLE IF EXISTS relationships;
        ALTER TABLE analytical_runs DROP CONSTRAINT analytical_runs_run_kind_check;
        ALTER TABLE analytical_runs ADD CONSTRAINT analytical_runs_run_kind_check
          CHECK (run_kind IN ('trace', 'indicators', 'statement_walk'));
        """
    )
