import { z } from "zod";

export const SalesDailyPointSchema = z.object({
  bucket_day: z.string(),
  orders: z.number().nullable().optional(),
  revenue: z.number().nullable().optional(),
  items_value: z.number().nullable().optional(),
  discounts: z.number().nullable().optional(),
  avg_ticket: z.number().nullable().optional(),
});

export const SalesHourPointSchema = z.object({
  bucket_hour: z.string(),
  store_id: z.number().nullable().optional(),
  channel_id: z.number().nullable().optional(),
  orders: z.number().nullable().optional(),
  revenue: z.number().nullable().optional(),
  amount_items: z.number().nullable().optional(),
  discounts: z.number().nullable().optional(),
  service_tax_fee: z.number().nullable().optional(),
  avg_ticket: z.number().nullable().optional(),
});

export const DeliveryPerformanceRowSchema = z.object({
  bucket_day: z.string(),
  city: z.string(),
  neighborhood: z.string(),
  deliveries: z.number(),
  avg_delivery_minutes: z.number(),
  p90_delivery_minutes: z.number(),
});
