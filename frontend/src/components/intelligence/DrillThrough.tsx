import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { OutletSummary, PlatformSummary } from "@/components/intelligence/analytics-types";
import { formatInr, formatInt, formatPct } from "@/components/intelligence/analytics-types";

/**
 * Drill-through surfaces — dedicated detail panels from scorecards / KPI drill.
 * Values are passed from AnalyticsReport slices only.
 */
export function PlatformIntelligenceDialog({
  open,
  onOpenChange,
  platform,
  onOpenReconciliation,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  platform: PlatformSummary | null;
  onOpenReconciliation?: () => void;
}) {
  if (!platform) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Platform Intelligence · {platform.platform}</DialogTitle>
        </DialogHeader>
        <dl className="grid grid-cols-2 gap-2 text-xs">
          <Stat label="Orders" value={formatInt(platform.order_count)} />
          <Stat label="Sales" value={formatInr(platform.sales)} />
          <Stat label="Payout" value={formatInr(platform.platform_payout)} />
          <Stat label="Commission" value={formatInr(platform.commission)} />
          <Stat label="Recoverable" value={formatInr(platform.recoverable_amount)} />
          <Stat label="Coverage" value={formatPct(platform.settlement_coverage_pct)} />
          <Stat label="Payment Match" value={formatPct(platform.payment_match_pct)} />
          <Stat label="Agreement Verified" value={formatPct(platform.agreement_verification_pct)} />
        </dl>
        {onOpenReconciliation ? (
          <Button type="button" size="sm" className="mt-3" onClick={onOpenReconciliation}>
            More details · Reconciliation
          </Button>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export function OutletIntelligenceDialog({
  open,
  onOpenChange,
  outlet,
  onOpenReconciliation,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  outlet: OutletSummary | null;
  onOpenReconciliation?: () => void;
}) {
  if (!outlet) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Outlet Intelligence · {outlet.outlet}</DialogTitle>
        </DialogHeader>
        <dl className="grid grid-cols-2 gap-2 text-xs">
          <Stat label="Orders" value={formatInt(outlet.total_orders)} />
          <Stat label="Sales" value={formatInr(outlet.sales)} />
          <Stat label="Payout" value={formatInr(outlet.platform_payout)} />
          <Stat label="AOV" value={formatInr(outlet.average_order_value)} />
          <Stat label="Commission" value={formatInr(outlet.commission)} />
          <Stat label="Recoverable" value={formatInr(outlet.recoverable_amount)} />
          <Stat label="Payment Match" value={formatPct(outlet.payment_match_pct)} />
          <Stat label="Cancelled" value={formatInt(outlet.cancelled)} />
          <Stat label="Pending" value={formatInt(outlet.pending)} />
        </dl>
        {onOpenReconciliation ? (
          <Button type="button" size="sm" className="mt-3" onClick={onOpenReconciliation}>
            More details · Reconciliation
          </Button>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 px-2 py-1.5">
      <dt className="text-[10px] uppercase text-muted-foreground">{label}</dt>
      <dd className="font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
