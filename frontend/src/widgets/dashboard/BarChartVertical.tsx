/**
 * Componente de gráfico de barras vertical para ranking
 */
"use client";

import { Card } from "@/shared/ui/card";
import dynamic from "next/dynamic";
import { ReactNode } from "react";

const BarChart = dynamic(() => import("recharts").then((m) => m.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((m) => m.Bar), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

type DataPoint = {
  name: string;
  value: number;
  [key: string]: string | number;
};

type BarChartVerticalProps = {
  data: DataPoint[];
  title: string | ReactNode;
  dataKey?: string;
  nameKey?: string;
  height?: number;
  formatValue?: (value: number) => string;
};

export default function BarChartVertical({
  data,
  title,
  dataKey = "value",
  nameKey = "name",
  height = 400,
  formatValue,
}: BarChartVerticalProps) {
  const hasData = data && data.length > 0;

  const defaultFormatter = (value: number) =>
    value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const formatter = formatValue || defaultFormatter;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-6">{title}</h3>
      {hasData ? (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={nameKey}
              angle={-45}
              textAnchor="end"
              height={80}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                // Format large numbers with K, M
                if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
                return value.toString();
              }}
            />
            <Tooltip
              formatter={(value) => {
                const numValue = typeof value === "number" ? value : Number(value);
                return formatter(numValue);
              }}
            />
            <Bar dataKey={dataKey} fill="hsl(var(--chart-1))" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div
          className="grid place-items-center text-center text-sm text-muted-foreground border border-dashed rounded-md p-6"
          style={{ minHeight: height }}
        >
          <div>
            <p className="font-medium mb-2">Nenhum dado disponível</p>
            <p className="text-xs">Tente selecionar um período diferente ou ajustar os filtros</p>
          </div>
        </div>
      )}
    </Card>
  );
}
