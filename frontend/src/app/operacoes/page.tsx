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
import { fetchPrepTime, fetchCancellations, fetchChannels, fetchSectionInsights } from "@/shared/api/sections";
import { KPICard } from "@/widgets/dashboard/KPICard";
import { InsightsCard } from "@/widgets/dashboard/InsightsCard";
import BarChartVertical from "@/widgets/dashboard/BarChartVertical";
import TimelineChart from "@/widgets/dashboard/TimelineChart";
import { TooltipInfo } from "@/shared/ui/tooltip-info";

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

export default function OperacoesPage() {
  const { isAuthenticated, isReady } = useRequireAuth();
  const [period, setPeriod] = useState<PeriodOption>("30days");
  const [customRange, setCustomRange] = useState<IsoRange>(() => rangeForPreset("30days"));
  const [channelOption, setChannelOption] = useState<number | null>(null);
  const [showAllPeriod, setShowAllPeriod] = useState(false);

  const displayRange = useMemo<IsoRange>(() => {
    if (showAllPeriod) {
      const now = new Date();
      const start = new Date(now);
      start.setFullYear(now.getFullYear() - 1);
      start.setHours(0, 0, 0, 0);
      return {
        start: start.toISOString(),
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

  // Fetch prep time by store
  const prepTimeQuery = useQuery({
    queryKey: ["ops", "prep-time", displayRange, channelOption],
    queryFn: () =>
      fetchPrepTime({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 20,
      }),
    enabled: isAuthenticated,
  });

  // Fetch cancellations timeline
  const cancellationsQuery = useQuery({
    queryKey: ["ops", "cancellations", displayRange, channelOption],
    queryFn: () =>
      fetchCancellations({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch AI insights for Operações section
  const insightsQuery = useQuery({
    queryKey: ["insights", "operacoes", displayRange, channelOption],
    queryFn: () =>
      fetchSectionInsights("operacoes", {
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Transform data for prep time chart
  const prepTimeChartData = useMemo(() => {
    if (!prepTimeQuery.data) return [];
    return prepTimeQuery.data.slice(0, 10).map((s) => ({
      name: s.store_name.length > 20 ? s.store_name.substring(0, 20) + "..." : s.store_name,
      value: s.avg_prep_minutes,
      p90: s.p90_prep_minutes,
      orders: s.orders,
    }));
  }, [prepTimeQuery.data]);

  // Transform data for cancellations timeline
  const cancellationsTimelineData = useMemo(() => {
    if (!cancellationsQuery.data) return [];
    return cancellationsQuery.data.map((c) => ({
      date: c.bucket_day,
      "Taxa de Cancelamento": c.cancellation_rate * 100, // Convert to percentage
      canceled: c.canceled,
      total: c.total,
    }));
  }, [cancellationsQuery.data]);

  // Calculate KPIs
  const kpis = useMemo(() => {
    const avgPrepTime = (prepTimeQuery.data?.reduce((sum, s) => sum + s.avg_prep_minutes, 0) ?? 0) / (prepTimeQuery.data?.length || 1);
    const avgP90 = (prepTimeQuery.data?.reduce((sum, s) => sum + s.p90_prep_minutes, 0) ?? 0) / (prepTimeQuery.data?.length || 1);
    
    const totalCanceled = cancellationsQuery.data?.reduce((sum, c) => sum + c.canceled, 0) || 0;
    const totalOrders = cancellationsQuery.data?.reduce((sum, c) => sum + c.total, 0) || 0;
    const cancellationRate = totalOrders > 0 ? (totalCanceled / totalOrders) * 100 : 0;
    
    return {
      avgPrepTime,
      avgP90,
      totalCanceled,
      cancellationRate,
    };
  }, [prepTimeQuery.data, cancellationsQuery.data]);

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
          <h1 className="text-3xl font-bold mb-2">Operações</h1>
          <p className="text-muted-foreground">
            Tempo de preparo, cancelamentos e eficiência operacional
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
                prepTimeQuery.refetch();
                cancellationsQuery.refetch();
                channelsQuery.refetch();
                insightsQuery.refetch();
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

          <TabsContent value="dashboard" className="space-y-6 mt-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KPICard
            title="Tempo Médio de Preparo"
            value={kpis.avgPrepTime}
            format="time"
            loading={prepTimeQuery.isLoading}
          />
          <KPICard
            title="P90 Tempo de Preparo"
            value={kpis.avgP90}
            format="time"
            loading={prepTimeQuery.isLoading}
          />
          <KPICard
            title="Total de Cancelamentos"
            value={kpis.totalCanceled}
            format="number"
            loading={cancellationsQuery.isLoading}
          />
          <KPICard
            title="Taxa de Cancelamento"
            value={kpis.cancellationRate}
            format="percent"
            loading={cancellationsQuery.isLoading}
          />
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
          {prepTimeQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando tempos de preparo...</div>
            </Card>
          ) : (
            <BarChartVertical
              data={prepTimeChartData}
              title="Tempo Médio de Preparo por Loja"
              formatValue={(value) => `${value.toFixed(0)} min`}
              height={350}
            />
          )}

          {cancellationsQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando cancelamentos...</div>
            </Card>
          ) : (
            <TimelineChart
              data={cancellationsTimelineData}
              title="Evolução da Taxa de Cancelamento"
              series={[{ dataKey: "Taxa de Cancelamento", name: "Taxa de Cancelamento (%)" }]}
              formatYAxis={(value) => `${value.toFixed(1)}%`}
              height={350}
            />
          )}
        </div>

        <div className="mt-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Análise Detalhada por Loja</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Loja</th>
                    <th className="pb-3 font-medium text-right">Pedidos</th>
                    <th className="pb-3 font-medium text-right">Cancelamentos</th>
                    <th className="pb-3 font-medium text-right">Taxa Canc.</th>
                    <th className="pb-3 font-medium text-right">Tempo Médio</th>
                    <th className="pb-3 font-medium text-right">
                      <span className="flex items-center justify-end">
                        P90
                        <TooltipInfo content="P90 (percentil 90) significa que 90% dos pedidos foram preparados neste tempo ou menos. Apenas 10% demoraram mais." />
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {prepTimeQuery.isLoading ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !prepTimeQuery.data || prepTimeQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-muted-foreground">
                        Nenhuma loja encontrada
                      </td>
                    </tr>
                  ) : (
                    prepTimeQuery.data.map((store) => (
                      <tr key={store.store_id} className="border-b last:border-0">
                        <td className="py-3">{store.store_name}</td>
                        <td className="py-3 text-right">{store.orders.toLocaleString("pt-BR")}</td>
                        <td className="py-3 text-right">{store.cancelled.toLocaleString("pt-BR")}</td>
                        <td className="py-3 text-right">
                          <span
                            className={
                              store.cancellation_rate > 6 ? "text-red-600" : "text-muted-foreground"
                            }
                          >
                            {store.cancellation_rate.toFixed(2)}%
                          </span>
                        </td>
                        <td className="py-3 text-right">{store.avg_prep_minutes.toFixed(0)} min</td>
                        <td className="py-3 text-right font-medium">
                          {store.p90_prep_minutes.toFixed(0)} min
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

          <TabsContent value="insights" className="mt-6">
            <InsightsCard
              insights={insightsQuery.data || null}
              isLoading={insightsQuery.isLoading}
              title="Insights de IA - Operações"
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
