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

type SalesChartProps = {
  data: Point[];
  title: string;
  showComparison?: boolean;
};

export default function SalesChart({ data, title, showComparison = false }: SalesChartProps) {
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-6">{title}</h3>
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
    </Card>
  );
}
