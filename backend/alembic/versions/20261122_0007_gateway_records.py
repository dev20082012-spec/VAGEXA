"""Synthetic payment-gateway records that bridge a payment reference and a merchant domain.

Revision ID: 20261122_0007
Revises: 20261122_0006
"""

from alembic import op

revision = "20261122_0007"
down_revision = "20261122_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE gateway_records (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          source_record_id text NOT NULL,
          source_system text NOT NULL,
          payment_reference text NOT NULL,
          payer_account_id uuid REFERENCES accounts (id),
          payee_account_id uuid NOT NULL REFERENCES accounts (id),
          merchant_domain_id uuid NOT NULL REFERENCES domain_names (id),
          merchant_label text NOT NULL,
          amount numeric(20, 4) NOT NULL CHECK (amount > 0),
          currency char(3) NOT NULL,
          processed_at timestamptz NOT NULL,
          original_record jsonb NOT NULL,
          data_classification text NOT NULL,
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (case_id, source_record_id)
        );
        CREATE INDEX gateway_records_reference ON gateway_records (case_id, payment_reference);
        CREATE TRIGGER gateway_records_append_only
          BEFORE UPDATE OR DELETE ON gateway_records
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        ALTER TABLE relationships DROP CONSTRAINT relationships_rel_type_check;
        ALTER TABLE relationships ADD CONSTRAINT relationships_rel_type_check CHECK (rel_type IN (
          'mentioned_in', 'infrastructure_overlap', 'same_payment', 'gateway_merchant'
        ));
        ALTER TABLE relationship_support DROP CONSTRAINT relationship_support_object_kind_check;
        ALTER TABLE relationship_support ADD CONSTRAINT relationship_support_object_kind_check
          CHECK (object_kind IN ('transaction', 'dns_observation', 'hosting_observation', 'gateway_record'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE relationship_support DROP CONSTRAINT relationship_support_object_kind_check;
        ALTER TABLE relationship_support ADD CONSTRAINT relationship_support_object_kind_check
          CHECK (object_kind IN ('transaction', 'dns_observation', 'hosting_observation'));
        ALTER TABLE relationships DROP CONSTRAINT relationships_rel_type_check;
        ALTER TABLE relationships ADD CONSTRAINT relationships_rel_type_check CHECK (rel_type IN (
          'mentioned_in', 'infrastructure_overlap', 'same_payment'
        ));
        DROP TABLE IF EXISTS gateway_records;
        """
    )
