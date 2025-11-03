import { z } from "zod";
import { SalesHourPointSchema, DeliveryPerformanceRowSchema } from "@/entities/metrics/schemas";
import { ProductRankingRowSchema } from "@/entities/products/schemas";
import { http } from "./http";

const SalesHourResponseSchema = z.array(SalesHourPointSchema);
const TopProductsResponseSchema = z.array(
  ProductRankingRowSchema.pick({
    product_id: true,
    product_name: true,
    qty: true,
  })
);
const ProductTopResponseSchema = z.array(ProductRankingRowSchema);
const DeliveryP90ResponseSchema = z.array(DeliveryPerformanceRowSchema);
const ChannelsResponseSchema = z.array(
  z.object({
    channel_id: z.number(),
    channel_name: z.string(),
    store_id: z.number(),
    store_name: z.string(),
    channel_store_key: z.string(),
    description: z.string().nullable().optional(),
    type: z.string().nullable().optional(),
  })
);

const DataRangeResponseSchema = z.object({
  ok: z.boolean(),
  start_date: z.string(),
  end_date: z.string(),
});

const StoresResponseSchema = z.array(
  z.object({
    id: z.number(),
    name: z.string(),
    city: z.string().nullable().optional(),
    state: z.string().nullable().optional(),
    is_active: z.boolean(),
  })
);

export type SalesHourPoint = z.infer<typeof SalesHourPointSchema>;
export type TopProductRow = z.infer<typeof TopProductsResponseSchema>[number];
export type ProductTopRow = z.infer<typeof ProductTopResponseSchema>[number];
export type DeliveryP90Row = z.infer<typeof DeliveryP90ResponseSchema>[number];
export type ChannelRow = z.infer<typeof ChannelsResponseSchema>[number];
export type DataRangeResponse = z.infer<typeof DataRangeResponseSchema>;
export type StoreRow = z.infer<typeof StoresResponseSchema>[number];

export async function fetchSalesHour(params?: Record<string, unknown>) {
  const response = await http.get("/utils/sales-hour", { params });
  return SalesHourResponseSchema.parse(response.data);
}

export async function fetchTopProducts(params?: Record<string, unknown>) {
  const response = await http.get("/utils/top-products", { params });
  return TopProductsResponseSchema.parse(response.data);
}

export async function fetchProductTop(params?: Record<string, unknown>) {
  const response = await http.get("/utils/product-top", { params });
  return ProductTopResponseSchema.parse(response.data);
}

export async function fetchDeliveryP90(params?: Record<string, unknown>) {
  const response = await http.get("/utils/delivery-p90", { params });
  return DeliveryP90ResponseSchema.parse(response.data);
}

export async function fetchChannels() {
  const response = await http.get("/channels");
  return ChannelsResponseSchema.parse(response.data);
}

export async function fetchDataRange() {
  const response = await http.get("/utils/data-range");
  return DataRangeResponseSchema.parse(response.data);
}

export async function fetchStores() {
  const response = await http.get("/stores");
  return StoresResponseSchema.parse(response.data);
}
