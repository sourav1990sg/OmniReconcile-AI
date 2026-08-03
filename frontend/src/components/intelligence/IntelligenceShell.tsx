import type { ReactNode } from "react";
import { useMemo } from "react";
import { Printer } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Discrepancy } from "@/components/reconcile/data";
import { exportToCsv, exportToExcel } from "@/components/reconcile/export";
import type {
  AgreementSummaryView,
  AnalyticsReport,
} from "@/components/intelligence/analytics-types";
import type { BusinessIntelligenceReport } from "@/components/intelligence/bi-types";
import { ExecutiveDashboard } from "@/components/intelligence/ExecutiveDashboard";
import { FinanceDashboard } from "@/components/intelligence/FinanceDashboard";
import { OperationsDashboard } from "@/components/intelligence/OperationsDashboard";
import { AgreementsDashboard } from "@/components/intelligence/AgreementsDashboard";
import { ReconciliationWorkspace } from "@/components/intelligence/ReconciliationWorkspace";
import { ExecutivePrintView } from "@/components/intelligence/ExecutivePrintView";
import { formatInr, formatInt, formatPct } from "@/components/intelligence/analytics-types";
import { MetricTile } from "@/components/intelligence/KpiStrip";
import { ExplainedMetric } from "@/components/intelligence/KpiExplain";
import {
  BiFilterProvider,
  useBiFilter,
} from "@/components/intelligence/interactive/BiFilterContext";
import { GlobalFilterBar } from "@/components/intelligence/interactive/GlobalFilterBar";

/**
 * Enterprise Intelligence Shell — interactive BI foundation (Sprint 10A).
 * AnalyticsReport primary; filters select slices; no KPI recalculation.
 */
export function IntelligenceShell({
  report,
  bi = null,
  rows,
  agreement,
  statusStyles,
  toolbar,
}: {
  report: AnalyticsReport;
  bi?: BusinessIntelligenceReport | null;
  rows: Discrepancy[];
  agreement: AgreementSummaryView | null;
  statusStyles: Record<string, string>;
  toolbar?: ReactNode;
}) {
  return (
    <BiFilterProvider report={report} bi={bi} rows={rows}>
      <IntelligenceShellInner
        agreement={agreement}
        statusStyles={statusStyles}
        toolbar={toolbar}
      />
    </BiFilterProvider>
  );
}

function IntelligenceShellInner({
  agreement,
  statusStyles,
  toolbar,
}: {
  agreement: AgreementSummaryView | null;
  statusStyles: Record<string, string>;
  toolbar?: ReactNode;
}) {
  const { view, filteredRows, ui, setTab, bi, report, crossFilterPaymentMatch } = useBiFilter();
  const hero = view.hero;
  const hasBi = Boolean(bi?.executive_summary);

  const aovDisplay = useMemo(() => formatInr(hero.aov), [hero.aov]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            OmniReconcile Interactive Intelligence
          </p>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Restaurant Financial Intelligence
          </h1>
          {hasBi && bi ? (
            <>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                {bi.executive_summary.headline}
              </p>
              <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
                Next: {bi.executive_summary.next_action}
              </p>
            </>
          ) : (
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              {formatInr(hero.online_sales)} online sales · {formatInt(hero.orders)} orders ·{" "}
              {formatPct(hero.settlement_coverage_pct)} coverage · AOV {aovDisplay}
            </p>
          )}
          <p className="mt-1 text-[10px] text-muted-foreground">KPI source · {hero.source_label}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {toolbar}
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs print:hidden"
            disabled={filteredRows.length === 0}
            onClick={() => {
              try {
                exportToCsv(filteredRows);
                toast.success("CSV exported (filtered view)");
              } catch {
                toast.error("CSV export failed");
              }
            }}
          >
            Export CSV
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs print:hidden"
            disabled={filteredRows.length === 0}
            onClick={() => {
              try {
                exportToExcel(filteredRows);
                toast.success("Excel exported (filtered view)");
              } catch {
                toast.error("Excel export failed");
              }
            }}
          >
            Export Excel
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs print:hidden"
            onClick={() => window.print()}
          >
            <Printer className="h-3.5 w-3.5" />
            Executive Report
          </Button>
        </div>
      </div>

      <GlobalFilterBar />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 print:hidden">
        <ExplainedMetric
          label="Online Sales"
          value={formatInr(hero.online_sales)}
          kpiId="total_online_sales"
          hint={hero.source_label}
        />
        <ExplainedMetric
          label="Platform Payout"
          value={formatInr(hero.platform_payout)}
          kpiId="platform_payout"
        />
        <ExplainedMetric
          label="Recoverable"
          value={formatInr(hero.recoverable)}
          kpiId="recoverable"
        />
        <ExplainedMetric
          label="Settlement Coverage"
          value={formatPct(hero.settlement_coverage_pct)}
          kpiId="settlement_coverage"
          onDrill={crossFilterPaymentMatch}
        />
      </section>

      <Tabs
        value={ui.tab}
        onValueChange={setTab}
        className="print:hidden"
      >
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 bg-muted/60 p-1">
          <TabsTrigger value="executive">Executive</TabsTrigger>
          <TabsTrigger value="finance">Finance</TabsTrigger>
          <TabsTrigger value="operations">Operations</TabsTrigger>
          <TabsTrigger value="reconciliation">Reconciliation</TabsTrigger>
          <TabsTrigger value="agreements">Agreements</TabsTrigger>
        </TabsList>

        <TabsContent value="executive" className="mt-4 focus-visible:outline-none">
          <ExecutiveDashboard report={report} bi={bi} />
        </TabsContent>
        <TabsContent value="finance" className="mt-4 focus-visible:outline-none">
          <FinanceDashboard report={report} bi={bi} />
        </TabsContent>
        <TabsContent value="operations" className="mt-4 focus-visible:outline-none">
          <OperationsDashboard report={report} bi={bi} />
        </TabsContent>
        <TabsContent value="reconciliation" className="mt-4 focus-visible:outline-none">
          <ReconciliationWorkspace rows={filteredRows} statusStyles={statusStyles} />
        </TabsContent>
        <TabsContent value="agreements" className="mt-4 focus-visible:outline-none">
          <AgreementsDashboard report={report} bi={bi} agreement={agreement} />
        </TabsContent>
      </Tabs>

      <ExecutivePrintView report={report} bi={bi} />
    </div>
  );
}
