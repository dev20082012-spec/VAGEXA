"""Investigator-supplied DNS and hosting observations.

Revision ID: 20261122_0005
Revises: 20261122_0004

dns_observations.case_id is required. The published column list treated the
answer as global, and a global read would show another case's collection time.
"""

from alembic import op

revision = "20261122_0005"
down_revision = "20261122_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE domain_names (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          name_norm text NOT NULL UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER domain_names_append_only
          BEFORE UPDATE OR DELETE ON domain_names
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE ip_addresses (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          address inet NOT NULL UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER ip_addresses_append_only
          BEFORE UPDATE OR DELETE ON ip_addresses
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE dns_observations (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          domain_id uuid NOT NULL REFERENCES domain_names (id),
          rrtype text NOT NULL CHECK (rrtype IN ('A', 'AAAA')),
          rdata text NOT NULL,
          ip_address_id uuid REFERENCES ip_addresses (id),
          observed_at timestamptz NOT NULL,
          resolver text NOT NULL,
          data_classification text NOT NULL,
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX dns_observations_domain_time ON dns_observations (domain_id, observed_at);
        CREATE INDEX dns_observations_case ON dns_observations (case_id, observed_at);
        CREATE TRIGGER dns_observations_append_only
          BEFORE UPDATE OR DELETE ON dns_observations
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE hosting_observations (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          ip_address_id uuid REFERENCES ip_addresses (id),
          provider_name text,
          source_note text NOT NULL,
          observed_at timestamptz NOT NULL,
          data_classification text NOT NULL,
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          created_at timestamptz NOT NULL DEFAULT now(),
          CHECK (ip_address_id IS NOT NULL OR provider_name IS NOT NULL)
        );
        CREATE INDEX hosting_observations_case ON hosting_observations (case_id, observed_at);
        CREATE TRIGGER hosting_observations_append_only
          BEFORE UPDATE OR DELETE ON hosting_observations
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS hosting_observations;
        DROP TABLE IF EXISTS dns_observations;
        DROP TABLE IF EXISTS ip_addresses;
        DROP TABLE IF EXISTS domain_names;
        """
    )
