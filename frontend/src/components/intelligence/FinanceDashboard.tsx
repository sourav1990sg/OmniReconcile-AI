import type { AnalyticsReport } from "@/components/intelligence/analytics-types";
import type { BusinessIntelligenceReport } from "@/components/intelligence/bi-types";
import { formatInr, formatInt, formatPct } from "@/components/intelligence/analytics-types";
import { ChartHost } from "@/components/intelligence/ChartHost";
import { DecisionCardGrid } from "@/components/intelligence/DecisionCards";
import { ExplainedMetric } from "@/components/intelligence/KpiExplain";
import { MetricTile } from "@/components/intelligence/KpiStrip";
import { useBiFilterOptional } from "@/components/intelligence/interactive/BiFilterContext";

export function FinanceDashboard({
  report,
  bi = null,
}: {
  report: AnalyticsReport;
  bi?: BusinessIntelligenceReport | null;
}) {
  const biFilter = useBiFilterOptional();
  const chartData = biFilter?.view.chart_data ?? report.chart_data;
  const hero = biFilter?.view.hero;
  const f = report.financial_summary;
  const ex = report.executive_summary;
  const coverage = hero?.settlement_coverage_pct ?? ex.settlement_coverage_pct;
  const hasBi = Boolean(bi?.executive_summary);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold tracking-tight">Finance Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Money movement from AnalyticsReport
          {hasBi ? " · risks from BusinessIntelligenceReport" : ""}.
        </p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ExplainedMetric
          label="Gross Order Value"
          value={formatInr(hero?.gross_order_value ?? f.gross_order_value)}
          kpiId="gross_order_value"
        />
        <ExplainedMetric
          label="Platform Payout"
          value={formatInr(hero?.platform_payout ?? f.net_platform_payout)}
          kpiId="platform_payout"
        />
        <ExplainedMetric
          label="Commission"
          value={formatInr(hero?.commission ?? f.total_commission)}
          kpiId="commission"
          onDrill={() => biFilter?.setTab("reconciliation")}
        />
        <MetricTile label="GST" value={formatInr(f.total_gst)} />
        <MetricTile label="TDS" value={formatInr(f.total_tds)} />
        <MetricTile label="TCS" value={formatInr(f.total_tcs)} />
        <MetricTile label="Government Charges" value={formatInr(f.total_government_charges)} />
        <MetricTile label="Total Platform Deductions" value={formatInr(f.total_platform_deductions)} />
        <ExplainedMetric
          label="Recoverable"
          value={formatInr(hero?.recoverable ?? f.recoverable)}
          kpiId="recoverable"
          onDrill={() => biFilter?.setTab("reconciliation")}
        />
        <ExplainedMetric
          label="Pending Orders"
          value={formatInt(ex.pending_orders)}
          kpiId="settlement_coverage"
          onDrill={() => {
            biFilter?.setFilter("pendingOnly", true);
            biFilter?.setTab("reconciliation");
          }}
        />
        <MetricTile label="Not Reconciled" value={formatInt(ex.not_reconciled_orders)} />
        <MetricTile label="Agreement Violations" value={formatInt(ex.agreement_violations)} />
      </section>

      <section aria-label="Financial health" className="rounded-xl border border-border/60 bg-card p-4">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Financial health — settlement coverage
        </h3>
        <div className="mt-3 flex items-end gap-4">
          <p className="text-4xl font-semibold tabular-nums">{formatPct(coverage)}</p>
          <div className="mb-2 h-3 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-teal-700 transition-all"
              style={{ width: `${Math.min(Math.max(coverage, 0), 100)}%` }}
              role="progressbar"
              aria-valuenow={coverage}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>
      </section>

      <ChartHost chartData={chartData} variant="finance" />

      {hasBi && bi ? (
        <>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Financial risks
            </h3>
            <DecisionCardGrid
              cards={bi.financial_risks}
              variant="risk"
              label="Financial risks"
              empty="No financial risks flagged."
            />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Commercial risks
            </h3>
            <DecisionCardGrid
              cards={bi.commercial_risks}
              variant="risk"
              label="Commercial risks"
              empty="No commercial risks flagged."
            />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Recovery opportunities
            </h3>
            <DecisionCardGrid
              cards={bi.recovery_opportunities}
              variant="opportunity"
              label="Recovery opportunities"
              empty="No recovery opportunities this period."
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
