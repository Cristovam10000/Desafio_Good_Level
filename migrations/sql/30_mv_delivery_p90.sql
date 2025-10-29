DROP MATERIALIZED VIEW IF EXISTS mv_delivery_p90 CASCADE;

CREATE MATERIALIZED VIEW mv_delivery_p90 AS
SELECT
  date_trunc('day', s.created_at)::date AS bucket_day,
  da.city,
  da.neighborhood,
  COUNT(*)                              AS deliveries,
  AVG(s.delivery_seconds)::float / 60.0 AS avg_delivery_minutes,
  PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds)::float / 60.0 AS p90_delivery_minutes
FROM sales s
JOIN delivery_addresses da ON da.sale_id = s.id
WHERE
  s.sale_status_desc = 'COMPLETED'
  AND s.delivery_seconds IS NOT NULL
GROUP BY 1,2,3;

-- ÚNICO para refresh concorrente
CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_delivery_p90
  ON mv_delivery_p90 (bucket_day, city, neighborhood);

-- Apoio
CREATE INDEX IF NOT EXISTS idx_mv_delivery_p90_bucket
  ON mv_delivery_p90 (bucket_day);
CREATE INDEX IF NOT EXISTS idx_mv_delivery_p90_geo
  ON mv_delivery_p90 (city, neighborhood);
