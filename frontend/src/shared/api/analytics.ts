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
