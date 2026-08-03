/**
 * Filter discrepancy rows for tables / exports / drill lists.
 * Display filtering only — does not produce KPI totals.
 */

import type { Discrepancy } from "@/components/reconcile/data";
import type { BiFilterState } from "@/components/intelligence/interactive/filter-types";

function inDateRange(dateStr: string, from: string | null, to: string | null): boolean {
  if (!from && !to) return true;
  const d = dateStr.slice(0, 10);
  if (!d || d === "—") return true;
  if (from && d < from) return false;
  if (to && d > to) return false;
  return true;
}

export function filterDiscrepancyRows(
  rows: Discrepancy[],
  f: BiFilterState,
): Discrepancy[] {
  const q = f.search.trim().toLowerCase();

  return rows.filter((r) => {
    if (f.platform !== "All" && r.platform !== f.platform) return false;
    if (f.outlet !== "All" && r.location !== f.outlet) return false;
    if (!inDateRange(r.date, f.dateFrom, f.dateTo)) return false;

    if (f.settlementStatus !== "All") {
      const st = (r.financialStatus || r.status || "").toUpperCase();
      if (st !== f.settlementStatus.toUpperCase()) return false;
    }

    if (f.verificationLevel !== "All") {
      if ((r.verificationLevel || "").toUpperCase() !== f.verificationLevel.toUpperCase()) {
        return false;
      }
    }

    if (f.paymentStatus === "Payment Match") {
      const ok =
        r.displayStatus === "Payment Match" ||
        r.displayStatus === "Verified by Agreement" ||
        ["SETTLEMENT_VERIFIED", "AGREEMENT_VERIFIED"].includes(
          (r.verificationLevel || "").toUpperCase(),
        );
      if (!ok) return false;
    } else if (f.paymentStatus === "Payment Mismatch") {
      const bad =
        r.displayStatus === "Payment Mismatch" ||
        (r.verificationLevel || "").toUpperCase() === "PAYMENT_MISMATCH" ||
        (r.financialStatus || "").toUpperCase() === "FINANCIAL_DISCREPANCY";
      if (!bad) return false;
    }

    if (f.agreementStatus === "Verified") {
      if ((r.verificationLevel || "").toUpperCase() !== "AGREEMENT_VERIFIED") return false;
    } else if (f.agreementStatus === "Violation") {
      if ((r.verificationLevel || "").toUpperCase() !== "AGREEMENT_VIOLATION") return false;
    }

    if (f.cancelledOnly) {
      if ((r.status || "").toUpperCase() !== "CANCELLED") return false;
    }
    if (f.pendingOnly) {
      const st = (r.status || "").toUpperCase();
      if (st !== "PENDING" && st !== "NOT_RECONCILED") return false;
    }

    if (q) {
      const hay = `${r.orderId} ${r.location} ${r.platform} ${r.sourceSettlement ?? ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }

    return true;
  });
}
