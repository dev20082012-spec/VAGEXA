/** Display helpers. Amounts stay decimal strings; nothing here does arithmetic on money. */

function groupIndian(integer: string): string {
  if (integer.length <= 3) return integer;
  const last = integer.slice(-3);
  const rest = integer.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return `${rest},${last}`;
}

export function formatAmount(amount: string | null | undefined, currency?: string | null): string {
  if (!amount) return "—";
  const negative = amount.startsWith("-");
  const raw = negative ? amount.slice(1) : amount;
  const [integer, fraction = ""] = raw.split(".");
  const trimmed = /^0*$/.test(fraction.slice(2)) ? fraction.slice(0, 2).padEnd(2, "0") : fraction;
  const grouped =
    currency === "INR" ? groupIndian(integer) : integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const symbol = currency === "INR" ? "₹" : currency ? `${currency} ` : "";
  return `${negative ? "-" : ""}${symbol}${grouped}${trimmed ? `.${trimmed}` : ""}`;
}

/** Orders two positive decimal strings without converting them to floating point. */
export function compareAmount(left: string, right: string): number {
  const [leftInt, leftFrac = ""] = left.split(".");
  const [rightInt, rightFrac = ""] = right.split(".");
  const a = leftInt.replace(/^0+(?=\d)/, "");
  const b = rightInt.replace(/^0+(?=\d)/, "");
  if (a.length !== b.length) return a.length - b.length;
  if (a !== b) return a < b ? -1 : 1;
  const width = Math.max(leftFrac.length, rightFrac.length);
  const fa = leftFrac.padEnd(width, "0");
  const fb = rightFrac.padEnd(width, "0");
  return fa === fb ? 0 : fa < fb ? -1 : 1;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return `${parsed.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export function formatBooking(
  date: string | null | undefined,
  clock: string | null | undefined,
): string {
  if (!date) return "—";
  return clock ? `${date} ${clock.slice(0, 5)}` : `${date} (date only)`;
}

/** Hours arrive as a decimal string from the API. This is time, not money. */
export function formatDelay(hours: string | null | undefined): string | null {
  if (!hours) return null;
  const minutes = Math.round(Number(hours) * 60);
  if (Number.isNaN(minutes)) return null;
  if (minutes < 60) return `${minutes} min after the previous hop`;
  const whole = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${whole} h ${rest} min after the previous hop`;
}

export function shortId(value: string | null | undefined): string {
  return value ? value.slice(0, 8) : "—";
}

export const REL_LABEL: Record<string, string> = {
  gateway_merchant: "Gateway settlement record",
  mentioned_in: "Host named in narration",
  infrastructure_overlap: "Shared infrastructure",
  same_payment: "Same payment reference",
  transfer: "Statement transfer",
  resolves_to: "DNS observation",
  hosted_with: "Hosting note",
};

export const CLASS_TEXT: Record<string, string> = {
  DIRECTLY_SUPPORTED: "A single stored source field states this claim.",
  CORROBORATED: "Two independent source records support the same link.",
  INFERRED: "A named method derived this from verified inputs.",
  HYPOTHESIS: "A possibility that needs more evidence.",
  UNRESOLVED:
    "A shared technical key was observed. Common ownership or control is not established.",
  CONTRADICTED: "Stored records disagree. Neither has been discarded.",
};

export const KIND_LABEL: Record<string, string> = {
  transaction: "Statement row",
  dns_observation: "DNS observation",
  hosting_observation: "Hosting note",
  gateway_record: "Payment-gateway record",
  account: "Account",
  domain: "Domain",
  ip: "IP address",
  provider: "Provider string",
  cash_exit: "Cash exit",
};

export const INDICATOR_LABEL: Record<string, string> = {
  FAN_IN: "Fan-in: many senders into one account",
  FAN_OUT: "Fan-out: one account paying many recipients",
  PASS_THROUGH: "Pass-through: inflow paid onward",
};

export const RULE_GUIDANCE: Record<
  string,
  { missing: string[]; alternatives: string[]; verify: string[] }
> = {
  gateway_merchant: {
    missing: [
      "Who registered or operates the merchant domain. Registration data is not collected in this deployment.",
      "The gateway's merchant onboarding file for the settlement account.",
    ],
    alternatives: [
      "The settlement account may belong to an aggregator or a third party.",
      "The merchant site may have been impersonated.",
    ],
    verify: [
      "Request the merchant onboarding and settlement records from the gateway.",
      "Confirm the settlement account holder with the bank.",
    ],
  },
  mentioned_in: {
    missing: ["Any record of who controls the named host."],
    alternatives: [
      "The narration may quote text the customer typed or the bank inserted.",
      "The host may be a payment page shared by many merchants.",
    ],
    verify: ["Compare the narration with the bank's original instrument record."],
  },
  infrastructure_overlap: {
    missing: ["Registration, hosting contracts, or any record of a shared operator."],
    alternatives: [
      "Unrelated customers commonly share hosting providers and addresses.",
      "A shared CDN or resolver produces the same address for many domains.",
    ],
    verify: [
      "Obtain hosting-provider records through the proper legal process before treating domains as linked.",
    ],
  },
  same_payment: {
    missing: [],
    alternatives: ["A bank can reuse a reference format. Check the amount and accounts as well."],
    verify: ["Compare both statement rows in the source files."],
  },
};
