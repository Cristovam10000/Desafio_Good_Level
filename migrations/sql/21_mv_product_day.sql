DROP MATERIALIZED VIEW IF EXISTS mv_product_day CASCADE;

CREATE MATERIALIZED VIEW mv_product_day AS
SELECT
  date_trunc('day', s.created_at)::date           AS bucket_day,
  ps.product_id,
  p.name                                          AS product_name,
  SUM(ps.quantity)::float                         AS qty,
  SUM(ps.total_price)::numeric(18,2)              AS revenue,
  COUNT(DISTINCT s.id)                            AS orders
FROM product_sales ps
JOIN sales s    ON s.id = ps.sale_id
JOIN products p ON p.id = ps.product_id
WHERE s.sale_status_desc = 'COMPLETED'
GROUP BY 1,2,3;

-- Indíce ÚNICO: exige chave única para refresh concorrente
CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_product_day
  ON mv_product_day (bucket_day, product_id);

-- Apoio
CREATE INDEX IF NOT EXISTS idx_mv_product_day_product_name
  ON mv_product_day (product_name);
CREATE INDEX IF NOT EXISTS idx_mv_product_day_bucket
  ON mv_product_day (bucket_day);
