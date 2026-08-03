export type Platform = "Swiggy" | "Zomato" | "Unknown";

/** UI status — includes business-rule statuses from the V2 pipeline. */
export type Status =
  | "Flagged"
  | "Disputed"
  | "Recovered"
  | "Under Review"
  | "Matched"
  | "RECONCILED"
  | "FINANCIALLY_RECONCILED"
  | "PENDING"
  | "NOT_RECONCILED"
  | "AMOUNT_MISMATCH"
  | "FINANCIAL_DISCREPANCY"
  | "CANCELLED"
  | "DUPLICATE_SETTLEMENT"
  | "MANUAL_REVIEW";

export type Location = string;

export interface Discrepancy {
  id: string;
  date: string;
  orderId: string;
  platform: Platform;
  location: Location;
  items: number;
  gross: number;
  commissionPct: number;
  /** Calculated payout (Sprint 6A); legacy "expected" field name kept for sort/export. */
  expected: number;
  /** Actual settlement payout. */
  settled: number;
  discrepancy: number;
  posSale: number;
  grossOrderValue: number;
  totalDeductions: number;
  calculatedPayout: number;
  actualPayout: number;
  financialDifference: number;
  financialStatus: string;
  platformFormula: string;
  explanation: string;
  deductionSummary: Record<string, number>;
  financialBreakdown: Record<string, unknown>;
  verificationLevel: string;
  displayStatus: string;
  agreementVersion: string;
  agreementStatus: string;
  commercialResult: string;
  commercialRemarks: string;
  status: Status;
  confidence: number;
  remarks?: string;
  recommendation?: string;
  matched?: boolean;
  sourcePos?: string;
  sourceSettlement?: string;
}

export interface DashboardSummary {
  total_pos_orders: number;
  cancelled_orders: number;
  eligible_orders: number;
  total_settlement_orders: number;
  matched_orders: number;
  unmatched_orders: number;
  unmatched_settlement?: number;
  amount_mismatch: number;
  financial_discrepancy?: number;
  pending: number;
  not_reconciled: number;
  reconciled?: number;
  financially_reconciled?: number;
  recoverable_amount: number;
  total_expected?: number;
  total_settled?: number;
  total_difference?: number;
  orders_verified_by_agreement?: number;
  orders_verified_by_settlement?: number;
  agreement_violations?: number;
  unknown_agreement_terms?: number;
  agreement_coverage?: {
    orders_verified_by_agreement?: number;
    orders_verified_by_settlement?: number;
    agreement_violations?: number;
    unknown_agreement_terms?: number;
    agreement_available?: boolean;
  };
}

export interface DatasetSummary {
  total_files?: number;
  total_orders?: number;
  cancelled_orders?: number;
  eligible_orders?: number;
  platforms?: string[];
  date_range?: { from?: string | null; to?: string | null };
  outlets?: string[];
}

/** Raw row shape returned by POST /api/reconcile (V2 pipeline + Sprint 6A). */
export interface ReconcileApiRow {
  Date?: string;
  "Order ID"?: string;
  Outlet?: string;
  "Expected Amount"?: number;
  "Settled Amount"?: number;
  Discrepancy?: number;
  "POS Sale"?: number;
  "Gross Order Value"?: number;
  "Total Deductions"?: number;
  "Calculated Payout"?: number;
  "Actual Payout"?: number;
  "Financial Difference"?: number;
  "Financial Status"?: string;
  "Platform Formula"?: string;
  Explanation?: string;
  "Deduction Summary"?: Record<string, number>;
  "Financial Breakdown"?: Record<string, unknown>;
  "Verification Level"?: string;
  "Display Status"?: string;
  "Agreement Version"?: string;
  "Agreement Status"?: string;
  "Commercial Verification Result"?: string;
  "Commercial Remarks"?: string;
  "Display Remarks"?: string;
  Status?: string;
  Platform?: string;
  Remarks?: string;
  Recommendation?: string;
  Matched?: boolean;
  "Source POS"?: string;
  "Source Settlement"?: string;
  LegacyStatus?: string;
}

export const locations: Array<"All Locations" | string> = [
  "All Locations",
  "Shop 1",
  "Shop 2",
  "Shop 3",
  "Shop 4",
];

export const inr = (value: number) =>
  `₹${Math.abs(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** Calculated − Actual (positive = underpayment / recoverable candidate). */
export const shortfall = (d: Discrepancy) =>
  Math.round((d.calculatedPayout - d.actualPayout) * 100) / 100;

/** Recoverable only for unexplained FINANCIAL_DISCREPANCY underpayments. */
export const recoverableShortfall = (d: Discrepancy) =>
  d.status === "FINANCIAL_DISCREPANCY" ? Math.max(shortfall(d), 0) : 0;

const KNOWN_STATUSES: Status[] = [
  "Flagged",
  "Disputed",
  "Recovered",
  "Under Review",
  "Matched",
  "RECONCILED",
  "FINANCIALLY_RECONCILED",
  "PENDING",
  "NOT_RECONCILED",
  "AMOUNT_MISMATCH",
  "FINANCIAL_DISCREPANCY",
  "CANCELLED",
  "DUPLICATE_SETTLEMENT",
  "MANUAL_REVIEW",
];

function normalizePlatform(value: unknown): Platform {
  const text = String(value ?? "").trim().toLowerCase();
  if (text.includes("swiggy")) return "Swiggy";
  if (text.includes("zomato")) return "Zomato";
  return "Unknown";
}

function normalizeStatus(value: unknown): Status {
  const text = String(value ?? "").trim();
  const match = KNOWN_STATUSES.find((s) => s.toLowerCase() === text.toLowerCase());
  return match ?? "Flagged";
}

function asNumber(value: unknown, fallback = 0): number {
  if (value === undefined || value === null || value === "") return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function mapReconcileRow(row: ReconcileApiRow, index: number): Discrepancy {
  const calculated = asNumber(
    row["Calculated Payout"] ?? row["Expected Amount"],
  );
  const actual = asNumber(row["Actual Payout"] ?? row["Settled Amount"]);
  const financialDiff =
    row["Financial Difference"] !== undefined && row["Financial Difference"] !== null
      ? asNumber(row["Financial Difference"])
      : row.Discrepancy !== undefined && row.Discrepancy !== null
        ? asNumber(row.Discrepancy)
        : actual - calculated;
  const orderId = String(row["Order ID"] ?? `row-${index + 1}`);
  const breakdown = (row["Financial Breakdown"] ?? {}) as Record<string, unknown>;

  return {
    id: `${orderId}-${index}`,
    date: String(row.Date ?? "").replace(/NaT/gi, "") || "—",
    orderId,
    platform: normalizePlatform(row.Platform),
    location: String(row.Outlet ?? "").trim() || "—",
    items: 0,
    gross: asNumber(row["Gross Order Value"]),
    commissionPct: 0,
    expected: calculated,
    settled: actual,
    discrepancy: financialDiff,
    posSale: asNumber(row["POS Sale"]),
    grossOrderValue: asNumber(row["Gross Order Value"]),
    totalDeductions: asNumber(row["Total Deductions"]),
    calculatedPayout: calculated,
    actualPayout: actual,
    financialDifference: financialDiff,
    financialStatus: String(row["Financial Status"] ?? row.Status ?? ""),
    platformFormula: String(row["Platform Formula"] ?? ""),
    explanation: String(row.Explanation ?? row.Remarks ?? ""),
    deductionSummary: (row["Deduction Summary"] ?? {}) as Record<string, number>,
    financialBreakdown: breakdown,
    verificationLevel: String(row["Verification Level"] ?? ""),
    displayStatus: String(row["Display Status"] ?? ""),
    agreementVersion: String(row["Agreement Version"] ?? ""),
    agreementStatus: String(row["Agreement Status"] ?? ""),
    commercialResult: String(row["Commercial Verification Result"] ?? ""),
    commercialRemarks: String(row["Commercial Remarks"] ?? row["Display Remarks"] ?? ""),
    status: normalizeStatus(row.Status),
    confidence: 0,
    remarks: row.Remarks,
    recommendation: row.Recommendation,
    matched: row.Matched,
    sourcePos: row["Source POS"],
    sourceSettlement: row["Source Settlement"],
  };
}

/** Payload sent to POST /api/generate-dispute */
export function toDisputePayload(row: Discrepancy): Record<string, unknown> {
  return {
    Date: row.date,
    "Order ID": row.orderId,
    Outlet: row.location,
    "Expected Amount": row.calculatedPayout,
    "Settled Amount": row.actualPayout,
    Discrepancy: row.financialDifference,
    "Calculated Payout": row.calculatedPayout,
    "Actual Payout": row.actualPayout,
    "Financial Difference": row.financialDifference,
    Status: row.status,
    Platform: row.platform,
    Remarks: row.remarks,
    Explanation: row.explanation,
  };
}

export interface AnalyticsPayload {
  kpi_cards?: Array<{
    id?: string;
    label: string;
    value: string;
    caption: string;
    tone?: "neutral" | "warning" | "success" | string;
  }>;
  executive_summary?: Record<string, unknown>;
  platform_summary?: unknown[];
  outlet_summary?: unknown[];
  business_insights?: string[];
  chart_data?: Record<string, unknown>;
  financial_summary?: Record<string, unknown>;
  dashboard?: DashboardSummary;
}

/** Build dashboard metric cards — prefers Analytics Engine KPI cards (Sprint 7A). */
export function buildMetricCards(
  d: DashboardSummary | null,
  analytics?: AnalyticsPayload | { kpi_cards?: AnalyticsPayload["kpi_cards"] } | null,
) {
  const cards = analytics?.kpi_cards;
  if (cards && cards.length > 0) {
    return cards.map((c) => ({
      label: c.label,
      value: c.value,
      caption: c.caption,
      tone: (c.tone === "warning" || c.tone === "success" ? c.tone : "neutral") as
        | "neutral"
        | "warning"
        | "success",
    }));
  }
  if (!d) {
    return [
      { label: "Total POS Orders", value: "—", caption: "Upload to begin", tone: "neutral" as const },
      { label: "Matched Orders", value: "—", caption: "Awaiting reconciliation", tone: "neutral" as const },
      { label: "Financial Discrepancy", value: "—", caption: "—", tone: "warning" as const },
      { label: "Recoverable Amount", value: "—", caption: "Unexplained underpayments only", tone: "success" as const },
      { label: "Agreement Coverage", value: "—", caption: "Optional commercial agreement", tone: "neutral" as const },
    ];
  }
  // Legacy fallback — values already produced by AnalyticsEngine.dashboard
  const discrepancy = d.financial_discrepancy ?? d.amount_mismatch;
  const reconciled = d.financially_reconciled ?? d.reconciled ?? 0;
  const byAgreement = d.orders_verified_by_agreement ?? d.agreement_coverage?.orders_verified_by_agreement ?? 0;
  const bySettlement = d.orders_verified_by_settlement ?? d.agreement_coverage?.orders_verified_by_settlement ?? 0;
  const violations = d.agreement_violations ?? d.agreement_coverage?.agreement_violations ?? 0;
  const unknownTerms = d.unknown_agreement_terms ?? d.agreement_coverage?.unknown_agreement_terms ?? 0;
  return [
    {
      label: "Total POS Orders",
      value: d.total_pos_orders.toLocaleString("en-IN"),
      caption: `${d.eligible_orders} eligible · ${d.cancelled_orders} cancelled`,
      tone: "neutral" as const,
    },
    {
      label: "Matched Orders",
      value: d.matched_orders.toLocaleString("en-IN"),
      caption: `${reconciled.toLocaleString("en-IN")} financially reconciled · ${d.unmatched_orders} unmatched POS`,
      tone: "neutral" as const,
    },
    {
      label: "Financial Discrepancy",
      value: discrepancy.toLocaleString("en-IN"),
      caption: `${d.not_reconciled} not reconciled · ${d.pending} pending`,
      tone: "warning" as const,
    },
    {
      label: "Recoverable Amount",
      value: inr(d.recoverable_amount),
      caption: "Unexplained underpayments only (excludes platform deductions)",
      tone: "success" as const,
    },
    {
      label: "Agreement Coverage",
      value: byAgreement.toLocaleString("en-IN"),
      caption: `${bySettlement} settlement-only · ${violations} violations · ${unknownTerms} unknown terms`,
      tone: violations > 0 ? ("warning" as const) : ("neutral" as const),
    },
  ];
}
