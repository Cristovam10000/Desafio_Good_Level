import { Card } from "@/shared/ui/card";
import { AlertCircle, CheckCircle, Info, TrendingUp, Lightbulb } from "lucide-react";
import type { SectionInsights, Improvement, AttentionPoint } from "@/shared/api/sections";

interface InsightsCardProps {
  insights: SectionInsights | null;
  isLoading: boolean;
  title?: string;
}

export function InsightsCard({ insights, isLoading, title = "Insights da IA" }: InsightsCardProps) {
  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          <h3 className="text-lg font-semibold">{title}</h3>
        </div>
        <div className="text-center text-muted-foreground py-8">
          Gerando insights com IA...
        </div>
      </Card>
    );
  }

  if (!insights) {
    return null;
  }

  if (insights.error) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          <h3 className="text-lg font-semibold">{title}</h3>
        </div>
        <div className="text-center text-muted-foreground py-4">
          <AlertCircle className="w-8 h-8 mx-auto mb-2 text-red-500" />
          <p>Erro ao gerar insights: {insights.error}</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-5 h-5 text-yellow-500" />
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>

      {/* Summary */}
      {insights.summary && (
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-sm leading-relaxed">{insights.summary}</p>
        </div>
      )}

      {/* Attention Points */}
      {insights.attention_points && insights.attention_points.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            Pontos de Atenção
          </h4>
          <div className="space-y-3">
            {insights.attention_points.map((point: AttentionPoint, idx: number) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border ${
                  point.severity === "critical"
                    ? "bg-red-50 dark:bg-red-950 border-red-300 dark:border-red-800"
                    : point.severity === "warning"
                    ? "bg-yellow-50 dark:bg-yellow-950 border-yellow-300 dark:border-yellow-800"
                    : "bg-blue-50 dark:bg-blue-950 border-blue-300 dark:border-blue-800"
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="mt-0.5">
                    {point.severity === "critical" ? (
                      <AlertCircle className="w-4 h-4 text-red-600" />
                    ) : point.severity === "warning" ? (
                      <AlertCircle className="w-4 h-4 text-yellow-600" />
                    ) : (
                      <Info className="w-4 h-4 text-blue-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium mb-1">{point.title}</p>
                    <p className="text-xs text-muted-foreground">{point.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Improvements */}
      {insights.improvements && insights.improvements.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Oportunidades de Melhoria
          </h4>
          <div className="space-y-3">
            {insights.improvements.map((improvement: Improvement, idx: number) => (
              <div
                key={idx}
                className="p-3 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <p className="text-sm font-medium flex-1">{improvement.title}</p>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      improvement.priority === "high"
                        ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                        : improvement.priority === "medium"
                        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
                        : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                    }`}
                  >
                    {improvement.priority === "high"
                      ? "Alta"
                      : improvement.priority === "medium"
                      ? "Média"
                      : "Baixa"}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mb-2">{improvement.description}</p>
                <p className="text-xs text-green-700 dark:text-green-300">
                  <strong>Impacto:</strong> {improvement.impact}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {insights.recommendations && insights.recommendations.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            Recomendações
          </h4>
          <ul className="space-y-2">
            {insights.recommendations.map((rec: string, idx: number) => (
              <li key={idx} className="text-sm flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
