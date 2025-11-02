"use client";

import { Navbar } from "@/widgets/layout/Navbar";
import { useState, useMemo, useCallback } from "react";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { IsoRange } from "@/shared/lib/date";
import { useQuery } from "@tanstack/react-query";
import { fetchStoresTop, fetchChannels, fetchSectionInsights } from "@/shared/api/sections";
import { KPICard } from "@/widgets/dashboard/KPICard";
import BarChartVertical from "@/widgets/dashboard/BarChartVertical";
import { Card } from "@/shared/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Calendar, BarChart3, Lightbulb } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
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

export default function LojasPage() {
  const { isAuthenticated, isReady } = useRequireAuth();
  const [period, setPeriod] = useState<PeriodOption>("30days");
  const [customRange, setCustomRange] = useState<IsoRange>(() => rangeForPreset("30days"));
  const [channelOption, setChannelOption] = useState<number | null>(null);
  const [showAllPeriod, setShowAllPeriod] = useState(false);

  const displayRange = useMemo<IsoRange>(() => {
    if (showAllPeriod) {
      const now = new Date();
      const end = new Date(now);
      const start = new Date(now);
      start.setFullYear(now.getFullYear() - 1);
      start.setHours(0, 0, 0, 0);
      return {
        start: start.toISOString(),
        end: end.toISOString(),
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

  // Fetch stores ranking
  const storesQuery = useQuery({
    queryKey: ["stores", "top", displayRange, channelOption],
    queryFn: () =>
      fetchStoresTop({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 20,
      }),
    enabled: isAuthenticated,
  });

  // Fetch insights
  const insightsQuery = useQuery({
    queryKey: ["insights", "lojas", displayRange, channelOption],
    queryFn: () =>
      fetchSectionInsights("lojas", {
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  // Calculate KPIs from stores data
  const kpis = useMemo(() => {
    if (!storesQuery.data || storesQuery.data.length === 0) {
      return {
        totalRevenue: 0,
        totalOrders: 0,
        avgTicket: 0,
        totalCancelled: 0,
        avgCancellationRate: 0,
      };
    }

    const totalRevenue = storesQuery.data.reduce((sum, s) => sum + s.revenue, 0);
    const totalOrders = storesQuery.data.reduce((sum, s) => sum + s.orders, 0);
    const totalCancelled = storesQuery.data.reduce((sum, s) => sum + s.cancelled, 0);
    const avgTicket = totalOrders > 0 ? totalRevenue / totalOrders : 0;
    
    // Calculate weighted average cancellation rate
    const totalOrdersIncludingCancelled = totalOrders + totalCancelled;
    const avgCancellationRate = totalOrdersIncludingCancelled > 0 
      ? (totalCancelled / totalOrdersIncludingCancelled) * 100 
      : 0;

    return { totalRevenue, totalOrders, avgTicket, totalCancelled, avgCancellationRate };
  }, [storesQuery.data]);

  // Transform data for ranking chart
  const chartData = useMemo(() => {
    if (!storesQuery.data) return [];
    return storesQuery.data.slice(0, 10).map((s) => ({
      name: s.store_name,
      value: s.revenue,
      orders: s.orders,
      ticket: s.avg_ticket,
    }));
  }, [storesQuery.data]);

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
          <h1 className="text-3xl font-bold mb-2">Lojas</h1>
          <p className="text-muted-foreground">
            Quais lojas performam melhor? Quem caiu ou subiu na semana?
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
                    const dateValue = e.target.value; // YYYY-MM-DD
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
                    const dateValue = e.target.value; // YYYY-MM-DD
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
                storesQuery.refetch();
                channelsQuery.refetch();
                insightsQuery.refetch();
              }}
            >
              <BarChart3 className="w-4 h-4 mr-2" />
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KPICard
            title="Receita Total"
            value={kpis.totalRevenue}
            format="currency"
            loading={storesQuery.isLoading}
          />
          <KPICard
            title="Pedidos"
            value={kpis.totalOrders}
            format="number"
            loading={storesQuery.isLoading}
          />
          <KPICard
            title="Ticket Médio"
            value={kpis.avgTicket}
            format="currency"
            loading={storesQuery.isLoading}
          />
          <KPICard
            title="Taxa de Cancelamento"
            value={kpis.avgCancellationRate}
            format="percent"
            loading={storesQuery.isLoading}
          />
        </div>

        <div className="mt-6">
          {storesQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando ranking...</div>
            </Card>
          ) : (
            <BarChartVertical data={chartData} title="Ranking de Lojas por Receita" />
          )}
        </div>

        <div className="mt-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Todas as Lojas</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Loja</th>
                    <th className="pb-3 font-medium">Cidade</th>
                    <th className="pb-3 font-medium text-right">Receita</th>
                    <th className="pb-3 font-medium text-right">Pedidos</th>
                    <th className="pb-3 font-medium text-right">Ticket Médio</th>
                    <th className="pb-3 font-medium text-right">Cancelamentos</th>
                    <th className="pb-3 font-medium text-right">Taxa Canc.</th>
                  </tr>
                </thead>
                <tbody>
                  {storesQuery.isLoading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !storesQuery.data || storesQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground">
                        Nenhuma loja encontrada
                      </td>
                    </tr>
                  ) : (
                    storesQuery.data.map((store) => (
                      <tr key={store.store_id} className="border-b last:border-0">
                        <td className="py-3">{store.store_name}</td>
                        <td className="py-3 text-muted-foreground">
                          {store.city && store.state ? `${store.city}, ${store.state}` : "-"}
                        </td>
                        <td className="py-3 text-right font-medium">
                          {store.revenue.toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })}
                        </td>
                        <td className="py-3 text-right">{store.orders.toLocaleString("pt-BR")}</td>
                        <td className="py-3 text-right">
                          {store.avg_ticket.toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })}
                        </td>
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
