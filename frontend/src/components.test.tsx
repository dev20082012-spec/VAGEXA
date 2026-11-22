import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { GraphEdge, RelationshipRow, SourceRecord } from "./api/types";
import { compareAmount, formatAmount } from "./format";
import { supportedGateway, supportedGatewayEdge } from "./selection";
import { ClassBadge, SourceRecordView } from "./ui";

describe("supported gateway selection", () => {
  const row = (id: string, classification: string): RelationshipRow =>
    ({
      id,
      rel_type: "gateway_merchant",
      classification,
      support: [],
    }) as unknown as RelationshipRow;

  it("keeps a contradicted gateway record off the opening selection", () => {
    const chosen = supportedGateway([
      row("later", "CONTRADICTED"),
      row("bridge", "CORROBORATED"),
    ]);
    expect(chosen?.id).toBe("bridge");
    const edge = supportedGatewayEdge([
      { id: "e1", kind: "gateway_merchant", classification: "CONTRADICTED" } as GraphEdge,
      { id: "e2", kind: "gateway_merchant", classification: "CORROBORATED" } as GraphEdge,
    ]);
    expect(edge?.id).toBe("e2");
  });
});

describe("formatAmount", () => {
  it("groups rupees the Indian way without changing the decimals", () => {
    expect(formatAmount("100000.0000", "INR")).toBe("₹1,00,000.00");
    expect(formatAmount("1820.5000", "INR")).toBe("₹1,820.50");
    expect(formatAmount("0.1234", "INR")).toBe("₹0.1234");
  });

  it("labels other currencies by code", () => {
    expect(formatAmount("10.0000", "USD")).toBe("USD 10.00");
  });
});

describe("compareAmount", () => {
  it("orders decimal strings without floating point", () => {
    expect(compareAmount("100000.0000", "99999.9999")).toBeGreaterThan(0);
    expect(compareAmount("0.1000", "0.1")).toBe(0);
    expect(compareAmount("20000.0000", "100000.0000")).toBeLessThan(0);
  });
});

describe("evidence components", () => {
  it("shows a classification with its meaning", () => {
    const html = renderToStaticMarkup(<ClassBadge value="UNRESOLVED" />);
    expect(html).toContain("unresolved");
    expect(html).toContain("Common ownership or control is not established");
  });

  it("renders a stored gateway record with its source and synthetic label", () => {
    const item: SourceRecord = {
      object_kind: "gateway_record",
      object_id: "11111111-2222-3333-4444-555555555555",
      data_classification: "synthetic",
      time: { field: "processed_at", value: "2026-01-15T03:30:20+00:00", clock: null, note: "UTC" },
      record: {
        source_record_id: "SYN-PG-0001",
        merchant_domain: "syn-a.test",
        payee_account_masked: "****0011",
        amount: "100000.0000",
        currency: "INR",
      },
      provenance: {
        id: "p",
        source_system: "synthetic_payment_gateway",
        source_reference: "SYN-PG-0001",
        collected_at: "2026-11-22T13:30:00+00:00",
        method_name: "gateway_record.v1",
        data_classification: "synthetic",
      },
    };
    const html = renderToStaticMarkup(<SourceRecordView item={item} />);
    expect(html).toContain("Payment-gateway record");
    expect(html).toContain("syn-a.test");
    expect(html).toContain("₹1,00,000.00");
    expect(html).toContain("synthetic_payment_gateway");
    expect(html).toContain("synthetic");
  });
});
