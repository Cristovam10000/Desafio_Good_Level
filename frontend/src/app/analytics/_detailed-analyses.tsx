"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";
import {
  fetchTopAdditions,
  fetchTopRemovals,
  fetchDeliveryTimeByRegion,
  fetchPaymentMixByChannel,
  type TopAdditionsResponse,
  type TopRemovalsResponse,
  type DeliveryTimeResponse,
  type PaymentMixResponse,
} from "@/shared/api/analytics";
import { Plus, Minus, Clock, CreditCard } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

interface DetailedAnalysesProps {
  start?: string;
  end?: string;
  storeId?: number;
}

export function DetailedAnalyses({ start, end, storeId }: DetailedAnalysesProps) {
  const additionsQuery = useQuery({
    queryKey: ["analytics", "top-additions", start, end, storeId],
    queryFn: () => fetchTopAdditions({ start, end, store_id: storeId }),
    enabled: !!start && !!end,
  });

  const removalsQuery = useQuery({
    queryKey: ["analytics", "top-removals", start, end, storeId],
    queryFn: () => fetchTopRemovals({ start, end, store_id: storeId }),
    enabled: !!start && !!end,
  });

  const deliveryTimeQuery = useQuery({
    queryKey: ["analytics", "delivery-time", start, end, storeId],
    queryFn: () => fetchDeliveryTimeByRegion({ start, end, store_id: storeId }),
    enabled: !!start && !!end,
  });

  const paymentMixQuery = useQuery({
    queryKey: ["analytics", "payment-mix", start, end, storeId],
    queryFn: () => fetchPaymentMixByChannel({ start, end, store_id: storeId }),
    enabled: !!start && !!end,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Análises Detalhadas da Estrutura de Vendas</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top 5 Itens Adicionais */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-green-600" />
              <CardTitle>Top 5 Itens Adicionais Mais Vendidos</CardTitle>
            </div>
            <CardDescription>
              Extras e complementos que os clientes mais adicionam aos pedidos
            </CardDescription>
          </CardHeader>
          <CardContent>
            {additionsQuery.isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : additionsQuery.error ? (
              <p className="text-sm text-muted-foreground">
                Erro ao carregar dados de adicionais
              </p>
            ) : !additionsQuery.data?.data.length ? (
              <p className="text-sm text-muted-foreground">
                Nenhum adicional encontrado no período
              </p>
            ) : (
              <div className="space-y-3">
                {additionsQuery.data.data.map((item, index) => (
                  <div
                    key={item.item_name}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 text-green-700 font-semibold text-sm">
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium">{item.item_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.quantidade_vendas.toLocaleString("pt-BR")} vendas
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">
                        {item.receita_total.toLocaleString("pt-BR", {
                          style: "currency",
                          currency: "BRL",
                        })}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Média: {item.preco_medio.toLocaleString("pt-BR", {
                          style: "currency",
                          currency: "BRL",
                        })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top 5 Produtos com Menor Venda */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Minus className="h-5 w-5 text-orange-600" />
              <CardTitle>Top 5 Produtos com Menor Venda</CardTitle>
            </div>
            <CardDescription>
              Produtos com menor quantidade de vendas no período
            </CardDescription>
          </CardHeader>
          <CardContent>
            {removalsQuery.isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : removalsQuery.error ? (
              <p className="text-sm text-muted-foreground">
                Erro ao carregar dados de produtos
              </p>
            ) : !removalsQuery.data?.data.length ? (
              <p className="text-sm text-muted-foreground">
                Nenhum produto encontrado no período
              </p>
            ) : (
              <div className="space-y-3">
                {removalsQuery.data.data.map((item, index) => (
                  <div
                    key={item.product_name}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-100 text-orange-700 font-semibold text-sm">
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium">{item.product_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.quantidade_itens.toLocaleString("pt-BR", {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                          })} itens
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-orange-600">
                        {item.quantidade_vendas.toLocaleString("pt-BR")}
                      </p>
                      <p className="text-sm text-muted-foreground">vendas</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tempo de Entrega por Região */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-600" />
              <CardTitle>Tempo Médio de Entrega por Bairro</CardTitle>
            </div>
            <CardDescription>
              Bairros com maior e menor tempo de entrega
            </CardDescription>
          </CardHeader>
          <CardContent>
            {deliveryTimeQuery.isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : deliveryTimeQuery.error ? (
              <p className="text-sm text-muted-foreground">
                Erro ao carregar dados de entrega
              </p>
            ) : !deliveryTimeQuery.data?.data.length ? (
              <p className="text-sm text-muted-foreground">
                Nenhum dado de entrega encontrado no período
              </p>
            ) : (
              <div className="space-y-3">
                {deliveryTimeQuery.data.data.map((item, index) => (
                  <div
                    key={item.regiao}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700 font-semibold text-sm">
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium">{item.regiao}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.total_entregas.toLocaleString("pt-BR")} entregas
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-blue-600">
                        {Math.round(item.tempo_medio_minutos)} min
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {Math.round(item.tempo_minimo)} - {Math.round(item.tempo_maximo)} min
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Mix de Pagamentos por Canal */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-purple-600" />
              <CardTitle>Mix de Pagamentos por Canal</CardTitle>
            </div>
            <CardDescription>
              Formas de pagamento preferidas em cada canal de venda
            </CardDescription>
          </CardHeader>
          <CardContent>
            {paymentMixQuery.isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : paymentMixQuery.error ? (
              <p className="text-sm text-muted-foreground">
                Erro ao carregar dados de pagamento
              </p>
            ) : !paymentMixQuery.data?.data.length ? (
              <p className="text-sm text-muted-foreground">
                Nenhum dado de pagamento encontrado no período
              </p>
            ) : (
              <div className="space-y-4">
                {Object.entries(
                  paymentMixQuery.data.data.reduce((acc, item) => {
                    if (!acc[item.canal]) acc[item.canal] = [];
                    acc[item.canal].push(item);
                    return acc;
                  }, {} as Record<string, typeof paymentMixQuery.data.data>)
                ).map(([canal, pagamentos]) => (
                  <div key={canal} className="space-y-2">
                    <h4 className="font-semibold text-sm text-purple-700">{canal}</h4>
                    <div className="space-y-2">
                      {pagamentos.slice(0, 3).map((item) => (
                        <div
                          key={`${canal}-${item.forma_pagamento}`}
                          className="flex items-center justify-between p-2 rounded bg-muted/30"
                        >
                          <div className="flex-1">
                            <p className="text-sm font-medium">{item.forma_pagamento}</p>
                            <div className="w-full bg-muted rounded-full h-2 mt-1">
                              <div
                                className="bg-purple-600 h-2 rounded-full transition-all"
                                style={{ width: `${item.percentual}%` }}
                              />
                            </div>
                          </div>
                          <div className="ml-4 text-right">
                            <p className="text-sm font-semibold">{item.percentual}%</p>
                            <p className="text-xs text-muted-foreground">
                              {item.quantidade_vendas} vendas
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
