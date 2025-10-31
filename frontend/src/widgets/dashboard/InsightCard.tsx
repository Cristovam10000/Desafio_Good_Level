import { Card } from "@/shared/ui/card";
import { cn } from "@/shared/lib/utils";
import { AlertTriangle, CheckCircle2, Info, TrendingUp } from "lucide-react";

const ICONS = {
  success: CheckCircle2,
  warning: AlertTriangle,
  info: Info,
  trend: TrendingUp,
} as const;

const COLOR_MAP: Record<keyof typeof ICONS, string> = {
  success: "text-emerald-600",
  warning: "text-amber-600",
  info: "text-sky-600",
  trend: "text-primary",
};

type InsightType = keyof typeof ICONS;

type InsightCardProps = {
  type: InsightType;
  title: string;
  description: string;
};

export function InsightCard({ type, title, description }: InsightCardProps) {
  const Icon = ICONS[type] ?? ICONS.info;
  return (
    <Card className="p-4 flex items-start gap-3 border-border/60">
      <div className={cn("rounded-full bg-muted p-2", COLOR_MAP[type])}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <h4 className="text-sm font-semibold">{title}</h4>
        <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </Card>
  );
}
