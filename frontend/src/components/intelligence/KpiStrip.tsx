import { cn } from "@/lib/utils";
import type { KpiCard, Tone } from "@/components/intelligence/analytics-types";

function toneClass(tone?: Tone | string) {
  if (tone === "warning") return "text-warning";
  if (tone === "success") return "text-success";
  return "text-foreground";
}

/** Renders AnalyticsReport.kpi_cards — display only. */
export function KpiStrip({ cards, className }: { cards: KpiCard[]; className?: string }) {
  if (!cards.length) return null;
  return (
    <section
      aria-label="KPI cards"
      className={cn("grid gap-3 sm:grid-cols-2 xl:grid-cols-3", className)}
    >
      {cards.map((card) => (
        <article
          key={card.id ?? card.label}
          className="card-elevated rounded-xl border border-border/60 bg-card p-4"
        >
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            {card.label}
          </p>
          <p className={cn("mt-2 text-2xl font-semibold tracking-tight tabular-nums", toneClass(card.tone))}>
            {card.value}
          </p>
          <p className="mt-1 truncate text-[11px] text-muted-foreground">{card.caption}</p>
        </article>
      ))}
    </section>
  );
}

export function MetricTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <article className="rounded-xl border border-border/60 bg-card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-xl font-semibold tabular-nums text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p> : null}
    </article>
  );
}
