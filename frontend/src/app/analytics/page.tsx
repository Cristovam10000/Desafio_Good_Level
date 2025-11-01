"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale/pt-BR";
import { fetchProductTop, fetchSalesHour, fetchChannels } from "@/shared/api/specials";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { isoRangeForLastNDays, expandToDateTime } from "@/shared/lib/date";
import { Navbar } from "@/widgets/layout/Navbar";
import AnalyticsTable from "./_table";
import ProductsByTime from "./_products-by-time";
import ChannelPie from "./_channel-pie";

export default function AnalyticsPage() {
  const { isAuthenticated } = useRequireAuth();

  const salesRange = useMemo(() => isoRangeForLastNDays(7), []);
  const topProductsRange = useMemo(() => isoRangeForLastNDays(30), []);

  const productTopQuery = useQuery({
    queryKey: ["specials", "product-top", topProductsRange.start, topProductsRange.end],
    queryFn: () => fetchProductTop({ start: topProductsRange.start, end: topProductsRange.end, limit: 20 }),
    enabled: isAuthenticated,
  });

  const salesHourQuery = useQuery({
    queryKey: ["specials", "sales-hour", salesRange.start, salesRange.end],
    queryFn: () => {
      const dtRange = expandToDateTime(salesRange);
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

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen">
      <Navbar activeTab="analytics" />
      <main className="px-4 sm:px-6 py-6 max-w-[1600px] mx-auto space-y-6">
        <h2 className="text-2xl font-bold">Analytics avancado</h2>
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
      </main>
    </div>
  );
}
