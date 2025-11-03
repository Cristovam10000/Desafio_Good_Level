/**
 * API functions for new section-based endpoints
 * Organized by: Lojas, Vendas, Produtos, Entregas, Financeiro, Operações
 */

import { z } from "zod";
import { http } from "./http";

// =============================================================================
// LOJAS
// =============================================================================

const StorePerformanceRowSchema = z.object({
  store_id: z.number(),
  store_name: z.string(),
  city: z.string().nullable().optional(),
  state: z.string().nullable().optional(),
  revenue: z.number(),
  orders: z.number(),
  avg_ticket: z.number(),
  cancelled: z.number(),
  cancellation_rate: z.number(),
  growth_pct: z.number().nullable().optional(),
});

const StoreTimeseriesRowSchema = z.object({
  bucket_day: z.string(),
  revenue: z.number(),
  orders: z.number(),
});

export type StorePerformanceRow = z.infer<typeof StorePerformanceRowSchema>;
export type StoreTimeseriesRow = z.infer<typeof StoreTimeseriesRowSchema>;

export async function fetchStoresTop(params?: Record<string, unknown>) {
  const response = await http.get("/stores/performance", { params });
  return z.array(StorePerformanceRowSchema).parse(response.data);
}

export async function fetchStoreTimeseries(params: Record<string, unknown>) {
  const response = await http.get("/stores/timeseries", { params });
  return z.array(StoreTimeseriesRowSchema).parse(response.data);
}

// =============================================================================
// VENDAS
// =============================================================================

const SalesSummarySchema = z.object({
  revenue: z.number(),
  orders: z.number(),
  avg_ticket: z.number(),
  discount_pct: z.number(),
});

const SalesByChannelRowSchema = z.object({
  channel_id: z.number(),
  channel_name: z.string(),
  revenue: z.number(),
  orders: z.number(),
  pct: z.number(),
});

export type SalesSummary = z.infer<typeof SalesSummarySchema>;
export type SalesByChannelRow = z.infer<typeof SalesByChannelRowSchema>;

export async function fetchSalesSummary(params?: Record<string, unknown>) {
  const response = await http.get("/sales/summary", { params });
  return SalesSummarySchema.parse(response.data);
}

export async function fetchSalesByChannel(params?: Record<string, unknown>) {
  const response = await http.get("/sales/by-channel", { params });
  return z.array(SalesByChannelRowSchema).parse(response.data);
}

const SalesByDayRowSchema = z.object({
  bucket_day: z.string(),
  revenue: z.number(),
  orders: z.number(),
  avg_ticket: z.number(),
});

const SalesByWeekdayRowSchema = z.object({
  weekday: z.number(),
  weekday_name: z.string(),
  revenue: z.number(),
  orders: z.number(),
  avg_ticket: z.number(),
});

export type SalesByDayRow = z.infer<typeof SalesByDayRowSchema>;
export type SalesByWeekdayRow = z.infer<typeof SalesByWeekdayRowSchema>;

export async function fetchSalesByDay(params?: Record<string, unknown>) {
  const response = await http.get("/sales/by-day", { params });
  return z.array(SalesByDayRowSchema).parse(response.data);
}

export async function fetchSalesByWeekday(params?: Record<string, unknown>) {
  const response = await http.get("/sales/by-weekday", { params });
  return z.array(SalesByWeekdayRowSchema).parse(response.data);
}

const DiscountReasonRowSchema = z.object({
  discount_reason: z.string(),
  occurrences: z.number(),
  total_discount_value: z.number(),
  avg_discount: z.number(),
});

export type DiscountReasonRow = z.infer<typeof DiscountReasonRowSchema>;

export async function fetchDiscountReasons(params?: Record<string, unknown>) {
  const response = await http.get("/sales/discount-reasons", { params });
  return z.array(DiscountReasonRowSchema).parse(response.data);
}

// =============================================================================
// PRODUTOS
// =============================================================================

const ProductLowSellersRowSchema = z.object({
  product_id: z.number(),
  product_name: z.string(),
  qty: z.number(),
  revenue: z.number(),
  orders: z.number(),
});

const ProductAddonsRowSchema = z.object({
  item_id: z.number(),
  item_name: z.string(),
  qty: z.number(),
  revenue: z.number(),
  uses: z.number(),
});

export type ProductLowSellersRow = z.infer<typeof ProductLowSellersRowSchema>;
export type ProductAddonsRow = z.infer<typeof ProductAddonsRowSchema>;

export async function fetchProductsLowSellers(params?: Record<string, unknown>) {
  const response = await http.get("/products/low-sellers", { params });
  return z.array(ProductLowSellersRowSchema).parse(response.data);
}

const ProductTopSellersRowSchema = z.object({
  product_id: z.number(),
  product_name: z.string(),
  qty: z.number(),
  revenue: z.number(),
  orders: z.number(),
});

export type ProductTopSellersRow = z.infer<typeof ProductTopSellersRowSchema>;

export async function fetchProductsTopSellers(params?: Record<string, unknown>) {
  const response = await http.get("/products/top-sellers", { params });
  return z.array(ProductTopSellersRowSchema).parse(response.data);
}

export async function fetchProductsAddonsTop(params?: Record<string, unknown>) {
  const response = await http.get("/products/addons/top", { params });
  return z.array(ProductAddonsRowSchema).parse(response.data);
}

const ProductWithMostCustomizationsRowSchema = z.object({
  product_id: z.number(),
  product_name: z.string(),
  total_customizations: z.number(),
  orders: z.number(),
  avg_customizations_per_order: z.number(),
});

const ProductCombinationRowSchema = z.object({
  product1_id: z.number(),
  product1_name: z.string(),
  product2_id: z.number(),
  product2_name: z.string(),
  times_together: z.number(),
});

export type ProductWithMostCustomizationsRow = z.infer<typeof ProductWithMostCustomizationsRowSchema>;
export type ProductCombinationRow = z.infer<typeof ProductCombinationRowSchema>;

export async function fetchProductsMostCustomized(params?: Record<string, unknown>) {
  const response = await http.get("/products/most-customized", { params });
  return z.array(ProductWithMostCustomizationsRowSchema).parse(response.data);
}

export async function fetchProductCombinations(params?: Record<string, unknown>) {
  const response = await http.get("/products/combinations", { params });
  return z.array(ProductCombinationRowSchema).parse(response.data);
}

// =============================================================================
// ENTREGAS
// =============================================================================

const DeliveryRegionsRowSchema = z.object({
  city: z.string(),
  neighborhood: z.string(),
  deliveries: z.number(),
  avg_minutes: z.number(),
  p90_minutes: z.number(),
});

const DeliveryPercentilesSchema = z.object({
  avg_minutes: z.number(),
  p50_minutes: z.number(),
  p90_minutes: z.number(),
  p95_minutes: z.number(),
  within_sla_pct: z.number(),
});

export type DeliveryRegionsRow = z.infer<typeof DeliveryRegionsRowSchema>;
export type DeliveryPercentiles = z.infer<typeof DeliveryPercentilesSchema>;

export async function fetchDeliveryRegions(params?: Record<string, unknown>) {
  const response = await http.get("/delivery/regions", { params });
  return z.array(DeliveryRegionsRowSchema).parse(response.data);
}

export async function fetchDeliveryPercentiles(params?: Record<string, unknown>) {
  const response = await http.get("/delivery/percentiles", { params });
  return DeliveryPercentilesSchema.parse(response.data);
}

const DeliveryStatsSchema = z.object({
  total_deliveries: z.number(),
  fastest_minutes: z.number(),
  slowest_minutes: z.number(),
  avg_minutes: z.number(),
});

const DeliveryCityRankRowSchema = z.object({
  city: z.string(),
  deliveries: z.number(),
  avg_minutes: z.number(),
  p90_minutes: z.number(),
});

const DeliveryStoreRankRowSchema = z.object({
  store_id: z.number(),
  store_name: z.string(),
  deliveries: z.number(),
  avg_minutes: z.number(),
  p90_minutes: z.number(),
});

export type DeliveryStats = z.infer<typeof DeliveryStatsSchema>;
export type DeliveryCityRankRow = z.infer<typeof DeliveryCityRankRowSchema>;
export type DeliveryStoreRankRow = z.infer<typeof DeliveryStoreRankRowSchema>;

export async function fetchDeliveryStats(params?: Record<string, unknown>) {
  const response = await http.get("/delivery/stats", { params });
  return DeliveryStatsSchema.parse(response.data);
}

export async function fetchDeliveryCitiesRank(params?: Record<string, unknown>) {
  const response = await http.get("/delivery/cities-rank", { params });
  return z.array(DeliveryCityRankRowSchema).parse(response.data);
}

export async function fetchDeliveryStoresRank(params?: Record<string, unknown>) {
  const response = await http.get("/delivery/stores-rank", { params });
  return z.array(DeliveryStoreRankRowSchema).parse(response.data);
}

// =============================================================================
// FINANCEIRO / PAGAMENTOS
// =============================================================================

const PaymentMixRowSchema = z.object({
  payment_type: z.string(),
  channel_name: z.string(),
  revenue: z.number(),
  transactions: z.number(),
  pct: z.number(),
});

const NetVsGrossSchema = z.object({
  gross_revenue: z.number(),
  total_discounts: z.number(),
  service_fees: z.number(),
  delivery_fees: z.number(),
  net_revenue: z.number(),
  discount_pct: z.number(),
});

export type PaymentMixRow = z.infer<typeof PaymentMixRowSchema>;
export type NetVsGross = z.infer<typeof NetVsGrossSchema>;

export async function fetchPaymentsMix(params?: Record<string, unknown>) {
  const response = await http.get("/finance/payments-mix", { params });
  return z.array(PaymentMixRowSchema).parse(response.data);
}

export async function fetchNetVsGross(params?: Record<string, unknown>) {
  const response = await http.get("/finance/net-vs-gross", { params });
  return NetVsGrossSchema.parse(response.data);
}

// =============================================================================
// OPERAÇÕES
// =============================================================================

const PrepTimeRowSchema = z.object({
  store_id: z.number(),
  store_name: z.string(),
  avg_prep_minutes: z.number(),
  p90_prep_minutes: z.number(),
  orders: z.number(),
  cancelled: z.number(),
  cancellation_rate: z.number(),
});

const CancellationsRowSchema = z.object({
  bucket_day: z.string(),
  canceled: z.number(),
  total: z.number(),
  cancellation_rate: z.number(),
});

export type PrepTimeRow = z.infer<typeof PrepTimeRowSchema>;
export type CancellationsRow = z.infer<typeof CancellationsRowSchema>;

export async function fetchPrepTime(params?: Record<string, unknown>) {
  const response = await http.get("/ops/prep-time", { params });
  return z.array(PrepTimeRowSchema).parse(response.data);
}

export async function fetchCancellations(params?: Record<string, unknown>) {
  const response = await http.get("/ops/cancellations", { params });
  return z.array(CancellationsRowSchema).parse(response.data);
}

// =============================================================================
// METADATA (Channels, Stores, etc.)
// =============================================================================

const ChannelRowSchema = z.object({
  channel_id: z.number(),
  channel_name: z.string(),
  channel_type: z.string().optional(), // 'P' = Presencial, 'D' = Delivery
  store_id: z.number().nullable().optional(),
  store_name: z.string().nullable().optional(),
  channel_store_key: z.string(),
});

export type ChannelRow = z.infer<typeof ChannelRowSchema>;

export async function fetchChannels() {
  const response = await http.get("/channels");
  return z.array(ChannelRowSchema).parse(response.data);
}

// =============================================================================
// AI INSIGHTS
// =============================================================================

const ImprovementSchema = z.object({
  title: z.string(),
  description: z.string(),
  priority: z.enum(["high", "medium", "low"]),
  impact: z.string(),
});

const AttentionPointSchema = z.object({
  title: z.string(),
  description: z.string(),
  severity: z.enum(["critical", "warning", "info"]),
});

const SectionInsightsSchema = z.object({
  summary: z.string(),
  improvements: z.array(ImprovementSchema),
  attention_points: z.array(AttentionPointSchema),
  recommendations: z.array(z.string()),
  error: z.string().optional(),
  raw_response: z.string().optional(),
});

export type Improvement = z.infer<typeof ImprovementSchema>;
export type AttentionPoint = z.infer<typeof AttentionPointSchema>;
export type SectionInsights = z.infer<typeof SectionInsightsSchema>;

export async function fetchSectionInsights(
  section: "entregas" | "vendas" | "operacoes" | "produtos" | "lojas" | "financeiro",
  params?: Record<string, unknown>
) {
  const response = await http.post(`/specials/insights/${section}`, null, { params });
  return SectionInsightsSchema.parse(response.data);
}

// =============================================================================
// ANOMALY DETECTION
// =============================================================================

const KnownAnomalySchema = z.object({
  type: z.enum(["sales_drop", "promotional_spike", "store_growth", "seasonal_product"]),
  title: z.string(),
  description: z.string(),
  detected: z.boolean(),
  confidence: z.number(),
  data_points: z.array(z.string()),
  impact: z.enum(["high", "medium", "low"]),
  recommendation: z.string(),
});

const OtherAnomalySchema = z.object({
  type: z.string(),
  title: z.string(),
  description: z.string(),
  confidence: z.number(),
  severity: z.enum(["critical", "warning", "info"]),
  affected_areas: z.array(z.string()),
  recommendation: z.string(),
});

const PatternSchema = z.object({
  type: z.string(),
  description: z.string(),
  frequency: z.enum(["daily", "weekly", "monthly", "seasonal"]),
  strength: z.enum(["strong", "moderate", "weak"]),
});

const AnomaliesResponseSchema = z.object({
  summary: z.string(),
  known_anomalies: z.array(KnownAnomalySchema),
  other_anomalies: z.array(OtherAnomalySchema),
  patterns: z.array(PatternSchema),
  insights: z.array(z.string()),
  error: z.string().optional(),
  raw_response: z.string().optional(),
});

export type KnownAnomaly = z.infer<typeof KnownAnomalySchema>;
export type OtherAnomaly = z.infer<typeof OtherAnomalySchema>;
export type Pattern = z.infer<typeof PatternSchema>;
export type AnomaliesResponse = z.infer<typeof AnomaliesResponseSchema>;

export async function fetchAnomalies(params?: Record<string, unknown>) {
  const response = await http.post("/specials/anomalies", null, { params });
  return AnomaliesResponseSchema.parse(response.data);
}

