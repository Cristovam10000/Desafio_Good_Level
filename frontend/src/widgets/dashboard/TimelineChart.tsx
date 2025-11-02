/**
 * Componente de gráfico de linha temporal para séries temporais
 */
"use client";

import { Card } from "@/shared/ui/card";
import dynamic from "next/dynamic";

import { Legend as RechartsLegend } from "recharts";

const LineChart = dynamic(() => import("recharts").then((m) => m.LineChart), { ssr: false });
const Line = dynamic(() => import("recharts").then((m) => m.Line), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

export type TimelineDataPoint = {
  date: string;
  [key: string]: string | number;
};

type SeriesConfig = {
  dataKey: string;
  name: string;
  color?: string;
};

type TimelineChartProps = {
  data: TimelineDataPoint[];
  title: string;
  series: SeriesConfig[];
  height?: number;
  xAxisKey?: string;
  formatYAxis?: (value: number) => string;
};

export default function TimelineChart({
  data,
  title,
  series,
  height = 350,
  xAxisKey = "date",
  formatYAxis,
}: TimelineChartProps) {
  const hasData = data && data.length > 0;

  const defaultFormatter = (value: number) =>
    value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-6">{title}</h3>
      {hasData ? (
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={xAxisKey}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                // Format date if it looks like a date string
                if (typeof value === "string" && value.includes("-")) {
                  const date = new Date(value);
                  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
                }
                return value;
              }}
            />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={formatYAxis} />
            <Tooltip
              formatter={(value) => {
                const numValue = typeof value === "number" ? value : Number(value);
                return formatYAxis ? formatYAxis(numValue) : defaultFormatter(numValue);
              }}
            />
            <RechartsLegend />
            {series.map((s, index) => (
              <Line
                key={s.dataKey}
                type="monotone"
                dataKey={s.dataKey}
                name={s.name}
                stroke={s.color || CHART_COLORS[index % CHART_COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div
          className="grid place-items-center text-sm text-muted-foreground border border-dashed rounded-md"
          style={{ height }}
        >
          Nenhum dado disponível
        </div>
      )}
    </Card>
  );
}
