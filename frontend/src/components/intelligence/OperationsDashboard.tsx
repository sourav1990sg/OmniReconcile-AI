import type { AnalyticsReport } from "@/components/intelligence/analytics-types";
import type { BusinessIntelligenceReport } from "@/components/intelligence/bi-types";
import { formatInr, formatInt } from "@/components/intelligence/analytics-types";
import { ChartHost } from "@/components/intelligence/ChartHost";
import { DecisionCardGrid } from "@/components/intelligence/DecisionCards";
import { MetricTile } from "@/components/intelligence/KpiStrip";
import { OutletScorecards } from "@/components/intelligence/Scorecards";
import { useBiFilterOptional } from "@/components/intelligence/interactive/BiFilterContext";

export function OperationsDashboard({
  report,
  bi = null,
}: {
  report: AnalyticsReport;
  bi?: BusinessIntelligenceReport | null;
}) {
  const biFilter = useBiFilterOptional();
  const outlets = biFilter?.view.outlets ?? report.outlet_summary;
  const chartData = biFilter?.view.chart_data ?? report.chart_data;
  const ex = report.executive_summary;
  const tops = report.top_performers;
  const maxCell = Math.max(
    1,
    ...outlets.flatMap((o) => [o.swiggy_orders ?? 0, o.zomato_orders ?? 0]),
  );
  const hasBi = Boolean(bi?.executive_summary);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold tracking-tight">Operations Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Restaurant operations from AnalyticsReport
          {hasBi ? " · opportunities from BusinessIntelligenceReport" : ""}.
        </p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <MetricTile label="Top Outlet (Orders)" value={tops.highest_orders_outlet ?? "—"} />
        <MetricTile label="Top Outlet (Sales)" value={tops.highest_online_sales_outlet ?? "—"} />
        <MetricTile label="Highest AOV Outlet" value={tops.highest_average_order_value ?? "—"} />
        <MetricTile label="Order Count (Matched)" value={formatInt(ex.matched_orders)} />
        <MetricTile label="Cancelled Orders" value={formatInt(ex.cancelled_orders)} />
        <MetricTile label="Pending Orders" value={formatInt(ex.pending_orders)} />
      </section>

      <ChartHost chartData={chartData} variant="operations" />

      <section
        aria-label="Outlet platform heatmap"
        className="rounded-xl border border-border/60 bg-card p-4"
      >
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Order heatmap · Outlet × Platform
        </h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[320px] text-xs">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-1.5 pr-3 font-medium">Outlet</th>
                <th className="py-1.5 pr-3 font-medium">Swiggy</th>
                <th className="py-1.5 font-medium">Zomato</th>
              </tr>
            </thead>
            <tbody>
              {outlets.map((o) => (
                <tr key={o.outlet}>
                  <td className="py-1.5 pr-3 font-medium">{o.outlet}</td>
                  <HeatCell value={o.swiggy_orders ?? 0} max={maxCell} />
                  <HeatCell value={o.zomato_orders ?? 0} max={maxCell} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {hasBi && bi ? (
        <>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Operations risks
            </h3>
            <DecisionCardGrid
              cards={bi.operations_risks}
              variant="risk"
              label="Operations risks"
              empty="No operations risks flagged."
            />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Outlet opportunities
            </h3>
            <DecisionCardGrid
              cards={bi.outlet_opportunities}
              variant="opportunity"
              label="Outlet opportunities"
              empty="No outlet opportunities."
            />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Platform opportunities
            </h3>
            <DecisionCardGrid
              cards={bi.platform_opportunities}
              variant="opportunity"
              label="Platform opportunities"
              empty="No platform opportunities."
            />
          </div>
        </>
      ) : null}

      <div>
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Outlet scorecards
        </h3>
        <OutletScorecards
          outlets={outlets}
          onSelect={(name) => biFilter?.crossFilterOutlet(name, "ops-scorecard")}
        />
      </div>

      <p className="text-xs text-muted-foreground">
        Platform mix from chart_data · payout {formatInr(ex.platform_payout)}
      </p>
    </div>
  );
}

function HeatCell({ value, max }: { value: number; max: number }) {
  const intensity = value / max;
  return (
    <td className="py-1.5 pr-3">
      <span
        className="inline-flex min-w-[3rem] justify-center rounded px-2 py-1 tabular-nums"
        style={{
          backgroundColor: `color-mix(in oklab, var(--color-primary) ${Math.round(intensity * 70)}%, transparent)`,
        }}
      >
        {formatInt(value)}
      </span>
    </td>
  );
}
