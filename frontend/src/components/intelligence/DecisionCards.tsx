import { AlertTriangle, Lightbulb, Target, TrendingUp } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type {
  IntelligenceCard,
  PriorityAction,
  Severity,
} from "@/components/intelligence/bi-types";

function severityTone(severity: Severity) {
  if (severity === "Critical" || severity === "High") return "destructive" as const;
  if (severity === "Medium") return "secondary" as const;
  return "outline" as const;
}

function severityClass(severity: Severity) {
  if (severity === "Critical") return "border-destructive/50 bg-destructive/5";
  if (severity === "High") return "border-destructive/40 bg-destructive/5";
  if (severity === "Medium") return "border-amber-700/30 bg-amber-50/50 dark:bg-amber-950/20";
  return "border-border/60 bg-card";
}

const OWNER_BY_DOMAIN: Record<string, string> = {
  finance: "CFO",
  recovery: "Finance",
  commercial: "Commercial",
  operations: "Operations",
  outlet: "Operations",
  platform: "CEO",
  general: "CEO",
};

function priorityFromSeverity(severity: Severity): string {
  if (severity === "Critical") return "P0";
  if (severity === "High") return "P1";
  if (severity === "Medium") return "P2";
  return "P3";
}

function MetricList({ metrics }: { metrics: IntelligenceCard["supporting_metrics"] }) {
  const entries = Object.entries(metrics ?? {}).slice(0, 8);
  if (!entries.length) return null;
  return (
    <dl className="mt-2 grid gap-1 sm:grid-cols-2">
      {entries.map(([k, v]) => (
        <div
          key={k}
          className="flex justify-between gap-2 rounded border border-border/40 px-2 py-1 text-[10px]"
        >
          <dt className="uppercase tracking-wide text-muted-foreground">
            {k.replace(/_/g, " ")}
          </dt>
          <dd className="font-medium tabular-nums text-foreground">{String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Decision card with expandable supporting metrics (Sprint 10A). */
export function DecisionCard({
  card,
  variant = "insight",
}: {
  card: IntelligenceCard;
  variant?: "insight" | "risk" | "opportunity" | "recommendation";
}) {
  const [open, setOpen] = useState(false);
  const Icon =
    variant === "risk"
      ? AlertTriangle
      : variant === "opportunity"
        ? TrendingUp
        : variant === "recommendation"
          ? Target
          : Lightbulb;
  const owner = OWNER_BY_DOMAIN[card.domain ?? "general"] ?? "CEO";
  const priority = priorityFromSeverity(card.severity);

  return (
    <article
      className={cn("rounded-xl border p-4", severityClass(card.severity))}
      aria-label={`${card.title} — ${card.severity}`}
    >
      <button type="button" className="w-full text-left" onClick={() => setOpen((v) => !v)}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-2">
            <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-muted">
              <Icon className="h-4 w-4" aria-hidden />
            </span>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold leading-snug">{card.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{card.description}</p>
            </div>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <Badge variant={severityTone(card.severity)} className="text-[10px]">
              {card.severity}
            </Badge>
            <Badge variant="outline" className="text-[10px]">
              {priority}
            </Badge>
          </div>
        </div>
      </button>
      <div className="mt-3 space-y-1.5 text-xs">
        <p>
          <span className="font-semibold text-foreground">Business impact: </span>
          <span className="text-muted-foreground">{card.business_impact}</span>
        </p>
        <p>
          <span className="font-semibold text-foreground">Recommended action: </span>
          <span className="text-foreground">{card.recommended_action}</span>
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          <Badge variant="secondary" className="text-[10px]">
            Owner · {owner}
          </Badge>
          <span className="text-[11px] text-muted-foreground">
            Confidence {Math.round((card.confidence ?? 0) * 100)}%
          </span>
          <button
            type="button"
            className="text-[11px] font-medium text-foreground underline"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide evidence" : "Supporting metrics"}
          </button>
        </div>
      </div>
      {open ? (
        <div className="mt-3 rounded-lg border border-border/50 bg-muted/20 p-3">
          <p className="text-[10px] font-semibold uppercase text-muted-foreground">
            Reason / evidence
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{card.description}</p>
          <p className="mt-2 text-[10px] font-semibold uppercase text-muted-foreground">
            Expected benefit
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Resolve this {variant} to protect payout integrity and operating margin.
          </p>
          <MetricList metrics={card.supporting_metrics} />
        </div>
      ) : null}
    </article>
  );
}

export function DecisionCardGrid({
  cards,
  variant,
  empty,
  label,
}: {
  cards: IntelligenceCard[];
  variant: "insight" | "risk" | "opportunity" | "recommendation";
  empty: string;
  label: string;
}) {
  if (!cards.length) {
    return <p className="text-sm text-muted-foreground">{empty}</p>;
  }
  return (
    <section aria-label={label} className="grid gap-3 md:grid-cols-2">
      {cards.map((c) => (
        <DecisionCard key={c.id} card={c} variant={variant} />
      ))}
    </section>
  );
}

export function PriorityActionList({ actions }: { actions: PriorityAction[] }) {
  if (!actions.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No priority actions — financials look stable this cycle.
      </p>
    );
  }
  return (
    <ol className="space-y-3" aria-label="Priority actions">
      {actions.map((a) => (
        <li
          key={`${a.rank}-${a.title}`}
          className={cn("flex gap-3 rounded-xl border p-4", severityClass(a.severity))}
        >
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-foreground text-sm font-semibold text-background">
            {a.rank}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold">{a.title}</h3>
              <Badge variant={severityTone(a.severity)} className="text-[10px]">
                {a.severity}
              </Badge>
              <Badge variant="outline" className="text-[10px]">
                {a.owner}
              </Badge>
              <Badge variant="secondary" className="text-[10px]">
                {priorityFromSeverity(a.severity)}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{a.description}</p>
            <p className="mt-2 text-xs">
              <span className="font-semibold">Do next: </span>
              {a.recommended_action}
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground">{a.business_impact}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
