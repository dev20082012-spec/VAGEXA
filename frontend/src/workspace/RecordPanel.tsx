import { api } from "../api/client";
import { ErrorBox, Skeleton, SourceRecordView, useLoad } from "../ui";

/** Opens one stored source row through the evidence route. */
export function RecordPanel({
  caseId,
  kind,
  objectId,
}: {
  caseId: string;
  kind: string;
  objectId: string;
}) {
  const record = useLoad(
    () => api.evidence(caseId, kind, objectId),
    [caseId, kind, objectId],
    "This record could not be opened.",
  );
  if (record.loading) return <Skeleton lines={4} />;
  if (record.error || !record.data)
    return <ErrorBox message={record.error ?? "Not available."} onRetry={record.reload} />;
  return <SourceRecordView item={record.data} />;
}
