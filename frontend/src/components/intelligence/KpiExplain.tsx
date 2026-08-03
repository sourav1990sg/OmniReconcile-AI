import { useState } from "react";
import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  KPI_EXPLANATIONS,
  type KpiExplanation,
} from "@/components/intelligence/kpi-explanations";
import { MetricTile } from "@/components/intelligence/KpiStrip";

/** Info control that opens a calculation provenance dialog. */
export function KpiExplainButton({
  kpiId,
  metrics,
}: {
  kpiId: string;
  metrics?: Array<{ label: string; value: string }> | undefined;
}) {
  const [open, setOpen] = useState(false);
  const exp: KpiExplanation | undefined = KPI_EXPLANATIONS[kpiId];
  if (!exp) return null;

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-6 gap-1 px-1.5 text-[10px] text-muted-foreground"
        onClick={() => setOpen(true)}
        aria-label={`How is ${exp.title} calculated?`}
      >
        <Info className="h-3.5 w-3.5" />
        Details
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{exp.title} — calculation</DialogTitle>
            <DialogDescription>{exp.description}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Formula
              </p>
              <p className="mt-1 font-mono text-xs leading-relaxed">{exp.formula}</p>
            </div>
            {metrics && metrics.length > 0 ? (
              <dl className="grid gap-2 sm:grid-cols-2">
                {metrics.map((m) => (
                  <div key={m.label} className="rounded border border-border/50 px-2 py-1.5">
                    <dt className="text-[10px] uppercase text-muted-foreground">{m.label}</dt>
                    <dd className="font-semibold tabular-nums">{m.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                AnalyticsReport fields
              </p>
              <ul className="mt-1 list-inside list-disc text-xs text-muted-foreground">
                {exp.sourceFields.map((f) => (
                  <li key={f} className="font-mono">
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            {exp.notes ? <p className="text-xs text-muted-foreground">{exp.notes}</p> : null}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Metric tile with explainability affordance. */
export function ExplainedMetric({
  label,
  value,
  hint,
  kpiId,
  metrics,
  onDrill,
}: {
  label: string;
  value: string;
  hint?: string | undefined;
  kpiId: string;
  metrics?: Array<{ label: string; value: string }> | undefined;
  onDrill?: (() => void) | undefined;
}) {
  return (
    <article className="rounded-xl border border-border/60 bg-card p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <KpiExplainButton kpiId={kpiId} {...(metrics ? { metrics } : {})} />
      </div>
      <button
        type="button"
        className="mt-2 block w-full text-left text-xl font-semibold tabular-nums text-foreground hover:underline"
        onClick={onDrill}
        disabled={!onDrill}
      >
        {value}
      </button>
      {hint ? <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p> : null}
    </article>
  );
}

export function ExplainedMetricStatic(props: {
  label: string;
  value: string;
  hint?: string;
}) {
  return <MetricTile {...props} />;
}
