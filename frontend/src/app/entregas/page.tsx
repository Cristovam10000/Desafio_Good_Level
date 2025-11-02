"use client";

import { Navbar } from "@/widgets/layout/Navbar";
import { Card } from "@/shared/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { Calendar, Clock, BarChart3, Lightbulb } from "lucide-react";
import { useState, useMemo, useCallback } from "react";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { IsoRange } from "@/shared/lib/date";
import { useQuery } from "@tanstack/react-query";
import { 
  fetchDeliveryPercentiles, 
  fetchChannels,
  fetchDeliveryStats,
  fetchDeliveryCitiesRank,
  fetchDeliveryStoresRank,
  fetchSectionInsights
} from "@/shared/api/sections";
import { KPICard } from "@/widgets/dashboard/KPICard";
import BarChartVertical from "@/widgets/dashboard/BarChartVertical";
import { TooltipInfo } from "@/shared/ui/tooltip-info";
import { InsightsCard } from "@/widgets/dashboard/InsightsCard";

export type PeriodOption = "7days" | "30days" | "90days" | "custom";

function rangeForPreset(preset: PeriodOption): IsoRange {
  const now = new Date();
  const end = new Date(now);
  const start = new Date(now);
  
  switch (preset) {
    case "7days":
      start.setDate(now.getDate() - 7);
      start.setHours(0, 0, 0, 0);
      break;
    case "30days":
      start.setDate(now.getDate() - 30);
      start.setHours(0, 0, 0, 0);
      break;
    case "90days":
      start.setDate(now.getDate() - 90);
      start.setHours(0, 0, 0, 0);
      break;
    case "custom":
      break;
  }
  
  return {
    start: start.toISOString(),
    end: end.toISOString(),
  };
}

export default function EntregasPage() {
  const { isAuthenticated, isReady } = useRequireAuth();
  const [period, setPeriod] = useState<PeriodOption>("30days");
  const [customRange, setCustomRange] = useState<IsoRange>(() => rangeForPreset("30days"));
  const [channelOption, setChannelOption] = useState<number | null>(null);
  const [showAllPeriod, setShowAllPeriod] = useState(false);

  const displayRange = useMemo<IsoRange>(() => {
    if (showAllPeriod) {
      // Todo o período disponível (1 ano atrás até agora)
      const now = new Date();
      const oneYearAgo = new Date(now);
      oneYearAgo.setFullYear(now.getFullYear() - 1);
      return {
        start: oneYearAgo.toISOString(),
        end: now.toISOString(),
      };
    }
    if (period === "custom") return customRange;
    return rangeForPreset(period);
  }, [customRange, period, showAllPeriod]);

  const handlePeriodChange = useCallback((value: PeriodOption) => {
    setPeriod(value);
    if (value !== "custom") {
      setCustomRange(rangeForPreset(value));
    }
  }, []);

  const handleCustomRangeChange = useCallback((range: IsoRange) => {
    setCustomRange(range);
    setPeriod("custom");
  }, []);

  // Fetch channels
  const channelsQuery = useQuery({
    queryKey: ["channels"],
    queryFn: fetchChannels,
  });

  // Fetch delivery percentiles
  const percentilesQuery = useQuery({
    queryKey: ["delivery", "percentiles", displayRange, channelOption],
    queryFn: () =>
      fetchDeliveryPercentiles({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch delivery stats
  const statsQuery = useQuery({
    queryKey: ["delivery", "stats", displayRange, channelOption],
    queryFn: () =>
      fetchDeliveryStats({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch cities ranking
  const citiesRankQuery = useQuery({
    queryKey: ["delivery", "cities-rank", displayRange, channelOption],
    queryFn: () =>
      fetchDeliveryCitiesRank({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 10,
      }),
    enabled: isAuthenticated,
  });

  // Fetch stores ranking (slowest)
  const storesSlowQuery = useQuery({
    queryKey: ["delivery", "stores-slow", displayRange, channelOption],
    queryFn: () =>
      fetchDeliveryStoresRank({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        order_by: "slowest",
        limit: 10,
      }),
    enabled: isAuthenticated,
  });

  // Fetch stores ranking (fastest)
  const storesFastQuery = useQuery({
    queryKey: ["delivery", "stores-fast", displayRange, channelOption],
    queryFn: () =>
      fetchDeliveryStoresRank({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        order_by: "fastest",
        limit: 10,
      }),
    enabled: isAuthenticated,
  });

  // Fetch AI insights for Entregas section
  const insightsQuery = useQuery({
    queryKey: ["insights", "entregas", displayRange, channelOption],
    queryFn: () =>
      fetchSectionInsights("entregas", {
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });

  // Transform data for chart (Top 10 neighborhoods by P90)
  // Removido: agora usamos citiesRankQuery diretamente

  // Transform cities data
  const citiesChartData = useMemo(() => {
    if (!citiesRankQuery.data) return [];
    return citiesRankQuery.data.map((c) => ({
      name: c.city.length > 20 ? c.city.substring(0, 20) + "..." : c.city,
      value: c.deliveries,
      avg: c.avg_minutes,
      p90: c.p90_minutes,
    }));
  }, [citiesRankQuery.data]);

  // Transform stores slow data
  const storesSlowChartData = useMemo(() => {
    if (!storesSlowQuery.data) return [];
    return storesSlowQuery.data.map((s) => ({
      name: s.store_name.length > 20 ? s.store_name.substring(0, 20) + "..." : s.store_name,
      value: s.avg_minutes,
      deliveries: s.deliveries,
      p90: s.p90_minutes,
    }));
  }, [storesSlowQuery.data]);

  // Transform stores fast data
  const storesFastChartData = useMemo(() => {
    if (!storesFastQuery.data) return [];
    return storesFastQuery.data.map((s) => ({
      name: s.store_name.length > 20 ? s.store_name.substring(0, 20) + "..." : s.store_name,
      value: s.avg_minutes,
      deliveries: s.deliveries,
      p90: s.p90_minutes,
    }));
  }, [storesFastQuery.data]);

  if (!isReady) {
    return (
      <div className="min-h-screen grid place-items-center text-muted-foreground">
        Carregando...
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Entregas</h1>
          <p className="text-muted-foreground">
            Análise de SLA, tempo médio e P90 por região
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
                  <SelectItem value="7days">Últimos 7 dias</SelectItem>
                  <SelectItem value="30days">Últimos 30 dias</SelectItem>
                  <SelectItem value="90days">Últimos 90 dias</SelectItem>
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

            <div className="flex items-center gap-2">
              <Select
                value={channelOption?.toString() || "all"}
                onValueChange={(v) => setChannelOption(v === "all" ? null : Number(v))}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Todos os canais" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os canais</SelectItem>
                  {channelsQuery.data?.map((ch) => (
                    <SelectItem key={ch.channel_id} value={ch.channel_id.toString()}>
                      {ch.channel_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              variant={showAllPeriod ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setShowAllPeriod(!showAllPeriod);
                if (!showAllPeriod) {
                  // Vai mostrar todo o período
                  percentilesQuery.refetch();
                  statsQuery.refetch();
                  citiesRankQuery.refetch();
                  storesSlowQuery.refetch();
                  storesFastQuery.refetch();
                  insightsQuery.refetch();
                }
              }}
            >
              <Clock className="w-4 h-4 mr-2" />
              {showAllPeriod ? "Período Personalizado" : "Analisar Todo Período"}
            </Button>
          </div>
        </Card>

        <Tabs defaultValue="dashboard" className="mt-6">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="dashboard" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="insights" className="flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
              Insights da IA
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <KPICard
            title="Total de Entregas"
            value={statsQuery.data?.total_deliveries || 0}
            format="number"
            loading={statsQuery.isLoading}
          />
          <KPICard
            title="Tempo Médio"
            value={percentilesQuery.data?.avg_minutes || 0}
            format="time"
            loading={percentilesQuery.isLoading}
          />
          <KPICard
            title="Entrega Mais Rápida"
            value={statsQuery.data?.fastest_minutes || 0}
            format="time"
            loading={statsQuery.isLoading}
          />
          <KPICard
            title="Entrega Mais Lenta"
            value={statsQuery.data?.slowest_minutes || 0}
            format="time"
            loading={statsQuery.isLoading}
          />
          <KPICard
            title={
              <span className="flex items-center">
                P90
                <TooltipInfo content="P90 (percentil 90) significa que 90% das entregas foram concluídas neste tempo ou menos. Apenas 10% demoraram mais. É uma métrica melhor que a média para avaliar o SLA." />
              </span>
            }
            value={percentilesQuery.data?.p90_minutes || 0}
            format="time"
            loading={percentilesQuery.isLoading}
          />
          <KPICard
            title="% Dentro do SLA"
            value={percentilesQuery.data?.within_sla_pct || 0}
            format="percent"
            loading={percentilesQuery.isLoading}
          />
        </div>

            <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
              {citiesRankQuery.isLoading ? (
                <Card className="p-6">
                  <div className="text-center text-muted-foreground">Carregando cidades...</div>
                </Card>
              ) : (
                <BarChartVertical
                  data={citiesChartData}
                  title="Top 10 Cidades com Mais Pedidos"
                  formatValue={(value) => `${value.toLocaleString('pt-BR')} pedidos`}
                  height={350}
                />
              )}

              {storesSlowQuery.isLoading ? (
                <Card className="p-6">
                  <div className="text-center text-muted-foreground">Carregando lojas...</div>
                </Card>
              ) : (
                <BarChartVertical
                  data={storesSlowChartData}
                  title="Top 10 Lojas com Maior Tempo de Entrega"
                  formatValue={(value) => `${value.toFixed(0)} min`}
                  height={350}
                />
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {storesFastQuery.isLoading ? (
                <Card className="p-6">
                  <div className="text-center text-muted-foreground">Carregando lojas...</div>
                </Card>
              ) : (
                <BarChartVertical
                  data={storesFastChartData}
                  title="Top 10 Lojas Mais Rápidas"
                  formatValue={(value) => `${value.toFixed(0)} min`}
                  height={350}
                />
              )}

              {citiesRankQuery.isLoading ? (
                <Card className="p-6">
                  <div className="text-center text-muted-foreground">Carregando cidades...</div>
                </Card>
              ) : (
                <BarChartVertical
                  data={citiesRankQuery.data?.slice(0, 10).map((c) => ({
                    name: c.city.length > 20 ? c.city.substring(0, 20) + "..." : c.city,
                    value: c.p90_minutes,
                    avg: c.avg_minutes,
                    deliveries: c.deliveries,
                  })) || []}
                  title={
                    <span className="flex items-center">
                      Top 10 Cidades por Tempo de Entrega (P90)
                      <TooltipInfo content="P90 (percentil 90) significa que 90% das entregas foram concluídas neste tempo ou menos. Apenas 10% demoraram mais." />
                    </span>
                  }
                  formatValue={(value) => `${value.toFixed(0)} min`}
                  height={350}
                />
              )}
            </div>

            <div>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Análise por Região</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b">
                      <tr className="text-left">
                        <th className="pb-3 font-medium">Cidade</th>
                        <th className="pb-3 font-medium text-right">Entregas</th>
                        <th className="pb-3 font-medium text-right">Média</th>
                        <th className="pb-3 font-medium text-right flex items-center justify-end">
                          P90
                          <TooltipInfo content="P90 (percentil 90) significa que 90% das entregas foram concluídas neste tempo ou menos." />
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {citiesRankQuery.isLoading ? (
                        <tr>
                          <td colSpan={4} className="py-8 text-center text-muted-foreground">
                            Carregando...
                          </td>
                        </tr>
                      ) : !citiesRankQuery.data || citiesRankQuery.data.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-12 text-center">
                            <div className="text-muted-foreground">
                              <p className="font-medium mb-1">Nenhuma cidade encontrada</p>
                              <p className="text-xs">
                                Não há dados de entrega para o período selecionado. 
                                Tente selecionar um período mais amplo (7 ou 30 dias).
                              </p>
                            </div>
                          </td>
                        </tr>
                      ) : (
                        citiesRankQuery.data.slice(0, 12).map((city, idx) => (
                          <tr key={`${city.city}-${idx}`} className="border-b last:border-0">
                            <td className="py-3">{city.city}</td>
                            <td className="py-3 text-right">{city.deliveries.toLocaleString("pt-BR")}</td>
                            <td className="py-3 text-right">{city.avg_minutes.toFixed(1)}m</td>
                            <td className="py-3 text-right font-medium">
                              {city.p90_minutes.toFixed(1)}m
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="insights">
            <InsightsCard
              insights={insightsQuery.data || null}
              isLoading={insightsQuery.isLoading}
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
