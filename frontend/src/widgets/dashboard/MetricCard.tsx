import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Card } from "@/shared/ui/card";
import { cn } from "@/shared/lib/utils";

type MetricCardProps = {
  title: string;
  value: string;
  change?: number | null;
  changeLabel?: string;
};

export function MetricCard({ title, value, change, changeLabel }: MetricCardProps) {
  const trend = typeof change === "number" ? (change > 0 ? "up" : change < 0 ? "down" : "flat") : "flat";

  return (
    <Card className="p-4 lg:p-5">
      <div className="flex flex-col gap-3">
        <span className="text-sm text-muted-foreground">{title}</span>
        <span className="text-2xl font-semibold">{value}</span>

        {change != null && (
          <div
            className={cn(
              "inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full w-max",
              trend === "up" && "text-emerald-600 bg-emerald-500/10",
              trend === "down" && "text-rose-600 bg-rose-500/10",
              trend === "flat" && "text-muted-foreground bg-muted/40"
            )}
          >
            {trend === "up" ? (
              <ArrowUpRight className="h-4 w-4" />
            ) : trend === "down" ? (
              <ArrowDownRight className="h-4 w-4" />
            ) : (
              <Minus className="h-4 w-4" />
            )}
            <span>{change.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%</span>
          </div>
        )}

        {changeLabel && <span className="text-xs text-muted-foreground">{changeLabel}</span>}
      </div>
    </Card>
  );
}
