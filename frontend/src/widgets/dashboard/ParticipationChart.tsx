/**
 * Componente de gráfico de pizza/rosca para participação percentual
 */
"use client";

import { Card } from "@/shared/ui/card";
import dynamic from "next/dynamic";

const PieChart = dynamic(() => import("recharts").then((m) => m.PieChart), { ssr: false });
const Pie = dynamic(() => import("recharts").then((m) => m.Pie), { ssr: false });
const Cell = dynamic(() => import("recharts").then((m) => m.Cell), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });
import { Legend as RechartsLegend } from "recharts";

const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

type ParticipationDataPoint = {
  name: string;
  value: number;
};

type ParticipationChartProps = {
  data: ParticipationDataPoint[];
  title: string;
  height?: number;
  innerRadius?: number; // 0 for pie, >0 for donut
};

export default function ParticipationChart({
  data,
  title,
  height = 350,
  innerRadius = 60,
}: ParticipationChartProps) {
  const hasData = data && data.length > 0;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-6">{title}</h3>
      {hasData ? (
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={innerRadius}
              outerRadius={120}
              paddingAngle={2}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              label={(props: any) => {
                const percent = props.percent || 0;
                const name = props.name || "";
                return `${name}: ${(percent * 100).toFixed(1)}%`;
              }}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => {
                const numValue = typeof value === "number" ? value : Number(value);
                return numValue.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
              }}
            />
            <RechartsLegend />
          </PieChart>
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
