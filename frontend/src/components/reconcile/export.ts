import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";

import type { Discrepancy } from "@/components/reconcile/data";

export type ExportRow = {
  Date: string;
  "Order ID": string;
  Platform: string;
  Outlet: string;
  "POS Sale": number;
  "Gross Order Value": number;
  "Total Deductions": number;
  "Calculated Payout": number;
  "Actual Payout": number;
  "Financial Difference": number;
  Status: string;
  Explanation: string;
};

const EXPORT_COLUMNS = [
  "Date",
  "Order ID",
  "Platform",
  "Outlet",
  "POS Sale",
  "Gross Order Value",
  "Total Deductions",
  "Calculated Payout",
  "Actual Payout",
  "Financial Difference",
  "Status",
  "Explanation",
] as const;

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/** Map discrepancy rows to the fixed export column set. */
export function toExportRows(data: Discrepancy[]): ExportRow[] {
  return data.map((row) => ({
    Date: row.date,
    "Order ID": row.orderId,
    Platform: row.platform,
    Outlet: row.location,
    "POS Sale": Number(row.posSale.toFixed(2)),
    "Gross Order Value": Number(row.grossOrderValue.toFixed(2)),
    "Total Deductions": Number(row.totalDeductions.toFixed(2)),
    "Calculated Payout": Number(row.calculatedPayout.toFixed(2)),
    "Actual Payout": Number(row.actualPayout.toFixed(2)),
    "Financial Difference": Number(row.financialDifference.toFixed(2)),
    Status: row.status,
    Explanation: row.explanation || row.remarks || "",
  }));
}

function escapeCsvCell(value: string | number): string {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function exportToCsv(data: Discrepancy[], filename = "Reconciliation_Report.csv") {
  const rows = toExportRows(data);
  const header = EXPORT_COLUMNS.join(",");
  const body = rows
    .map((row) => EXPORT_COLUMNS.map((col) => escapeCsvCell(row[col])).join(","))
    .join("\n");
  const csv = `${header}\n${body}`;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  triggerDownload(blob, filename);
}

export function exportToExcel(data: Discrepancy[], filename = "Reconciliation_Report.xlsx") {
  const rows = toExportRows(data);
  const worksheet = XLSX.utils.json_to_sheet(rows, { header: [...EXPORT_COLUMNS] });
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Discrepancies");
  XLSX.writeFile(workbook, filename);
}

export function exportToPdf(data: Discrepancy[], filename = "Reconciliation_Report.pdf") {
  const rows = toExportRows(data);
  const doc = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });

  doc.setFontSize(14);
  doc.text("OmniReconcile AI - Platform Financial Report", 40, 36);

  autoTable(doc, {
    startY: 50,
    head: [EXPORT_COLUMNS.map((col) => col)],
    body: rows.map((row) => EXPORT_COLUMNS.map((col) => row[col])),
    styles: { fontSize: 7, cellPadding: 3 },
    headStyles: { fillColor: [30, 64, 175], textColor: 255 },
    alternateRowStyles: { fillColor: [245, 247, 250] },
  });

  doc.save(filename);
}
