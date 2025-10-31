export type SalesDailyPoint = {
  bucket_day: string;
  orders: number | null;
  revenue: number | null;
  items_value?: number | null;
  discounts?: number | null;
  avg_ticket?: number | null;
};

export type SalesHourPoint = {
  bucket_hour: string;
  store_id?: number | null;
  channel_id?: number | null;
  orders?: number | null;
  revenue?: number | null;
  amount_items?: number | null;
  discounts?: number | null;
  service_tax_fee?: number | null;
  avg_ticket?: number | null;
};

export type DeliveryPerformanceRow = {
  bucket_day: string;
  city: string;
  neighborhood: string;
  deliveries: number;
  avg_delivery_minutes: number;
  p90_delivery_minutes: number;
};
