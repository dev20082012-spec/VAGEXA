"""Analytical runs, FIFO results, indicators, and findings.

Revision ID: 20261122_0004
Revises: 20261122_0003

complaint_id is stored without a foreign key. The complaints table is not in
this schema yet, and a trace does not invent one.
"""

from alembic import op

revision = "20261122_0004"
down_revision = "20261122_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS transactions_counterparty ON transactions (counterparty_account_id);

        CREATE TABLE analytical_runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          run_kind text NOT NULL CHECK (run_kind IN ('trace', 'indicators', 'statement_walk')),
          method_name text NOT NULL,
          method_version text NOT NULL,
          parameters jsonb NOT NULL,
          input_hash char(64) NOT NULL,
          output_hash char(64),
          output jsonb,
          status text NOT NULL CHECK (status IN ('succeeded', 'failed')),
          error_code text,
          requested_by uuid NOT NULL REFERENCES users (id),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX analytical_runs_case ON analytical_runs (case_id, created_at);
        CREATE TRIGGER analytical_runs_append_only
          BEFORE UPDATE OR DELETE ON analytical_runs
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE trace_seeds (
          analytical_run_id uuid NOT NULL REFERENCES analytical_runs (id),
          transaction_id uuid NOT NULL REFERENCES transactions (id),
          complaint_id uuid,
          PRIMARY KEY (analytical_run_id, transaction_id)
        );
        CREATE TRIGGER trace_seeds_append_only
          BEFORE UPDATE OR DELETE ON trace_seeds
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE trace_flows (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          analytical_run_id uuid NOT NULL REFERENCES analytical_runs (id),
          case_id uuid NOT NULL REFERENCES cases (id),
          origin_complaint_id uuid,
          from_account_id uuid NOT NULL REFERENCES accounts (id),
          to_account_id uuid REFERENCES accounts (id),
          exit_kind text CHECK (exit_kind IN ('cash', 'unresolved')),
          source_transaction_id uuid NOT NULL REFERENCES transactions (id),
          amount numeric(20, 4) NOT NULL CHECK (amount > 0),
          currency char(3) NOT NULL,
          layer_to integer NOT NULL CHECK (layer_to BETWEEN 0 AND 5),
          assertion_kind text NOT NULL CHECK (assertion_kind IN ('verified', 'inferred', 'hypothesis')),
          method_name text NOT NULL,
          method_version text NOT NULL,
          CONSTRAINT trace_flows_destination CHECK (
            (to_account_id IS NOT NULL AND exit_kind IS NULL)
            OR (to_account_id IS NULL AND exit_kind IS NOT NULL)
          )
        );
        CREATE INDEX trace_flows_run ON trace_flows (analytical_run_id, layer_to);
        CREATE TRIGGER trace_flows_append_only
          BEFORE UPDATE OR DELETE ON trace_flows
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE trace_residuals (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          analytical_run_id uuid NOT NULL REFERENCES analytical_runs (id),
          account_id uuid NOT NULL REFERENCES accounts (id),
          complaint_id uuid,
          amount numeric(20, 4) NOT NULL CHECK (amount > 0),
          currency char(3) NOT NULL,
          reason text NOT NULL CHECK (reason IN ('no_onward_record', 'outside_horizon', 'unallocated'))
        );
        CREATE INDEX trace_residuals_run ON trace_residuals (analytical_run_id);
        CREATE TRIGGER trace_residuals_append_only
          BEFORE UPDATE OR DELETE ON trace_residuals
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE account_indicators (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          analytical_run_id uuid NOT NULL REFERENCES analytical_runs (id),
          case_id uuid NOT NULL REFERENCES cases (id),
          account_id uuid NOT NULL REFERENCES accounts (id),
          code text NOT NULL CHECK (code IN ('FAN_IN', 'FAN_OUT', 'PASS_THROUGH')),
          window_start date NOT NULL,
          window_end date NOT NULL,
          threshold jsonb NOT NULL,
          support_transaction_ids uuid[] NOT NULL CHECK (cardinality(support_transaction_ids) > 0),
          assertion_kind text NOT NULL CHECK (assertion_kind = 'inferred'),
          method_name text NOT NULL,
          method_version text NOT NULL,
          limitations text NOT NULL CHECK (length(limitations) > 0)
        );
        CREATE INDEX account_indicators_case ON account_indicators (case_id, code);
        CREATE TRIGGER account_indicators_append_only
          BEFORE UPDATE OR DELETE ON account_indicators
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE evidence_records (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          kind text NOT NULL CHECK (kind IN (
            'source_file', 'transaction', 'observation', 'analytical_finding', 'report', 'annotation'
          )),
          object_id uuid NOT NULL,
          content_hash char(64) NOT NULL,
          supersedes_id uuid REFERENCES evidence_records (id),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (case_id, kind, object_id)
        );
        CREATE TRIGGER evidence_records_append_only
          BEFORE UPDATE OR DELETE ON evidence_records
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE findings (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          analytical_run_id uuid NOT NULL REFERENCES analytical_runs (id),
          case_id uuid NOT NULL REFERENCES cases (id),
          finding_kind text NOT NULL,
          summary text NOT NULL,
          assertion_kind text NOT NULL CHECK (assertion_kind IN ('verified', 'inferred', 'hypothesis')),
          limitations text NOT NULL CHECK (length(limitations) > 0),
          method_name text NOT NULL,
          method_version text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX findings_case ON findings (case_id, created_at);
        CREATE TRIGGER findings_append_only
          BEFORE UPDATE OR DELETE ON findings
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE finding_support (
          finding_id uuid NOT NULL REFERENCES findings (id),
          evidence_id uuid NOT NULL REFERENCES evidence_records (id),
          PRIMARY KEY (finding_id, evidence_id)
        );
        CREATE TRIGGER finding_support_append_only
          BEFORE UPDATE OR DELETE ON finding_support
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS finding_support;
        DROP TABLE IF EXISTS findings;
        DROP TABLE IF EXISTS evidence_records;
        DROP TABLE IF EXISTS account_indicators;
        DROP TABLE IF EXISTS trace_residuals;
        DROP TABLE IF EXISTS trace_flows;
        DROP TABLE IF EXISTS trace_seeds;
        DROP TABLE IF EXISTS analytical_runs;
        DROP INDEX IF EXISTS transactions_counterparty;
        """
    )
