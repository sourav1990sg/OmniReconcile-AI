import type { AnalyticsReport } from "@/components/intelligence/analytics-types";
import type { BusinessIntelligenceReport } from "@/components/intelligence/bi-types";
import { formatInr, formatInt, formatPct } from "@/components/intelligence/analytics-types";
import { DecisionCardGrid, PriorityActionList } from "@/components/intelligence/DecisionCards";
import { InsightCards } from "@/components/intelligence/InsightCards";

/** Board-ready A4 landscape executive report. */
export function ExecutivePrintView({
  report,
  bi = null,
}: {
  report: AnalyticsReport;
  bi?: BusinessIntelligenceReport | null;
}) {
  const ex = report.executive_summary;
  const f = report.financial_summary;
  const tops = report.top_performers;
  const hasBi = Boolean(bi?.executive_summary);
  const generated = new Date().toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <div
      id="executive-print-root"
      className="mx-auto hidden max-w-[1100px] bg-white p-8 text-slate-900 print:block"
    >
      <header className="border-b border-slate-200 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">OmniReconcile AI</p>
            <h1 className="mt-1 text-2xl font-semibold">Executive Financial Intelligence Report</h1>
            <p className="text-sm text-slate-600">
              Prepared for CEO · CFO · Board · Prepared by OmniReconcile AI
            </p>
          </div>
          <div className="text-right text-xs text-slate-500">
            <p>Generated</p>
            <p className="font-medium text-slate-800">{generated}</p>
          </div>
        </div>
        {hasBi && bi ? (
          <p className="mt-3 text-sm font-medium text-slate-800">
            Next action: {bi.executive_summary.next_action}
          </p>
        ) : null}
      </header>

      <section className="mt-6">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          1. Executive summary
        </h2>
        <div className="mt-3 grid grid-cols-4 gap-3 text-sm">
          <PrintStat label="Online Sales" value={formatInr(ex.total_online_sales)} />
          <PrintStat label="Platform Payout" value={formatInr(ex.platform_payout)} />
          <PrintStat label="Settlement Coverage" value={formatPct(ex.settlement_coverage_pct)} />
          <PrintStat label="Recoverable" value={formatInr(ex.recoverable_amount)} />
          <PrintStat label="Orders" value={formatInt(ex.total_pos_orders)} />
          <PrintStat label="Matched" value={formatInt(ex.matched_orders)} />
          <PrintStat label="Payment Match" value={formatInt(ex.payment_match_orders)} />
          <PrintStat label="Agreement Verified" value={formatInt(ex.agreement_verified_orders)} />
        </div>
      </section>

      <section className="mt-6">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          2. Platform performance
        </h2>
        <table className="mt-2 w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th className="py-1">Platform</th>
              <th>Orders</th>
              <th>Sales</th>
              <th>Payout</th>
              <th>Commission</th>
              <th>Recoverable</th>
              <th>Coverage</th>
            </tr>
          </thead>
          <tbody>
            {report.platform_summary.map((p) => (
              <tr key={p.platform} className="border-b border-slate-100">
                <td className="py-1.5 font-medium">{p.platform}</td>
                <td>{formatInt(p.order_count)}</td>
                <td>{formatInr(p.sales)}</td>
                <td>{formatInr(p.platform_payout)}</td>
                <td>{formatInr(p.commission)}</td>
                <td>{formatInr(p.recoverable_amount)}</td>
                <td>{formatPct(p.settlement_coverage_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-6">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          3. Outlet performance
        </h2>
        <ul className="mt-2 grid grid-cols-2 gap-2 text-sm">
          <li>Highest sales: {tops.highest_online_sales_outlet ?? "—"}</li>
          <li>Highest orders: {tops.highest_orders_outlet ?? "—"}</li>
          <li>Highest AOV: {tops.highest_average_order_value ?? "—"}</li>
          <li>Highest recoverable: {tops.highest_recoverable_amount ?? "—"}</li>
        </ul>
      </section>

      <section className="mt-6">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          4. Financial performance
        </h2>
        <div className="mt-2 grid grid-cols-4 gap-3 text-sm">
          <PrintStat label="Commission" value={formatInr(f.total_commission)} />
          <PrintStat label="GST" value={formatInr(f.total_gst)} />
          <PrintStat label="TDS" value={formatInr(f.total_tds)} />
          <PrintStat label="TCS" value={formatInr(f.total_tcs)} />
          <PrintStat label="Gov Charges" value={formatInr(f.total_government_charges)} />
          <PrintStat label="Deductions" value={formatInr(f.total_platform_deductions)} />
          <PrintStat label="Net Payout" value={formatInr(f.net_platform_payout)} />
          <PrintStat label="Recoverable" value={formatInr(f.recoverable)} />
        </div>
      </section>

      {hasBi && bi ? (
        <>
          <section className="mt-6">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              5. Business risks
            </h2>
            <div className="mt-2">
              <DecisionCardGrid
                cards={bi.risk_cards.slice(0, 4)}
                variant="risk"
                label="Risks"
                empty="No material risks."
              />
            </div>
          </section>
          <section className="mt-6">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              6. Recommendations & action plan
            </h2>
            <div className="mt-2">
              <PriorityActionList actions={bi.priority_actions.slice(0, 6)} />
            </div>
          </section>
        </>
      ) : (
        <section className="mt-6">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            5. Insights
          </h2>
          <div className="mt-2">
            <InsightCards insights={report.business_insights ?? []} />
          </div>
        </section>
      )}

      <footer className="mt-8 border-t border-slate-200 pt-3 text-[10px] text-slate-500">
        All figures sourced from AnalyticsReport (and BusinessIntelligenceReport where present).
        Rounding tolerance ₹0.01. Confidential — for internal leadership use.
      </footer>
    </div>
  );
}

function PrintStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}
