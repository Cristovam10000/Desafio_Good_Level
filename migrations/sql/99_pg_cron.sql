-- Habilita pg_cron
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Dica: por padrão o pg_cron executa no mesmo DB em que você rodar o comando.
-- Aqui vamos presumir que estamos conectados na challenge_db.

-- REMOÇÃO de jobs antigos com mesmo nome (idempotência)
SELECT cron.unschedule('mv_sales_hour_refresh')  WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname='mv_sales_hour_refresh');
SELECT cron.unschedule('mv_product_day_refresh') WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname='mv_product_day_refresh');
SELECT cron.unschedule('mv_delivery_p90_refresh') WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname='mv_delivery_p90_refresh');

-- Agendamentos (crontab):
-- "*/5 * * * *"   = a cada 5 minutos
-- "*/10 * * * *"  = a cada 10 minutos
-- "15 * * * *"    = minuto 15 de toda hora (1x/h)

-- Sales por hora: atualiza frequentemente
SELECT cron.schedule(
  'mv_sales_hour_refresh',
  '*/5 * * * *',
  $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_hour$$
);

-- Product por dia: a cada 10 min é suficiente
SELECT cron.schedule(
  'mv_product_day_refresh',
  '*/10 * * * *',
  $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_day$$
);

-- Delivery p90: 1x por hora (custo maior)
SELECT cron.schedule(
  'mv_delivery_p90_refresh',
  '15 * * * *',
  $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_delivery_p90$$
);
