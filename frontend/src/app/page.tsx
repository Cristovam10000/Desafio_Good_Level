"use client";

import { useMemo, useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format, parseISO, addDays, differenceInCalendarDays, subDays, formatISO } from "date-fns";
import { ptBR } from "date-fns/locale/pt-BR";
import FilterPanel, { PeriodOption } from "@/features/filters/components/FilterPanel";
import { fetchInsights } from "@/shared/api/analytics";
import { fetchChannels, fetchSalesHour } from "@/shared/api/specials";
import { useAuth } from "@/shared/hooks/useAuth";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { IsoRange, expandToDateTime } from "@/shared/lib/date";
import { InsightCard } from "@/widgets/dashboard/InsightCard";
import ChannelChart from "@/widgets/dashboard/ChannelChart.client";
import SalesChart from "@/widgets/dashboard/SalesChart.client";
import { MetricCard } from "@/widgets/dashboard/MetricCard";
import { Navbar } from "@/widgets/layout/Navbar";

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

function ensureOrderedRange(range: IsoRange): IsoRange {
  const startDate = parseISO(range.start);
  const endDate = parseISO(range.end);
  if (startDate <= endDate) {
    return range;
  }
  return {
    start: formatISO(endDate, { representation: "date" }),
    end: formatISO(startDate, { representation: "date" }),
  };
}

function rangeForPreset(option: PeriodOption): IsoRange {
  const today = new Date();
  const formatDate = (date: Date) => formatISO(date, { representation: "date" });
  switch (option) {
    case "today": {
      const start = formatDate(today);
      return { start, end: start };
    }
    case "7days": {
      return { start: formatDate(subDays(today, 6)), end: formatDate(today) };
    }
    case "30days": {
      return { start: formatDate(subDays(today, 29)), end: formatDate(today) };
    }
    case "90days": {
      return { start: formatDate(subDays(today, 89)), end: formatDate(today) };
    }
    default:
      return { start: formatDate(subDays(today, 6)), end: formatDate(today) };
  }
}

function normalizeRangeForApi(range: IsoRange): IsoRange {
  const ordered = ensureOrderedRange(range);
  const startDate = parseISO(ordered.start);
  let endDate = parseISO(ordered.end);
  if (endDate <= startDate) {
    endDate = addDays(startDate, 1);
  }
  return {
    start: formatISO(startDate, { representation: "date" }),
    end: formatISO(endDate, { representation: "date" }),
  };
}


export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { auth, isReady: authReady } = useAuth();
  const { isAuthenticated, isReady: guardReady } = useRequireAuth();
  const isReady = authReady && guardReady;

  const [period, setPeriod] = useState<PeriodOption>("7days");
  const [customRange, setCustomRange] = useState<IsoRange>(() => rangeForPreset("today"));
  const [channelFilter, setChannelFilter] = useState<number | null>(null);

  const displayRange = useMemo<IsoRange>(() => {
    if (period === "custom") {
      return ensureOrderedRange(customRange);
    }
    return rangeForPreset(period);
  }, [customRange, period]);

  const apiRange = useMemo(() => normalizeRangeForApi(displayRange), [displayRange]);

  const rangeSpanDays = useMemo(() => {
    const startDate = parseISO(displayRange.start);
    const endDate = parseISO(displayRange.end);
    const diff = differenceInCalendarDays(endDate, startDate);
    return diff >= 0 ? diff + 1 : 1;
  }, [displayRange]);

  const previousRange = useMemo<IsoRange>(() => {
    const startDate = parseISO(displayRange.start);
    const prevEnd = subDays(startDate, 1);
    const prevStart = subDays(startDate, rangeSpanDays);
    return {
      start: formatISO(prevStart, { representation: "date" }),
      end: formatISO(prevEnd, { representation: "date" }),
    };
  }, [displayRange, rangeSpanDays]);

  const previousApiRange = useMemo(() => normalizeRangeForApi(previousRange), [previousRange]);

  const handlePeriodChange = useCallback((value: PeriodOption) => {
    setPeriod(value);
    if (value !== "custom") {
      setCustomRange(rangeForPreset(value));
    }
  }, []);

  const handleCustomRangeChange = useCallback((range: IsoRange) => {
    setCustomRange(ensureOrderedRange(range));
    setPeriod("custom");
  }, []);

  const handleChannelChange = useCallback((value: number | null) => {
    setChannelFilter(value);
  }, []);

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "insights"] });
    queryClient.invalidateQueries({ queryKey: ["analytics", "insights", "previous"] });
    queryClient.invalidateQueries({ queryKey: ["specials", "sales-hour"] });
  }, [queryClient]);

  const insightsQuery = useQuery({
    queryKey: ["analytics", "insights", apiRange.start, apiRange.end, channelFilter],
    queryFn: () =>
      fetchInsights({
        start: apiRange.start,
        end: apiRange.end,
        ...(channelFilter != null ? { channel_id: channelFilter } : {}),
      }),
    enabled: isAuthenticated && isReady,
  });

  const previousInsightsQuery = useQuery({
    queryKey: ["analytics", "insights", "previous", previousApiRange.start, previousApiRange.end, channelFilter],
    queryFn: () =>
      fetchInsights({
        start: previousApiRange.start,
        end: previousApiRange.end,
        ...(channelFilter != null ? { channel_id: channelFilter } : {}),
      }),
    enabled: isAuthenticated && isReady,
  });

  const salesHourQuery = useQuery({
    queryKey: ["specials", "sales-hour", displayRange.start, displayRange.end, channelFilter],
    queryFn: () => {
      const dtRange = expandToDateTime(displayRange);
      return fetchSalesHour({
        start: dtRange.start,
        end: dtRange.end,
        ...(channelFilter != null ? { channel_id: channelFilter } : {}),
      });
    },
    enabled: isAuthenticated && isReady,
  });

  const channelsQuery = useQuery({
    queryKey: ["specials", "channels"],
    queryFn: fetchChannels,
    staleTime: Infinity,
    enabled: isAuthenticated && isReady,
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

    const totals = new Map<string, { id: string; name: string; value: number }>();
    salesHourQuery.data?.forEach((row) => {
      if (row.channel_id == null) {
        return;
      }
      const channelId = row.channel_id;
      const name = channels.get(channelId) ?? `Canal ${channelId}`;
      const key = name.toLowerCase();
      const current = totals.get(key) ?? { id: String(channelId), name, value: 0 };
      totals.set(key, {
        id: current.id,
        name,
        value: current.value + (row.revenue ?? 0),
      });
    });

    return Array.from(totals.values())
      .map((entry) => ({
        id: entry.id,
        name: entry.name,
        value: Number(entry.value.toFixed(2)),
      }))
      .sort((a, b) => b.value - a.value);
  }, [salesHourQuery.data, channelsQuery.data]);

  const greetingName = auth?.user.name ?? "Maria";
  const insightItems = metrics.insights.slice(0, 4);

  if (!isReady) {
    return (
      <div className="min-h-screen grid place-items-center text-muted-foreground">
        Carregando painel...
      </div>
    );
  }

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
          <FilterPanel
            period={period}
            range={displayRange}
            onPeriodChange={handlePeriodChange}
            onCustomRangeChange={handleCustomRangeChange}
            channelId={channelFilter}
            onChannelChange={handleChannelChange}
            channels={channelsQuery.data ?? []}
            isChannelLoading={channelsQuery.isLoading}
            onRefresh={handleRefresh}
          />
        </div>

        {insightsQuery.isError && (
          <div className="mb-6 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Nao foi possivel carregar os dados do dashboard. Tente novamente mais tarde.
          </div>
        )}

        {insightsQuery.data?.insights_error && !insightsQuery.isError && (
          <div className="mb-6 rounded-md border border-amber-300/60 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {insightsQuery.data.insights_error}
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
