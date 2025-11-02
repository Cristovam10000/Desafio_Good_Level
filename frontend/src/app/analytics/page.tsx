"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale/pt-BR";
import { fetchProductTop, fetchSalesHour, fetchChannels, fetchDataRange } from "@/shared/api/specials";
import { fetchAnomalies } from "@/shared/api/analytics";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { useAuth } from "@/shared/hooks/useAuth";
import { isoRangeForLastNDays, expandToDateTime, type IsoRange } from "@/shared/lib/date";
import { Navbar } from "@/widgets/layout/Navbar";
import FilterPanel, { type PeriodOption } from "@/features/filters/components/FilterPanel";
import AnalyticsTable from "./_table";
import ProductsByTime from "./_products-by-time";
import ChannelPie from "./_channel-pie";
import AnomalyDetector from "./_anomaly-detector";
import { DetailedAnalyses } from "./_detailed-analyses";

export default function AnalyticsPage() {
  const { isAuthenticated, isReady: guardReady } = useRequireAuth();
  const { isReady: authReady } = useAuth();
  const isReady = authReady && guardReady;

  // Estado do filtro de período
  const [period, setPeriod] = useState<PeriodOption>("7days");
  const [customRange, setCustomRange] = useState<IsoRange>(() => isoRangeForLastNDays(7));

  // Calcula o range baseado no período selecionado
  const salesRange = useMemo(() => {
    switch (period) {
      case "today":
        return isoRangeForLastNDays(1);
      case "7days":
        return isoRangeForLastNDays(7);
      case "30days":
        return isoRangeForLastNDays(30);
      case "90days":
        return isoRangeForLastNDays(90);
      case "custom":
        return customRange;
      default:
        return isoRangeForLastNDays(7);
    }
  }, [period, customRange]);

  const topProductsRange = salesRange; // Usa o mesmo período selecionado

  const productTopQuery = useQuery({
    queryKey: ["specials", "product-top", topProductsRange.start, topProductsRange.end],
    queryFn: () => fetchProductTop({ start: topProductsRange.start, end: topProductsRange.end, limit: 20 }),
    enabled: isAuthenticated && isReady,
  });

  const salesHourQuery = useQuery({
    queryKey: ["specials", "sales-hour", salesRange.start, salesRange.end],
    queryFn: () => {
      const dtRange = expandToDateTime(salesRange);
      return fetchSalesHour({ start: dtRange.start, end: dtRange.end });
    },
    enabled: isAuthenticated && isReady,
  });

  const channelsQuery = useQuery({
    queryKey: ["specials", "channels"],
    queryFn: fetchChannels,
    staleTime: Infinity,
    enabled: isAuthenticated && isReady,
  });

  const dataRangeQuery = useQuery({
    queryKey: ["specials", "data-range"],
    queryFn: fetchDataRange,
    staleTime: Infinity,
    enabled: isAuthenticated && isReady,
  });

  const handleFullPeriod = () => {
    if (dataRangeQuery.data) {
      setPeriod("custom");
      setCustomRange({
        start: dataRangeQuery.data.start_date,
        end: dataRangeQuery.data.end_date,
      });
    }
  };

  const anomaliesQuery = useQuery({
    queryKey: ["analytics", "anomalies", salesRange.start, salesRange.end],
    queryFn: () => fetchAnomalies({
      start: salesRange.start,
      end: salesRange.end,
    }),
    enabled: isAuthenticated && isReady,
    staleTime: 2 * 60 * 1000, // 2 minutos
  });

  const hourlyData = useMemo(() => {
    const buckets = new Map<string, { revenue: number; orders: number }>();
    salesHourQuery.data?.forEach((row) => {
      const date = parseISO(row.bucket_hour);
      const label = format(date, "HH'h'", { locale: ptBR });
      const entry = buckets.get(label) ?? { revenue: 0, orders: 0 };
      entry.revenue += row.revenue ?? 0;
      entry.orders += row.orders ?? 0;
      buckets.set(label, entry);
    });

    return Array.from(buckets.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([label, value]) => ({
        label,
        revenue: Number(value.revenue.toFixed(2)),
        orders: value.orders,
      }));
  }, [salesHourQuery.data]);

  const channelData = useMemo(() => {
    const channelMap = new Map<number, string>();
    channelsQuery.data?.forEach((channel) => channelMap.set(channel.id, channel.name));

    const totals = new Map<string, { id: string; name: string; value: number }>();
    salesHourQuery.data?.forEach((row) => {
      if (row.channel_id == null) return;
      const channelId = row.channel_id;
      const name = channelMap.get(channelId) ?? `Canal ${channelId}`;
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

  const productRows = useMemo(
    () =>
      (productTopQuery.data ?? []).map((row) => ({
        id: row.product_id,
        product: row.product_name,
        revenue: row.revenue ?? 0,
        orders: row.orders ?? 0,
        qty: row.qty ?? 0,
      })),
    [productTopQuery.data]
  );

  if (!isReady) {
    return (
      <div className="min-h-screen grid place-items-center text-muted-foreground">
        Carregando analytics...
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen">
      <Navbar activeTab="analytics" />
      <main className="px-4 sm:px-6 py-6 max-w-[1600px] mx-auto space-y-6">
        <h2 className="text-2xl font-bold">Analytics avancado</h2>
        
        {/* Filtro de período */}
        <FilterPanel
          period={period}
          range={salesRange}
          onPeriodChange={setPeriod}
          onCustomRangeChange={setCustomRange}
          channelOption={null}
          onChannelChange={() => {}}
          channels={[]}
          isChannelLoading={false}
          onRefresh={() => {
            productTopQuery.refetch();
            salesHourQuery.refetch();
            channelsQuery.refetch();
          }}
          onFullPeriod={handleFullPeriod}
        />

        {(productTopQuery.isError || salesHourQuery.isError) && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Nao foi possivel carregar os dados analiticos. Recarregue a pagina ou tente novamente.
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ProductsByTime data={hourlyData} />
          <ChannelPie data={channelData} />
        </div>
        <AnalyticsTable rows={productRows} />
        
        {/* Detector de Anomalias */}
        <AnomalyDetector 
          data={anomaliesQuery.data || null}
          isLoading={anomaliesQuery.isLoading}
          isError={anomaliesQuery.isError}
        />

        {/* Análises Detalhadas da Estrutura de Vendas */}
        <DetailedAnalyses
          start={salesRange.start}
          end={salesRange.end}
          storeId={undefined}
        />
      </main>
    </div>
  );
}
