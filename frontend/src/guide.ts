/** Walkthrough for the SYN-DEMO case. Each step opens a real tab; the tab selects stored records itself. */

export const DEMO_REFERENCE = "SYN-DEMO";

export type GuideStep = { path: string; query: string; title: string; text: string };

export const GUIDE: GuideStep[] = [
  {
    path: "",
    query: "",
    title: "Case overview",
    text: "Every figure here is a count of stored synthetic rows. The narrative is assembled from those rows.",
  },
  {
    path: "financial",
    query: "view=transactions&focus=bridge",
    title: "The opening payment",
    text: "The selected debit pays the first account in the chain. Its narration names a merchant host.",
  },
  {
    path: "financial",
    query: "view=flow",
    title: "Fund flow",
    text: "fifo.v1 allocates the payment across three hops and stops at the horizon. The last holder is not called the beneficiary.",
  },
  {
    path: "financial",
    query: "view=findings",
    title: "Pattern findings",
    text: "Fan-in and fan-out rules matched on one collection account. These are rule matches, not findings of guilt.",
  },
  {
    path: "network",
    query: "select=bridge",
    title: "Network",
    text: "Statement transfers, DNS observations, and the gateway link in one graph. The selected edge is the bridge.",
  },
  {
    path: "infrastructure",
    query: "focus=bridge",
    title: "Infrastructure",
    text: "The merchant domain shares an address with another domain. That is technical overlap and stays unresolved.",
  },
  {
    path: "unified",
    query: "focus=bridge",
    title: "Unified intelligence",
    text: "The selected relationship is the corroborated gateway link. A later payment has two gateway records that name different domains; those stay contradicted.",
  },
  {
    path: "evidence",
    query: "focus=bridge",
    title: "Evidence",
    text: "The gateway record as stored, with its source and collection time.",
  },
  {
    path: "report",
    query: "",
    title: "Report",
    text: "The case report separates observed records from analytical results and lists open questions.",
  },
];

export function guideHref(caseId: string, step: number): string {
  const item = GUIDE[step - 1];
  const query = [item.query, `guide=${step}`].filter(Boolean).join("&");
  return `/cases/${caseId}${item.path ? `/${item.path}` : ""}?${query}`;
}
