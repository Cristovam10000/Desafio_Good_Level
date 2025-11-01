import { z } from "zod";
import { SalesDailyPointSchema } from "@/entities/metrics/schemas";
import { DeliveryPerformanceRowSchema } from "@/entities/metrics/schemas";
import { ProductRankingRowSchema } from "@/entities/products/schemas";
import { http } from "./http";

const AnalyticsFiltersSchema = z.object({
  store_ids: z.array(z.number()).nullable().optional(),
  channel_id: z.number().nullable().optional(),
  city: z.string().nullable().optional(),
});

const InsightsPreviewSchema = z.object({
  sales_daily: z.array(SalesDailyPointSchema),
  top_products: z.array(ProductRankingRowSchema),
  delivery_stats: z.array(DeliveryPerformanceRowSchema),
});

const AnalyticsInsightsResponseSchema = z.object({
  ok: z.boolean(),
  period: z.object({
    start: z.string(),
    end: z.string(),
  }),
  filters: AnalyticsFiltersSchema,
  preview: InsightsPreviewSchema,
  insights: z.array(z.string()),
  raw_text: z.string().nullable(),
  insights_error: z.string().optional(),
});

export type AnalyticsInsightsResponse = z.infer<typeof AnalyticsInsightsResponseSchema>;

export async function fetchInsights(params: {
  start?: string;
  end?: string;
  store_id?: number;
  channel_id?: number;
  channel_ids?: string;
  city?: string;
}): Promise<AnalyticsInsightsResponse> {
  const response = await http.get("/analytics/insights", { params });
  return AnalyticsInsightsResponseSchema.parse(response.data);
}

const AnomalyResultsSchema = z.object({
  queda_semanal: z.string(),
  pico_promocional: z.string(),
  crescimento_linear: z.string(),
  sazonalidade: z.string(),
});

const AnomaliesResponseSchema = z.object({
  ok: z.boolean(),
  anomalies_found: z.number(),
  results: AnomalyResultsSchema,
  raw_response: z.string().nullable(),
  period: z.object({
    start: z.string(),
    end: z.string(),
  }),
  error: z.string().optional(),
});

export type AnomaliesResponse = z.infer<typeof AnomaliesResponseSchema>;

export async function fetchAnomalies(params: {
  start?: string;
  end?: string;
  store_id?: number;
  channel_ids?: string;
}): Promise<AnomaliesResponse> {
  const response = await http.get("/analytics/anomalies", { params });
  return AnomaliesResponseSchema.parse(response.data);
}

// -----------------------------------------------------------------------------
// Análises Detalhadas
// -----------------------------------------------------------------------------

const TopAdditionSchema = z.object({
  item_name: z.string(),
  quantidade_vendas: z.number(),
  receita_total: z.number(),
  preco_medio: z.number(),
});

const TopAdditionsResponseSchema = z.object({
  ok: z.boolean(),
  data: z.array(TopAdditionSchema),
  period: z.object({
    start: z.string(),
    end: z.string(),
  }),
});

export type TopAdditionsResponse = z.infer<typeof TopAdditionsResponseSchema>;

export async function fetchTopAdditions(params: {
  start?: string;
  end?: string;
  store_id?: number;
}): Promise<TopAdditionsResponse> {
  const response = await http.get("/analytics/top-additions", { params });
  return TopAdditionsResponseSchema.parse(response.data);
}

const TopRemovalSchema = z.object({
  product_name: z.string(),
  quantidade_vendas: z.number(),
  quantidade_itens: z.number(),
});

const TopRemovalsResponseSchema = z.object({
  ok: z.boolean(),
  data: z.array(TopRemovalSchema),
  period: z.object({
    start: z.string(),
    end: z.string(),
  }),
});

export type TopRemovalsResponse = z.infer<typeof TopRemovalsResponseSchema>;

export async function fetchTopRemovals(params: {
  start?: string;
  end?: string;
  store_id?: number;
}): Promise<TopRemovalsResponse> {
  const response = await http.get("/analytics/top-removals", { params });
  return TopRemovalsResponseSchema.parse(response.data);
}

const DeliveryTimeRegionSchema = z.object({
  regiao: z.string(),
  tempo_medio_minutos: z.number(),
  total_entregas: z.number(),
  tempo_minimo: z.number(),
  tempo_maximo: z.number(),
});

const DeliveryTimeResponseSchema = z.object({
  ok: z.boolean(),
  data: z.array(DeliveryTimeRegionSchema),
  period: z.object({
    start: z.string(),
    end: z.string(),
  }),
});

export type DeliveryTimeResponse = z.infer<typeof DeliveryTimeResponseSchema>;

export async function fetchDeliveryTimeByRegion(params: {
  start?: string;
  end?: string;
  store_id?: number;
}): Promise<DeliveryTimeResponse> {
  const response = await http.get("/analytics/delivery-time-by-region", { params });
  return DeliveryTimeResponseSchema.parse(response.data);
}

const PaymentMixSchema = z.object({
  canal: z.string(),
  forma_pagamento: z.string(),
  quantidade_vendas: z.number(),
  valor_total: z.number(),
  percentual: z.number(),
});

const PaymentMixResponseSchema = z.object({
  ok: z.boolean(),
  data: z.array(PaymentMixSchema),
  period: z.object({
    start: z.string(),
    end: z.string(),
  }),
});

export type PaymentMixResponse = z.infer<typeof PaymentMixResponseSchema>;

export async function fetchPaymentMixByChannel(params: {
  start?: string;
  end?: string;
  store_id?: number;
}): Promise<PaymentMixResponse> {
  const response = await http.get("/analytics/payment-mix-by-channel", { params });
  return PaymentMixResponseSchema.parse(response.data);
}
