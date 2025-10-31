"use client";

import { Card } from "@/shared/ui/card";
import dynamic from "next/dynamic";

const AreaChart = dynamic(() => import("recharts").then((m) => m.AreaChart), { ssr: false });
const Area = dynamic(() => import("recharts").then((m) => m.Area), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

type DataPoint = {
  label: string;
  revenue: number;
  orders: number;
};

export default function ProductsByTime({ data }: { data: DataPoint[] }) {
  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">Vendas por hora</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis />
          <Tooltip />
          <Area type="monotone" dataKey="revenue" name="Receita" stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1) / 0.25)" />
          <Area type="monotone" dataKey="orders" name="Pedidos" stroke="hsl(var(--chart-2))" fill="hsl(var(--chart-2) / 0.15)" />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}
