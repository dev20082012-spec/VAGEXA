import { FormEvent, useState } from "react";
import { api, errorText } from "../../api/client";
import type { IngestionIssue, IngestionJob } from "../../api/types";
import { Empty, ErrorBox, Panel } from "../../ui";

export function IntakeView({ caseId, onLoaded }: { caseId: string; onLoaded: () => void }) {
  const [job, setJob] = useState<IngestionJob | null>(null);
  const [issues, setIssues] = useState<IngestionIssue[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a CSV or JSON file.");
      return;
    }
    setPending(true);
    setError(null);
    setJob(null);
    setIssues([]);
    try {
      const created = await api.uploadDataset(
        caseId,
        file,
        String(form.get("subject_account") || ""),
        String(form.get("subject_ifsc") || ""),
      );
      setJob(created);
      setIssues((await api.jobIssues(created.id)).items);
      onLoaded();
    } catch (err) {
      setError(errorText(err, "The upload failed."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="split">
      <Panel
        title="Load a statement or transfer file"
        subtitle="CSV or JSON. The same file twice returns the first job and adds no rows. Invalid rows are listed, not dropped."
      >
        <form onSubmit={onSubmit}>
          <label className="field">
            File
            <input name="file" type="file" accept=".csv,.json,text/csv,application/json" required />
          </label>
          <div className="grid-2">
            <label className="field">
              Statement account (statement files only)
              <input name="subject_account" />
            </label>
            <label className="field">
              Statement IFSC
              <input name="subject_ifsc" />
            </label>
          </div>
          {error ? <ErrorBox message={error} /> : null}
          <button className="primary" type="submit" disabled={pending}>
            {pending ? "Loading…" : "Load file"}
          </button>
        </form>
      </Panel>
      <Panel title="Ingestion result">
        {!job ? <Empty>No file loaded in this session.</Empty> : null}
        {job ? (
          <>
            <p>
              Job <strong>{job.status}</strong>. {job.summary.records_valid} valid,{" "}
              {job.summary.records_invalid} invalid, {job.summary.records_duplicate} duplicate,{" "}
              {job.summary.records_potential_duplicate} similar rows kept separate.
              {job.summary.idempotent_replay
                ? " This file was already loaded, so no rows were added."
                : ""}
            </p>
            {issues.length > 0 ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Field</th>
                    <th>Problem</th>
                    <th>Correction</th>
                  </tr>
                </thead>
                <tbody>
                  {issues.map((issue) => (
                    <tr key={`${issue.line_number}-${issue.field_name}-${issue.category}`}>
                      <td>{issue.line_number}</td>
                      <td>{issue.field_name}</td>
                      <td>
                        {issue.category}
                        <div className="small muted">{issue.message}</div>
                      </td>
                      <td className="small">{issue.suggestion}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No row was rejected.</p>
            )}
          </>
        ) : null}
      </Panel>
    </div>
  );
}
