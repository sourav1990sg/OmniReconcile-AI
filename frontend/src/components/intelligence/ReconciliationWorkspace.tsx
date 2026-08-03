import { Fragment, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Discrepancy } from "@/components/reconcile/data";
import { inr } from "@/components/reconcile/data";
import { cn } from "@/lib/utils";

/**
 * Reconciliation workspace — filtered rows from BiFilterContext.
 * Local column status filter + sort; sticky header; expand detail.
 */
export function ReconciliationWorkspace({
  rows,
  statusStyles,
}: {
  rows: Discrepancy[];
  statusStyles: Record<string, string>;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [statusCol, setStatusCol] = useState("All");
  const [sortKey, setSortKey] = useState<"date" | "diff" | "orderId">("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [localSearch, setLocalSearch] = useState("");

  const visible = useMemo(() => {
    let list = rows;
    if (statusCol !== "All") {
      list = list.filter(
        (r) => (r.financialStatus || r.status || "").toUpperCase() === statusCol.toUpperCase(),
      );
    }
    if (localSearch.trim()) {
      const q = localSearch.trim().toLowerCase();
      list = list.filter(
        (r) =>
          r.orderId.toLowerCase().includes(q) ||
          r.location.toLowerCase().includes(q) ||
          r.platform.toLowerCase().includes(q),
      );
    }
    const dir = sortDir === "asc" ? 1 : -1;
    return [...list].sort((a, b) => {
      if (sortKey === "diff") return (a.financialDifference - b.financialDifference) * dir;
      if (sortKey === "orderId") return a.orderId.localeCompare(b.orderId) * dir;
      return String(a.date).localeCompare(String(b.date)) * dir;
    });
  }, [rows, statusCol, localSearch, sortKey, sortDir]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  // Virtualization-lite: render window for very large sets
  const WINDOW = 500;
  const windowed = visible.length > WINDOW ? visible.slice(0, WINDOW) : visible;

  return (
    <div className="space-y-3">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Reconciliation Workspace</h2>
          <p className="text-sm text-muted-foreground">
            {visible.length.toLocaleString("en-IN")} filtered orders
            {visible.length > WINDOW
              ? ` · showing first ${WINDOW.toLocaleString("en-IN")} (refine filters)`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Input
            className="h-8 w-[180px] text-xs"
            placeholder="Quick search"
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            aria-label="Quick search reconciliation"
          />
          <Select value={statusCol} onValueChange={setStatusCol}>
            <SelectTrigger className="h-8 w-[180px] text-xs">
              <SelectValue placeholder="Status column" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All statuses</SelectItem>
              <SelectItem value="FINANCIALLY_RECONCILED">Financially reconciled</SelectItem>
              <SelectItem value="FINANCIAL_DISCREPANCY">Financial discrepancy</SelectItem>
              <SelectItem value="PENDING">Pending</SelectItem>
              <SelectItem value="CANCELLED">Cancelled</SelectItem>
              <SelectItem value="NOT_RECONCILED">Not reconciled</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </header>

      <div className="max-h-[70vh] overflow-auto rounded-xl border border-border/60">
        <Table className="text-xs">
          <TableHeader className="sticky top-0 z-10 bg-card shadow-sm">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-8" />
              <TableHead>
                <button type="button" className="font-semibold" onClick={() => toggleSort("date")}>
                  Date
                </button>
              </TableHead>
              <TableHead>
                <button type="button" className="font-semibold" onClick={() => toggleSort("orderId")}>
                  Order ID
                </button>
              </TableHead>
              <TableHead>Outlet</TableHead>
              <TableHead>Platform</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actual Payout</TableHead>
              <TableHead className="text-right">
                <button type="button" className="font-semibold" onClick={() => toggleSort("diff")}>
                  Fin. Diff
                </button>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {windowed.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                  No orders match the current filters.
                </TableCell>
              </TableRow>
            ) : (
              windowed.map((row) => {
                const open = expanded.has(row.id);
                const bd = row.financialBreakdown ?? {};
                return (
                  <Fragment key={row.id}>
                    <TableRow className="cursor-pointer" onClick={() => toggle(row.id)}>
                      <TableCell className="pr-0">
                        {open ? (
                          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell>{row.date}</TableCell>
                      <TableCell className="font-medium">{row.orderId}</TableCell>
                      <TableCell>{row.location}</TableCell>
                      <TableCell>{row.platform}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn("text-[10px] font-normal", statusStyles[row.status])}
                        >
                          {row.financialStatus || row.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {inr(row.actualPayout)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {inr(row.financialDifference)}
                      </TableCell>
                    </TableRow>
                    {open ? (
                      <TableRow className="bg-muted/25 hover:bg-muted/25">
                        <TableCell colSpan={8} className="py-3">
                          <dl className="grid gap-2 px-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                            <Detail label="POS Sale" value={inr(row.posSale)} />
                            <Detail label="Gross Order Value" value={inr(row.grossOrderValue)} />
                            <Detail
                              label="Commission"
                              value={inr(Number(bd["commission"] ?? 0))}
                            />
                            <Detail
                              label="Payment Fee"
                              value={inr(Number(bd["payment_fee"] ?? 0))}
                            />
                            <Detail label="GST" value={inr(Number(bd["gst"] ?? 0))} />
                            <Detail label="TCS" value={inr(Number(bd["tcs"] ?? 0))} />
                            <Detail label="TDS" value={inr(Number(bd["tds"] ?? 0))} />
                            <Detail
                              label="Calculated Payout"
                              value={inr(row.calculatedPayout)}
                            />
                            <Detail label="Actual Payout" value={inr(row.actualPayout)} />
                            <Detail
                              label="Financial Difference"
                              value={inr(row.financialDifference)}
                            />
                            <Detail
                              label="Verification Level"
                              value={row.verificationLevel || "—"}
                            />
                            <Detail
                              label="Agreement Result"
                              value={row.commercialResult || "—"}
                            />
                          </dl>
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}
