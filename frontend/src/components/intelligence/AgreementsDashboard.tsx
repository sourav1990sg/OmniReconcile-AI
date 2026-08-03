import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AgreementSummaryView, AnalyticsReport } from "@/components/intelligence/analytics-types";
import type { BusinessIntelligenceReport } from "@/components/intelligence/bi-types";
import { formatInt } from "@/components/intelligence/analytics-types";
import { DecisionCardGrid } from "@/components/intelligence/DecisionCards";
import { MetricTile } from "@/components/intelligence/KpiStrip";
import { useBiFilterOptional } from "@/components/intelligence/interactive/BiFilterContext";

type AgreementCard = NonNullable<AgreementSummaryView["active"]>;

function asAgreementCard(raw: Record<string, unknown> | AgreementCard): AgreementCard {
  const out: AgreementCard = {};
  if (typeof raw.agreement_id === "string") out.agreement_id = raw.agreement_id;
  if (typeof raw.version === "string") out.version = raw.version;
  if (typeof raw.status === "string") out.status = raw.status;
  if (typeof raw.platform === "string") out.platform = raw.platform;
  if (typeof raw.restaurant === "string") out.restaurant = raw.restaurant;
  if (typeof raw.source_filename === "string") out.source_filename = raw.source_filename;
  if (typeof raw.unknown_terms === "number") out.unknown_terms = raw.unknown_terms;
  if (typeof raw.effective_from === "string" || raw.effective_from === null) {
    out.effective_from = raw.effective_from as string | null;
  }
  if (typeof raw.effective_to === "string" || raw.effective_to === null) {
    out.effective_to = raw.effective_to as string | null;
  }
  if (raw.rules && typeof raw.rules === "object") {
    out.rules = raw.rules as NonNullable<AgreementCard["rules"]>;
  }
  return out;
}

/**
 * Agreements dashboard — interactive local filters on agreement metadata.
 * Coverage KPIs still read from AnalyticsReport only.
 */
export function AgreementsDashboard({
  report,
  bi = null,
  agreement,
}: {
  report: AnalyticsReport;
  bi?: BusinessIntelligenceReport | null;
  agreement: AgreementSummaryView | null;
}) {
  const biFilter = useBiFilterOptional();
  const ex = report.executive_summary;
  const platforms = biFilter?.view.platforms ?? report.platform_summary;
  const hasBi = Boolean(bi?.executive_summary);

  const [platformFilter, setPlatformFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [ruleCategory, setRuleCategory] = useState("All");

  const allCards = useMemo(() => {
    if (agreement?.agreements?.length) {
      return agreement.agreements.map((a) => asAgreementCard(a));
    }
    if (agreement?.active) return [agreement.active];
    return [] as AgreementCard[];
  }, [agreement]);

  const agreements = useMemo(() => {
    return allCards.filter((a) => {
      if (platformFilter !== "All" && (a.platform ?? "") !== platformFilter) return false;
      if (statusFilter !== "All" && (a.status ?? "") !== statusFilter) return false;
      return true;
    });
  }, [allCards, platformFilter, statusFilter]);

  const active = agreements[0] ?? agreement?.active ?? null;
  const rules = active?.rules ? Object.entries(active.rules) : [];
  const filteredRules =
    ruleCategory === "All"
      ? rules
      : rules.filter(([key]) => key.toLowerCase().includes(ruleCategory.toLowerCase()));

  const statuses = useMemo(() => {
    const s = new Set<string>();
    allCards.forEach((a) => {
      if (a.status) s.add(a.status);
    });
    return ["All", ...Array.from(s)];
  }, [allCards]);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold tracking-tight">Commercial Agreements</h2>
        <p className="text-sm text-muted-foreground">
          Coverage from AnalyticsReport
          {hasBi ? " · commercial risks from BusinessIntelligenceReport" : ""}.
        </p>
      </header>

      <div className="flex flex-wrap gap-2 print:hidden">
        <Select
          value={platformFilter}
          onValueChange={(v) => {
            setPlatformFilter(v);
            if (v !== "All") biFilter?.crossFilterPlatform(v, "agreement");
          }}
        >
          <SelectTrigger className="h-8 w-[140px] text-xs">
            <SelectValue placeholder="Platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All platforms</SelectItem>
            {platforms.map((p) => (
              <SelectItem key={p.platform} value={p.platform}>
                {p.platform}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="h-8 w-[160px] text-xs">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {statuses.map((s) => (
              <SelectItem key={s} value={s}>
                {s === "All" ? "All statuses" : s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={ruleCategory} onValueChange={setRuleCategory}>
          <SelectTrigger className="h-8 w-[160px] text-xs">
            <SelectValue placeholder="Rule category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All rule categories</SelectItem>
            <SelectItem value="commission">Commission</SelectItem>
            <SelectItem value="gst">GST</SelectItem>
            <SelectItem value="tds">TDS</SelectItem>
            <SelectItem value="tcs">TCS</SelectItem>
            <SelectItem value="payment">Payment</SelectItem>
            <SelectItem value="promo">Promo</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Agreement Verified Orders" value={formatInt(ex.agreement_verified_orders)} />
        <MetricTile label="Agreement Violations" value={formatInt(ex.agreement_violations)} />
        <MetricTile label="Payment Match Orders" value={formatInt(ex.payment_match_orders)} />
        <MetricTile
          label="Uploaded Agreements"
          value={formatInt(agreement?.count ?? (active ? 1 : 0))}
        />
      </section>

      {hasBi && bi ? (
        <div>
          <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Commercial risks
          </h3>
          <DecisionCardGrid
            cards={bi.commercial_risks}
            variant="risk"
            label="Commercial risks"
            empty="No commercial agreement risks."
          />
        </div>
      ) : null}

      {agreements.length > 1 ? (
        <ul className="grid gap-2 md:grid-cols-2">
          {agreements.map((a, i) => (
            <li
              key={`${a.platform}-${a.version}-${i}`}
              className="rounded-xl border border-border/60 bg-card p-3 text-xs"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{a.source_filename ?? a.platform ?? "Agreement"}</span>
                <Badge variant="outline">{a.status ?? "—"}</Badge>
                <Badge variant="secondary">v{a.version ?? "1"}</Badge>
              </div>
              <p className="mt-1 text-muted-foreground">
                {a.platform ?? "—"} · {a.effective_from ?? "—"} → {a.effective_to ?? "—"}
              </p>
            </li>
          ))}
        </ul>
      ) : null}

      {active ? (
        <article className="rounded-xl border border-border/60 bg-card p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold">{active.source_filename ?? "Agreement"}</h3>
            <Badge variant="outline">{active.status ?? "Pending Review"}</Badge>
            <Badge variant="secondary">Version {active.version ?? "1"}</Badge>
          </div>
          <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">Platform</dt>
              <dd className="font-medium">{active.platform ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Effective</dt>
              <dd className="font-medium">{active.effective_from ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Expiry</dt>
              <dd className="font-medium">{active.effective_to ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Unknown terms</dt>
              <dd className="font-medium">{active.unknown_terms ?? 0}</dd>
            </div>
          </dl>
          {filteredRules.length > 0 ? (
            <dl className="mt-4 grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
              {filteredRules.slice(0, 24).map(([key, field]) => (
                <div
                  key={key}
                  className="flex justify-between gap-2 rounded border border-border/50 px-2 py-1"
                >
                  <dt className="truncate text-muted-foreground">{key.replace(/_/g, " ")}</dt>
                  <dd className="font-medium tabular-nums">
                    {field.unknown || field.value == null ? "UNKNOWN" : String(field.value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-3 text-xs text-muted-foreground">No rules match this category.</p>
          )}
        </article>
      ) : (
        <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">
          No commercial agreement uploaded. Settlement verification still applies.
        </p>
      )}
    </div>
  );
}
