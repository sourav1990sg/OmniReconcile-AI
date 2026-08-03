import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Discrepancy } from "@/components/reconcile/data";
import type { AnalyticsReport } from "@/components/intelligence/analytics-types";
import type { BusinessIntelligenceReport } from "@/components/intelligence/bi-types";
import {
  BI_FILTER_STORAGE_KEY,
  BI_UI_STORAGE_KEY,
  DEFAULT_BI_FILTERS,
  DEFAULT_BI_UI,
  countActiveFilters,
  type BiFilterState,
  type BiUiState,
} from "@/components/intelligence/interactive/filter-types";
import { filterDiscrepancyRows } from "@/components/intelligence/interactive/filter-rows";
import {
  projectAnalyticsView,
  type AnalyticsViewModel,
} from "@/components/intelligence/interactive/project-analytics";

interface BiFilterContextValue {
  filters: BiFilterState;
  ui: BiUiState;
  setFilter: <K extends keyof BiFilterState>(key: K, value: BiFilterState[K]) => void;
  patchFilters: (patch: Partial<BiFilterState>) => void;
  clearFilters: () => void;
  resetAll: () => void;
  setTab: (tab: string) => void;
  setUi: (patch: Partial<BiUiState>) => void;
  /** Cross-filter: set platform from chart click */
  crossFilterPlatform: (platform: string, source?: string) => void;
  crossFilterOutlet: (outlet: string, source?: string) => void;
  crossFilterPaymentMatch: () => void;
  view: AnalyticsViewModel;
  filteredRows: Discrepancy[];
  activeFilterCount: number;
  report: AnalyticsReport;
  bi: BusinessIntelligenceReport | null;
  allRows: Discrepancy[];
}

const BiFilterContext = createContext<BiFilterContextValue | null>(null);

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return fallback;
    return { ...fallback, ...JSON.parse(raw) } as T;
  } catch {
    return fallback;
  }
}

export function BiFilterProvider({
  report,
  bi = null,
  rows,
  children,
}: {
  report: AnalyticsReport;
  bi?: BusinessIntelligenceReport | null;
  rows: Discrepancy[];
  children: ReactNode;
}) {
  const [filters, setFilters] = useState<BiFilterState>(() =>
    loadJson(BI_FILTER_STORAGE_KEY, DEFAULT_BI_FILTERS),
  );
  const [ui, setUiState] = useState<BiUiState>(() => loadJson(BI_UI_STORAGE_KEY, DEFAULT_BI_UI));

  useEffect(() => {
    try {
      sessionStorage.setItem(BI_FILTER_STORAGE_KEY, JSON.stringify(filters));
    } catch {
      /* ignore */
    }
  }, [filters]);

  useEffect(() => {
    try {
      sessionStorage.setItem(BI_UI_STORAGE_KEY, JSON.stringify(ui));
    } catch {
      /* ignore */
    }
  }, [ui]);

  const setFilter = useCallback(<K extends keyof BiFilterState>(key: K, value: BiFilterState[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value, crossFilterSource: null }));
  }, []);

  const patchFilters = useCallback((patch: Partial<BiFilterState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({ ...DEFAULT_BI_FILTERS });
  }, []);

  const resetAll = useCallback(() => {
    setFilters({ ...DEFAULT_BI_FILTERS });
    setUiState({ ...DEFAULT_BI_UI });
  }, []);

  const setTab = useCallback((tab: string) => {
    setUiState((prev) => ({ ...prev, tab }));
  }, []);

  const setUi = useCallback((patch: Partial<BiUiState>) => {
    setUiState((prev) => ({ ...prev, ...patch }));
  }, []);

  const crossFilterPlatform = useCallback((platform: string, source = "chart") => {
    setFilters((prev) => ({
      ...prev,
      platform: prev.platform === platform ? "All" : platform,
      crossFilterSource: source,
    }));
  }, []);

  const crossFilterOutlet = useCallback((outlet: string, source = "chart") => {
    setFilters((prev) => ({
      ...prev,
      outlet: prev.outlet === outlet ? "All" : outlet,
      crossFilterSource: source,
    }));
  }, []);

  const crossFilterPaymentMatch = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      paymentStatus: prev.paymentStatus === "Payment Match" ? "All" : "Payment Match",
      crossFilterSource: "kpi",
    }));
  }, []);

  const view = useMemo(() => projectAnalyticsView(report, filters), [report, filters]);

  const filteredRows = useMemo(
    () => filterDiscrepancyRows(rows, filters),
    [rows, filters],
  );

  const activeFilterCount = useMemo(() => countActiveFilters(filters), [filters]);

  const value = useMemo(
    () => ({
      filters,
      ui,
      setFilter,
      patchFilters,
      clearFilters,
      resetAll,
      setTab,
      setUi,
      crossFilterPlatform,
      crossFilterOutlet,
      crossFilterPaymentMatch,
      view,
      filteredRows,
      activeFilterCount,
      report,
      bi,
      allRows: rows,
    }),
    [
      filters,
      ui,
      setFilter,
      patchFilters,
      clearFilters,
      resetAll,
      setTab,
      setUi,
      crossFilterPlatform,
      crossFilterOutlet,
      crossFilterPaymentMatch,
      view,
      filteredRows,
      activeFilterCount,
      report,
      bi,
      rows,
    ],
  );

  return <BiFilterContext.Provider value={value}>{children}</BiFilterContext.Provider>;
}

export function useBiFilter(): BiFilterContextValue {
  const ctx = useContext(BiFilterContext);
  if (!ctx) {
    throw new Error("useBiFilter must be used within BiFilterProvider");
  }
  return ctx;
}

/** Optional hook when provider may be absent. */
export function useBiFilterOptional(): BiFilterContextValue | null {
  return useContext(BiFilterContext);
}
