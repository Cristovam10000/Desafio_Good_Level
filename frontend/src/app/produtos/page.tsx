"use client";

import { Navbar } from "@/widgets/layout/Navbar";
import { Card } from "@/shared/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Calendar, BarChart3, Lightbulb } from "lucide-react";
import { useState, useMemo, useCallback } from "react";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { IsoRange } from "@/shared/lib/date";
import { useQuery } from "@tanstack/react-query";
import { 
  fetchProductsLowSellers, 
  fetchProductsTopSellers, 
  fetchProductsAddonsTop,
  fetchProductsMostCustomized,
  fetchProductCombinations,
  fetchChannels,
  fetchSectionInsights 
} from "@/shared/api/sections";
import { KPICard } from "@/widgets/dashboard/KPICard";
import BarChartVertical from "@/widgets/dashboard/BarChartVertical";
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

export default function ProdutosPage() {
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

  // Fetch low sellers
  const lowSellersQuery = useQuery({
    queryKey: ["products", "low-sellers", displayRange, channelOption],
    queryFn: () =>
      fetchProductsLowSellers({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 10,
      }),
    enabled: isAuthenticated,
  });

  // Fetch top sellers
  const topSellersQuery = useQuery({
    queryKey: ["products", "top-sellers", displayRange, channelOption],
    queryFn: () =>
      fetchProductsTopSellers({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 5,
      }),
    enabled: isAuthenticated,
  });

  // Fetch top addons
  const addonsQuery = useQuery({
    queryKey: ["products", "addons", displayRange, channelOption],
    queryFn: () =>
      fetchProductsAddonsTop({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 10,
      }),
    enabled: isAuthenticated,
  });

  // Fetch products with most customizations
  const mostCustomizedQuery = useQuery({
    queryKey: ["products", "most-customized", displayRange, channelOption],
    queryFn: () =>
      fetchProductsMostCustomized({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 10,
      }),
    enabled: isAuthenticated,
  });

  // Fetch product combinations
  const combinationsQuery = useQuery({
    queryKey: ["products", "combinations", displayRange, channelOption],
    queryFn: () =>
      fetchProductCombinations({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
        limit: 10,
      }),
    enabled: isAuthenticated,
  });

  // Fetch insights
  const insightsQuery = useQuery({
    queryKey: ["insights", "produtos", displayRange, channelOption],
    queryFn: () =>
      fetchSectionInsights("produtos", {
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  // Transform data for charts
  const lowSellersChartData = useMemo(() => {
    if (!lowSellersQuery.data) return [];
    return lowSellersQuery.data.slice(0, 5).map((p) => ({
      name: p.product_name.length > 20 ? p.product_name.substring(0, 20) + "..." : p.product_name,
      value: p.revenue,
      qty: p.qty,
      orders: p.orders,
    }));
  }, [lowSellersQuery.data]);

  const topSellersChartData = useMemo(() => {
    if (!topSellersQuery.data) return [];
    return topSellersQuery.data.map((p) => ({
      name: p.product_name.length > 20 ? p.product_name.substring(0, 20) + "..." : p.product_name,
      value: p.qty,
      revenue: p.revenue,
      orders: p.orders,
    }));
  }, [topSellersQuery.data]);

  const addonsChartData = useMemo(() => {
    if (!addonsQuery.data) return [];
    return addonsQuery.data.slice(0, 5).map((a) => ({
      name: a.item_name.length > 20 ? a.item_name.substring(0, 20) + "..." : a.item_name,
      value: a.revenue,
      qty: a.qty,
      uses: a.uses,
    }));
  }, [addonsQuery.data]);

  // Calculate KPIs
  const kpis = useMemo(() => {
    const totalRevenueLowSellers = lowSellersQuery.data?.reduce((sum, p) => sum + p.revenue, 0) || 0;
    const totalRevenueAddons = addonsQuery.data?.reduce((sum, a) => sum + a.revenue, 0) || 0;
    const skusCount = lowSellersQuery.data?.length || 0;
    
    return {
      totalRevenueLowSellers,
      totalRevenueAddons,
      skusCount,
    };
  }, [lowSellersQuery.data, addonsQuery.data]);

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
          <h1 className="text-3xl font-bold mb-2">Produtos</h1>
          <p className="text-muted-foreground">
            Ranking de produtos, adicionais mais populares e análise de vendas
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
                lowSellersQuery.refetch();
                topSellersQuery.refetch();
                addonsQuery.refetch();
                mostCustomizedQuery.refetch();
                combinationsQuery.refetch();
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KPICard
            title="Receita Total (Produtos)"
            value={kpis.totalRevenueLowSellers}
            format="currency"
            loading={lowSellersQuery.isLoading}
          />
          <KPICard
            title="Receita Total (Adicionais)"
            value={kpis.totalRevenueAddons}
            format="currency"
            loading={addonsQuery.isLoading}
          />
          <KPICard
            title="SKUs Ativos"
            value={kpis.skusCount}
            format="number"
            loading={lowSellersQuery.isLoading}
          />
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
          {lowSellersQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando produtos...</div>
            </Card>
          ) : (
            <BarChartVertical
              data={lowSellersChartData}
              title="Top 5 Produtos Menos Vendidos"
              height={350}
            />
          )}

          {addonsQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando adicionais...</div>
            </Card>
          ) : (
            <BarChartVertical
              data={addonsChartData}
              title="Top 5 Adicionais Mais Populares"
              height={350}
            />
          )}
        </div>

        {/* Top 5 Produtos Mais Vendidos */}
        <div className="mt-6">
          {topSellersQuery.isLoading ? (
            <Card className="p-6 flex items-center justify-center" style={{ height: 350 }}>
              <p className="text-muted-foreground">Carregando dados dos produtos mais vendidos...</p>
            </Card>
          ) : !topSellersQuery.data || topSellersQuery.data.length === 0 ? (
            <Card className="p-6 flex items-center justify-center" style={{ height: 350 }}>
              <p className="text-muted-foreground">Nenhum dado disponível para os produtos mais vendidos.</p>
            </Card>
          ) : (
            <BarChartVertical
              data={topSellersChartData}
              title="Top 5 Produtos Mais Vendidos"
              formatValue={(value) => `${value.toFixed(0)} unidades`}
              height={350}
            />
          )}
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Produtos Menos Vendidos (Completo)</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Produto</th>
                    <th className="pb-3 font-medium text-right">Qtd</th>
                    <th className="pb-3 font-medium text-right">Receita</th>
                    <th className="pb-3 font-medium text-right">Pedidos</th>
                  </tr>
                </thead>
                <tbody>
                  {lowSellersQuery.isLoading ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !lowSellersQuery.data || lowSellersQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Nenhum produto encontrado
                      </td>
                    </tr>
                  ) : (
                    lowSellersQuery.data.map((product) => (
                      <tr key={product.product_id} className="border-b last:border-0">
                        <td className="py-3">{product.product_name}</td>
                        <td className="py-3 text-right">{product.qty.toLocaleString("pt-BR")}</td>
                        <td className="py-3 text-right font-medium">
                          {product.revenue.toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })}
                        </td>
                        <td className="py-3 text-right">{product.orders.toLocaleString("pt-BR")}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Adicionais Mais Populares (Completo)</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Adicional</th>
                    <th className="pb-3 font-medium text-right">Qtd</th>
                    <th className="pb-3 font-medium text-right">Receita</th>
                    <th className="pb-3 font-medium text-right">Usos</th>
                  </tr>
                </thead>
                <tbody>
                  {addonsQuery.isLoading ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !addonsQuery.data || addonsQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">
                        Nenhum adicional encontrado
                      </td>
                    </tr>
                  ) : (
                    addonsQuery.data.map((addon) => (
                      <tr key={addon.item_id} className="border-b last:border-0">
                        <td className="py-3">{addon.item_name}</td>
                        <td className="py-3 text-right">{addon.qty.toLocaleString("pt-BR")}</td>
                        <td className="py-3 text-right font-medium">
                          {addon.revenue.toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })}
                        </td>
                        <td className="py-3 text-right">{addon.uses.toLocaleString("pt-BR")}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Produtos com Mais Customizações</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Produto</th>
                    <th className="pb-3 font-medium text-right">Customizações</th>
                    <th className="pb-3 font-medium text-right">Média/Pedido</th>
                  </tr>
                </thead>
                <tbody>
                  {mostCustomizedQuery.isLoading ? (
                    <tr>
                      <td colSpan={3} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !mostCustomizedQuery.data || mostCustomizedQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="py-8 text-center text-muted-foreground">
                        Nenhum produto encontrado
                      </td>
                    </tr>
                  ) : (
                    mostCustomizedQuery.data.map((product) => (
                      <tr key={product.product_id} className="border-b last:border-0">
                        <td className="py-3">{product.product_name}</td>
                        <td className="py-3 text-right font-semibold">
                          {product.total_customizations.toLocaleString("pt-BR")}
                        </td>
                        <td className="py-3 text-right">
                          {product.avg_customizations_per_order.toFixed(1)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Combinações Mais Comuns</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Combinação</th>
                    <th className="pb-3 font-medium text-right">Vezes Juntos</th>
                  </tr>
                </thead>
                <tbody>
                  {combinationsQuery.isLoading ? (
                    <tr>
                      <td colSpan={2} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !combinationsQuery.data || combinationsQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={2} className="py-8 text-center text-muted-foreground">
                        Nenhuma combinação encontrada
                      </td>
                    </tr>
                  ) : (
                    combinationsQuery.data.map((combo, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="py-3">
                          <div className="flex flex-col">
                            <span className="font-medium">{combo.product1_name}</span>
                            <span className="text-xs text-muted-foreground">+ {combo.product2_name}</span>
                          </div>
                        </td>
                        <td className="py-3 text-right font-semibold">
                          {combo.times_together.toLocaleString("pt-BR")}
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
