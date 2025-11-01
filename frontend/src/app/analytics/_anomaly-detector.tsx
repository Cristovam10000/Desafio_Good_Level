"use client";

import { Card } from "@/shared/ui/card";
import { AlertTriangle, TrendingDown, TrendingUp, Calendar, Sparkles } from "lucide-react";
import { cn } from "@/shared/lib/utils";

type AnomalyType = "queda_semanal" | "pico_promocional" | "crescimento_linear" | "sazonalidade";

const ANOMALY_CONFIG: Record<
  AnomalyType,
  {
    title: string;
    icon: React.ElementType;
    color: string;
    bgColor: string;
  }
> = {
  queda_semanal: {
    title: "Queda Semanal",
    icon: TrendingDown,
    color: "text-red-600",
    bgColor: "bg-red-50 dark:bg-red-950",
  },
  pico_promocional: {
    title: "Pico Promocional",
    icon: TrendingUp,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50 dark:bg-emerald-950",
  },
  crescimento_linear: {
    title: "Crescimento Linear",
    icon: Calendar,
    color: "text-blue-600",
    bgColor: "bg-blue-50 dark:bg-blue-950",
  },
  sazonalidade: {
    title: "Sazonalidade",
    icon: Sparkles,
    color: "text-purple-600",
    bgColor: "bg-purple-50 dark:bg-purple-950",
  },
};

type AnomalyCardProps = {
  type: AnomalyType;
  description: string;
  detected: boolean;
};

function AnomalyCard({ type, description, detected }: AnomalyCardProps) {
  const config = ANOMALY_CONFIG[type];
  const Icon = config.icon;
  const isNotDetected = description.toUpperCase().includes("NÃO DETECTADA");

  return (
    <Card
      className={cn(
        "p-4 border-l-4 transition-all",
        detected && !isNotDetected
          ? `${config.bgColor} border-l-${config.color.split("-")[1]}-500`
          : "bg-muted/30 border-l-gray-300 opacity-60"
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "p-2 rounded-lg",
            detected && !isNotDetected ? config.bgColor : "bg-muted"
          )}
        >
          <Icon className={cn("w-5 h-5", detected && !isNotDetected ? config.color : "text-muted-foreground")} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-sm mb-1">{config.title}</h4>
          <p className={cn("text-sm", isNotDetected ? "text-muted-foreground italic" : "text-foreground")}>
            {description}
          </p>
        </div>
      </div>
    </Card>
  );
}

type AnomalyDetectorProps = {
  data: {
    anomalies_found: number;
    results: {
      queda_semanal?: string;
      pico_promocional?: string;
      crescimento_linear?: string;
      sazonalidade?: string;
    };
  } | null;
  isLoading: boolean;
  isError: boolean;
};

export default function AnomalyDetector({ data, isLoading, isError }: AnomalyDetectorProps) {
  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-amber-600" />
          <h3 className="text-xl font-bold">Detector de Anomalias</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-muted/50 animate-pulse rounded-lg" />
          ))}
        </div>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-amber-600" />
          <h3 className="text-xl font-bold">Detector de Anomalias</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Não foi possível carregar a detecção de anomalias. Tente novamente mais tarde.
        </p>
      </Card>
    );
  }

  const { anomalies_found, results } = data;

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-amber-600" />
          <h3 className="text-xl font-bold">Detector de Anomalias</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Anomalias encontradas:</span>
          <span
            className={cn(
              "text-lg font-bold",
              anomalies_found > 0 ? "text-amber-600" : "text-emerald-600"
            )}
          >
            {anomalies_found}/4
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AnomalyCard
          type="queda_semanal"
          description={results.queda_semanal || "NÃO DETECTADA"}
          detected={!results.queda_semanal?.toUpperCase().includes("NÃO DETECTADA")}
        />
        <AnomalyCard
          type="pico_promocional"
          description={results.pico_promocional || "NÃO DETECTADA"}
          detected={!results.pico_promocional?.toUpperCase().includes("NÃO DETECTADA")}
        />
        <AnomalyCard
          type="crescimento_linear"
          description={results.crescimento_linear || "NÃO DETECTADA"}
          detected={!results.crescimento_linear?.toUpperCase().includes("NÃO DETECTADA")}
        />
        <AnomalyCard
          type="sazonalidade"
          description={results.sazonalidade || "NÃO DETECTADA"}
          detected={!results.sazonalidade?.toUpperCase().includes("NÃO DETECTADA")}
        />
      </div>

      {anomalies_found === 0 && (
        <div className="mt-4 p-3 bg-emerald-50 dark:bg-emerald-950 rounded-lg border border-emerald-200 dark:border-emerald-800">
          <p className="text-sm text-emerald-800 dark:text-emerald-200 text-center">
            ✓ Nenhuma anomalia crítica detectada no período analisado
          </p>
        </div>
      )}
    </Card>
  );
}
