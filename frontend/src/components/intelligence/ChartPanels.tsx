import {
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartData } from "@/components/intelligence/analytics-types";
import { ChartPanelChrome } from "@/components/intelligence/ChartPanelChrome";
import { useBiFilterOptional } from "@/components/intelligence/interactive/BiFilterContext";

const COLORS = ["#0f766e", "#b45309", "#1e3a5f", "#64748b", "#0ea5e9", "#78716c"];

function Panel({
  title,
  children,
  onExport,
}: {
  title: string;
  children: import("react").ReactNode;
  onExport?: () => void;
}) {
  return (
    <ChartPanelChrome title={title} {...(onExport ? { onExportCsv: onExport } : {})}>
      {children}
    </ChartPanelChrome>
  );
}

function downloadCsv(filename: string, rows: Record<string, string | number>[]) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]!);
  const lines = [
    keys.join(","),
    ...rows.map((r) => keys.map((k) => JSON.stringify(r[k] ?? "")).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Interactive chart panels — click bars/pies to cross-filter.
 * Data must already be projected from AnalyticsReport.chart_data.
 */
export default function ChartPanels({
  chartData,
  variant,
  formatInr,
}: {
  chartData: ChartData;
  variant: "executive" | "finance" | "operations";
  formatInr: (n: number) => string;
}) {
  const bi = useBiFilterOptional();
  const revPlatform = chartData.revenue_by_platform ?? [];
  const ordPlatform = chartData.orders_by_platform ?? [];
  const revOutlet = (chartData.revenue_by_outlet ?? []).slice(0, 12);
  const ordOutlet = (chartData.orders_by_outlet ?? []).slice(0, 12);
  const commission = chartData.commission_by_platform ?? [];
  const recoverable = chartData.recoverable_by_outlet ?? [];
  const payment = chartData.payment_match;
  const share = revPlatform.map((d) => ({ name: d.platform, value: d.revenue }));

  const onPlatform = (name: string) => bi?.crossFilterPlatform(name, "chart");
  const onOutlet = (name: string) => bi?.crossFilterOutlet(name, "chart");

  if (variant === "executive") {
    return (
      <div className="grid gap-3 lg:grid-cols-2">
        <Panel
          title="Revenue by Platform · click to filter"
          onExport={() => downloadCsv("revenue_by_platform.csv", revPlatform)}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={revPlatform}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="platform" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => formatInr(v)} />
              <Legend />
              <Bar
                dataKey="revenue"
                fill={COLORS[0]}
                radius={[4, 4, 0, 0]}
                cursor="pointer"
                onClick={(d) => onPlatform(String((d as { platform?: string }).platform ?? ""))}
              />
              <Brush dataKey="platform" height={18} stroke={COLORS[2]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Orders by Platform · click to filter">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ordPlatform}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="platform" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar
                dataKey="orders"
                fill={COLORS[2]}
                radius={[4, 4, 0, 0]}
                cursor="pointer"
                onClick={(d) => onPlatform(String((d as { platform?: string }).platform ?? ""))}
              />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Revenue by Outlet · click to filter">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={revOutlet} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="outlet" width={110} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number) => formatInr(v)} />
              <Bar
                dataKey="revenue"
                fill={COLORS[1]}
                radius={[0, 4, 4, 0]}
                cursor="pointer"
                onClick={(d) => onOutlet(String((d as { outlet?: string }).outlet ?? ""))}
              />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Platform Share · click to filter">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={share}
                dataKey="value"
                nameKey="name"
                innerRadius={55}
                outerRadius={80}
                cursor="pointer"
                onClick={(_, i) => {
                  const row = share[i];
                  if (row) onPlatform(row.name);
                }}
              >
                {share.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => formatInr(v)} />
              <Legend
                onClick={(e) => {
                  const name = String((e as { value?: string }).value ?? "");
                  if (name) onPlatform(name);
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </Panel>
      </div>
    );
  }

  if (variant === "finance") {
    return (
      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="Commission by Platform · click to filter">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={commission}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="platform" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => formatInr(v)} />
              <Bar
                dataKey="commission"
                fill={COLORS[1]}
                radius={[4, 4, 0, 0]}
                cursor="pointer"
                onClick={(d) => onPlatform(String((d as { platform?: string }).platform ?? ""))}
              />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Recoverable by Outlet · click to filter">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={recoverable.length ? recoverable : [{ outlet: "None", recoverable: 0 }]}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="outlet" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => formatInr(v)} />
              <Bar
                dataKey="recoverable"
                fill={COLORS[3]}
                radius={[4, 4, 0, 0]}
                cursor="pointer"
                onClick={(d) => onOutlet(String((d as { outlet?: string }).outlet ?? ""))}
              />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Settlement / Payment Match">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={[
                  { name: "Matched", value: payment?.payment_match_orders ?? 0 },
                  {
                    name: "Other",
                    value: Math.max(
                      (payment?.matched_orders ?? 0) - (payment?.payment_match_orders ?? 0),
                      0,
                    ),
                  },
                ]}
                dataKey="value"
                nameKey="name"
                innerRadius={50}
                outerRadius={80}
                cursor="pointer"
                onClick={(_, i) => {
                  if (i === 0) bi?.crossFilterPaymentMatch();
                }}
              >
                <Cell fill={COLORS[0]} />
                <Cell fill={COLORS[3]} />
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Orders by Outlet">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={ordOutlet}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="outlet" hide />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="orders" stroke={COLORS[2]} strokeWidth={2} />
              <Brush dataKey="outlet" height={18} stroke={COLORS[2]} />
            </LineChart>
          </ResponsiveContainer>
        </Panel>
      </div>
    );
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Panel title="Orders by Outlet · click to filter">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={ordOutlet}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="outlet" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar
              dataKey="orders"
              fill={COLORS[2]}
              radius={[4, 4, 0, 0]}
              cursor="pointer"
              onClick={(d) => onOutlet(String((d as { outlet?: string }).outlet ?? ""))}
            />
          </BarChart>
        </ResponsiveContainer>
      </Panel>
      <Panel title="Swiggy vs Zomato · click to filter">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={(chartData.orders_by_platform ?? []).map((d) => ({
                name: d.platform,
                orders: d.orders,
              }))}
              dataKey="orders"
              nameKey="name"
              outerRadius={80}
              cursor="pointer"
              onClick={(_, i) => {
                const row = (chartData.orders_by_platform ?? [])[i];
                if (row) onPlatform(row.platform);
              }}
            >
              {(chartData.orders_by_platform ?? []).map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </Panel>
      <Panel title="Outlet Performance (Revenue)">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={revOutlet}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="outlet" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number) => formatInr(v)} />
            <Bar
              dataKey="revenue"
              fill={COLORS[0]}
              radius={[4, 4, 0, 0]}
              cursor="pointer"
              onClick={(d) => onOutlet(String((d as { outlet?: string }).outlet ?? ""))}
            />
          </BarChart>
        </ResponsiveContainer>
      </Panel>
      <Panel title="Order Distribution">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={ordOutlet} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="outlet" width={110} tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar
              dataKey="orders"
              fill={COLORS[4]}
              radius={[0, 4, 4, 0]}
              cursor="pointer"
              onClick={(d) => onOutlet(String((d as { outlet?: string }).outlet ?? ""))}
            />
          </BarChart>
        </ResponsiveContainer>
      </Panel>
    </div>
  );
}
