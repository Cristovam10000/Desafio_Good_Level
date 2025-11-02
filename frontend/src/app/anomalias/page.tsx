"use client";

import { Navbar } from "@/widgets/layout/Navbar";
import { useState, useMemo, useCallback } from "react";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { IsoRange } from "@/shared/lib/date";
import { useQuery } from "@tanstack/react-query";
import { fetchAnomalies } from "@/shared/api/sections";
import { fetchDataRange } from "@/shared/api/specials";
import type { KnownAnomaly, OtherAnomaly, Pattern } from "@/shared/api/sections";
import { Card } from "@/shared/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Input } from "@/shared/ui/input";
import { Calendar, AlertTriangle, TrendingDown, TrendingUp, Sparkles, Activity, Lightbulb } from "lucide-react";

export type PeriodOption = "30days" | "60days" | "90days" | "180days" | "full" | "custom";

function rangeForPreset(preset: PeriodOption, datasetEnd?: string): IsoRange {
  // Usa a data final do dataset ou a data atual
  const referenceDate = datasetEnd ? new Date(datasetEnd) : new Date();
  const end = new Date(referenceDate);
  const start = new Date(referenceDate);
  
  switch (preset) {
    case "30days":
      start.setDate(end.getDate() - 30);
      start.setHours(0, 0, 0, 0);
      break;
    case "60days":
      start.setDate(end.getDate() - 60);
      start.setHours(0, 0, 0, 0);
      break;
    case "90days":
      start.setDate(end.getDate() - 90);
      start.setHours(0, 0, 0, 0);
      break;
    case "180days":
      start.setDate(end.getDate() - 180);
      start.setHours(0, 0, 0, 0);
      break;
    case "full":
    case "custom":
      break;
  }
  
  return {
    start: start.toISOString(),
    end: end.toISOString(),
  };
}

export default function AnomaliesPage() {
  const { isAuthenticated, isReady } = useRequireAuth();
  const [period, setPeriod] = useState<PeriodOption>("full");
  const [customRange, setCustomRange] = useState<IsoRange>(() => rangeForPreset("full"));

  // Buscar o período completo do dataset
  const dataRangeQuery = useQuery({
    queryKey: ["specials", "data-range"],
    queryFn: fetchDataRange,
    staleTime: Infinity,
    enabled: isAuthenticated,
  });

  const displayRange = useMemo<IsoRange>(() => {
    if (period === "full" && dataRangeQuery.data) {
      return {
        start: dataRangeQuery.data.start_date,
        end: dataRangeQuery.data.end_date,
      };
    }
    if (period === "custom") return customRange;
    return rangeForPreset(period, dataRangeQuery.data?.end_date);
  }, [customRange, period, dataRangeQuery.data]);

  const handlePeriodChange = useCallback((value: PeriodOption) => {
    setPeriod(value);
    if (value === "full" && dataRangeQuery.data) {
      setCustomRange({
        start: dataRangeQuery.data.start_date,
        end: dataRangeQuery.data.end_date,
      });
    } else if (value !== "custom") {
      setCustomRange(rangeForPreset(value, dataRangeQuery.data?.end_date));
    }
  }, [dataRangeQuery.data]);

  const handleCustomRangeChange = useCallback((range: IsoRange) => {
    setCustomRange(range);
    setPeriod("custom");
  }, []);

  // Fetch anomalies
  const anomaliesQuery = useQuery({
    queryKey: ["anomalies", displayRange],
    queryFn: () =>
      fetchAnomalies({
        start: displayRange.start,
        end: displayRange.end,
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  if (!isReady) {
    return (
      <div className="min-h-screen grid place-items-center text-muted-foreground">
        Carregando...
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const data = anomaliesQuery.data;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
            <Activity className="w-8 h-8" />
            Detecção de Anomalias
          </h1>
          <p className="text-muted-foreground">
            Identificação automática de padrões anômalos e insights nos dados de negócio usando IA
          </p>
        </div>

        <Card className="p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <Select value={period} onValueChange={(v) => handlePeriodChange(v as PeriodOption)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">Período Completo</SelectItem>
                  <SelectItem value="30days">Últimos 30 dias</SelectItem>
                  <SelectItem value="60days">Últimos 60 dias</SelectItem>
                  <SelectItem value="90days">Últimos 90 dias</SelectItem>
                  <SelectItem value="180days">Últimos 180 dias</SelectItem>
                  <SelectItem value="custom">Personalizado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {period === "custom" && (
              <div className="flex items-center gap-2">
                <Input
                  type="date"
                  value={customRange.start.split("T")[0]}
                  onChange={(e) => {
                    const dateValue = e.target.value;
                    const isoString = new Date(dateValue + "T00:00:00.000Z").toISOString();
                    handleCustomRangeChange({ ...customRange, start: isoString });
                  }}
                  className="w-[150px]"
                />
                <span className="text-muted-foreground">até</span>
                <Input
                  type="date"
                  value={customRange.end.split("T")[0]}
                  onChange={(e) => {
                    const dateValue = e.target.value;
                    const isoString = new Date(dateValue + "T23:59:59.999Z").toISOString();
                    handleCustomRangeChange({ ...customRange, end: isoString });
                  }}
                  className="w-[150px]"
                />
              </div>
            )}
          </div>
        </Card>

        {anomaliesQuery.isLoading ? (
          <Card className="p-12">
            <div className="text-center">
              <Activity className="w-12 h-12 mx-auto mb-4 text-muted-foreground animate-pulse" />
              <p className="text-lg font-medium">Analisando dados com IA...</p>
              <p className="text-sm text-muted-foreground mt-2">
                Isso pode levar alguns segundos
              </p>
            </div>
          </Card>
        ) : anomaliesQuery.error ? (
          <Card className="p-6">
            <div className="text-center text-red-600">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
              <p>Erro ao detectar anomalias</p>
            </div>
          </Card>
        ) : data ? (
          <div className="space-y-6">
            {/* Summary */}
            {data.summary && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-purple-500" />
                  Resumo Executivo
                </h2>
                <p className="text-sm leading-relaxed">{data.summary}</p>
              </Card>
            )}

            {/* Known Anomalies */}
            {data.known_anomalies && data.known_anomalies.length > 0 && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  Anomalias Conhecidas (Injetadas para Teste)
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {data.known_anomalies.map((anomaly: KnownAnomaly, idx: number) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-lg border-2 ${
                        anomaly.detected
                          ? "bg-red-50 dark:bg-red-950 border-red-300 dark:border-red-800"
                          : "bg-gray-50 dark:bg-gray-900 border-gray-300 dark:border-gray-700"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold flex items-center gap-2">
                          {anomaly.type === "sales_drop" && <TrendingDown className="w-4 h-4 text-red-600" />}
                          {anomaly.type === "promotional_spike" && <TrendingUp className="w-4 h-4 text-green-600" />}
                          {anomaly.type === "store_growth" && <TrendingUp className="w-4 h-4 text-blue-600" />}
                          {anomaly.type === "seasonal_product" && <Activity className="w-4 h-4 text-purple-600" />}
                          {anomaly.title}
                        </h3>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-xs px-2 py-1 rounded-full font-medium ${
                              anomaly.detected
                                ? "bg-red-200 text-red-800 dark:bg-red-900 dark:text-red-200"
                                : "bg-gray-200 text-gray-800 dark:bg-gray-800 dark:text-gray-200"
                            }`}
                          >
                            {anomaly.detected ? "✓ Detectada" : "✗ Não detectada"}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{anomaly.description}</p>
                      
                      {anomaly.detected && (
                        <>
                          <div className="mb-2">
                            <span className="text-xs font-medium">Confiança: </span>
                            <span className="text-xs">{(anomaly.confidence * 100).toFixed(0)}%</span>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-1">
                              <div
                                className="bg-blue-600 h-2 rounded-full"
                                style={{ width: `${anomaly.confidence * 100}%` }}
                              />
                            </div>
                          </div>

                          {anomaly.data_points && anomaly.data_points.length > 0 && (
                            <div className="mb-3">
                              <p className="text-xs font-medium mb-1">Evidências:</p>
                              <ul className="text-xs text-muted-foreground space-y-1">
                                {anomaly.data_points.map((point: string, i: number) => (
                                  <li key={i}>• {point}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <div className="pt-3 border-t">
                            <p className="text-xs">
                              <strong>Recomendação:</strong> {anomaly.recommendation}
                            </p>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Other Anomalies */}
            {data.other_anomalies && data.other_anomalies.length > 0 && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-yellow-500" />
                  Outras Anomalias Detectadas
                </h2>
                <div className="space-y-3">
                  {data.other_anomalies.map((anomaly: OtherAnomaly, idx: number) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-lg border ${
                        anomaly.severity === "critical"
                          ? "bg-red-50 dark:bg-red-950 border-red-300 dark:border-red-800"
                          : anomaly.severity === "warning"
                          ? "bg-yellow-50 dark:bg-yellow-950 border-yellow-300 dark:border-yellow-800"
                          : "bg-blue-50 dark:bg-blue-950 border-blue-300 dark:border-blue-800"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">{anomaly.title}</h3>
                          <p className="text-sm text-muted-foreground mb-2">{anomaly.description}</p>
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded-full ml-2 ${
                            anomaly.severity === "critical"
                              ? "bg-red-200 text-red-800"
                              : anomaly.severity === "warning"
                              ? "bg-yellow-200 text-yellow-800"
                              : "bg-blue-200 text-blue-800"
                          }`}
                        >
                          {anomaly.severity === "critical" ? "Crítico" : anomaly.severity === "warning" ? "Atenção" : "Info"}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-xs mb-3">
                        <div>
                          <span className="font-medium">Tipo:</span> {anomaly.type}
                        </div>
                        <div>
                          <span className="font-medium">Confiança:</span> {(anomaly.confidence * 100).toFixed(0)}%
                        </div>
                      </div>

                      {anomaly.affected_areas && anomaly.affected_areas.length > 0 && (
                        <div className="mb-2">
                          <span className="text-xs font-medium">Áreas afetadas: </span>
                          <span className="text-xs text-muted-foreground">
                            {anomaly.affected_areas.join(", ")}
                          </span>
                        </div>
                      )}

                      <div className="pt-3 border-t">
                        <p className="text-xs">
                          <strong>Recomendação:</strong> {anomaly.recommendation}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Patterns */}
            {data.patterns && data.patterns.length > 0 && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-green-500" />
                  Padrões Identificados
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {data.patterns.map((pattern: Pattern, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800"
                    >
                      <h3 className="font-semibold text-sm mb-2">{pattern.type}</h3>
                      <p className="text-xs text-muted-foreground mb-2">{pattern.description}</p>
                      <div className="flex items-center gap-4 text-xs">
                        <span>
                          <strong>Frequência:</strong>{" "}
                          {pattern.frequency === "daily" ? "Diária" : 
                           pattern.frequency === "weekly" ? "Semanal" : 
                           pattern.frequency === "monthly" ? "Mensal" : "Sazonal"}
                        </span>
                        <span>
                          <strong>Força:</strong>{" "}
                          {pattern.strength === "strong" ? "Forte" : 
                           pattern.strength === "moderate" ? "Moderada" : "Fraca"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* General Insights */}
            {data.insights && data.insights.length > 0 && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-yellow-500" />
                  Insights Gerais
                </h2>
                <ul className="space-y-2">
                  {data.insights.map((insight: string, idx: number) => (
                    <li key={idx} className="text-sm flex items-start gap-2">
                      <span className="text-blue-600 mt-1">•</span>
                      <span>{insight}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>
        ) : null}
      </main>
    </div>
  );
}
