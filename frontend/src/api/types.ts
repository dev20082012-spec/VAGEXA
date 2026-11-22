export type CaseRecord = {
  id: string;
  reference: string;
  title: string;
  status: "open" | "closed";
  data_classification: "synthetic" | "official";
  opened_on: string;
  synthetic_batch_id?: string | null;
  counts?: { statements: number; transactions: number; proposed_relationships: number };
};

export type ProblemBody = {
  type: string;
  title: string;
  status: number;
  detail: string;
  request_id?: string;
  errors?: { field: string; reason: string }[];
};

export type IngestionJob = {
  id: string;
  status: string;
  error_code: string | null;
  summary: {
    original_filename: string | null;
    records_total: number;
    records_valid: number;
    records_invalid: number;
    records_duplicate: number;
    records_potential_duplicate: number;
    idempotent_replay: boolean;
    unexpected_columns: string[];
    data_classification: string | null;
  };
};

export type IngestionIssue = {
  line_number: number;
  field_name: string;
  category: string;
  message: string;
  suggestion: string;
  blocks_insert: boolean;
};

export type TransactionRow = {
  id: string;
  account_id: string | null;
  account_masked: string | null;
  counterparty_account_id: string | null;
  line_number: number;
  booking_date: string;
  booking_time: string | null;
  time_precision: string;
  direction: "debit" | "credit";
  amount: string;
  currency: string;
  rail: string;
  counterparty_masked: string | null;
  counterparty_resolution: string;
  reference_raw: string | null;
  source_transaction_id: string | null;
  data_classification: string;
};

export type InvestigationSummary = {
  case: {
    id: string;
    reference: string;
    title: string;
    status: string;
    data_classification: string;
    opened_on: string;
  };
  synthetic_notice: string | null;
  counts: {
    statements: number;
    transactions: number;
    dns_observations: number;
    hosting_observations: number;
    gateway_records: number;
    findings: number;
    relationships: number;
  };
  relationships_by_classification: Record<string, number>;
  cross_domain_by_classification: Record<string, number>;
  overlap_count: number;
  latest_trace: {
    id: string;
    method_version: string;
    max_layer: number | null;
    flow_count: number;
    residuals: {
      account_masked: string | null;
      amount: string;
      currency: string;
      reason: string;
    }[];
  } | null;
  indicators: {
    code: string;
    account_masked: string | null;
    support_count: number;
    assertion_kind: string;
  }[];
  key_relationships: {
    id: string;
    rel_type: string;
    classification: string | null;
    from_label: string | null;
    to_label: string | null;
    status: string;
  }[];
  recent_activity: { action: string; outcome: string; occurred_at: string }[];
  limitations: string;
};

export type Entities = {
  data_classification: string;
  accounts: { id: string; masked: string | null; role: string; statement_rows: number }[];
  domains: { id: string; name: string; dns_observations: number; in_gateway_record: boolean }[];
  ip_addresses: { id: string; address: string }[];
  note: string;
};

export type SourceRecord = {
  object_kind: string;
  object_id: string;
  data_classification: string;
  time: { field: string; value: string; clock: string | null; note: string };
  record: Record<string, unknown>;
  provenance: {
    id: string;
    source_system: string;
    source_reference: string;
    collected_at: string;
    method_name: string;
    data_classification: string;
  } | null;
};

export type AuditEventRow = {
  action: string;
  outcome: string;
  object_kind: string;
  occurred_at: string;
};

export type TraceFlow = {
  from_account_masked: string | null;
  to_account_masked: string | null;
  amount: string;
  currency: string;
  layer_to: number;
  assertion_kind: string;
  method_name: string;
  exit_kind: string | null;
  booking_date: string | null;
  booking_time: string | null;
  hours_after_previous: string | null;
  source_transaction_id: string;
  reference: string | null;
};

export type TraceResult = {
  id: string;
  status: string;
  error_code: string | null;
  method_version: string;
  max_layer: number;
  limitations: string;
  output_hash: string | null;
  path_summary?: {
    origin_accounts_masked: string[];
    accounts_by_layer: { layer: number; accounts_masked: string[] }[];
    holding_accounts_masked: string[];
    note: string;
  };
  flows: TraceFlow[];
  residuals: {
    account_masked: string | null;
    amount: string;
    currency: string;
    reason: string;
  }[];
};

export type IndicatorHit = {
  code: string;
  account_masked: string | null;
  account_id?: string;
  assertion_kind: string;
  method_version: string;
  support_transaction_ids: string[];
  limitations: string;
  window_start?: string;
  window_end?: string;
};

export type FindingRow = {
  id: string;
  analytical_run_id: string;
  finding_kind: string;
  summary: string;
  assertion_kind: string;
  limitations: string;
  method_name: string;
  method_version: string;
  evidence_ids: string[];
  support_transaction_ids: string[];
};

export type ActivityRow = {
  account_masked: string | null;
  account_id: string;
  currency: string;
  incoming_count: number;
  outgoing_count: number;
  incoming_amount: string;
  outgoing_amount: string;
  unique_counterparties: number;
  average_amount: string | null;
  median_amount: string | null;
  maximum_amount: string | null;
  period_start: string;
  period_end: string;
  row_count: number;
  coverage: string;
};

export type FinancialSummary = {
  data_classification: string;
  transaction_count: number;
  currencies: string[];
  activity: ActivityRow[];
  latest_trace_status: string | null;
  indicator_codes: string[];
  coverage: string;
};

export type WalkResult = {
  status: string;
  method_version: string;
  direction: string;
  limitations: string;
  truncated: boolean;
  paths: {
    stop_reason: string;
    hops: {
      from_account_masked: string | null;
      to_account_masked: string | null;
      amount: string;
      booking_date: string | null;
      hours_after_previous: string | null;
    }[];
  }[];
};

export type GraphNode = {
  id: string;
  kind: "account" | "cash_exit" | "domain" | "ip" | "provider";
  label: string;
  data_classification: string;
  residuals: { amount: string; currency: string; reason: string; trace_run_id: string }[];
};

export type GraphEdge = {
  id: string;
  from: string;
  to: string;
  kind: string;
  assertion_kind: "verified" | "inferred" | "hypothesis";
  method_name: string;
  method_version: string;
  amount: string;
  currency: string;
  booking_date: string | null;
  provenance_id: string | null;
  evidence_ids: string[];
  source_transaction_ids: string[];
  layer_to: number | null;
  trace_run_id: string | null;
  explanation: string;
  support: { object_kind: string; object_id: string }[];
  relationship_id: string | null;
  classification: string | null;
  status: string | null;
};

export type GraphPayload = {
  bounds: { case_id: string; focus: string | null; max_hops: number; trace_id: string | null };
  truncated: boolean;
  limitations: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  components: { id: string; node_ids: string[] }[];
  path: string[] | null;
  path_reason: string | null;
};

export type CrossCaseSignal = {
  identifier_kind: string;
  masked: string;
  other_case_count: number;
  assertion_kind: string;
  method: string;
  limitations: string;
};

export type RelationshipRow = {
  id: string;
  analytical_run_id: string;
  rel_type: string;
  from_kind: string;
  from_id: string;
  to_kind: string;
  to_id: string;
  assertion_kind: string;
  classification: string | null;
  claim: string | null;
  from_label: string | null;
  to_label: string | null;
  method_version: string;
  status: "proposed" | "confirmed" | "rejected";
  limitation: string;
  explanation: string;
  temporal_context: {
    object_kind: string;
    object_id: string;
    field: string;
    value: string;
    clock: string | null;
    note: string;
  }[];
  support: { object_kind: string; object_id: string }[];
  reviews: { decision: string; reason: string; created_at: string | null }[];
};

export type ObservationList = {
  data_classification: string;
  limitation: string;
  registration_reason: string;
  certificate_reason: string;
  dns: {
    id: string;
    domain: string;
    rrtype: string;
    rdata: string;
    observed_at: string;
    resolver: string;
    provenance_id: string;
    data_classification: string;
  }[];
  hosting: {
    id: string;
    ip: string | null;
    provider_name: string | null;
    source_note: string;
    observed_at: string;
    provenance_id: string;
    data_classification: string;
  }[];
};

export type SessionBody = {
  user: { id: string; username: string; display_name: string };
  roles: string[];
  permissions: string[];
  data_mode: string;
  csrf_token: string;
};
