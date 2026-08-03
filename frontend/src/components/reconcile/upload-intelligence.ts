/** Sprint 5A — Upload Intelligence types & helpers */

export type PreviewStatus = "READY" | "WARNING" | "FAILED";
export type PlatformKind = "petpooja" | "swiggy" | "zomato" | "unknown";
export type DatasetRole = "pos" | "settlement" | "unknown";
export type FindingSeverity = "INFO" | "WARNING" | "ERROR";

export interface ValidationFinding {
  code: string;
  message: string;
  severity: FindingSeverity;
  filename?: string | null;
  field?: string | null;
}

export interface FilePreview {
  filename: string;
  platform: PlatformKind;
  confidence_pct: number;
  status: PreviewStatus;
  dataset_role: DatasetRole;
  rows: number;
  cancelled_orders: number;
  eligible_orders: number;
  duplicate_orders: number;
  date_range?: { from?: string | null; to?: string | null };
  outlets: string[];
  warnings: string[];
  findings: ValidationFinding[];
  reasons: string[];
  column_map?: Record<string, string>;
  checksum?: string;
  currency?: string;
  source?: string;
}

export interface CoverageReport {
  pos_from?: string | null;
  pos_to?: string | null;
  settlement_from?: string | null;
  settlement_to?: string | null;
  coverage_pct: number;
  missing_from?: string | null;
  missing_to?: string | null;
  missing_days: number;
}

export interface AnalyzeResponse {
  message?: string;
  previews: FilePreview[];
  pos_files: FilePreview[];
  settlement_files: FilePreview[];
  unknown_files: FilePreview[];
  mixed_platforms: boolean;
  can_commit_pos: boolean;
  can_commit_settlement: boolean;
  findings: ValidationFinding[];
}

export interface UploadHistoryEntry {
  upload_time: string;
  uploaded_by: string;
  session_id: string;
  action: string;
  files: string[];
  rows: number;
  platform: string;
  date_from?: string | null;
  date_to?: string | null;
  checksums: string[];
}

export const previewStatusStyles: Record<PreviewStatus, string> = {
  READY: "border-success/40 bg-success/10 text-success",
  WARNING: "border-warning/50 bg-warning/15 text-warning",
  FAILED: "border-destructive/40 bg-destructive/10 text-destructive",
};

export function formatDateRange(from?: string | null, to?: string | null): string {
  if (!from && !to) return "—";
  if (from && to) return `${from} → ${to}`;
  return from || to || "—";
}
