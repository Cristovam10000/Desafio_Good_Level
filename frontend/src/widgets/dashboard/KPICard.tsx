/**
 * Componente reutilizável para KPI Cards
 */
import { Card } from "@/shared/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { ReactNode } from "react";

type KPICardProps = {
  title: string | ReactNode;
  value: string | number;
  change?: number | null;
  format?: "currency" | "number" | "percent" | "time";
  loading?: boolean;
};

export function KPICard({ title, value, change, format = "number", loading = false }: KPICardProps) {
  const formatValue = (val: string | number) => {
    if (loading) return "...";
    if (typeof val === "string") return val;
    
    switch (format) {
      case "currency":
        return val.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
      case "percent":
        return `${val.toFixed(1)}%`;
      case "time":
        return `${val.toFixed(0)}min`;
      default:
        return val.toLocaleString("pt-BR");
    }
  };

  const showTrend = change !== undefined && change !== null;
  const isPositive = change && change > 0;
  const isNegative = change && change < 0;

  return (
    <Card className="p-6">
      <p className="text-sm text-muted-foreground mb-1">{title}</p>
      <div className="flex items-end justify-between">
        <p className="text-2xl font-bold">{formatValue(value)}</p>
        {showTrend && (
          <div
            className={cn(
              "flex items-center gap-1 text-sm font-medium",
              isPositive && "text-green-600",
              isNegative && "text-red-600"
            )}
          >
            {isPositive && <TrendingUp className="w-4 h-4" />}
            {isNegative && <TrendingDown className="w-4 h-4" />}
            <span>{Math.abs(change!).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </Card>
  );
}
