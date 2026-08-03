/**
 * Interactive BI filter state — selection only.
 * Never used to recompute KPIs; AnalyticsReport slices are selected by key.
 */

export type PeriodPreset = "all" | "month" | "quarter" | "fy" | "custom";

export interface BiFilterState {
  dateFrom: string | null;
  dateTo: string | null;
  period: PeriodPreset;
  outlet: string; // "All" | canonical name
  platform: string; // "All" | "Swiggy" | "Zomato"
  paymentStatus: string; // All | Payment Match | Payment Mismatch | …
  agreementStatus: string; // All | Verified | Violation | None
  verificationLevel: string; // All | SETTLEMENT_VERIFIED | …
  settlementStatus: string; // All | FINANCIALLY_RECONCILED | FINANCIAL_DISCREPANCY | …
  cancelledOnly: boolean;
  pendingOnly: boolean;
  search: string; // order id / invoice / outlet text
  /** Cross-filter origin for UI chips */
  crossFilterSource: string | null;
}

export const DEFAULT_BI_FILTERS: BiFilterState = {
  dateFrom: null,
  dateTo: null,
  period: "all",
  outlet: "All",
  platform: "All",
  paymentStatus: "All",
  agreementStatus: "All",
  verificationLevel: "All",
  settlementStatus: "All",
  cancelledOnly: false,
  pendingOnly: false,
  search: "",
  crossFilterSource: null,
};

export const BI_FILTER_STORAGE_KEY = "omni.bi.filters.v1";
export const BI_UI_STORAGE_KEY = "omni.bi.ui.v1";

export interface BiUiState {
  tab: string;
  expandedPanels: string[];
  reconSortKey: string;
  reconSortDir: "asc" | "desc";
  chartSelection: string | null;
}

export const DEFAULT_BI_UI: BiUiState = {
  tab: "executive",
  expandedPanels: [],
  reconSortKey: "date",
  reconSortDir: "desc",
  chartSelection: null,
};

export function countActiveFilters(f: BiFilterState): number {
  let n = 0;
  if (f.outlet !== "All") n += 1;
  if (f.platform !== "All") n += 1;
  if (f.paymentStatus !== "All") n += 1;
  if (f.agreementStatus !== "All") n += 1;
  if (f.verificationLevel !== "All") n += 1;
  if (f.settlementStatus !== "All") n += 1;
  if (f.cancelledOnly) n += 1;
  if (f.pendingOnly) n += 1;
  if (f.search.trim()) n += 1;
  if (f.period !== "all") n += 1;
  if (f.dateFrom || f.dateTo) n += 1;
  return n;
}
