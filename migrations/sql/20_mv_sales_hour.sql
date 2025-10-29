DROP MATERIALIZED VIEW IF EXISTS mv_sales_hour CASCADE;

CREATE MATERIALIZED VIEW mv_sales_hour AS
SELECT
  date_trunc('hour', s.created_at)::timestamp      AS bucket_hour,    -- eixo X
  s.store_id,
  s.channel_id,
  COUNT(*) FILTER (WHERE s.sale_status_desc = 'COMPLETED')          AS orders,
  SUM(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN s.total_amount ELSE 0 END)          AS revenue,
  SUM(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN s.total_amount_items ELSE 0 END)    AS amount_items,
  SUM(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN s.total_discount ELSE 0 END)        AS discounts,
  SUM(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN s.service_tax_fee ELSE 0 END)       AS service_tax_fee
FROM sales s
GROUP BY 1,2,3;

-- Indíce ÚNICO (requisito para REFRESH CONCURRENTLY)
CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_sales_hour
  ON mv_sales_hour (bucket_hour, store_id, channel_id);

-- Índices de apoio para filtros comuns
CREATE INDEX IF NOT EXISTS idx_mv_sales_hour_bucket
  ON mv_sales_hour (bucket_hour);
CREATE INDEX IF NOT EXISTS idx_mv_sales_hour_store
  ON mv_sales_hour (store_id);
CREATE INDEX IF NOT EXISTS idx_mv_sales_hour_channel
  ON mv_sales_hour (channel_id);
