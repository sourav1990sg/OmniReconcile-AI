import { useCallback, useState } from "react";
import { Download, Maximize2, Minimize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Chart chrome: fullscreen toggle + CSV export (PNG/SVG via browser print/download).
 */
export function ChartPanelChrome({
  title,
  children,
  onExportCsv,
  className,
}: {
  title: string;
  children: import("react").ReactNode;
  onExportCsv?: () => void;
  className?: string;
}) {
  const [fullscreen, setFullscreen] = useState(false);

  const toggle = useCallback(() => setFullscreen((v) => !v), []);

  return (
    <article
      className={cn(
        "rounded-xl border border-border/60 bg-card p-4",
        fullscreen && "fixed inset-4 z-50 overflow-auto shadow-2xl",
        className,
      )}
      aria-label={title}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </h3>
        <div className="flex items-center gap-1">
          {onExportCsv ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 gap-1 px-1.5 text-[10px]"
              onClick={onExportCsv}
              aria-label={`Export ${title} CSV`}
            >
              <Download className="h-3 w-3" />
              CSV
            </Button>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 gap-1 px-1.5 text-[10px]"
            onClick={toggle}
            aria-label={fullscreen ? "Exit fullscreen" : "Fullscreen chart"}
          >
            {fullscreen ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
          </Button>
        </div>
      </div>
      <div className={cn("mt-3 w-full", fullscreen ? "h-[min(70vh,640px)]" : "h-[240px]")}>
        {children}
      </div>
      {fullscreen ? (
        <p className="mt-2 text-[10px] text-muted-foreground">
          Tip: use browser Print → Save as PDF for PNG/SVG capture of the filtered view.
        </p>
      ) : null}
    </article>
  );
}
