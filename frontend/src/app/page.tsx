"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale/pt-BR";
import FilterPanel from "@/features/filters/components/FilterPanel";
import { fetchInsights } from "@/shared/api/analytics";
import { fetchChannels, fetchSalesHour } from "@/shared/api/specials";
import { useAuth } from "@/shared/hooks/useAuth";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { isoRange, isoRangeForLastNDays, expandToDateTime } from "@/shared/lib/date";
import { InsightCard } from "@/widgets/dashboard/InsightCard";
import ChannelChart from "@/widgets/dashboard/ChannelChart.client";
import SalesChart from "@/widgets/dashboard/SalesChart.client";
import { MetricCard } from "@/widgets/dashboard/MetricCard";
import { Navbar } from "@/widgets/layout/Navbar";

const DASHBOARD_DAYS = 7;
const INSIGHT_TYPES = ["success", "warning", "info", "trend"] as const;

function sum(values: Array<number | null | undefined>) {
  return values.reduce<number>((acc, value) => acc + (value ?? 0), 0);
}

function calculateChange(current: number, previous?: number | null) {
  if (previous == null || previous === 0) return null;
  return ((current - previous) / previous) * 100;
}

function formatCurrency(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatNumber(value: number) {
  return value.toLocaleString("pt-BR");
}

function splitInsight(text: string) {
  const [title, ...rest] = text.split(". ");
  const description = rest.length > 0 ? rest.join(". ") : text;
  return {
    title: title.trim(),
    description: description.trim(),
  };
}

export default function DashboardPage() {
  const { auth } = useAuth();
  const { isAuthenticated } = useRequireAuth();

  const ranges = useMemo(
    () => ({
      current: isoRangeForLastNDays(DASHBOARD_DAYS),
      previous: isoRange(DASHBOARD_DAYS, DASHBOARD_DAYS),
    }),
    []
  );

  const insightsQuery = useQuery({
    queryKey: ["analytics", "insights", ranges.current.start, ranges.current.end],
    queryFn: () => fetchInsights({ start: ranges.current.start, end: ranges.current.end }),
    enabled: isAuthenticated,
  });

  const previousInsightsQuery = useQuery({
    queryKey: ["analytics", "insights", ranges.previous.start, ranges.previous.end],
    queryFn: () => fetchInsights({ start: ranges.previous.start, end: ranges.previous.end }),
    enabled: isAuthenticated,
  });

  const salesHourQuery = useQuery({
    queryKey: ["specials", "sales-hour", ranges.current.start, ranges.current.end],
    queryFn: () => {
      const dtRange = expandToDateTime(ranges.current);
      return fetchSalesHour({ start: dtRange.start, end: dtRange.end });
    },
    enabled: isAuthenticated,
  });

  const channelsQuery = useQuery({
    queryKey: ["specials", "channels"],
    queryFn: fetchChannels,
    staleTime: Infinity,
    enabled: isAuthenticated,
  });

  const metrics = useMemo(() => {
    const currentSales = (insightsQuery.data?.preview.sales_daily ?? []).slice().sort((a, b) => a.bucket_day.localeCompare(b.bucket_day));
    const previousSales = (previousInsightsQuery.data?.preview.sales_daily ?? []).slice().sort((a, b) => a.bucket_day.localeCompare(b.bucket_day));

    const currentRevenue = sum(currentSales.map((item) => item.revenue ?? 0));
    const previousRevenue = sum(previousSales.map((item) => item.revenue ?? 0));
    const currentOrders = sum(currentSales.map((item) => item.orders ?? 0));
    const previousOrders = sum(previousSales.map((item) => item.orders ?? 0));

    const currentAvgTicket = currentOrders > 0 ? currentRevenue / currentOrders : 0;
    const previousAvgTicket = previousOrders > 0 ? previousRevenue / previousOrders : 0;

    const deliveryStats = insightsQuery.data?.preview.delivery_stats ?? [];
    const prevDeliveryStats = previousInsightsQuery.data?.preview.delivery_stats ?? [];
    const currentAvgDelivery = deliveryStats.length ? sum(deliveryStats.map((item) => item.avg_delivery_minutes)) / deliveryStats.length : 0;
    const previousAvgDelivery = prevDeliveryStats.length ? sum(prevDeliveryStats.map((item) => item.avg_delivery_minutes)) / prevDeliveryStats.length : null;

    return {
      revenue: currentRevenue,
      revenueChange: calculateChange(currentRevenue, previousRevenue),
      orders: currentOrders,
      ordersChange: calculateChange(currentOrders, previousOrders),
      avgTicket: currentAvgTicket,
      avgTicketChange: calculateChange(currentAvgTicket, previousAvgTicket),
      avgDelivery: currentAvgDelivery,
      avgDeliveryChange:
        previousAvgDelivery != null && previousAvgDelivery !== 0
          ? ((previousAvgDelivery - currentAvgDelivery) / previousAvgDelivery) * 100
          : null,
      chartCurrent: currentSales,
      chartPrevious: previousSales,
      insights: insightsQuery.data?.insights ?? [],
    };
  }, [insightsQuery.data, previousInsightsQuery.data]);

  const chartData = useMemo(() => {
    const previous = metrics.chartPrevious ?? [];
    return (metrics.chartCurrent ?? []).map((point, index) => ({
      name: format(parseISO(point.bucket_day), "EEE", { locale: ptBR }),
      current: point.revenue ?? 0,
      previous: previous[index]?.revenue ?? null,
    }));
  }, [metrics.chartCurrent, metrics.chartPrevious]);

  const channelData = useMemo(() => {
    const channels = new Map<number, string>();
    channelsQuery.data?.forEach((channel) => {
      channels.set(channel.id, channel.name);
    });

    const totals = new Map<number, number>();
    salesHourQuery.data?.forEach((row) => {
      if (row.channel_id == null) {
        return;
      }
      const value = totals.get(row.channel_id) ?? 0;
      totals.set(row.channel_id, value + (row.revenue ?? 0));
    });

    return Array.from(totals.entries())
      .map(([channelId, value]) => ({
        name: channels.get(channelId) ?? `Canal ${channelId}`,
        value: Number(value.toFixed(2)),
      }))
      .sort((a, b) => b.value - a.value);
  }, [salesHourQuery.data, channelsQuery.data]);

  const greetingName = auth?.user.name ?? "Maria";
  const insightItems = metrics.insights.slice(0, 4);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="px-4 sm:px-6 py-6 max-w-[1600px] mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl sm:text-3xl font-bold">Ola, {greetingName.split(" ")[0]}!</h2>
          <p className="text-sm text-muted-foreground">Resumo dos ultimos 7 dias</p>
        </div>

        <div className="mb-4">
          <FilterPanel />
        </div>

        {insightsQuery.isError && (
          <div className="mb-6 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Nao foi possivel carregar os dados do dashboard. Tente novamente mais tarde.
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Receita Total"
            value={formatCurrency(metrics.revenue ?? 0)}
            change={metrics.revenueChange}
            changeLabel="vs. semana anterior"
          />
          <MetricCard
            title="Pedidos"
            value={formatNumber(metrics.orders ?? 0)}
            change={metrics.ordersChange}
            changeLabel="vs. semana anterior"
          />
          <MetricCard
            title="Ticket Medio"
            value={formatCurrency(metrics.avgTicket ?? 0)}
            change={metrics.avgTicketChange}
            changeLabel="vs. semana anterior"
          />
          <MetricCard
            title="Tempo medio de entrega"
            value={`${(metrics.avgDelivery ?? 0).toFixed(0)} min`}
            change={metrics.avgDeliveryChange}
            changeLabel="vs. semana anterior"
          />
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Insights automaticos</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {insightItems.length === 0 && (
              <p className="text-sm text-muted-foreground">Nenhum insight disponivel para o periodo selecionado.</p>
            )}
            {insightItems.map((text, index) => {
              const parsed = splitInsight(text);
              const type = INSIGHT_TYPES[index % INSIGHT_TYPES.length];
              return <InsightCard key={text} type={type} title={parsed.title} description={parsed.description} />;
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <SalesChart data={chartData} title="Evolucao de vendas" showComparison />
          <ChannelChart data={channelData} title="Vendas por canal" />
        </div>
      </main>
    </div>
  );
}
