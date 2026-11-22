"""Statement ingestion tables.

Revision ID: 20261122_0003
Revises: 20261122_0002
"""

from alembic import op

revision = "20261122_0003"
down_revision = "20261122_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE provenance_records (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          data_classification text NOT NULL,
          source_system text NOT NULL,
          source_reference text NOT NULL,
          collected_at timestamptz NOT NULL,
          collected_by text NOT NULL,
          method_name text NOT NULL,
          raw_hash char(64)
        );
        CREATE TRIGGER provenance_records_append_only
          BEFORE UPDATE OR DELETE ON provenance_records
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE accounts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          kind text NOT NULL CHECK (kind IN ('bank', 'vpa')),
          account_number_norm text,
          ifsc_norm text,
          vpa_norm text,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT accounts_bank CHECK (
            kind <> 'bank' OR (account_number_norm IS NOT NULL AND ifsc_norm IS NOT NULL AND vpa_norm IS NULL)
          ),
          CONSTRAINT accounts_vpa CHECK (
            kind <> 'vpa' OR (vpa_norm IS NOT NULL AND account_number_norm IS NULL)
          )
        );
        CREATE UNIQUE INDEX accounts_bank_key ON accounts (account_number_norm, ifsc_norm)
          WHERE account_number_norm IS NOT NULL AND ifsc_norm IS NOT NULL;
        CREATE UNIQUE INDEX accounts_vpa_key ON accounts (vpa_norm) WHERE vpa_norm IS NOT NULL;
        CREATE TRIGGER accounts_append_only
          BEFORE UPDATE OR DELETE ON accounts
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE jobs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          kind text NOT NULL,
          case_id uuid NOT NULL REFERENCES cases (id),
          payload jsonb NOT NULL,
          status text NOT NULL CHECK (status IN (
            'queued', 'running', 'succeeded', 'succeeded_with_errors', 'failed', 'cancelled'
          )),
          attempts integer NOT NULL DEFAULT 0,
          locked_at timestamptz,
          locked_by text,
          error_code text,
          created_at timestamptz NOT NULL DEFAULT now(),
          finished_at timestamptz
        );
        CREATE INDEX jobs_status ON jobs (status, created_at);

        CREATE TABLE source_files (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          job_id uuid REFERENCES jobs (id),
          sha256 char(64) NOT NULL,
          byte_size bigint NOT NULL CHECK (byte_size > 0),
          original_filename text NOT NULL,
          media_type text NOT NULL,
          storage_key text NOT NULL UNIQUE,
          status text NOT NULL CHECK (status IN ('stored', 'parsed', 'rejected')),
          data_classification text NOT NULL,
          uploaded_by uuid NOT NULL REFERENCES users (id),
          uploaded_at timestamptz NOT NULL DEFAULT now(),
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          UNIQUE (case_id, sha256)
        );

        CREATE TABLE statements (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id uuid NOT NULL REFERENCES cases (id),
          source_file_id uuid NOT NULL REFERENCES source_files (id),
          account_id uuid NOT NULL REFERENCES accounts (id),
          parser_name text NOT NULL,
          parser_version text NOT NULL,
          currency char(3) NOT NULL,
          data_classification text NOT NULL,
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          supersedes_statement_id uuid REFERENCES statements (id)
        );

        CREATE TABLE transactions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          statement_id uuid NOT NULL REFERENCES statements (id),
          case_id uuid NOT NULL REFERENCES cases (id),
          line_number integer NOT NULL CHECK (line_number > 0),
          booking_date date NOT NULL,
          booking_time time,
          time_precision text NOT NULL CHECK (time_precision IN ('date', 'time')),
          direction text NOT NULL CHECK (direction IN ('debit', 'credit')),
          amount numeric(20, 4) NOT NULL CHECK (amount > 0),
          currency char(3) NOT NULL,
          rail text NOT NULL,
          narration_raw text NOT NULL DEFAULT '',
          counterparty_account_id uuid REFERENCES accounts (id),
          counterparty_resolution text NOT NULL CHECK (
            counterparty_resolution IN ('structured_field', 'narration_pattern', 'unresolved')
          ),
          reference_raw text,
          source_transaction_id text,
          original_record jsonb NOT NULL,
          data_classification text NOT NULL,
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (statement_id, line_number)
        );
        CREATE UNIQUE INDEX transactions_source_id
          ON transactions (case_id, source_transaction_id)
          WHERE source_transaction_id IS NOT NULL;
        CREATE INDEX transactions_case_date ON transactions (case_id, booking_date, line_number);
        CREATE TRIGGER transactions_append_only
          BEFORE UPDATE OR DELETE ON transactions
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE account_observations (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id uuid NOT NULL REFERENCES accounts (id),
          case_id uuid NOT NULL REFERENCES cases (id),
          statement_id uuid REFERENCES statements (id),
          account_number_raw text,
          data_classification text NOT NULL,
          provenance_id uuid NOT NULL REFERENCES provenance_records (id),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER account_observations_append_only
          BEFORE UPDATE OR DELETE ON account_observations
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();

        CREATE TABLE ingestion_issues (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          job_id uuid NOT NULL REFERENCES jobs (id),
          case_id uuid NOT NULL REFERENCES cases (id),
          line_number integer NOT NULL,
          field_name text NOT NULL,
          category text NOT NULL,
          message text NOT NULL,
          suggestion text NOT NULL,
          blocks_insert boolean NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER ingestion_issues_append_only
          BEFORE UPDATE OR DELETE ON ingestion_issues
          FOR EACH ROW EXECUTE FUNCTION vagexa_forbid_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS ingestion_issues;
        DROP TABLE IF EXISTS account_observations;
        DROP TABLE IF EXISTS transactions;
        DROP TABLE IF EXISTS statements;
        DROP TABLE IF EXISTS source_files;
        DROP TABLE IF EXISTS jobs;
        DROP TABLE IF EXISTS accounts;
        DROP TABLE IF EXISTS provenance_records;
        """
    )
