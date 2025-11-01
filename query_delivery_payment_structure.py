from app.infra.db import fetch_all

print("=" * 80)
print("ESTRUTURA DA TABELA delivery_sales")
print("=" * 80)
result = fetch_all("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'delivery_sales'
    ORDER BY ordinal_position
""", {})
for row in result:
    print(f"  - {row['column_name']}: {row['data_type']}")

print("\n" + "=" * 80)
print("SAMPLE DE delivery_sales (3 registros com JOIN)")
print("=" * 80)
result = fetch_all("""
    SELECT ds.*, da.city, s.sale_status_desc
    FROM delivery_sales ds
    JOIN delivery_addresses da ON da.id = ds.delivery_address_id
    JOIN sales s ON s.id = ds.sale_id
    WHERE ds.delivered_at IS NOT NULL AND ds.dispatched_at IS NOT NULL
    LIMIT 3
""", {})
for row in result:
    print(row)

print("\n" + "=" * 80)
print("TESTE: TEMPO DE ENTREGA")
print("=" * 80)
result = fetch_all("""
    SELECT 
        da.city AS regiao,
        AVG(EXTRACT(EPOCH FROM (ds.delivered_at - ds.dispatched_at))/60)::float AS tempo_medio_minutos,
        COUNT(*)::int AS total_entregas
    FROM delivery_sales ds
    JOIN delivery_addresses da ON da.id = ds.delivery_address_id
    JOIN sales s ON s.id = ds.sale_id
    WHERE s.sale_status_desc = 'COMPLETED'
        AND ds.delivered_at IS NOT NULL
        AND ds.dispatched_at IS NOT NULL
        AND da.city IS NOT NULL
    GROUP BY da.city
    HAVING COUNT(*) >= 5
    ORDER BY tempo_medio_minutos DESC
    LIMIT 5
""", {})
print(f"Total de cidades: {len(result)}")
for row in result:
    print(f"  - {row['regiao']}: {row['tempo_medio_minutos']:.1f} min ({row['total_entregas']} entregas)")

print("\n" + "=" * 80)
print("ESTRUTURA DA TABELA payments")
print("=" * 80)
result = fetch_all("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'payments'
    ORDER BY ordinal_position
""", {})
for row in result:
    print(f"  - {row['column_name']}: {row['data_type']}")

print("\n" + "=" * 80)
print("SAMPLE DE payments com JOIN")
print("=" * 80)
result = fetch_all("""
    SELECT p.*, pt.name as payment_type_name, s.channel_id, c.name as channel_name
    FROM payments p
    JOIN sales s ON s.id = p.sale_id
    JOIN payment_types pt ON pt.id = p.payment_type_id
    JOIN channels c ON c.id = s.channel_id
    LIMIT 5
""", {})
for row in result:
    print(row)

print("\n" + "=" * 80)
print("TESTE: MIX DE PAGAMENTOS POR CANAL")
print("=" * 80)
result = fetch_all("""
    SELECT 
        c.name AS canal,
        pt.name AS forma_pagamento,
        COUNT(*)::int AS quantidade_vendas,
        ROUND((COUNT(*)::float / SUM(COUNT(*)) OVER (PARTITION BY c.name) * 100), 1)::float AS percentual
    FROM payments p
    JOIN sales s ON s.id = p.sale_id
    JOIN payment_types pt ON pt.id = p.payment_type_id
    JOIN channels c ON c.id = s.channel_id
    WHERE s.sale_status_desc = 'COMPLETED'
    GROUP BY c.name, pt.name
    ORDER BY c.name, quantidade_vendas DESC
    LIMIT 10
""", {})
print(f"Total: {len(result)}")
for row in result:
    print(f"  - Canal {row['canal']} / {row['forma_pagamento']}: {row['quantidade_vendas']} vendas ({row['percentual']}%)")
