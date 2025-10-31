import { z } from "zod";

export const ProductRankingRowSchema = z.object({
  product_id: z.number(),
  product_name: z.string(),
  qty: z.number(),
  revenue: z.number().optional(),
  orders: z.number().optional(),
});
