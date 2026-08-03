import { lazy, Suspense, useMemo } from "react";
import type { ChartData } from "@/components/intelligence/analytics-types";
import { formatInr } from "@/components/intelligence/analytics-types";

const LazyCharts = lazy(() => import("@/components/intelligence/ChartPanels"));

function ChartSkeleton() {
  return (
    <div className="grid min-h-[220px] place-items-center rounded-xl border border-border/60 bg-muted/30 text-xs text-muted-foreground">
      Loading charts…
    </div>
  );
}

/** Lazy chart host — data must already be AnalyticsReport.chart_data. */
export function ChartHost({
  chartData,
  variant,
}: {
  chartData: ChartData;
  variant: "executive" | "finance" | "operations";
}) {
  const ready = useMemo(() => chartData, [chartData]);
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <LazyCharts chartData={ready} variant={variant} formatInr={formatInr} />
    </Suspense>
  );
}
