import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DependencyList,
  type ReactNode,
} from "react";
import { errorText } from "./api/client";
import type { SourceRecord } from "./api/types";
import {
  CLASS_TEXT,
  KIND_LABEL,
  formatAmount,
  formatBooking,
  formatDateTime,
  shortId,
} from "./format";

export type Loaded<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

/** Load once per dependency change. A failed request stays an error; it is never replaced by sample data. */
export function useLoad<T>(
  load: () => Promise<T>,
  deps: DependencyList,
  fallback = "Could not load.",
): Loaded<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const loader = useRef(load);
  loader.current = load;

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    loader
      .current()
      .then((value) => {
        if (live) setData(value);
      })
      .catch((err: unknown) => {
        if (live) setError(errorText(err, fallback));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((value) => value + 1), []);
  return { data, error, loading, reload };
}

export function SyntheticNotice({ text }: { text?: string | null }) {
  return (
    <div className="synthetic" role="status">
      <span className="badge synthetic">Synthetic</span>
      <span>
        {text ?? "Synthetic demonstration records. These are not official investigative files."}
      </span>
    </div>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton" aria-label="Loading">
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} style={{ width: `${92 - index * 12}%` }} />
      ))}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-box" role="alert">
      <span>{message}</span>
      {onRetry ? (
        <button className="quiet" type="button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function Panel({
  title,
  subtitle,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className ?? ""}`}>
      {title || actions ? (
        <div className="panel-head">
          <div>
            {title ? <h2>{title}</h2> : null}
            {subtitle ? <p className="muted small">{subtitle}</p> : null}
          </div>
          {actions ? <div className="actions">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="metric">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

export function ClassBadge({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="badge neutral">Not classified</span>;
  return (
    <span className={`badge ${value}`} title={CLASS_TEXT[value]}>
      {value.replace("_", " ").toLowerCase()}
    </span>
  );
}

export function AssertionBadge({ value }: { value: string }) {
  return (
    <span className={`badge ${value}`} title="Stored assertion kind">
      {value}
    </span>
  );
}

export function StatusBadge({ value }: { value: string }) {
  return <span className={`badge status-${value}`}>{value}</span>;
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

const RECORD_FIELDS: Record<string, [string, string][]> = {
  transaction: [
    ["subject_account_masked", "Statement account"],
    ["direction", "Direction"],
    ["counterparty_masked", "Counterparty"],
    ["reference", "Payment reference"],
    ["rail", "Rail"],
    ["narration", "Narration"],
    ["source_transaction_id", "Source transaction id"],
    ["line_number", "Statement line"],
    ["counterparty_resolution", "Counterparty taken from"],
  ],
  dns_observation: [
    ["domain", "Domain"],
    ["rrtype", "Record type"],
    ["rdata", "Answer"],
    ["resolver", "Resolver label"],
  ],
  hosting_observation: [
    ["ip", "IP address"],
    ["provider_name", "Provider string"],
    ["source_note", "Note"],
  ],
  gateway_record: [
    ["source_record_id", "Gateway record id"],
    ["source_system", "Source system"],
    ["payment_reference", "Payment reference"],
    ["payer_account_masked", "Payer account"],
    ["payee_account_masked", "Settlement account"],
    ["merchant_domain", "Merchant domain"],
    ["merchant_label", "Merchant label"],
  ],
};

export function SourceRecordView({
  item,
  showOriginal = true,
}: {
  item: SourceRecord;
  showOriginal?: boolean;
}) {
  const fields = RECORD_FIELDS[item.object_kind] ?? [];
  const amount = item.record.amount as string | undefined;
  const currency = item.record.currency as string | undefined;
  const original = item.record.original_record as Record<string, unknown> | undefined;
  return (
    <div className="record-card">
      <div className="panel-head">
        <div>
          <h3>{KIND_LABEL[item.object_kind] ?? item.object_kind}</h3>
          <p className="muted small mono">id {shortId(item.object_id)}</p>
        </div>
        <span
          className={`badge ${item.data_classification === "synthetic" ? "synthetic" : "neutral"}`}
        >
          {item.data_classification}
        </span>
      </div>
      <dl className="kv">
        {amount ? (
          <>
            <dt>Amount</dt>
            <dd className="mono">{formatAmount(amount, currency)}</dd>
          </>
        ) : null}
        <dt>
          {item.time.field === "booking_date"
            ? "Booked"
            : item.time.field === "processed_at"
              ? "Processed"
              : "Observed"}
        </dt>
        <dd>
          {item.time.field === "booking_date"
            ? formatBooking(item.time.value, item.time.clock)
            : formatDateTime(item.time.value)}
          <div className="muted small">{item.time.note}</div>
        </dd>
        {fields.map(([key, label]) => (
          <FieldRow key={key} label={label} value={display(item.record[key])} />
        ))}
        {item.provenance ? (
          <>
            <dt>Source</dt>
            <dd>
              {item.provenance.source_system} · method {item.provenance.method_name}
              <div className="muted small mono">ref {item.provenance.source_reference}</div>
              <div className="muted small">
                Collected {formatDateTime(item.provenance.collected_at)}
              </div>
            </dd>
          </>
        ) : null}
      </dl>
      {showOriginal && original ? (
        <details>
          <summary className="small">Original record as supplied</summary>
          <dl className="kv small">
            {Object.entries(original).map(([key, value]) => (
              <FieldRow key={key} label={key} value={display(value)} mono />
            ))}
          </dl>
        </details>
      ) : null}
    </div>
  );
}

function FieldRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <>
      <dt>{label}</dt>
      <dd className={mono ? "mono" : undefined}>{value}</dd>
    </>
  );
}
