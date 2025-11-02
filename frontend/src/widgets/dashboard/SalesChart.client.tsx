"use client";

import { Card } from "@/shared/ui/card";
import dynamic from "next/dynamic";

const AreaChart = dynamic(() => import("recharts").then((m) => m.AreaChart), { ssr: false });
const Area = dynamic(() => import("recharts").then((m) => m.Area), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

type Point = { name: string; current: number; previous?: number | null };
type PointByStore = { name: string; [key: string]: number | string };

type SalesChartProps = {
  data?: Point[];
  dataByStore?: PointByStore[];
  storeNames?: { id: number; name: string }[];
  title: string;
  showComparison?: boolean;
};

const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

export default function SalesChart({ data, dataByStore, storeNames, title, showComparison = false }: SalesChartProps) {
  const hasData = (data && data.length > 0) || (dataByStore && dataByStore.length > 0);
  
  // Modo: múltiplas lojas
  if (dataByStore && dataByStore.length > 0 && storeNames && storeNames.length > 0) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">{title}</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={dataByStore}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            {storeNames.map((store, index) => (
              <Area
                key={store.id}
                type="monotone"
                dataKey={`store_${store.id}`}
                name={store.name}
                stroke={CHART_COLORS[index % CHART_COLORS.length]}
                fill={`${CHART_COLORS[index % CHART_COLORS.length]} / 0.25`}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    );
  }
  
  // Modo: agregado tradicional
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-6">{title}</h3>
      {hasData && data ? (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Area
              type="monotone"
              dataKey="current"
              name="Período ativo"
              stroke="hsl(var(--chart-1))"
              fill="hsl(var(--chart-1) / 0.25)"
              strokeWidth={3}
              dot={false}
            />
            {showComparison && (
              <Area
                type="monotone"
                dataKey="previous"
                name="Período anterior"
                stroke="hsl(var(--chart-2))"
                fill="hsl(var(--chart-2) / 0.2)"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-[300px] grid place-items-center text-sm text-muted-foreground border border-dashed rounded-md">
          Nenhum dado disponível para o período selecionado.
        </div>
      )}
    </Card>
  );
}
