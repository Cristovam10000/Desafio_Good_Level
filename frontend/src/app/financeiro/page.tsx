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
import { fetchPaymentsMix, fetchNetVsGross, fetchChannels, fetchSectionInsights } from "@/shared/api/sections";
import { KPICard } from "@/widgets/dashboard/KPICard";
import ParticipationChart from "@/widgets/dashboard/ParticipationChart";
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

export default function FinanceiroPage() {
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

  // Fetch payments mix
  const paymentsMixQuery = useQuery({
    queryKey: ["finance", "payments-mix", displayRange, channelOption],
    queryFn: () =>
      fetchPaymentsMix({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch net vs gross
  const netVsGrossQuery = useQuery({
    queryKey: ["finance", "net-vs-gross", displayRange, channelOption],
    queryFn: () =>
      fetchNetVsGross({
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
  });

  // Fetch insights
  const insightsQuery = useQuery({
    queryKey: ["insights", "financeiro", displayRange, channelOption],
    queryFn: () =>
      fetchSectionInsights("financeiro", {
        start: displayRange.start,
        end: displayRange.end,
        ...(channelOption ? { channel_id: channelOption } : {}),
      }),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  // Transform data for pie chart - aggregate by payment_type
  const paymentsChartData = useMemo(() => {
    if (!paymentsMixQuery.data) return [];
    
    // Aggregate multiple channels of same payment type
    const aggregated = new Map<string, number>();
    paymentsMixQuery.data.forEach((p) => {
      const current = aggregated.get(p.payment_type) || 0;
      aggregated.set(p.payment_type, current + p.revenue);
    });
    
    return Array.from(aggregated.entries()).map(([name, value]) => ({
      name,
      value,
    }));
  }, [paymentsMixQuery.data]);

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
          <h1 className="text-3xl font-bold mb-2">Financeiro</h1>
          <p className="text-muted-foreground">
            Receita líquida vs bruta, descontos, taxas e mix de pagamentos
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
                paymentsMixQuery.refetch();
                netVsGrossQuery.refetch();
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
            title="Receita Bruta"
            value={netVsGrossQuery.data?.gross_revenue || 0}
            format="currency"
            loading={netVsGrossQuery.isLoading}
          />
          <KPICard
            title="Descontos"
            value={netVsGrossQuery.data?.total_discounts || 0}
            format="currency"
            loading={netVsGrossQuery.isLoading}
          />
          <KPICard
            title="Taxas"
            value={(netVsGrossQuery.data?.service_fees || 0) + (netVsGrossQuery.data?.delivery_fees || 0)}
            format="currency"
            loading={netVsGrossQuery.isLoading}
          />
          <KPICard
            title="Receita Líquida"
            value={netVsGrossQuery.data?.net_revenue || 0}
            format="currency"
            loading={netVsGrossQuery.isLoading}
          />
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
          {paymentsMixQuery.isLoading ? (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">Carregando mix de pagamentos...</div>
            </Card>
          ) : (
            <ParticipationChart
              data={paymentsChartData}
              title="Mix de Pagamentos"
              height={350}
            />
          )}

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Receita Líquida vs Bruta</h3>
            {netVsGrossQuery.isLoading ? (
              <div className="text-center text-muted-foreground py-8">Carregando...</div>
            ) : netVsGrossQuery.data ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center py-3 border-b">
                  <span className="text-muted-foreground">Receita Bruta</span>
                  <span className="text-lg font-bold">
                    {netVsGrossQuery.data.gross_revenue.toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-b">
                  <span className="text-muted-foreground">(-) Descontos</span>
                  <span className="text-red-600">
                    -{netVsGrossQuery.data.total_discounts.toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-b">
                  <span className="text-muted-foreground">(-) Taxas de Serviço</span>
                  <span className="text-red-600">
                    -{netVsGrossQuery.data.service_fees.toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-b">
                  <span className="text-muted-foreground">(-) Taxas de Entrega</span>
                  <span className="text-red-600">
                    -{netVsGrossQuery.data.delivery_fees.toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 bg-muted/50 px-4 rounded-lg">
                  <span className="font-semibold">Receita Líquida</span>
                  <span className="text-xl font-bold text-green-600">
                    {netVsGrossQuery.data.net_revenue.toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    })}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-muted-foreground">% Desconto</span>
                  <span className="text-sm">
                    {netVsGrossQuery.data.discount_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                Nenhum dado disponível
              </div>
            )}
          </Card>
        </div>

        <div className="mt-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Detalhamento por Tipo de Pagamento</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-medium">Tipo de Pagamento</th>
                    <th className="pb-3 font-medium">Canal</th>
                    <th className="pb-3 font-medium text-right">Receita</th>
                    <th className="pb-3 font-medium text-right">Transações</th>
                    <th className="pb-3 font-medium text-right">% Participação</th>
                  </tr>
                </thead>
                <tbody>
                  {paymentsMixQuery.isLoading ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground">
                        Carregando...
                      </td>
                    </tr>
                  ) : !paymentsMixQuery.data || paymentsMixQuery.data.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground">
                        Nenhum dado encontrado
                      </td>
                    </tr>
                  ) : (
                    paymentsMixQuery.data.map((payment, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="py-3">{payment.payment_type}</td>
                        <td className="py-3 text-muted-foreground">{payment.channel_name || "-"}</td>
                        <td className="py-3 text-right font-medium">
                          {payment.revenue.toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })}
                        </td>
                        <td className="py-3 text-right">{payment.transactions.toLocaleString("pt-BR")}</td>
                        <td className="py-3 text-right">{payment.pct.toFixed(1)}%</td>
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
