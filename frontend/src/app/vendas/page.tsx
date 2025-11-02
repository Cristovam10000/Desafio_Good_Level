"use client";

import { Navbar } from "@/widgets/layout/Navbar";
import { Card } from "@/shared/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { Calendar, BarChart3, Lightbulb } from "lucide-react";
import { useState, useMemo, useCallback } from "react";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { IsoRange } from "@/shared/lib/date";
import { useQuery } from "@tanstack/react-query";
import { 
  fetchSalesSummary, 
  fetchSalesByChannel, 
  fetchSalesByDay,
  fetchSalesByWeekday,
  fetchDiscountReasons,
  fetchChannels,
  fetchSectionInsights
} from "@/shared/api/sections";
import { KPICard } from "@/widgets/dashboard/KPICard";
import ParticipationChart from "@/widgets/dashboard/ParticipationChart";
import TimelineChart from "@/widgets/dashboard/TimelineChart";
import BarChartVertical from "@/widgets/dashboard/BarChartVertical";
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

export default function VendasPage() {
  const { isAuthenticated, isReady } = useRequireAuth();
  const [period, setPeriod] = useState<PeriodOption>("30days");
  const [customRange, setCustomRange] = useState<IsoRange>(() => rangeForPreset("30days"));
  const [channelOption, setChannelOption] = useState<number | null>(null);
  const [showAllPeriod, setShowAllPeriod] = useState(false);

  const displayRange = useMemo<IsoRange>(() => {
    if (period === "custom") return customRange;
    return rangeForPreset(period);
  }, [customRange, period]);

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

  // Fetch sales summary
  const summaryQuery = useQuery({
    queryKey: ["sales", "summary", displayRange, channelOption],
    queryFn: () =>
      fetchSalesSummary({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch sales by channel
  const byChannelQuery = useQuery({
    queryKey: ["sales", "by-channel", displayRange],
    queryFn: () =>
      fetchSalesByChannel({
        start: displayRange.start,
        end: displayRange.end,
      }),
    enabled: isAuthenticated,
  });

  // Fetch sales by day
  const byDayQuery = useQuery({
    queryKey: ["sales", "by-day", displayRange, channelOption],
    queryFn: () =>
      fetchSalesByDay({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch sales by weekday
  const byWeekdayQuery = useQuery({
    queryKey: ["sales", "by-weekday", displayRange, channelOption],
    queryFn: () =>
      fetchSalesByWeekday({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch discount reasons
  const discountReasonsQuery = useQuery({
    queryKey: ["sales", "discount-reasons", displayRange, channelOption],
    queryFn: () =>
      fetchDiscountReasons({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch AI insights for Vendas section
  const insightsQuery = useQuery({
    queryKey: ["insights", "vendas", displayRange, channelOption],
    queryFn: () =>
      fetchSectionInsights("vendas", {
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Transform data for pie chart
  const chartData = useMemo(() => {
    if (!byChannelQuery.data) return [];
    return byChannelQuery.data.map((ch) => ({
      name: ch.channel_name,
      value: ch.revenue,
    }));
  }, [byChannelQuery.data]);

  // Transform data for timeline (vendas por dia)
  const timelineData = useMemo(() => {
    if (!byDayQuery.data) return [];
    return byDayQuery.data.map((d) => ({
      date: d.bucket_day,
      "Receita": d.revenue,
      "Pedidos": d.orders,
    }));
  }, [byDayQuery.data]);

  // Transform data for weekday chart
  const weekdayChartData = useMemo(() => {
    if (!byWeekdayQuery.data) return [];
    
    // Ordem correta: Segunda(1), Terça(2), Quarta(3), Quinta(4), Sexta(5), Sábado(6), Domingo(0)
    const orderedData = [...byWeekdayQuery.data].sort((a, b) => {
      const orderA = a.weekday === 0 ? 7 : a.weekday; // Domingo vai para o final
      const orderB = b.weekday === 0 ? 7 : b.weekday;
      return orderA - orderB;
    });
    
    return orderedData.map((w) => ({
      name: w.weekday_name,
      value: w.revenue,
      orders: w.orders,
      avg_ticket: w.avg_ticket,
    }));
  }, [byWeekdayQuery.data]);

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
          <h1 className="text-3xl font-bold mb-2">Vendas</h1>
          <p className="text-muted-foreground">
            Como está a curva? Qual canal puxa a receita?
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
                summaryQuery.refetch();
                byChannelQuery.refetch();
                byDayQuery.refetch();
                byWeekdayQuery.refetch();
                discountReasonsQuery.refetch();
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

          <TabsContent value="dashboard" className="space-y-6 mt-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KPICard
            title="Receita"
            value={summaryQuery.data?.revenue || 0}
            format="currency"
            loading={summaryQuery.isLoading}
          />
          <KPICard
            title="Pedidos"
            value={summaryQuery.data?.orders || 0}
            format="number"
            loading={summaryQuery.isLoading}
          />
          <KPICard
            title="Ticket Médio"
            value={summaryQuery.data?.avg_ticket || 0}
            format="currency"
            loading={summaryQuery.isLoading}
          />
          <KPICard
            title="% Desconto"
            value={summaryQuery.data?.discount_pct || 0}
            format="percent"
            loading={summaryQuery.isLoading}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          {byChannelQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando gráfico...</div>
            </Card>
          ) : (
            <ParticipationChart
              data={chartData}
              title="Participação por Canal"
              innerRadius={60}
            />
          )}

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Detalhamento por Canal</h3>
            <div className="space-y-3">
              {byChannelQuery.isLoading ? (
                <div className="text-center text-muted-foreground py-4">Carregando...</div>
              ) : !byChannelQuery.data || byChannelQuery.data.length === 0 ? (
                <div className="text-center text-muted-foreground py-4">
                  Nenhum dado disponível
                </div>
              ) : (
                byChannelQuery.data.map((ch) => (
                  <div key={ch.channel_id} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{ch.channel_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {ch.orders.toLocaleString("pt-BR")} pedidos
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">
                        {ch.revenue.toLocaleString("pt-BR", {
                          style: "currency",
                          currency: "BRL",
                        })}
                      </p>
                      <p className="text-sm text-muted-foreground">{ch.pct.toFixed(1)}%</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
          {byDayQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando evolução...</div>
            </Card>
          ) : (
            <TimelineChart
              data={timelineData}
              title="Evolução de Vendas por Dia"
              series={[
                { dataKey: "Receita", name: "Receita (R$)", color: "#10b981" },
              ]}
              height={350}
            />
          )}

          {byWeekdayQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando dias da semana...</div>
            </Card>
          ) : (
            <BarChartVertical
              data={weekdayChartData}
              title="Ranking: Dias da Semana com Mais Vendas"
              formatValue={(value) => value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              height={350}
            />
          )}
        </div>

        <div className="mt-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Ranking: Vendas por Dia da Semana</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Dia da Semana</th>
                    <th className="pb-3 font-medium text-right">Receita</th>
                    <th className="pb-3 font-medium text-right">Pedidos</th>
                    <th className="pb-3 font-medium text-right">Ticket Médio</th>
                  </tr>
                </thead>
                <tbody>
                  {byWeekdayQuery.isLoading ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !byWeekdayQuery.data || byWeekdayQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Nenhum dado disponível
                      </td>
                    </tr>
                  ) : (
                    // Ordenar: Segunda, Terça, Quarta, Quinta, Sexta, Sábado, Domingo
                    [...byWeekdayQuery.data]
                      .sort((a, b) => {
                        const orderA = a.weekday === 0 ? 7 : a.weekday;
                        const orderB = b.weekday === 0 ? 7 : b.weekday;
                        return orderA - orderB;
                      })
                      .map((day) => (
                        <tr key={day.weekday} className="border-b last:border-0">
                          <td className="py-3 font-medium">{day.weekday_name}</td>
                          <td className="py-3 text-right">
                            {day.revenue.toLocaleString("pt-BR", {
                              style: "currency",
                              currency: "BRL",
                            })}
                          </td>
                          <td className="py-3 text-right font-semibold">
                            {day.orders.toLocaleString("pt-BR")}
                          </td>
                          <td className="py-3 text-right">
                            {day.avg_ticket.toLocaleString("pt-BR", {
                              style: "currency",
                              currency: "BRL",
                            })}
                          </td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="mt-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Ranking: Motivos de Desconto</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Motivo</th>
                    <th className="pb-3 font-medium text-right">Ocorrências</th>
                    <th className="pb-3 font-medium text-right">Valor Total</th>
                    <th className="pb-3 font-medium text-right">Desconto Médio</th>
                  </tr>
                </thead>
                <tbody>
                  {discountReasonsQuery.isLoading ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !discountReasonsQuery.data || discountReasonsQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Nenhum desconto concedido no período
                      </td>
                    </tr>
                  ) : (
                    discountReasonsQuery.data.map((reason, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="py-3 font-medium">{reason.discount_reason}</td>
                        <td className="py-3 text-right font-semibold">
                          {reason.occurrences.toLocaleString("pt-BR")}
                        </td>
                        <td className="py-3 text-right">
                          {reason.total_discount_value.toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })}
                        </td>
                        <td className="py-3 text-right">
                          {reason.avg_discount.toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })}
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
              title="Insights de IA - Vendas"
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
