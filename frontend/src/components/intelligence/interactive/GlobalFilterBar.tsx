import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBiFilter } from "@/components/intelligence/interactive/BiFilterContext";

/**
 * Global filter bar — drives every dashboard via BiFilterContext.
 * Does not compute KPIs; only sets selection state.
 */
export function GlobalFilterBar() {
  const {
    filters,
    setFilter,
    clearFilters,
    resetAll,
    report,
    activeFilterCount,
    filteredRows,
    allRows,
  } = useBiFilter();

  const outlets = report.outlet_summary.map((o) => o.outlet);
  const [searchDraft, setSearchDraft] = useState(filters.search);

  useEffect(() => {
    setSearchDraft(filters.search);
  }, [filters.search]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      if (searchDraft !== filters.search) setFilter("search", searchDraft);
    }, 250);
    return () => window.clearTimeout(t);
  }, [searchDraft, filters.search, setFilter]);

  return (
    <section
      aria-label="Global intelligence filters"
      className="space-y-2 rounded-xl border border-border/60 bg-card/80 p-3 print:hidden"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Interactive filters
          </p>
          <p className="text-[11px] text-muted-foreground">
            {filteredRows.length.toLocaleString("en-IN")} / {allRows.length.toLocaleString("en-IN")}{" "}
            orders in view · KPIs from AnalyticsReport slices
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Button type="button" variant="outline" size="sm" className="h-7 text-xs" onClick={clearFilters}>
            Clear Filters
          </Button>
          <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={resetAll}>
            Reset
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Select value={filters.period} onValueChange={(v) => setFilter("period", v as typeof filters.period)}>
          <SelectTrigger className="h-8 w-[130px] text-xs" aria-label="Period">
            <SelectValue placeholder="Period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All time</SelectItem>
            <SelectItem value="month">Month</SelectItem>
            <SelectItem value="quarter">Quarter</SelectItem>
            <SelectItem value="fy">Financial year</SelectItem>
            <SelectItem value="custom">Custom range</SelectItem>
          </SelectContent>
        </Select>

        <Input
          type="date"
          className="h-8 w-[140px] text-xs"
          value={filters.dateFrom ?? ""}
          onChange={(e) => setFilter("dateFrom", e.target.value || null)}
          aria-label="Date from"
        />
        <Input
          type="date"
          className="h-8 w-[140px] text-xs"
          value={filters.dateTo ?? ""}
          onChange={(e) => setFilter("dateTo", e.target.value || null)}
          aria-label="Date to"
        />

        <Select value={filters.outlet} onValueChange={(v) => setFilter("outlet", v)}>
          <SelectTrigger className="h-8 w-[180px] text-xs" aria-label="Outlet">
            <SelectValue placeholder="Outlet" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All outlets</SelectItem>
            {outlets.map((o) => (
              <SelectItem key={o} value={o}>
                {o}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filters.platform} onValueChange={(v) => setFilter("platform", v)}>
          <SelectTrigger className="h-8 w-[120px] text-xs" aria-label="Platform">
            <SelectValue placeholder="Platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All platforms</SelectItem>
            <SelectItem value="Swiggy">Swiggy</SelectItem>
            <SelectItem value="Zomato">Zomato</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={filters.paymentStatus}
          onValueChange={(v) => setFilter("paymentStatus", v)}
        >
          <SelectTrigger className="h-8 w-[150px] text-xs" aria-label="Payment status">
            <SelectValue placeholder="Payment" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All payment</SelectItem>
            <SelectItem value="Payment Match">Payment Match</SelectItem>
            <SelectItem value="Payment Mismatch">Payment Mismatch</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={filters.agreementStatus}
          onValueChange={(v) => setFilter("agreementStatus", v)}
        >
          <SelectTrigger className="h-8 w-[140px] text-xs" aria-label="Agreement status">
            <SelectValue placeholder="Agreement" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All agreements</SelectItem>
            <SelectItem value="Verified">Verified</SelectItem>
            <SelectItem value="Violation">Violation</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={filters.verificationLevel}
          onValueChange={(v) => setFilter("verificationLevel", v)}
        >
          <SelectTrigger className="h-8 w-[170px] text-xs" aria-label="Verification level">
            <SelectValue placeholder="Verification" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All verification</SelectItem>
            <SelectItem value="SETTLEMENT_VERIFIED">Settlement verified</SelectItem>
            <SelectItem value="AGREEMENT_VERIFIED">Agreement verified</SelectItem>
            <SelectItem value="AGREEMENT_VIOLATION">Agreement violation</SelectItem>
            <SelectItem value="PAYMENT_MISMATCH">Payment mismatch</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={filters.settlementStatus}
          onValueChange={(v) => setFilter("settlementStatus", v)}
        >
          <SelectTrigger className="h-8 w-[180px] text-xs" aria-label="Settlement status">
            <SelectValue placeholder="Settlement" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All settlement</SelectItem>
            <SelectItem value="FINANCIALLY_RECONCILED">Financially reconciled</SelectItem>
            <SelectItem value="FINANCIAL_DISCREPANCY">Financial discrepancy</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="CANCELLED">Cancelled</SelectItem>
            <SelectItem value="NOT_RECONCILED">Not reconciled</SelectItem>
          </SelectContent>
        </Select>

        <Button
          type="button"
          size="sm"
          variant={filters.cancelledOnly ? "default" : "outline"}
          className="h-8 text-xs"
          onClick={() => setFilter("cancelledOnly", !filters.cancelledOnly)}
        >
          Cancelled
        </Button>
        <Button
          type="button"
          size="sm"
          variant={filters.pendingOnly ? "default" : "outline"}
          className="h-8 text-xs"
          onClick={() => setFilter("pendingOnly", !filters.pendingOnly)}
        >
          Pending
        </Button>

        <Input
          className="h-8 min-w-[180px] flex-1 text-xs"
          placeholder="Search order / invoice / outlet"
          value={searchDraft}
          onChange={(e) => setSearchDraft(e.target.value)}
          aria-label="Search orders"
        />
      </div>

      {activeFilterCount > 0 ? (
        <div className="flex flex-wrap items-center gap-1.5" aria-label="Active filters">
          <span className="text-[10px] uppercase text-muted-foreground">Active</span>
          {filters.platform !== "All" ? (
            <Chip label={`Platform: ${filters.platform}`} onClear={() => setFilter("platform", "All")} />
          ) : null}
          {filters.outlet !== "All" ? (
            <Chip label={`Outlet: ${filters.outlet}`} onClear={() => setFilter("outlet", "All")} />
          ) : null}
          {filters.paymentStatus !== "All" ? (
            <Chip
              label={filters.paymentStatus}
              onClear={() => setFilter("paymentStatus", "All")}
            />
          ) : null}
          {filters.agreementStatus !== "All" ? (
            <Chip
              label={`Agreement: ${filters.agreementStatus}`}
              onClear={() => setFilter("agreementStatus", "All")}
            />
          ) : null}
          {filters.verificationLevel !== "All" ? (
            <Chip
              label={filters.verificationLevel}
              onClear={() => setFilter("verificationLevel", "All")}
            />
          ) : null}
          {filters.settlementStatus !== "All" ? (
            <Chip
              label={filters.settlementStatus}
              onClear={() => setFilter("settlementStatus", "All")}
            />
          ) : null}
          {filters.cancelledOnly ? (
            <Chip label="Cancelled" onClear={() => setFilter("cancelledOnly", false)} />
          ) : null}
          {filters.pendingOnly ? (
            <Chip label="Pending" onClear={() => setFilter("pendingOnly", false)} />
          ) : null}
          {filters.search.trim() ? (
            <Chip label={`Search: ${filters.search}`} onClear={() => setFilter("search", "")} />
          ) : null}
          {filters.crossFilterSource ? (
            <Badge variant="secondary" className="text-[10px]">
              Cross-filter · {filters.crossFilterSource}
            </Badge>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function Chip({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <Badge variant="outline" className="gap-1 pr-1 text-[10px] font-normal">
      {label}
      <button
        type="button"
        className="rounded p-0.5 hover:bg-muted"
        onClick={onClear}
        aria-label={`Clear ${label}`}
      >
        <X className="h-3 w-3" />
      </button>
    </Badge>
  );
}
