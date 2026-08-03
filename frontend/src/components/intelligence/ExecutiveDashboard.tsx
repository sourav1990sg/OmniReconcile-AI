import { useMemo, useState, type ReactNode } from "react";
import type { AnalyticsReport } from "@/components/intelligence/analytics-types";
import type { BusinessIntelligenceReport } from "@/components/intelligence/bi-types";
import { formatInr, formatInt, formatPct } from "@/components/intelligence/analytics-types";
import { ChartHost } from "@/components/intelligence/ChartHost";
import {
  DecisionCardGrid,
  PriorityActionList,
} from "@/components/intelligence/DecisionCards";
import { InsightCards } from "@/components/intelligence/InsightCards";
import { ExplainedMetric } from "@/components/intelligence/KpiExplain";
import { PlatformScorecards, OutletScorecards } from "@/components/intelligence/Scorecards";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useBiFilterOptional } from "@/components/intelligence/interactive/BiFilterContext";

type Drill =
  | { kind: "settlement" }
  | { kind: "recoverable" }
  | { kind: "commission" }
  | { kind: "platform"; name: string }
  | { kind: "outlet"; name: string }
  | null;

/**
 * Executive Dashboard — interactive; KPIs from AnalyticsReport / projected slices.
 */
export function ExecutiveDashboard({
  report,
  bi = null,
}: {
  report: AnalyticsReport;
  bi?: BusinessIntelligenceReport | null;
}) {
  const biFilter = useBiFilterOptional();
  const view = biFilter?.view;
  const platforms = view?.platforms ?? report.platform_summary;
  const outlets = view?.outlets ?? report.outlet_summary;
  const chartData = view?.chart_data ?? report.chart_data;
  const hero = view?.hero;
  const ex = report.executive_summary;
  const fin = report.financial_summary;
  const tops = report.top_performers;
  const hasBi = Boolean(bi?.executive_summary);
  const [drill, setDrill] = useState<Drill>(null);

  const paymentMatchPct = hero?.payment_match_pct ?? chartData.payment_match?.pct ?? 0;
  const aov = hero?.aov ?? 0;

  const leaderboard = useMemo(() => {
    const by = (key: keyof (typeof outlets)[0], desc = true) =>
      [...outlets].sort((a, b) => {
        const av = Number(a[key] ?? 0);
        const bv = Number(b[key] ?? 0);
        return desc ? bv - av : av - bv;
      })[0];
    return {
      highestSales: tops.highest_online_sales_outlet,
      highestOrders: tops.highest_orders_outlet,
      highestAov: tops.highest_average_order_value,
      highestRecoverable: tops.highest_recoverable_amount,
      highestPaymentMatch: by("payment_match_pct")?.outlet,
      lowestPaymentMatch: by("payment_match_pct", false)?.outlet,
      highestCommission: by("commission")?.outlet,
      highestCancellation: tops.most_cancelled_outlet,
    };
  }, [outlets, tops]);

  const onPlatform = (name: string) => {
    biFilter?.crossFilterPlatform(name, "scorecard");
    setDrill({ kind: "platform", name });
  };
  const onOutlet = (name: string) => {
    biFilter?.crossFilterOutlet(name, "scorecard");
    setDrill({ kind: "outlet", name });
  };

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-lg font-semibold tracking-tight">Executive Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Sales · platforms · outlets · finance — under 30 seconds.
        </p>
      </header>

      {/* Sales Overview */}
      <section aria-label="Sales overview" className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Sales overview
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <ExplainedMetric
            label="Total Online Sales"
            value={formatInr(hero?.online_sales ?? ex.total_online_sales)}
            kpiId="total_online_sales"
            metrics={[
              { label: "Matched orders", value: formatInt(ex.matched_orders) },
              { label: "Eligible", value: formatInt(ex.eligible_orders) },
            ]}
          />
          <ExplainedMetric
            label="Platform Payout"
            value={formatInr(hero?.platform_payout ?? ex.platform_payout)}
            kpiId="platform_payout"
          />
          <ExplainedMetric
            label="Gross Order Value"
            value={formatInr(hero?.gross_order_value ?? ex.gross_order_value)}
            kpiId="gross_order_value"
          />
          <ExplainedMetric
            label="Recoverable"
            value={formatInr(hero?.recoverable ?? ex.recoverable_amount)}
            kpiId="recoverable"
            metrics={[
              {
                label: "Discrepancy orders",
                value: formatInt(ex.financial_discrepancy_orders),
              },
            ]}
            onDrill={() => setDrill({ kind: "recoverable" })}
          />
          <ExplainedMetric
            label="Average Order Value"
            value={formatInr(aov)}
            kpiId="aov"
            {...(tops.highest_average_order_value
              ? { hint: tops.highest_average_order_value }
              : {})}
          />
          <ExplainedMetric
            label="Settlement Coverage"
            value={formatPct(hero?.settlement_coverage_pct ?? ex.settlement_coverage_pct)}
            kpiId="settlement_coverage"
            metrics={[
              { label: "Matched", value: formatInt(ex.matched_orders) },
              { label: "Pending", value: formatInt(ex.pending_orders) },
              { label: "Cancelled", value: formatInt(ex.cancelled_orders) },
              { label: "Eligible", value: formatInt(ex.eligible_orders) },
            ]}
            onDrill={() => setDrill({ kind: "settlement" })}
          />
          <ExplainedMetric
            label="Payment Match %"
            value={formatPct(paymentMatchPct)}
            kpiId="payment_match"
            metrics={[
              { label: "Payment match orders", value: formatInt(ex.payment_match_orders) },
              { label: "Matched", value: formatInt(ex.matched_orders) },
            ]}
            onDrill={() => biFilter?.crossFilterPaymentMatch()}
          />
          <ExplainedMetric
            label="Agreement Coverage"
            value={formatInt(ex.agreement_verified_orders)}
            hint={`${formatInt(ex.agreement_violations)} violations`}
            kpiId="agreement_coverage"
          />
        </div>
      </section>

      {/* Platform Comparison */}
      <section aria-label="Platform comparison" className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Platform comparison
        </h3>
        <PlatformScorecards
          platforms={platforms}
          shares={{
            swiggy: report.platform_comparison.swiggy_revenue_share_pct,
            zomato: report.platform_comparison.zomato_revenue_share_pct,
          }}
          onSelect={onPlatform}
        />
      </section>

      <ChartHost chartData={chartData} variant="executive" />

      {/* Outlet Leaderboard */}
      <section aria-label="Outlet leaderboard" className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Outlet leaderboard
        </h3>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Highest Sales", leaderboard.highestSales],
            ["Highest Orders", leaderboard.highestOrders],
            ["Highest AOV", leaderboard.highestAov],
            ["Highest Payment Match", leaderboard.highestPaymentMatch],
            ["Lowest Payment Match", leaderboard.lowestPaymentMatch],
            ["Highest Recoverable", leaderboard.highestRecoverable],
            ["Highest Commission", leaderboard.highestCommission],
            ["Highest Cancellation", leaderboard.highestCancellation],
          ].map(([label, value]) => (
            <button
              key={String(label)}
              type="button"
              className="rounded-xl border border-border/60 bg-card p-3 text-left hover:bg-muted/40"
              onClick={() => value && onOutlet(String(value))}
            >
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-1 text-sm font-semibold">{value ?? "—"}</p>
            </button>
          ))}
        </div>
        <OutletScorecards outlets={outlets} onSelect={onOutlet} />
      </section>

      {/* Financial Summary */}
      <section aria-label="Financial summary" className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Financial summary
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <ExplainedMetric
            label="Commission"
            value={formatInr(hero?.commission ?? fin.total_commission)}
            kpiId="commission"
            onDrill={() => setDrill({ kind: "commission" })}
          />
          <ExplainedMetric label="GST" value={formatInr(fin.total_gst)} kpiId="commission" />
          <ExplainedMetric label="TDS" value={formatInr(fin.total_tds)} kpiId="commission" />
          <ExplainedMetric label="TCS" value={formatInr(fin.total_tcs)} kpiId="commission" />
          <ExplainedMetric
            label="Government Charges"
            value={formatInr(fin.total_government_charges)}
            kpiId="commission"
          />
          <ExplainedMetric
            label="Platform Charges"
            value={formatInr(fin.total_platform_deductions)}
            kpiId="commission"
          />
          <ExplainedMetric
            label="Net Platform Payout"
            value={formatInr(fin.net_platform_payout)}
            kpiId="platform_payout"
          />
          <ExplainedMetric
            label="Recoverable / Outstanding"
            value={formatInr(fin.recoverable)}
            kpiId="recoverable"
            hint={`${formatInt(ex.pending_orders)} pending · ${formatInt(ex.not_reconciled_orders)} not reconciled`}
          />
        </div>
      </section>

      {hasBi && bi ? (
        <section aria-label="Business intelligence" className="space-y-6">
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Priority actions
            </h3>
            <PriorityActionList actions={bi.priority_actions} />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Insight cards
            </h3>
            <DecisionCardGrid
              cards={bi.insight_cards}
              variant="insight"
              label="Insight cards"
              empty="No insight cards for this period."
            />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Risk cards
            </h3>
            <DecisionCardGrid
              cards={bi.risk_cards}
              variant="risk"
              label="Risk cards"
              empty="No risk cards."
            />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Opportunity cards
            </h3>
            <DecisionCardGrid
              cards={bi.opportunity_cards}
              variant="opportunity"
              label="Opportunity cards"
              empty="No opportunity cards."
            />
          </div>
          <div>
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Recommendation cards
            </h3>
            <DecisionCardGrid
              cards={bi.recommendation_cards}
              variant="recommendation"
              label="Recommendations"
              empty="No recommendations."
            />
          </div>
        </section>
      ) : (
        <div>
          <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Executive insights
          </h3>
          <InsightCards insights={report.business_insights ?? []} />
        </div>
      )}

      <DrillDialog
        report={report}
        platforms={platforms}
        outlets={outlets}
        drill={drill}
        onClose={() => setDrill(null)}
        onDrillThrough={() => {
          biFilter?.setTab("reconciliation");
          setDrill(null);
        }}
      />
    </div>
  );
}

function DrillDialog({
  report,
  platforms,
  outlets,
  drill,
  onClose,
  onDrillThrough,
}: {
  report: AnalyticsReport;
  platforms: AnalyticsReport["platform_summary"];
  outlets: AnalyticsReport["outlet_summary"];
  drill: Drill;
  onClose: () => void;
  onDrillThrough?: () => void;
}) {
  const ex = report.executive_summary;
  const open = drill != null;

  let title = "Details";
  let body: ReactNode = null;

  if (drill?.kind === "settlement") {
    title = "Settlement Coverage";
    body = (
      <dl className="grid gap-2 sm:grid-cols-2 text-sm">
        <Row label="Matched" value={formatInt(ex.matched_orders)} />
        <Row label="Pending" value={formatInt(ex.pending_orders)} />
        <Row label="Not reconciled" value={formatInt(ex.not_reconciled_orders)} />
        <Row label="Cancelled" value={formatInt(ex.cancelled_orders)} />
        <Row label="Eligible" value={formatInt(ex.eligible_orders)} />
        <Row label="Coverage" value={formatPct(ex.settlement_coverage_pct)} />
      </dl>
    );
  } else if (drill?.kind === "recoverable") {
    title = "Recoverable breakdown";
    body = (
      <div className="space-y-3 text-sm">
        <p>
          Total recoverable{" "}
          <span className="font-semibold tabular-nums">{formatInr(ex.recoverable_amount)}</span>
        </p>
        <ul className="space-y-1">
          {outlets
            .filter((o) => o.recoverable_amount > 0)
            .map((o) => (
              <li key={o.outlet} className="flex justify-between gap-2 border-b border-border/40 py-1">
                <span>{o.outlet}</span>
                <span className="tabular-nums">{formatInr(o.recoverable_amount)}</span>
              </li>
            ))}
          {!outlets.some((o) => o.recoverable_amount > 0) ? (
            <li className="text-muted-foreground">No outlet recoverable this period.</li>
          ) : null}
        </ul>
      </div>
    );
  } else if (drill?.kind === "commission") {
    title = "Commission by platform";
    body = (
      <ul className="space-y-1 text-sm">
        {platforms.map((p) => (
          <li key={p.platform} className="flex justify-between gap-2 border-b border-border/40 py-1">
            <span>{p.platform}</span>
            <span className="tabular-nums">{formatInr(p.commission)}</span>
          </li>
        ))}
      </ul>
    );
  } else if (drill?.kind === "platform") {
    title = `${drill.name} platform`;
    const p = platforms.find((x) => x.platform === drill.name);
    body = p ? (
      <dl className="grid gap-2 sm:grid-cols-2 text-sm">
        <Row label="Orders" value={formatInt(p.order_count)} />
        <Row label="Sales" value={formatInr(p.sales)} />
        <Row label="Payout" value={formatInr(p.platform_payout)} />
        <Row label="Commission" value={formatInr(p.commission)} />
        <Row label="Recoverable" value={formatInr(p.recoverable_amount)} />
        <Row label="Payment Match" value={formatPct(p.payment_match_pct)} />
        <Row label="Settlement %" value={formatPct(p.settlement_coverage_pct)} />
        <Row label="Agreement %" value={formatPct(p.agreement_verification_pct)} />
      </dl>
    ) : (
      <p className="text-sm text-muted-foreground">Platform not found in AnalyticsReport.</p>
    );
  } else if (drill?.kind === "outlet") {
    title = `${drill.name}`;
    const o = outlets.find((x) => x.outlet === drill.name);
    body = o ? (
      <dl className="grid gap-2 sm:grid-cols-2 text-sm">
        <Row label="Orders" value={formatInt(o.total_orders)} />
        <Row label="Sales" value={formatInr(o.sales)} />
        <Row label="Payout" value={formatInr(o.platform_payout)} />
        <Row label="AOV" value={formatInr(o.average_order_value)} />
        <Row label="Commission" value={formatInr(o.commission)} />
        <Row label="Recoverable" value={formatInr(o.recoverable_amount)} />
        <Row label="Payment Match" value={formatPct(o.payment_match_pct)} />
        <Row label="Cancelled" value={formatInt(o.cancelled)} />
        <Row label="Pending" value={formatInt(o.pending)} />
      </dl>
    ) : (
      <p className="text-sm text-muted-foreground">Outlet not found in AnalyticsReport.</p>
    );
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {body}
        {onDrillThrough && (drill?.kind === "platform" || drill?.kind === "outlet") ? (
          <button
            type="button"
            className="mt-4 text-sm font-medium text-foreground underline"
            onClick={onDrillThrough}
          >
            More details · open Reconciliation (filtered)
          </button>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border/50 px-2 py-1.5">
      <dt className="text-[10px] uppercase text-muted-foreground">{label}</dt>
      <dd className="font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
