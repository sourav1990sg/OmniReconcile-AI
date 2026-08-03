import type { OutletSummary, PlatformSummary } from "@/components/intelligence/analytics-types";
import { formatInr, formatInt, formatPct } from "@/components/intelligence/analytics-types";

function topPlatform(o: OutletSummary): string {
  const entries = Object.entries(o.platform_wise_orders ?? {});
  if (!entries.length) return "—";
  entries.sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0));
  return entries[0]?.[0] ?? "—";
}

/** Outlet scorecard — values from AnalyticsReport.outlet_summary only. */
export function OutletScorecards({
  outlets,
  onSelect,
}: {
  outlets: OutletSummary[];
  onSelect?: (outlet: string) => void;
}) {
  return (
    <section aria-label="Outlet scorecards" className="grid gap-3 lg:grid-cols-2">
      {outlets.map((o) => (
        <article
          key={o.outlet}
          className="rounded-xl border border-border/60 bg-card p-4 shadow-none"
        >
          <header className="flex items-start justify-between gap-2">
            <div>
              <button
                type="button"
                className="text-left text-base font-semibold text-foreground hover:underline"
                onClick={() => onSelect?.(o.outlet)}
              >
                {o.outlet}
              </button>
              <p className="text-[11px] text-muted-foreground">Top platform · {topPlatform(o)}</p>
            </div>
            <span className="rounded-md bg-muted px-2 py-1 text-[11px] tabular-nums">
              {formatInt(o.total_orders)} orders
            </span>
          </header>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
            <Stat label="Sales" value={formatInr(o.sales)} />
            <Stat label="GOV" value={formatInr(o.gross_order_value)} />
            <Stat label="Payout" value={formatInr(o.platform_payout)} />
            <Stat label="AOV" value={formatInr(o.average_order_value)} />
            <Stat label="Commission" value={formatInr(o.commission)} />
            <Stat label="Recoverable" value={formatInr(o.recoverable_amount)} />
            <Stat label="Payment Match" value={formatPct(o.payment_match_pct)} />
            <Stat label="Agreement Verified" value={formatPct(o.agreement_verified_pct)} />
            <Stat label="Cancelled" value={formatInt(o.cancelled)} />
            <Stat label="Pending" value={formatInt(o.pending)} />
          </dl>
        </article>
      ))}
    </section>
  );
}

/** Platform scorecard — full AnalyticsReport.platform_summary surface. */
export function PlatformScorecards({
  platforms,
  shares,
  onSelect,
}: {
  platforms: PlatformSummary[];
  shares?: { swiggy?: number; zomato?: number };
  onSelect?: (platform: string) => void;
}) {
  return (
    <section aria-label="Platform scorecards" className="grid gap-3 md:grid-cols-2">
      {platforms.map((p) => {
        const share =
          p.platform === "Swiggy"
            ? shares?.swiggy
            : p.platform === "Zomato"
              ? shares?.zomato
              : undefined;
        const discount = (p.restaurant_discount ?? 0) + (p.platform_discount ?? 0);
        return (
          <article key={p.platform} className="rounded-xl border border-border/60 bg-card p-4">
            <header className="flex items-center justify-between">
              <button
                type="button"
                className="text-base font-semibold hover:underline"
                onClick={() => onSelect?.(p.platform)}
              >
                {p.platform}
              </button>
              {share != null ? (
                <span className="text-[11px] text-muted-foreground">
                  Revenue share {formatPct(share)}
                </span>
              ) : null}
            </header>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
              <Stat label="Orders" value={formatInt(p.order_count)} />
              <Stat label="Online Sales" value={formatInr(p.sales)} />
              <Stat label="Gross Order Value" value={formatInr(p.gross_order_value)} />
              <Stat label="Platform Payout" value={formatInr(p.platform_payout)} />
              <Stat label="Commission" value={formatInr(p.commission)} />
              <Stat label="Discount" value={formatInr(discount)} />
              <Stat label="Promo Recovery" value={formatInr(p.promo_recovery)} />
              <Stat label="Customer Comp." value={formatInr(p.customer_compensation)} />
              <Stat label="Recoverable" value={formatInr(p.recoverable_amount)} />
              <Stat label="Settlement Coverage" value={formatPct(p.settlement_coverage_pct)} />
              <Stat label="Agreement Coverage" value={formatPct(p.agreement_verification_pct)} />
              <Stat label="AOV" value={formatInr(p.average_order_value)} />
              <Stat label="Payment Match %" value={formatPct(p.payment_match_pct)} />
            </dl>
            {p.order_count > 0 && p.sales === 0 ? (
              <p className="mt-2 text-[11px] text-destructive">
                Data integrity: orders &gt; 0 but sales is ₹0 — review AnalyticsReport.
              </p>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 px-2 py-1.5">
      <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-semibold tabular-nums text-foreground">{value}</dd>
    </div>
  );
}
