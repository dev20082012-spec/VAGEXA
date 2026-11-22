import { useOutletContext } from "react-router-dom";
import type { CaseRecord, InvestigationSummary } from "../api/types";

export type WorkspaceContext = {
  caseId: string;
  record: CaseRecord;
  summary: InvestigationSummary | null;
  summaryError: string | null;
  reloadSummary: () => void;
};

export function useWorkspace(): WorkspaceContext {
  return useOutletContext<WorkspaceContext>();
}

export const CASE_EVENT = "vagexa:case-opened";
