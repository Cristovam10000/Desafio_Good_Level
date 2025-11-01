
-- Base: sales
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_status_date
  ON sales (sale_status_desc, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_store_channel_date
  ON sales (store_id, channel_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_store_date
  ON sales (store_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_delivery_seconds
  ON sales (delivery_seconds)
  WHERE delivery_seconds IS NOT NULL;

-- Base: product_sales
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_sales_sale
  ON product_sales (sale_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_sales_product
  ON product_sales (product_id);

-- Base: delivery_addresses
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_addresses_sale
  ON delivery_addresses (sale_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_addresses_geo
  ON delivery_addresses (city, neighborhood);

-- Base: products (nome às vezes entra em ranking/tabela)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_name
  ON products (name);




