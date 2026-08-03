import { Lightbulb } from "lucide-react";

/** Renders AnalyticsReport.business_insights — display only. */
export function InsightCards({ insights }: { insights: string[] }) {
  if (!insights.length) {
    return (
      <p className="text-sm text-muted-foreground">
        Insights appear after reconciliation produces an AnalyticsReport.
      </p>
    );
  }
  return (
    <section aria-label="Executive insights" className="grid gap-3 md:grid-cols-2">
      {insights.map((text) => (
        <article
          key={text}
          className="flex gap-3 rounded-xl border border-border/60 bg-card p-4"
        >
          <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-muted text-foreground">
            <Lightbulb className="h-4 w-4" aria-hidden />
          </span>
          <p className="text-sm leading-relaxed text-foreground">{text}</p>
        </article>
      ))}
    </section>
  );
}
