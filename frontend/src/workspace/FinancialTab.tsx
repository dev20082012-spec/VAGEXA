import { useSearchParams } from "react-router-dom";
import { useWorkspace } from "./context";
import { AccountsView } from "./financial/AccountsView";
import { FindingsView } from "./financial/FindingsView";
import { FlowView } from "./financial/FlowView";
import { IntakeView } from "./financial/IntakeView";
import { TransactionsView } from "./financial/TransactionsView";

const VIEWS = [
  { key: "transactions", label: "Transactions" },
  { key: "accounts", label: "Accounts" },
  { key: "flow", label: "Fund flow" },
  { key: "findings", label: "Findings" },
  { key: "intake", label: "Load statements" },
];

export function FinancialTab() {
  const { caseId, reloadSummary } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const view = VIEWS.some((item) => item.key === params.get("view"))
    ? String(params.get("view"))
    : "transactions";

  function choose(key: string) {
    const next = new URLSearchParams(params);
    next.set("view", key);
    next.delete("focus");
    setParams(next);
  }

  return (
    <>
      <div className="subnav" role="tablist" aria-label="Financial intelligence views">
        {VIEWS.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={view === item.key}
            className={view === item.key ? "active" : ""}
            onClick={() => choose(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {view === "transactions" ? <TransactionsView caseId={caseId} /> : null}
      {view === "accounts" ? <AccountsView caseId={caseId} /> : null}
      {view === "flow" ? <FlowView caseId={caseId} /> : null}
      {view === "findings" ? <FindingsView caseId={caseId} /> : null}
      {view === "intake" ? <IntakeView caseId={caseId} onLoaded={reloadSummary} /> : null}
    </>
  );
}
