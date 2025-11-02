/**
 * Componente de gráfico de barras horizontal para ranking
 */
"use client";

import { Card } from "@/shared/ui/card";
import dynamic from "next/dynamic";

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

type RankingChartProps = {
  data: DataPoint[];
  title: string;
  dataKey?: string;
  nameKey?: string;
  height?: number;
};

export default function RankingChart({
  data,
  title,
  dataKey = "value",
  nameKey = "name",
  height = 400,
}: RankingChartProps) {
  const hasData = data && data.length > 0;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-6">{title}</h3>
      {hasData ? (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data} layout="vertical" margin={{ left: 100, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" />
            <YAxis type="category" dataKey={nameKey} width={90} />
            <Tooltip
              formatter={(value) => {
                const numValue = typeof value === "number" ? value : Number(value);
                return numValue.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
              }}
            />
            <Bar dataKey={dataKey} fill="hsl(var(--chart-1))" radius={[0, 4, 4, 0]} />
          </BarChart>
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
