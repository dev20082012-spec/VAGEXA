import type {
  ActivityRow,
  AuditEventRow,
  CaseRecord,
  CrossCaseSignal,
  Entities,
  FinancialSummary,
  FindingRow,
  GraphPayload,
  IndicatorHit,
  IngestionIssue,
  IngestionJob,
  InvestigationSummary,
  ObservationList,
  ProblemBody,
  RelationshipRow,
  SessionBody,
  SourceRecord,
  TraceResult,
  TransactionRow,
  WalkResult,
} from "./types";

export const SESSION_EXPIRED_EVENT = "vagexa:session-expired";

let csrfToken: string | null = null;

function rememberSession(body: SessionBody) {
  csrfToken = body.csrf_token;
}

export class ApiError extends Error {
  status: number;
  body: ProblemBody;

  constructor(status: number, body: ProblemBody) {
    super(body.detail || body.title);
    this.status = status;
    this.body = body;
  }
}

export function errorText(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return err.body.detail || err.body.title || fallback;
  }
  return fallback;
}

async function fail(response: Response, path: string): Promise<never> {
  let body: ProblemBody;
  try {
    body = (await response.json()) as ProblemBody;
  } catch {
    body = {
      type: "about:blank",
      title: "Request failed",
      status: response.status,
      detail: `The server answered ${response.status}.`,
    };
  }
  if (response.status === 401 && !path.startsWith("/api/v1/auth/")) {
    csrfToken = null;
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
  throw new ApiError(response.status, body);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken && init?.method && init.method !== "GET" ? { "X-CSRF-Token": csrfToken } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    return fail(response, path);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function upload<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
    body,
  });
  if (!response.ok) {
    return fail(response, path);
  }
  return (await response.json()) as T;
}

const caseRoot = (caseId: string) => `/api/v1/cases/${caseId}`;

export const api = {
  me: async () => {
    const body = await request<SessionBody>("/api/v1/auth/me");
    rememberSession(body);
    return body;
  },
  login: async (username: string, password: string) => {
    const body = await request<SessionBody>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    rememberSession(body);
    return body;
  },
  changePassword: async (currentPassword: string, newPassword: string) => {
    const body = await request<{ status: string; csrf_token: string }>("/api/v1/auth/password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    csrfToken = body.csrf_token;
    return body;
  },
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  cases: () => request<{ items: CaseRecord[]; next_cursor: string | null }>("/api/v1/cases"),
  case: (id: string) => request<CaseRecord>(caseRoot(id)),
  createCase: (input: { reference: string; title: string; opened_on: string }) =>
    request<CaseRecord>("/api/v1/cases", {
      method: "POST",
      body: JSON.stringify({ ...input, data_classification: "synthetic" }),
    }),
  summary: (caseId: string) => request<InvestigationSummary>(`${caseRoot(caseId)}/summary`),
  entities: (caseId: string) => request<Entities>(`${caseRoot(caseId)}/entities`),
  auditEvents: (caseId: string) =>
    request<{ items: AuditEventRow[] }>(`${caseRoot(caseId)}/audit-events`),
  evidence: (caseId: string, kind: string, objectId: string) =>
    request<SourceRecord>(`${caseRoot(caseId)}/evidence/${kind}/${objectId}`),
  relationshipEvidence: (relationshipId: string) =>
    request<{ relationship_id: string; analytical_note: string; items: SourceRecord[] }>(
      `/api/v1/relationships/${relationshipId}/evidence`,
    ),
  gatewayRecords: (caseId: string) =>
    request<{ items: SourceRecord[] }>(`${caseRoot(caseId)}/gateway-records`),
  uploadDataset: (caseId: string, file: File, subjectAccount: string, subjectIfsc: string) => {
    const body = new FormData();
    body.set("file", file);
    if (subjectAccount) body.set("subject_account", subjectAccount);
    if (subjectIfsc) body.set("subject_ifsc", subjectIfsc);
    return upload<IngestionJob>(`${caseRoot(caseId)}/statements`, body);
  },
  jobIssues: (jobId: string) =>
    request<{ items: IngestionIssue[] }>(`/api/v1/jobs/${jobId}/issues`),
  transactions: (caseId: string, query = "") =>
    request<{ items: TransactionRow[]; next_cursor: string | null }>(
      `${caseRoot(caseId)}/transactions${query}`,
    ),
  financialSummary: (caseId: string) =>
    request<FinancialSummary>(`${caseRoot(caseId)}/financial-summary`),
  activity: (caseId: string) =>
    request<{ items: ActivityRow[]; comparison: string }>(`${caseRoot(caseId)}/activity`),
  getTrace: (traceId: string) => request<TraceResult>(`/api/v1/traces/${traceId}`),
  trace: (caseId: string, seedIds: string[], maxLayer: number) =>
    request<TraceResult>(`${caseRoot(caseId)}/traces`, {
      method: "POST",
      body: JSON.stringify({
        seed_transaction_ids: seedIds,
        policy: "fifo",
        policy_version: "fifo.v1",
        max_layer: maxLayer,
        currency: "INR",
      }),
    }),
  listIndicators: (caseId: string) =>
    request<{ items: IndicatorHit[]; run_id: string | null; parameters?: Record<string, unknown> }>(
      `${caseRoot(caseId)}/indicators`,
    ),
  indicators: (caseId: string, windowStart: string, windowEnd: string) =>
    request<{ items: IndicatorHit[] }>(`${caseRoot(caseId)}/indicator-runs`, {
      method: "POST",
      body: JSON.stringify({ window_start: windowStart, window_end: windowEnd, currency: "INR" }),
    }),
  findings: (caseId: string) => request<{ items: FindingRow[] }>(`${caseRoot(caseId)}/findings`),
  walk: (caseId: string, accountId: string, direction: string) =>
    request<WalkResult>(`${caseRoot(caseId)}/statement-walks`, {
      method: "POST",
      body: JSON.stringify({
        start_account_id: accountId,
        direction,
        max_layer: 3,
        currency: "INR",
        window_start: "2026-01-01",
        window_end: "2026-12-31",
      }),
    }),
  graph: (caseId: string, query: string) =>
    request<GraphPayload>(`${caseRoot(caseId)}/graph${query}`),
  crossCaseSignals: (caseId: string) =>
    request<{ items: CrossCaseSignal[] }>(`${caseRoot(caseId)}/cross-case-signals`),
  observations: (caseId: string) => request<ObservationList>(`${caseRoot(caseId)}/observations`),
  addObservation: (caseId: string, body: Record<string, string>) =>
    request<{ id: string; kind: string }>(`${caseRoot(caseId)}/observations`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  importObservations: (caseId: string, file: File) => {
    const body = new FormData();
    body.set("file", file);
    return upload<{ inserted: number; errors: { line_number: number; message: string }[] }>(
      `${caseRoot(caseId)}/observations/import`,
      body,
    );
  },
  requestLookup: (caseId: string, domain: string) =>
    request<void>(`${caseRoot(caseId)}/observations/dns`, {
      method: "POST",
      body: JSON.stringify({ domain }),
    }),
  relationships: (caseId: string) =>
    request<{ items: RelationshipRow[] }>(`${caseRoot(caseId)}/relationships`),
  correlate: (caseId: string) =>
    request<{ inserted: number; already_present: number; items: RelationshipRow[] }>(
      `${caseRoot(caseId)}/correlations`,
      { method: "POST" },
    ),
  reviewRelationship: (id: string, decision: "confirm" | "reject", note: string) =>
    request<RelationshipRow>(`/api/v1/relationships/${id}/${decision}`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
};
