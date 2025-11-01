-- ============================================================================
-- ÍNDICES BRIN (Block Range Index) para colunas temporais
-- ============================================================================
-- BRIN é ideal para tabelas MUITO grandes com correlação física/temporal
-- (dados ordenados no disco). Ocupa ~1000x menos espaço que B-tree e
-- acelera scans em faixas de tempo.
--
-- Ref: https://www.postgresql.org/docs/current/brin-intro.html
-- ============================================================================

-- Sales: created_at é naturalmente ordenado (timestamp de inserção)
-- Com 1M+ registros, BRIN reduz drasticamente o custo de range scans
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_created_at_brin
  ON sales USING BRIN (created_at)
  WITH (pages_per_range = 128);

-- Sales: sale_date também pode se beneficiar se houver muitas consultas por dia
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_sale_date_brin
  ON sales USING BRIN (sale_date)
  WITH (pages_per_range = 128);

-- ============================================================================
-- Notas:
-- - pages_per_range=128 é um bom padrão (16KB*128 = 2MB por range)
-- - BRIN funciona melhor quando dados estão fisicamente ordenados
-- - Se a tabela for frequentemente reordenada (DELETE/UPDATE), considere
--   usar CLUSTER ou REINDEX CONCURRENTLY periodicamente
-- ============================================================================
