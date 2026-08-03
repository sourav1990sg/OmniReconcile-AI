import { createFileRoute } from "@tanstack/react-router";
import { Fragment, useCallback, useMemo, useRef, useState } from "react";
import { format } from "date-fns";
import type { DateRange } from "react-day-picker";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CalendarIcon,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Copy,
  FileDown,
  FileSpreadsheet,
  FileText,
  Loader2,
  Receipt,
  RotateCw,
  Send,
  Sparkles,
  TrendingUp,
  UploadCloud,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Toaster } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";
import {
  exportToCsv,
  exportToExcel,
  exportToPdf,
} from "@/components/reconcile/export";
import { IntelligenceShell } from "@/components/intelligence";
import type {
  AnalyticsReport,
  AgreementSummaryView,
  BusinessIntelligenceReport,
} from "@/components/intelligence";
import {
  buildMetricCards,
  inr,
  locations,
  mapReconcileRow,
  recoverableShortfall,
  toDisputePayload,
  type DashboardSummary,
  type DatasetSummary,
  type Discrepancy,
  type ReconcileApiRow,
  type Status,
} from "@/components/reconcile/data";
import {
  CoveragePanel,
  UploadHistoryList,
  UploadPreviewCards,
} from "@/components/reconcile/UploadPreviewCards";
import type {
  AnalyzeResponse,
  CoverageReport,
  FilePreview,
  UploadHistoryEntry,
} from "@/components/reconcile/upload-intelligence";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "OmniReconcile AI — Restaurant Financial Intelligence" },
      {
        name: "description",
        content:
          "High-density reconciliation console for multi-location sweet shops: match Swiggy and Zomato settlements to POS records and auto-draft disputes.",
      },
      { property: "og:title", content: "OmniReconcile AI — Payout Reconciliation Console" },
      {
        property: "og:description",
        content:
          "Filter by outlet, platform and date range, spot settlement shortfalls and recover lost revenue with AI dispute drafts.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

// Same-origin paths — Vite proxies /api → http://127.0.0.1:8000 (see vite.config.ts).
const RECONCILE_URL = "/api/reconcile";
const UPLOAD_POS_URL = "/api/upload/pos";
const UPLOAD_POS_REPLACE_URL = "/api/upload/pos/replace";
const UPLOAD_SETTLEMENT_URL = "/api/upload/settlement";
const UPLOAD_ANALYZE_URL = "/api/upload/analyze";
const RECONCILE_RUN_URL = "/api/reconcile/run";
const UPLOAD_AGREEMENT_URL = "/api/upload/agreement";
const DISPUTE_URL = "/api/generate-dispute";
const HEALTH_URL = "/api/health";

type WorkflowStep = "pos" | "settlement" | "ready" | "done";

const statusStyles: Record<Status, string> = {
  Flagged: "border-destructive/40 bg-destructive/10 text-destructive",
  Disputed: "border-warning/50 bg-warning/15 text-warning",
  "Under Review": "border-border bg-muted text-muted-foreground",
  Recovered: "border-success/40 bg-success/12 text-success",
  Matched: "border-success/40 bg-success/12 text-success",
  RECONCILED: "border-success/40 bg-success/12 text-success",
  FINANCIALLY_RECONCILED: "border-success/40 bg-success/12 text-success",
  PENDING: "border-border bg-muted text-muted-foreground",
  NOT_RECONCILED: "border-destructive/40 bg-destructive/10 text-destructive",
  AMOUNT_MISMATCH: "border-warning/50 bg-warning/15 text-warning",
  FINANCIAL_DISCREPANCY: "border-warning/50 bg-warning/15 text-warning",
  CANCELLED: "border-border bg-muted text-muted-foreground",
  DUPLICATE_SETTLEMENT: "border-destructive/40 bg-destructive/10 text-destructive",
  MANUAL_REVIEW: "border-border bg-muted text-muted-foreground",
};

type SortKey =
  | "date"
  | "orderId"
  | "platform"
  | "location"
  | "posSale"
  | "grossOrderValue"
  | "totalDeductions"
  | "expected"
  | "settled"
  | "diff"
  | "status";

/** Map analyze previews back to File objects by filename (column detection — no filename heuristics). */
function filesForPreviews(all: File[], previews: FilePreview[]): File[] {
  const byName = new Map(all.map((f) => [f.name, f]));
  const out: File[] = [];
  for (const p of previews) {
    const f = byName.get(p.filename);
    if (f) out.push(f);
  }
  return out;
}

/** Prefer FastAPI's `detail` field; never invent a CORS message. */
function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const loc = Array.isArray((item as { loc?: unknown }).loc)
            ? (item as { loc: unknown[] }).loc.join(".")
            : "";
          const msg = (item as { msg?: unknown }).msg;
          return [loc, msg].filter(Boolean).join(": ");
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    const obj = detail as { message?: string; findings?: Array<{ message?: string }> };
    if (obj.message) {
      const extra = (obj.findings ?? [])
        .map((f) => f.message)
        .filter(Boolean)
        .slice(0, 3)
        .join("; ");
      return extra ? `${obj.message}: ${extra}` : obj.message;
    }
    return JSON.stringify(detail);
  }
  return String(detail ?? "Unknown error");
}

async function readApiError(response: Response): Promise<string> {
  const rawBody = await response.text();
  console.error(`[api] HTTP ${response.status} ${response.url}\n`, rawBody);
  try {
    const errBody = JSON.parse(rawBody) as { detail?: unknown };
    if (errBody?.detail !== undefined) {
      return `HTTP ${response.status}: ${formatApiDetail(errBody.detail)}`;
    }
  } catch {
    /* not JSON */
  }
  return rawBody
    ? `HTTP ${response.status}: ${rawBody.slice(0, 500)}`
    : `HTTP ${response.status}: ${response.statusText || "Request failed"}`;
}

function apiErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

function Index() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [posFiles, setPosFiles] = useState<File[]>([]);
  const [settlementFiles, setSettlementFiles] = useState<File[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [posLocked, setPosLocked] = useState(false);
  const [workflowStep, setWorkflowStep] = useState<WorkflowStep>("pos");
  const [posSummary, setPosSummary] = useState<DatasetSummary | null>(null);
  const [settlementSummary, setSettlementSummary] = useState<DatasetSummary | null>(null);
  const [filePreviews, setFilePreviews] = useState<FilePreview[]>([]);
  const [coverage, setCoverage] = useState<CoverageReport | null>(null);
  const [uploadHistory, setUploadHistory] = useState<UploadHistoryEntry[]>([]);
  const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);
  const [pendingReplaceFiles, setPendingReplaceFiles] = useState<File[] | null>(null);
  const [replaceArmed, setReplaceArmed] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsReport | null>(null);
  const [businessIntelligence, setBusinessIntelligence] =
    useState<BusinessIntelligenceReport | null>(null);
  const [discrepancyRows, setDiscrepancyRows] = useState<Discrepancy[]>([]);
  const [reconciling, setReconciling] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [active, setActive] = useState<Discrepancy | null>(null);
  const [draft, setDraft] = useState("");
  const [location, setLocation] = useState<string>("All Locations");
  const [platform, setPlatform] = useState<string>("All");
  const [range, setRange] = useState<DateRange | undefined>(undefined);
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "date",
    dir: "desc",
  });
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [agreementSummary, setAgreementSummary] = useState<{
    count?: number;
    active?: {
      agreement_id?: string;
      version?: string;
      status?: string;
      source_filename?: string;
      unknown_terms?: number;
      rules?: Record<string, { value?: unknown; unknown?: boolean; confidence?: number }>;
    } | null;
  } | null>(null);
  const [agreementUploading, setAgreementUploading] = useState(false);
  const agreementInputRef = useRef<HTMLInputElement>(null);

  const metricCards = useMemo(() => buildMetricCards(dashboard, analytics), [dashboard, analytics]);
  /** Sprint 7B gate restored — AnalyticsReport alone mounts the shell. */
  const intelligenceReady = Boolean(analytics?.executive_summary);

  const applyIntelligencePayload = useCallback((payload: {
    analytics?: unknown;
    business_intelligence?: unknown;
  }) => {
    const analyticsOnly = (payload.analytics as AnalyticsReport | undefined) ?? null;
    const biRaw = (payload.business_intelligence as BusinessIntelligenceReport | undefined) ?? null;
    // Always prefer top-level AnalyticsReport for dashboard visibility.
    setAnalytics(analyticsOnly);
    // BI is optional enrichment — never required to show the shell.
    // Accept BI even if nested analytics is missing/incomplete.
    setBusinessIntelligence(biRaw?.executive_summary ? biRaw : null);
  }, []);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const ensureHealth = useCallback(async () => {
    try {
      const health = await fetch(HEALTH_URL, { method: "GET" });
      if (!health.ok) throw new Error(await readApiError(health));
    } catch (healthError) {
      const msg =
        healthError instanceof TypeError
          ? "Backend unreachable at /api/health (proxied to http://127.0.0.1:8000). Start uvicorn: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
          : apiErrorMessage(healthError, "Backend health check failed.");
      throw new Error(msg);
    }
  }, []);

  const uploadAgreement = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      if (!list.length) return;
      setAgreementUploading(true);
      try {
        await ensureHealth();
        const form = new FormData();
        list.forEach((f) => form.append("agreement_files", f));
        if (sessionId) form.append("session_id", sessionId);
        const res = await fetch(UPLOAD_AGREEMENT_URL, { method: "POST", body: form });
        if (!res.ok) throw new Error(await readApiError(res));
        const payload = (await res.json()) as {
          session_id?: string;
          agreement_summary?: typeof agreementSummary;
        };
        if (payload.session_id) setSessionId(payload.session_id);
        setAgreementSummary(payload.agreement_summary ?? null);
        toast.success("Commercial agreement uploaded", {
          description: "Optional — settlement verification still runs without it.",
        });
      } catch (error) {
        toast.error("Agreement upload failed", {
          description: apiErrorMessage(error, "Could not parse agreement."),
        });
      } finally {
        setAgreementUploading(false);
      }
    },
    [ensureHealth, sessionId],
  );

  const analyzeFiles = useCallback(
    async (files: File[]): Promise<AnalyzeResponse> => {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      await ensureHealth();
      const response = await fetch(UPLOAD_ANALYZE_URL, { method: "POST", body: formData });
      if (!response.ok) throw new Error(await readApiError(response));
      return (await response.json()) as AnalyzeResponse;
    },
    [ensureHealth],
  );

  const uploadPosStep = useCallback(
    async (files: File[]) => {
      const formData = new FormData();
      files.forEach((f) => formData.append("pos_files", f));
      if (sessionId) formData.append("session_id", sessionId);
      await ensureHealth();
      const response = await fetch(UPLOAD_POS_URL, { method: "POST", body: formData });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      const totalOrders = Number(payload.pos_summary?.total_orders ?? 0);
      if (!totalOrders) {
        throw new Error(
          "POS upload produced 0 orders. Files must match Petpooja columns (Aggregator Order No., My amount, …).",
        );
      }
      setSessionId(payload.session_id);
      setPosLocked(Boolean(payload.pos_locked ?? true));
      setPosFiles(files);
      setPosSummary(payload.pos_summary ?? null);
      setFilePreviews(Array.isArray(payload.previews) ? payload.previews : []);
      setCoverage(payload.coverage ?? null);
      setUploadHistory(Array.isArray(payload.upload_history) ? payload.upload_history : []);
      setWorkflowStep("settlement");
      toast.success("POS dataset locked", {
        description: `${totalOrders} orders · ${payload.pos_summary?.cancelled_orders ?? 0} cancelled`,
      });
    },
    [ensureHealth, sessionId],
  );

  const replacePosStep = useCallback(
    async (files: File[]) => {
      const formData = new FormData();
      files.forEach((f) => formData.append("pos_files", f));
      if (sessionId) formData.append("session_id", sessionId);
      formData.append("confirm", "REPLACE");
      await ensureHealth();
      const response = await fetch(UPLOAD_POS_REPLACE_URL, { method: "POST", body: formData });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      setSessionId(payload.session_id);
      setPosLocked(true);
      setPosFiles(files);
      setPosSummary(payload.pos_summary ?? null);
      setSettlementFiles([]);
      setSettlementSummary(null);
      setDashboard(null);
      setAnalytics(null);
      setBusinessIntelligence(null);
      setDiscrepancyRows([]);
      setFilePreviews(Array.isArray(payload.previews) ? payload.previews : []);
      setCoverage(payload.coverage ?? null);
      setUploadHistory(Array.isArray(payload.upload_history) ? payload.upload_history : []);
      setWorkflowStep("settlement");
      toast.success("POS dataset replaced", {
        description: `New session · ${payload.pos_summary?.total_orders ?? 0} orders`,
      });
    },
    [ensureHealth, sessionId],
  );

  const uploadSettlementStep = useCallback(
    async (files: File[]) => {
      if (!sessionId) {
        toast.error("Upload POS first");
        return;
      }
      const formData = new FormData();
      files.forEach((f) => formData.append("agg_files", f));
      formData.append("session_id", sessionId);
      await ensureHealth();
      const response = await fetch(UPLOAD_SETTLEMENT_URL, { method: "POST", body: formData });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      const totalOrders = Number(payload.settlement_summary?.total_orders ?? 0);
      if (!totalOrders) {
        throw new Error(
          "Settlement upload produced 0 orders. Files must match Swiggy/Zomato settlement columns.",
        );
      }
      setSettlementFiles(files);
      setSettlementSummary(payload.settlement_summary ?? null);
      if (payload.pos_summary) setPosSummary(payload.pos_summary);
      setFilePreviews((prev) => [
        ...prev.filter((p) => p.dataset_role === "pos"),
        ...(Array.isArray(payload.previews) ? payload.previews : []),
      ]);
      setCoverage(payload.coverage ?? null);
      setUploadHistory(Array.isArray(payload.upload_history) ? payload.upload_history : []);
      setWorkflowStep("ready");
      toast.success("Settlement dataset loaded", {
        description: `${totalOrders} settlement orders · coverage ${payload.coverage?.coverage_pct ?? "—"}%`,
      });
    },
    [ensureHealth, sessionId],
  );

  const runStagedReconciliation = useCallback(async () => {
    if (!sessionId) {
      toast.error("Missing session — upload POS and settlements first");
      return;
    }
    setReconciling(true);
    try {
      await ensureHealth();
      const formData = new FormData();
      formData.append("session_id", sessionId);
      const response = await fetch(RECONCILE_RUN_URL, { method: "POST", body: formData });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      const rawRows: ReconcileApiRow[] = Array.isArray(payload?.data) ? payload.data : [];
      setDiscrepancyRows(rawRows.map(mapReconcileRow));
      setDashboard(payload.dashboard ?? null);
      applyIntelligencePayload(payload);
      if (payload.agreement_summary) setAgreementSummary(payload.agreement_summary);
      if (payload.pos_summary) setPosSummary(payload.pos_summary);
      if (payload.settlement_summary) setSettlementSummary(payload.settlement_summary);
      setWorkflowStep("done");
      toast.success("Reconciliation complete", {
        description: `${payload.dashboard?.matched_orders ?? rawRows.length} matched · recoverable ${inr(payload.dashboard?.recoverable_amount ?? 0)}`,
      });
    } catch (error) {
      toast.error("Reconciliation failed", {
        description: apiErrorMessage(error, "Unable to reconcile."),
      });
    } finally {
      setReconciling(false);
    }
  }, [ensureHealth, sessionId, applyIntelligencePayload]);

  /** Column-based routing via /api/upload/analyze — never filename heuristics. */
  const runReconciliation = useCallback(async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    if (!files.length) {
      toast.error("Nothing to upload");
      return;
    }

    const finish = () => {
      if (fileInputRef.current) fileInputRef.current.value = "";
    };

    setReconciling(true);
    try {
      const analysis = await analyzeFiles(files);
      setFilePreviews(analysis.previews ?? []);

      const posBatch = filesForPreviews(files, analysis.pos_files ?? []);
      const settlementBatch = filesForPreviews(files, analysis.settlement_files ?? []);
      const failedCount = (analysis.unknown_files ?? []).length;

      if (failedCount && !posBatch.length && !settlementBatch.length) {
        toast.error("Unknown files", {
          description: "No file matched Petpooja / Swiggy / Zomato columns. Nothing imported.",
        });
        return;
      }

      // POS locked — settlement only (never overwrite POS unless Replace)
      if (sessionId && posLocked && (workflowStep === "settlement" || workflowStep === "ready" || workflowStep === "done")) {
        if (posBatch.length && (replaceArmed || !settlementBatch.length)) {
          if (replaceArmed) {
            setReplaceArmed(false);
            await replacePosStep(posBatch);
            return;
          }
          setPendingReplaceFiles(posBatch);
          setReplaceDialogOpen(true);
          return;
        }
        if (!settlementBatch.length) {
          toast.error("No settlement files detected", {
            description: "Drop Swiggy/Zomato settlement files, or use Replace POS Dataset.",
          });
          return;
        }
        await uploadSettlementStep(settlementBatch);
        return;
      }

      // First POS lock
      if ((!sessionId || !posLocked) && posBatch.length && !settlementBatch.length) {
        await uploadPosStep(posBatch);
        return;
      }

      if ((!sessionId || !posLocked) && settlementBatch.length && !posBatch.length) {
        toast.error("Upload POS first", {
          description: "Petpooja columns required before settlement import.",
        });
        return;
      }

      // Both sides detected by columns
      if (posBatch.length && settlementBatch.length) {
        if (!sessionId || !posLocked) {
          setPosFiles(posBatch);
          setSettlementFiles(settlementBatch);
          const formData = new FormData();
          posBatch.forEach((file) => formData.append("pos_files", file));
          settlementBatch.forEach((file) => formData.append("agg_files", file));
          const response = await fetch(RECONCILE_URL, { method: "POST", body: formData });
          if (!response.ok) throw new Error(await readApiError(response));
          const payload = await response.json();
          const posOrders = Number(payload.pos_summary?.total_orders ?? 0);
          if (!posOrders) {
            throw new Error("Reconciliation produced 0 POS orders after column filtering.");
          }
          const rawRows: ReconcileApiRow[] = Array.isArray(payload?.data) ? payload.data : [];
          setDiscrepancyRows(rawRows.map(mapReconcileRow));
          setDashboard(payload.dashboard ?? null);
          applyIntelligencePayload(payload);
          if (payload.agreement_summary) setAgreementSummary(payload.agreement_summary);
          setPosSummary(payload.pos_summary ?? null);
          setSettlementSummary(payload.settlement_summary ?? null);
          if (payload.previews?.pos || payload.previews?.settlement) {
            setFilePreviews([
              ...(payload.previews?.pos ?? []),
              ...(payload.previews?.settlement ?? []),
            ]);
          }
          setWorkflowStep("done");
          toast.success("Reconciliation complete", {
            description: `${posOrders} POS · ${payload.dashboard?.matched_orders ?? rawRows.length} matched`,
          });
          return;
        }
        await uploadSettlementStep(settlementBatch);
        return;
      }

      toast.error("Nothing to import", {
        description: "Drop Petpooja POS and/or Swiggy/Zomato settlement files.",
      });
    } catch (error) {
      console.error("Upload intelligence error:", error);
      toast.error("Upload failed", {
        description: apiErrorMessage(error, "Unable to analyze or import files."),
      });
    } finally {
      setReconciling(false);
      finish();
    }
  }, [
    analyzeFiles,
    applyIntelligencePayload,
    posLocked,
    replaceArmed,
    replacePosStep,
    sessionId,
    uploadPosStep,
    uploadSettlementStep,
    workflowStep,
  ]);

  const openDispute = useCallback(async (row: Discrepancy) => {
    setActive(row);
    setDraft("");
    setDrafting(true);

    try {
      const response = await fetch(DISPUTE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toDisputePayload(row)),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const payload = await response.json();
      const email =
        (typeof payload?.email === "string" && payload.email) ||
        (typeof payload?.email_draft === "string" && payload.email_draft) ||
        "";

      if (!email) {
        throw new Error("API returned an empty dispute email.");
      }

      setDraft(email);
    } catch (error) {
      console.error("Network/Fetch error:", error);
      toast.error("Could not draft dispute email", {
        description: apiErrorMessage(error, "AI drafting failed."),
      });
      setActive(null);
    } finally {
      setDrafting(false);
    }
  }, []);

  const toggleSort = (key: SortKey) =>
    setSort((s) => ({ key, dir: s.key === key && s.dir === "asc" ? "desc" : "asc" }));

  const outletOptions = useMemo(() => {
    const fromData = Array.from(
      new Set(discrepancyRows.map((d) => d.location).filter((l) => l && l !== "—")),
    ).sort();
    return fromData.length ? ["All Locations", ...fromData] : locations;
  }, [discrepancyRows]);

  const rows = useMemo(() => {
    const filtered = discrepancyRows.filter((d) => {
      const locationOk = location === "All Locations" || d.location === location;
      const platformOk = platform === "All" || d.platform === platform;
      let dateOk = true;
      if (range?.from) {
        const rowDate = new Date(d.date);
        if (!Number.isNaN(rowDate.getTime())) {
          const from = range.from;
          const to = range.to ?? range.from;
          dateOk = rowDate >= from && rowDate <= to;
        }
      }
      return locationOk && platformOk && dateOk;
    });

    const dir = sort.dir === "asc" ? 1 : -1;
    const value = (d: Discrepancy) => {
      switch (sort.key) {
        case "posSale":
          return d.posSale;
        case "grossOrderValue":
          return d.grossOrderValue;
        case "totalDeductions":
          return d.totalDeductions;
        case "expected":
          return d.calculatedPayout;
        case "settled":
          return d.actualPayout;
        case "diff":
          return d.financialDifference;
        default:
          return d[sort.key];
      }
    };

    return [...filtered].sort((a, b) => {
      const av = value(a);
      const bv = value(b);
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv)) * dir;
    });
  }, [discrepancyRows, location, platform, range, sort]);

  const totals = useMemo(
    () => ({
      exposure: rows.reduce((sum, d) => sum + recoverableShortfall(d), 0),
      orders: rows.length,
    }),
    [rows],
  );

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    if (reconciling) return;
    void runReconciliation(event.dataTransfer.files);
  };

  const openFilePicker = () => {
    if (reconciling) return;
    fileInputRef.current?.click();
  };

  const copyDraft = async () => {
    try {
      await navigator.clipboard.writeText(draft);
      toast.success("Draft copied to clipboard");
    } catch {
      toast.error("Couldn't access the clipboard");
    }
  };

  const SortHead = ({
    label,
    sortKey,
    align = "left",
  }: {
    label: string;
    sortKey: SortKey;
    align?: "left" | "right";
  }) => (
    <TableHead className={cn("h-9 py-0", align === "right" && "text-right")}>
      <button
        type="button"
        onClick={() => toggleSort(sortKey)}
        className={cn(
          "inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:text-foreground",
          align === "right" && "flex-row-reverse",
        )}
      >
        {label}
        {sort.key !== sortKey ? (
          <ArrowUpDown className="h-3 w-3 opacity-40" />
        ) : sort.dir === "asc" ? (
          <ArrowUp className="h-3 w-3 text-primary" />
        ) : (
          <ArrowDown className="h-3 w-3 text-primary" />
        )}
      </button>
    </TableHead>
  );

  const commission = active ? (active.gross * active.commissionPct) / 100 : 0;
  const hasBreakdownExtras = Boolean(active && active.gross > 0);

  return (
    <div className="min-h-screen bg-background">
      <Toaster />
      <header className="sticky top-0 z-40 border-b border-border bg-card/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-2.5 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="gradient-brand grid h-8 w-8 shrink-0 place-items-center rounded-lg text-primary-foreground">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-tight">OmniReconcile AI</p>
              <p className="hidden text-[11px] text-muted-foreground sm:block">
                Restaurant financial intelligence · CEO · CFO · Ops
              </p>
            </div>
          </div>
          <Badge
            variant="outline"
            className="shrink-0 gap-1.5 border-primary/30 bg-accent px-2.5 py-1 text-[11px] font-semibold text-accent-foreground"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            Admin: Sourav
          </Badge>
        </div>
      </header>

      <div className="sticky top-[53px] z-30 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-2 px-4 py-2 sm:px-6">
          <Select value={location} onValueChange={setLocation}>
            <SelectTrigger className="h-8 w-[150px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {outletOptions.map((l) => (
                <SelectItem key={l} value={l} className="text-xs">
                  {l}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <ToggleGroup
            type="single"
            value={platform}
            onValueChange={(v) => v && setPlatform(v)}
            variant="outline"
            size="sm"
            className="h-8"
          >
            <ToggleGroupItem value="All" className="h-8 px-3 text-xs">
              All
            </ToggleGroupItem>
            <ToggleGroupItem value="Swiggy" className="h-8 px-3 text-xs">
              Swiggy
            </ToggleGroupItem>
            <ToggleGroupItem value="Zomato" className="h-8 px-3 text-xs">
              Zomato
            </ToggleGroupItem>
          </ToggleGroup>

          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 gap-2 text-xs font-normal">
                <CalendarIcon className="h-3.5 w-3.5" />
                {range?.from
                  ? range.to
                    ? `${format(range.from, "dd MMM")} – ${format(range.to, "dd MMM yyyy")}`
                    : format(range.from, "dd MMM yyyy")
                  : "Pick date range"}
                <ChevronsUpDown className="h-3 w-3 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="range"
                selected={range}
                onSelect={setRange}
                numberOfMonths={2}
                initialFocus
                className={cn("p-3 pointer-events-auto")}
              />
            </PopoverContent>
          </Popover>

          <Separator orientation="vertical" className="mx-1 hidden !h-6 lg:block" />

          <div className="hidden items-center gap-4 text-[11px] text-muted-foreground lg:flex">
            <span>
              Rows: <span className="font-semibold tabular-nums text-foreground">{rows.length}</span>
            </span>
            {intelligenceReady && analytics ? (
              <span>
                Recoverable:{" "}
                <span className="font-semibold tabular-nums text-foreground">
                  {inr(analytics.executive_summary.recoverable_amount)}
                </span>
              </span>
            ) : (
              <span>
                Exposure:{" "}
                <span className="font-semibold tabular-nums text-destructive">
                  {inr(totals.exposure)}
                </span>
              </span>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="ml-auto h-8 gap-1.5 text-xs"
            disabled={reconciling}
            onClick={openFilePicker}
          >
            {reconciling ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RotateCw className="h-3.5 w-3.5" />
            )}
            {reconciling ? "Reconciling…" : "Upload"}
          </Button>
        </div>
      </div>

      <main className="mx-auto max-w-[1600px] space-y-4 px-4 py-5 sm:px-6">
        <h1 className="sr-only">OmniReconcile AI restaurant financial intelligence</h1>

        {!intelligenceReady ? (
        <section aria-label="Financial metrics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {metricCards.map(({ label, value, caption, tone }) => (
            <div
              key={label}
              className="card-elevated rounded-xl p-4 transition-shadow duration-300 hover:shadow-lg"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="min-w-0 truncate text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {label}
                </p>
                <span
                  className={cn(
                    "grid h-7 w-7 shrink-0 place-items-center rounded-lg",
                    tone === "warning" && "bg-warning/15 text-warning",
                    tone === "success" && "bg-success/15 text-success",
                    tone === "neutral" && "bg-accent text-accent-foreground",
                  )}
                >
                  {tone === "warning" ? (
                    <AlertTriangle className="h-3.5 w-3.5" />
                  ) : tone === "success" ? (
                    <TrendingUp className="h-3.5 w-3.5" />
                  ) : (
                    <Receipt className="h-3.5 w-3.5" />
                  )}
                </span>
              </div>
              <div className="mt-2 min-w-0">
                <p
                  className={cn(
                    "text-2xl font-semibold tracking-tight tabular-nums",
                    tone === "warning" && "text-warning",
                    tone === "success" && "text-success",
                  )}
                >
                  {value}
                </p>
                <p className="mt-1 truncate text-[11px] text-muted-foreground">{caption}</p>
              </div>
            </div>
          ))}
        </section>
        ) : null}

        <section aria-label="Workflow" className="flex flex-wrap items-center gap-2 text-[11px]">
          {(
            [
              ["pos", "1. Upload POS"],
              ["settlement", "2. Upload Settlement"],
              ["ready", "3. Run Reconciliation"],
              ["done", "4. Dashboard"],
            ] as const
          ).map(([step, label]) => (
            <Badge
              key={step}
              variant={workflowStep === step || (workflowStep === "done" && step === "done") ? "default" : "secondary"}
              className="font-normal"
            >
              {label}
            </Badge>
          ))}
          {posLocked && (
            <Badge variant="outline" className="border-success/40 bg-success/10 font-normal text-success">
              POS locked
            </Badge>
          )}
          {workflowStep === "ready" && (
            <Button size="sm" className="h-7 text-xs" disabled={reconciling} onClick={() => void runStagedReconciliation()}>
              {reconciling ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : null}
              Run Reconciliation
            </Button>
          )}
          {posLocked && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={reconciling}
              onClick={() => {
                setPendingReplaceFiles(null);
                setReplaceDialogOpen(true);
              }}
            >
              Replace POS Dataset
            </Button>
          )}
        </section>

        {(posSummary || settlementSummary) && (
          <section aria-label="Dataset summaries" className="grid gap-3 sm:grid-cols-2">
            {posSummary && (
              <div className="card-elevated rounded-xl p-4 text-sm">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">POS Dataset</p>
                <p className="mt-1 font-semibold tabular-nums">
                  {posSummary.total_orders ?? 0} orders · {posSummary.cancelled_orders ?? 0} cancelled ·{" "}
                  {posSummary.eligible_orders ?? 0} eligible
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {posSummary.date_range?.from ?? "—"} → {posSummary.date_range?.to ?? "—"} · {posFiles.length} file(s)
                  {sessionId ? ` · ${sessionId.slice(0, 8)}…` : ""}
                </p>
              </div>
            )}
            {settlementSummary && (
              <div className="card-elevated rounded-xl p-4 text-sm">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Settlement Dataset</p>
                <p className="mt-1 font-semibold tabular-nums">
                  {settlementSummary.total_orders ?? 0} orders · {(settlementSummary.platforms ?? []).join(", ") || "—"}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {settlementSummary.date_range?.from ?? "—"} → {settlementSummary.date_range?.to ?? "—"} ·{" "}
                  {settlementFiles.length} file(s)
                </p>
              </div>
            )}
          </section>
        )}

        <Collapsible defaultOpen={!intelligenceReady} className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Upload intelligence & diagnostics
            </p>
            <CollapsibleTrigger asChild>
              <Button type="button" variant="ghost" size="sm" className="h-7 text-xs">
                {intelligenceReady ? "Expand / Collapse" : "Diagnostics"}
              </Button>
            </CollapsibleTrigger>
          </div>
          <CollapsibleContent className="space-y-3">
            {coverage && <CoveragePanel coverage={coverage} />}
            {filePreviews.length > 0 && <UploadPreviewCards previews={filePreviews} />}
            {uploadHistory.length > 0 && <UploadHistoryList history={uploadHistory} />}
          </CollapsibleContent>
        </Collapsible>

        <section aria-label="Commercial Agreement" className="card-elevated rounded-xl p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Commercial Agreement
              </p>
              <p className="mt-1 text-sm text-foreground">
                Optional — settlement verification works without an agreement.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                ref={agreementInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.length) void uploadAgreement(e.target.files);
                  e.target.value = "";
                }}
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-8 text-xs"
                disabled={agreementUploading}
                onClick={() => agreementInputRef.current?.click()}
              >
                {agreementUploading ? (
                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <FileText className="mr-1 h-3.5 w-3.5" />
                )}
                Upload Agreement
              </Button>
            </div>
          </div>
          {agreementSummary?.active ? (
            <div className="mt-3 space-y-2 text-xs">
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="font-normal">
                  Status: {agreementSummary.active.status ?? "Pending Review"}
                </Badge>
                <Badge variant="secondary" className="font-normal">
                  Version {agreementSummary.active.version ?? "1"}
                </Badge>
                <Badge variant="secondary" className="font-normal">
                  {agreementSummary.active.unknown_terms ?? 0} unknown terms
                </Badge>
              </div>
              <p className="text-muted-foreground">
                File: {agreementSummary.active.source_filename ?? "—"}
              </p>
              {agreementSummary.active.rules ? (
                <dl className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(agreementSummary.active.rules)
                    .slice(0, 9)
                    .map(([key, field]) => (
                      <div
                        key={key}
                        className="flex justify-between gap-2 rounded border border-border/60 bg-card px-2 py-1"
                      >
                        <dt className="truncate text-muted-foreground">{key.replace(/_/g, " ")}</dt>
                        <dd className="font-medium tabular-nums">
                          {field.unknown || field.value == null ? "UNKNOWN" : String(field.value)}
                        </dd>
                      </div>
                    ))}
                </dl>
              ) : null}
            </div>
          ) : (
            <p className="mt-3 text-[11px] text-muted-foreground">
              No agreement uploaded. Orders will show Verification Level = SETTLEMENT_VERIFIED when
              payouts reconcile.
            </p>
          )}
        </section>

        <section aria-label="Upload statements">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls,.xlsm"
            multiple
            className="hidden"
            disabled={reconciling}
            onChange={(e) => {
              if (e.target.files?.length) void runReconciliation(e.target.files);
            }}
          />
          <div
            role="button"
            tabIndex={reconciling ? -1 : 0}
            aria-disabled={reconciling}
            onDragOver={(e) => {
              e.preventDefault();
              if (!reconciling) setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={openFilePicker}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openFilePicker();
              }
            }}
            className={cn(
              "group flex cursor-pointer flex-wrap items-center gap-3 rounded-xl border border-dashed border-border bg-card px-4 py-2.5 transition-all duration-300 outline-none",
              "hover:border-primary/60 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring",
              dragging && "border-primary bg-accent/60",
              reconciling && "pointer-events-none opacity-70",
            )}
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground transition-transform duration-300 group-hover:-translate-y-0.5">
              {reconciling ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UploadCloud className="h-4 w-4" />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {reconciling
                  ? "Analyzing columns & importing..."
                  : "Drag & Drop Petpooja POS + Swiggy/Zomato settlements"}
              </p>
              <p className="truncate text-[11px] text-muted-foreground">
                {reconciling
                  ? "Column-based detection · confidence scoring · preview"
                  : posLocked
                    ? "POS locked — drop settlements, or Replace POS Dataset"
                    : "Detected by columns (not filenames) · unknown files are rejected"}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1.5 text-[11px] text-muted-foreground">
              <Badge variant="secondary" className="gap-1 px-1.5 py-0 font-normal">
                <FileSpreadsheet className="h-3 w-3" /> POS .xlsx
              </Badge>
              <Badge variant="secondary" className="gap-1 px-1.5 py-0 font-normal">
                <Receipt className="h-3 w-3" /> Agg .csv/.xlsx
              </Badge>
              <span className="hidden sm:inline">Multi-file</span>
            </div>
          </div>
        </section>

        {intelligenceReady && analytics ? (
          <IntelligenceShell
            report={analytics}
            bi={businessIntelligence}
            rows={rows}
            agreement={agreementSummary as AgreementSummaryView | null}
            statusStyles={statusStyles}
            toolbar={
              <div className="flex flex-wrap items-center gap-1.5 print:hidden">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  disabled={rows.length === 0}
                  onClick={() => {
                    try {
                      exportToCsv(rows);
                      toast.success("CSV downloaded");
                    } catch {
                      toast.error("CSV export failed");
                    }
                  }}
                >
                  <FileText className="h-3.5 w-3.5" />
                  CSV
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  disabled={rows.length === 0}
                  onClick={() => {
                    try {
                      exportToExcel(rows);
                      toast.success("Excel downloaded");
                    } catch {
                      toast.error("Excel export failed");
                    }
                  }}
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  Excel
                </Button>
                <Badge variant="secondary" className="text-[11px]">
                  {rows.length} rows
                </Badge>
              </div>
            }
          />
        ) : null}

        {!intelligenceReady ? (
        <section aria-label="Discrepancies" className="card-elevated overflow-hidden rounded-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-2.5">
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold tracking-tight">Open discrepancies</h2>
              <p className="text-[11px] text-muted-foreground">
                {location} · {platform === "All" ? "All platforms" : platform}
                {discrepancyRows.length === 0 ? " · upload files to begin" : ""}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  disabled={rows.length === 0}
                  onClick={() => {
                    try {
                      exportToCsv(rows);
                      toast.success("CSV downloaded", {
                        description: "Reconciliation_Report.csv",
                      });
                    } catch {
                      toast.error("CSV export failed");
                    }
                  }}
                >
                  <FileText className="h-3.5 w-3.5" />
                  Export CSV
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  disabled={rows.length === 0}
                  onClick={() => {
                    try {
                      exportToExcel(rows);
                      toast.success("Excel downloaded", {
                        description: "Reconciliation_Report.xlsx",
                      });
                    } catch {
                      toast.error("Excel export failed");
                    }
                  }}
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  Export Excel
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  disabled={rows.length === 0}
                  onClick={() => {
                    try {
                      exportToPdf(rows);
                      toast.success("PDF downloaded", {
                        description: "Reconciliation_Report.pdf",
                      });
                    } catch {
                      toast.error("PDF export failed");
                    }
                  }}
                >
                  <FileDown className="h-3.5 w-3.5" />
                  Export PDF
                </Button>
              </div>
              <Badge variant="secondary" className="shrink-0 text-[11px]">
                {rows.length} rows
              </Badge>
            </div>
          </div>
          <div className="overflow-x-auto">
            <Table className="text-xs">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="h-9 w-8 py-0" />
                  <SortHead label="Date" sortKey="date" />
                  <SortHead label="Order ID" sortKey="orderId" />
                  <SortHead label="Platform" sortKey="platform" />
                  <SortHead label="Outlet" sortKey="location" />
                  <SortHead label="POS Sale" sortKey="posSale" align="right" />
                  <SortHead label="GOV" sortKey="grossOrderValue" align="right" />
                  <SortHead label="Deductions" sortKey="totalDeductions" align="right" />
                  <SortHead label="Calc. Payout" sortKey="expected" align="right" />
                  <SortHead label="Actual Payout" sortKey="settled" align="right" />
                  <SortHead label="Fin. Diff" sortKey="diff" align="right" />
                  <SortHead label="Financial Status" sortKey="status" />
                  <TableHead className="h-9 py-0 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Verification
                  </TableHead>
                  <TableHead className="h-9 py-0 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Action
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={14} className="h-24 text-center text-muted-foreground">
                      {reconciling
                        ? "Reconciling data..."
                        : "No reconciled rows yet. Upload Petpooja POS Excel batches with aggregator settlement files."}
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((row) => {
                    const open = expandedIds.has(row.id);
                    const deductionEntries = Object.entries(row.deductionSummary);
                    const finDiff = row.financialDifference;
                    return (
                      <Fragment key={row.id}>
                        <TableRow className="transition-colors">
                          <TableCell className="py-1.5 pr-0">
                            <button
                              type="button"
                              aria-label={open ? "Collapse deductions" : "Expand deductions"}
                              className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                              onClick={() => toggleExpanded(row.id)}
                            >
                              {open ? (
                                <ChevronDown className="h-3.5 w-3.5" />
                              ) : (
                                <ChevronRight className="h-3.5 w-3.5" />
                              )}
                            </button>
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 text-muted-foreground">
                            {row.date}
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 font-medium">
                            {row.orderId}
                          </TableCell>
                          <TableCell className="py-1.5">
                            <Badge
                              variant="outline"
                              className={cn(
                                "px-1.5 py-0 text-[11px] font-normal",
                                row.platform === "Swiggy"
                                  ? "border-warning/40 text-warning"
                                  : "border-destructive/40 text-destructive",
                              )}
                            >
                              {row.platform}
                            </Badge>
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 text-muted-foreground">
                            {row.location}
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 text-right tabular-nums">
                            {inr(row.posSale)}
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 text-right tabular-nums">
                            {inr(row.grossOrderValue)}
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 text-right tabular-nums text-muted-foreground">
                            {inr(row.totalDeductions)}
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 text-right tabular-nums">
                            {inr(row.calculatedPayout)}
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-1.5 text-right tabular-nums">
                            {inr(row.actualPayout)}
                          </TableCell>
                          <TableCell
                            className={cn(
                              "whitespace-nowrap py-1.5 text-right font-semibold tabular-nums",
                              Math.abs(finDiff) > 0.01 ? "text-destructive" : "text-success",
                            )}
                          >
                            {finDiff < 0 ? `-${inr(finDiff)}` : inr(finDiff)}
                          </TableCell>
                          <TableCell className="py-1.5">
                            <Badge
                              variant="outline"
                              className={cn(
                                "px-1.5 py-0 text-[11px] font-medium",
                                statusStyles[row.status],
                              )}
                            >
                              {row.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="py-1.5">
                            <div className="space-y-0.5">
                              <Badge variant="secondary" className="px-1.5 py-0 text-[10px] font-normal">
                                {row.displayStatus || row.verificationLevel || "—"}
                              </Badge>
                              {row.verificationLevel ? (
                                <p className="text-[10px] text-muted-foreground">{row.verificationLevel}</p>
                              ) : null}
                            </div>
                          </TableCell>
                          <TableCell className="py-1.5 text-right">
                            <Button
                              size="sm"
                              onClick={() => void openDispute(row)}
                              disabled={drafting && active?.id === row.id}
                              className="h-7 whitespace-nowrap px-2.5 text-xs transition-transform duration-200 hover:-translate-y-0.5"
                            >
                              <Sparkles className="h-3 w-3" />
                              Generate Dispute
                            </Button>
                          </TableCell>
                        </TableRow>
                        {open ? (
                          <TableRow className="bg-muted/30 hover:bg-muted/30">
                            <TableCell colSpan={14} className="py-3">
                              <div className="space-y-2 px-2">
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                  Platform formula
                                </p>
                                <p className="text-xs text-foreground">
                                  {row.platformFormula || "—"}
                                </p>
                                <p className="text-[11px] leading-relaxed text-muted-foreground">
                                  {row.explanation || row.remarks || "No financial explanation."}
                                </p>
                                {row.commercialRemarks ? (
                                  <p className="text-[11px] leading-relaxed text-foreground">
                                    Commercial: {row.commercialRemarks}
                                    {row.agreementVersion
                                      ? ` · Agreement v${row.agreementVersion}`
                                      : ""}
                                    {row.agreementStatus ? ` · ${row.agreementStatus}` : ""}
                                  </p>
                                ) : null}
                                {deductionEntries.length > 0 ? (
                                  <dl className="grid gap-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                                    {deductionEntries.map(([key, value]) => (
                                      <div
                                        key={key}
                                        className="flex justify-between gap-2 rounded border border-border/60 bg-card px-2 py-1"
                                      >
                                        <dt className="truncate text-[11px] text-muted-foreground">
                                          {key.replace(/_/g, " ")}
                                        </dt>
                                        <dd className="text-[11px] font-medium tabular-nums">
                                          {inr(Number(value))}
                                        </dd>
                                      </div>
                                    ))}
                                  </dl>
                                ) : (
                                  <p className="text-[11px] text-muted-foreground">
                                    No component deductions detected for this row.
                                  </p>
                                )}
                              </div>
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
        </section>
        ) : null}
      </main>

      <Dialog
        open={active !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActive(null);
            setDraft("");
            setDrafting(false);
          }
        }}
      >
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-primary" />
              AI dispute draft
            </DialogTitle>
            <DialogDescription className="text-xs">
              Order <span className="font-medium text-foreground">{active?.orderId}</span> ·{" "}
              {active?.platform} · {active?.location} · financial diff{" "}
              <span className="font-medium text-destructive">
                {active ? inr(active.financialDifference) : ""}
              </span>
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_260px]">
            {drafting ? (
              <div className="space-y-3 rounded-md border border-border p-4" aria-busy="true">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  Drafting email...
                </div>
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : (
              <Textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                aria-label="AI generated support email"
                placeholder="Generated dispute email will appear here…"
                className="min-h-[340px] resize-none font-mono text-xs leading-relaxed"
              />
            )}

            <aside className="space-y-3 rounded-xl border border-border bg-muted/40 p-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Discrepancy breakdown
                </p>
                <dl className="mt-2 space-y-1.5 text-xs">
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Status</dt>
                    <dd className="font-medium">{active?.status}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">POS Sale</dt>
                    <dd className="tabular-nums">{active ? inr(active.posSale) : ""}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Gross Order Value</dt>
                    <dd className="tabular-nums">{active ? inr(active.grossOrderValue) : ""}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Total Deductions</dt>
                    <dd className="tabular-nums">{active ? inr(active.totalDeductions) : ""}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Calculated Payout</dt>
                    <dd className="font-semibold tabular-nums">
                      {active ? inr(active.calculatedPayout) : ""}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Actual Payout</dt>
                    <dd className="tabular-nums">{active ? inr(active.actualPayout) : ""}</dd>
                  </div>
                  <Separator className="my-1.5" />
                  <div className="flex justify-between gap-2">
                    <dt className="font-medium">Financial Difference</dt>
                    <dd className="font-semibold tabular-nums text-destructive">
                      {active ? inr(active.financialDifference) : ""}
                    </dd>
                  </div>
                  {active?.platformFormula ? (
                    <div className="pt-1">
                      <dt className="text-muted-foreground">Formula</dt>
                      <dd className="mt-0.5 text-[11px] leading-relaxed">{active.platformFormula}</dd>
                    </div>
                  ) : null}
                  {active?.explanation || active?.remarks ? (
                    <div className="pt-1">
                      <dt className="text-muted-foreground">Explanation</dt>
                      <dd className="mt-0.5 text-[11px] leading-relaxed">
                        {active.explanation || active.remarks}
                      </dd>
                    </div>
                  ) : null}
                  {active?.recommendation ? (
                    <div className="pt-1">
                      <dt className="text-muted-foreground">Recommendation</dt>
                      <dd className="mt-0.5 text-[11px] leading-relaxed">{active.recommendation}</dd>
                    </div>
                  ) : null}
                  {active?.sourcePos ? (
                    <div className="pt-1 text-[10px] text-muted-foreground">POS: {active.sourcePos}</div>
                  ) : null}
                  {active?.sourceSettlement ? (
                    <div className="text-[10px] text-muted-foreground">
                      Settlement: {active.sourceSettlement}
                    </div>
                  ) : null}
                </dl>
              </div>

              {active && active.confidence > 0 ? (
                <div className="rounded-lg border border-border bg-card p-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                      AI confidence score
                    </p>
                    <span className="text-sm font-semibold tabular-nums text-primary">
                      {active.confidence}%
                    </span>
                  </div>
                  <Progress value={active.confidence} className="mt-2 h-1.5" />
                </div>
              ) : (
                <div className="rounded-lg border border-border bg-card p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Source
                  </p>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                    Drafted by Gemini from this reconciliation row via{" "}
                    <span className="font-medium text-foreground">/api/generate-dispute</span>.
                  </p>
                </div>
              )}
            </aside>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={copyDraft} disabled={drafting || !draft}>
              <Copy className="h-4 w-4" />
              Copy Draft
            </Button>
            <Button
              disabled={drafting || !draft}
              onClick={() => {
                toast.success("Dispute sent to platform support", {
                  description: `${active?.orderId} moved to Pending Disputes`,
                  icon: <Check className="h-4 w-4" />,
                });
                setActive(null);
                setDraft("");
              }}
            >
              <Send className="h-4 w-4" />
              Send to Support
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={replaceDialogOpen}
        onOpenChange={(open) => {
          setReplaceDialogOpen(open);
          if (!open) setPendingReplaceFiles(null);
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Replace POS Dataset?</DialogTitle>
            <DialogDescription>
              This removes the current locked POS session{sessionId ? ` (${sessionId.slice(0, 8)}…)` : ""} and
              clears settlement data. A new session will be created. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setReplaceDialogOpen(false);
                setPendingReplaceFiles(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={reconciling}
              onClick={() => {
                setReplaceDialogOpen(false);
                if (pendingReplaceFiles?.length) {
                  setReconciling(true);
                  void replacePosStep(pendingReplaceFiles)
                    .catch((error) => {
                      toast.error("Replace failed", {
                        description: apiErrorMessage(error, "Unable to replace POS."),
                      });
                    })
                    .finally(() => {
                      setReconciling(false);
                      setPendingReplaceFiles(null);
                    });
                  return;
                }
                setReplaceArmed(true);
                toast.message("Select new Petpooja POS files", {
                  description: "Current session will be replaced after upload.",
                });
                fileInputRef.current?.click();
              }}
            >
              Confirm Replace
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
