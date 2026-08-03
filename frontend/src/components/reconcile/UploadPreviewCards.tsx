import { AlertTriangle, CheckCircle2, ChevronDown, XCircle } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  formatDateRange,
  previewStatusStyles,
  type CoverageReport,
  type FilePreview,
  type PreviewStatus,
  type UploadHistoryEntry,
} from "@/components/reconcile/upload-intelligence";

function StatusIcon({ status }: { status: PreviewStatus }) {
  if (status === "READY") return <CheckCircle2 className="h-4 w-4 text-success" />;
  if (status === "WARNING") return <AlertTriangle className="h-4 w-4 text-warning" />;
  return <XCircle className="h-4 w-4 text-destructive" />;
}

export function UploadPreviewCards({
  previews,
  title = "Upload intelligence",
}: {
  previews: FilePreview[];
  title?: string;
}) {
  if (!previews.length) return null;

  return (
    <section aria-label={title} className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {previews.map((p) => (
          <DetectionCard key={`${p.filename}-${p.checksum ?? p.confidence_pct}`} preview={p} />
        ))}
      </div>
    </section>
  );
}

function DetectionCard({ preview: p }: { preview: FilePreview }) {
  const [open, setOpen] = useState(p.status === "FAILED");
  const mapEntries = Object.entries(p.column_map ?? {});

  return (
    <article
      className={cn(
        "rounded-xl border p-3 text-sm transition-shadow",
        p.status === "READY" && "border-success/30 bg-success/5",
        p.status === "WARNING" && "border-warning/40 bg-warning/5",
        p.status === "FAILED" && "border-destructive/30 bg-destructive/5",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium" title={p.filename}>
            {p.filename}
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            {p.source || p.platform} · {p.confidence_pct}% confidence
          </p>
        </div>
        <Badge
          variant="outline"
          className={cn("shrink-0 gap-1 font-normal", previewStatusStyles[p.status])}
        >
          <StatusIcon status={p.status} />
          {p.status}
        </Badge>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <div>
          <dt className="text-muted-foreground">Platform</dt>
          <dd className="font-medium capitalize">{p.platform}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Rows</dt>
          <dd className="font-medium tabular-nums">{p.rows}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-muted-foreground">Date range</dt>
          <dd className="font-medium">
            {formatDateRange(p.date_range?.from, p.date_range?.to)}
          </dd>
        </div>
        <div className="col-span-2">
          <dt className="text-muted-foreground">Outlet</dt>
          <dd className="truncate font-medium" title={p.outlets.join(", ")}>
            {p.outlets.length ? p.outlets.join(", ") : "—"}
          </dd>
        </div>
        {p.dataset_role === "pos" && (
          <>
            <div>
              <dt className="text-muted-foreground">Cancelled</dt>
              <dd className="tabular-nums">{p.cancelled_orders}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Eligible</dt>
              <dd className="tabular-nums">{p.eligible_orders}</dd>
            </div>
          </>
        )}
        <div>
          <dt className="text-muted-foreground">Duplicates</dt>
          <dd className="tabular-nums">{p.duplicate_orders}</dd>
        </div>
      </dl>

      <button
        type="button"
        className="mt-2 flex w-full items-center justify-between text-[11px] font-medium text-muted-foreground"
        onClick={() => setOpen((v) => !v)}
      >
        Detection decision
        <ChevronDown className={cn("h-3.5 w-3.5 transition", open && "rotate-180")} />
      </button>
      {open ? (
        <div className="mt-2 space-y-2 rounded-lg border border-border/50 bg-background/80 p-2 text-[11px]">
          <p>
            <span className="font-semibold">Decision: </span>
            {p.status === "FAILED"
              ? "REJECTED — confidence below 95% or schema mismatch"
              : p.status === "WARNING"
                ? "ACCEPTED WITH WARNINGS"
                : "ACCEPTED"}
          </p>
          <p>
            <span className="font-semibold">Confidence: </span>
            {p.confidence_pct}% (enterprise threshold 95%)
          </p>
          <div>
            <p className="font-semibold">Matched schema</p>
            <p className="text-muted-foreground">
              {mapEntries.length
                ? mapEntries
                    .slice(0, 8)
                    .map(([col, role]) => `${col} → ${role}`)
                    .join(" · ")
                : "—"}
            </p>
          </div>
          <div>
            <p className="font-semibold">Detected columns</p>
            <p className="truncate text-muted-foreground">
              {mapEntries.length
                ? mapEntries
                    .map(([c]) => c)
                    .slice(0, 10)
                    .join(", ")
                : "See reasons below"}
            </p>
          </div>
          {(p.reasons.length > 0 || p.warnings.length > 0) && (
            <ul className="space-y-0.5 text-muted-foreground">
              {[...p.reasons, ...p.warnings].slice(0, 5).map((r) => (
                <li key={r} title={r}>
                  · {r}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </article>
  );
}

export function CoveragePanel({ coverage }: { coverage: CoverageReport | null }) {
  if (!coverage) return null;
  const pct = Math.max(0, Math.min(100, coverage.coverage_pct ?? 0));

  return (
    <section
      aria-label="Upload coverage"
      className="card-elevated rounded-xl border border-border p-4 text-sm"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Upload coverage
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{pct}%</p>
        </div>
        <div className="grid grid-cols-2 gap-4 text-[11px]">
          <div>
            <p className="text-muted-foreground">POS</p>
            <p className="font-medium">{formatDateRange(coverage.pos_from, coverage.pos_to)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Settlement</p>
            <p className="font-medium">
              {formatDateRange(coverage.settlement_from, coverage.settlement_to)}
            </p>
          </div>
        </div>
      </div>
      <Progress value={pct} className="mt-3 h-2" />
      {coverage.missing_days > 0 && (
        <p className="mt-2 text-[11px] text-warning">
          Missing {coverage.missing_from} → {coverage.missing_to} ({coverage.missing_days} day
          {coverage.missing_days === 1 ? "" : "s"})
        </p>
      )}
    </section>
  );
}

export function UploadHistoryList({ history }: { history: UploadHistoryEntry[] }) {
  if (!history.length) return null;
  return (
    <section aria-label="Upload history" className="space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Upload history
      </p>
      <ul className="max-h-36 space-y-1 overflow-y-auto text-[11px] text-muted-foreground">
        {[...history].reverse().map((h, idx) => (
          <li
            key={`${h.upload_time}-${idx}`}
            className="rounded-md border border-border/60 bg-card/40 px-2 py-1.5"
          >
            <span className="font-medium text-foreground">{h.action}</span> · {h.platform} ·{" "}
            {h.rows} rows · {h.files.length} file(s) · {h.upload_time}
            <span className="block truncate">session {h.session_id}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
