# -*- coding: utf-8 -*-
"""
Script para mostrar detalhes completos de uma venda do sistema de delivery.
Mostra toda a estrutura: loja, produtos, adicionais, pagamento, entrega, etc.
"""

import os
import sys

# Force UTF-8 encoding on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional


def get_db_connection():
    """Conecta ao banco PostgreSQL via Docker."""
    return psycopg2.connect(
        host="localhost",
        port="5432",
        database="challenge_db",
        user="challenge",
        password="challenge123",
        cursor_factory=RealDictCursor,
        client_encoding='UTF8'
    )


def format_currency(value: float) -> str:
    """Formata valor como moeda brasileira."""
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_time(seconds: Optional[int]) -> str:
    """Formata segundos em minutos."""
    if seconds is None:
        return "N/A"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}min {secs}s" if secs > 0 else f"{minutes}min"


def get_sale_header(cursor, sale_id: int):
    """Busca dados principais da venda."""
    cursor.execute("""
        SELECT 
            s.id,
            s.cod_sale1,
            st.name as store_name,
            st.city as store_city,
            st.state as store_state,
            ch.name as channel_name,
            s.customer_name,
            s.total_amount_items,
            s.total_discount,
            s.total_increase,
            s.delivery_fee,
            s.service_tax_fee,
            s.total_amount,
            s.value_paid,
            s.production_seconds,
            s.delivery_seconds,
            s.sale_status_desc,
            s.created_at,
            s.discount_reason,
            s.increase_reason
        FROM sales s
        JOIN stores st ON st.id = s.store_id
        JOIN channels ch ON ch.id = s.channel_id
        WHERE s.id = %s
    """, (sale_id,))
    return cursor.fetchone()


def get_sale_products(cursor, sale_id: int):
    """Busca produtos da venda."""
    cursor.execute("""
        SELECT 
            ps.id,
            p.name as product_name,
            ps.quantity,
            ps.base_price,
            ps.total_price,
            ps.observations
        FROM product_sales ps
        JOIN products p ON p.id = ps.product_id
        WHERE ps.sale_id = %s
        ORDER BY ps.id
    """, (sale_id,))
    return cursor.fetchall()


def get_product_items(cursor, product_sale_id: int):
    """Busca adicionais/remoções de um produto."""
    cursor.execute("""
        SELECT 
            i.name as item_name,
            ips.quantity,
            ips.additional_price,
            ips.price,
            ips.amount
        FROM item_product_sales ips
        JOIN items i ON i.id = ips.item_id
        WHERE ips.product_sale_id = %s
        ORDER BY ips.id
    """, (product_sale_id,))
    return cursor.fetchall()


def get_sale_payments(cursor, sale_id: int):
    """Busca formas de pagamento da venda."""
    cursor.execute("""
        SELECT 
            pt.description as payment_type,
            p.value,
            p.is_online,
            p.description as payment_description
        FROM payments p
        JOIN payment_types pt ON pt.id = p.payment_type_id
        WHERE p.sale_id = %s
        ORDER BY p.id
    """, (sale_id,))
    return cursor.fetchall()


def get_delivery_address(cursor, sale_id: int):
    """Busca endereço de entrega."""
    cursor.execute("""
        SELECT 
            street,
            number,
            complement,
            neighborhood,
            city,
            state,
            postal_code,
            reference
        FROM delivery_addresses
        WHERE sale_id = %s
        LIMIT 1
    """, (sale_id,))
    return cursor.fetchone()


def print_sale_details(sale_id: int):
    """Imprime detalhes completos de uma venda de forma organizada."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Busca dados
        sale = get_sale_header(cursor, sale_id)
        
        if not sale:
            print(f"❌ Venda #{sale_id} não encontrada!")
            return
        
        products = get_sale_products(cursor, sale_id)
        payments = get_sale_payments(cursor, sale_id)
        delivery = get_delivery_address(cursor, sale_id)
        
        # Imprime cabeçalho
        print("\n" + "="*80)
        print(f"🧾 VENDA #{sale['id']}" + (f" - Código: {sale['cod_sale1']}" if sale['cod_sale1'] else ""))
        print("="*80)
        
        # Loja e Canal
        print(f"\n🏪 Loja: {sale['store_name']}")
        print(f"   Localização: {sale['store_city']}/{sale['store_state']}")
        print(f"📱 Canal: {sale['channel_name']}")
        
        # Cliente
        if sale['customer_name']:
            print(f"👤 Cliente: {sale['customer_name']}")
        else:
            print("👤 Cliente: Não identificado")
        
        # Data/Hora
        created_at = sale['created_at']
        print(f"📅 Data/Hora: {created_at.strftime('%d/%m/%Y às %H:%M:%S')}")
        
        # Status
        status_emoji = "✅" if sale['sale_status_desc'] == 'COMPLETED' else "❌"
        print(f"{status_emoji} Status: {sale['sale_status_desc']}")
        
        # Produtos
        print("\n" + "-"*80)
        print("🍔 PRODUTOS:")
        print("-"*80)
        
        for idx, product in enumerate(products, 1):
            qty = int(product['quantity']) if product['quantity'].is_integer() else product['quantity']
            print(f"\n  {idx}. {product['product_name']}")
            print(f"     Quantidade: {qty}x")
            print(f"     Preço unitário: {format_currency(product['base_price'])}")
            print(f"     Subtotal: {format_currency(product['total_price'])}")
            
            if product['observations']:
                print(f"     📝 Obs: {product['observations']}")
            
            # Busca adicionais/remoções
            items = get_product_items(cursor, product['id'])
            if items:
                print("     ├── Personalizações:")
                for item in items:
                    item_qty = int(item['quantity']) if item['quantity'].is_integer() else item['quantity']
                    if item['additional_price'] > 0:
                        print(f"     │   ├── + {item['item_name']} ({item_qty}x) - {format_currency(item['additional_price'])}")
                    elif item['additional_price'] < 0:
                        print(f"     │   ├── - {item['item_name']} ({item_qty}x) - {format_currency(abs(item['additional_price']))}")
                    else:
                        print(f"     │   ├── {item['item_name']} ({item_qty}x) - Sem custo")
        
        # Resumo financeiro
        print("\n" + "-"*80)
        print("💰 RESUMO FINANCEIRO:")
        print("-"*80)
        print(f"  Subtotal (produtos): {format_currency(sale['total_amount_items'])}")
        
        if sale['total_discount'] and sale['total_discount'] > 0:
            print(f"  Desconto: -{format_currency(sale['total_discount'])}")
            if sale['discount_reason']:
                print(f"    └─ Motivo: {sale['discount_reason']}")
        
        if sale['total_increase'] and sale['total_increase'] > 0:
            print(f"  Acréscimo: +{format_currency(sale['total_increase'])}")
            if sale['increase_reason']:
                print(f"    └─ Motivo: {sale['increase_reason']}")
        
        if sale['delivery_fee'] and sale['delivery_fee'] > 0:
            print(f"  Taxa de entrega: +{format_currency(sale['delivery_fee'])}")
        
        if sale['service_tax_fee'] and sale['service_tax_fee'] > 0:
            print(f"  Taxa de serviço: +{format_currency(sale['service_tax_fee'])}")
        
        print(f"\n  {'='*20}")
        print(f"  TOTAL: {format_currency(sale['total_amount'])}")
        print(f"  {'='*20}")
        
        # Pagamento
        if payments:
            print("\n" + "-"*80)
            print("💳 PAGAMENTO:")
            print("-"*80)
            for payment in payments:
                online_tag = "💻 Online" if payment['is_online'] else "🏪 Presencial"
                print(f"  {payment['payment_type']} - {format_currency(payment['value'])} ({online_tag})")
                if payment['payment_description']:
                    print(f"    └─ {payment['payment_description']}")
        
        # Tempos
        print("\n" + "-"*80)
        print("⏱️  TEMPOS:")
        print("-"*80)
        print(f"  Preparo: {format_time(sale['production_seconds'])}")
        print(f"  Entrega: {format_time(sale['delivery_seconds'])}")
        if sale['production_seconds'] and sale['delivery_seconds']:
            total_time = sale['production_seconds'] + sale['delivery_seconds']
            print(f"  Total: {format_time(total_time)}")
        
        # Endereço de entrega
        if delivery:
            print("\n" + "-"*80)
            print("📍 ENTREGA:")
            print("-"*80)
            address_parts = []
            if delivery['street']:
                address_parts.append(delivery['street'])
            if delivery['number']:
                address_parts.append(f"nº {delivery['number']}")
            if delivery['complement']:
                address_parts.append(delivery['complement'])
            
            if address_parts:
                print(f"  Endereço: {', '.join(address_parts)}")
            
            if delivery['neighborhood']:
                print(f"  Bairro: {delivery['neighborhood']}")
            
            if delivery['city'] and delivery['state']:
                print(f"  Cidade: {delivery['city']}/{delivery['state']}")
            
            if delivery['postal_code']:
                print(f"  CEP: {delivery['postal_code']}")
            
            if delivery['reference']:
                print(f"  Referência: {delivery['reference']}")
        
        print("\n" + "="*80 + "\n")
        
    finally:
        cursor.close()
        conn.close()


def find_complex_sale(store_ids: list = [1, 2, 3]):
    """Encontra uma venda com múltiplos produtos das lojas da Maria."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT s.id, COUNT(ps.id) as num_products
            FROM sales s
            JOIN product_sales ps ON ps.sale_id = s.id
            WHERE s.store_id = ANY(%s)
              AND s.sale_status_desc = 'COMPLETED'
            GROUP BY s.id
            HAVING COUNT(ps.id) >= 2
            ORDER BY s.id
            LIMIT 5
        """, (store_ids,))
        
        sales = cursor.fetchall()
        
        if sales:
            print("\n🔍 Vendas encontradas com múltiplos produtos:")
            for sale in sales:
                print(f"  - Venda #{sale['id']} ({sale['num_products']} produtos)")
            return sales[0]['id']
        else:
            # Se não encontrar com múltiplos, pega qualquer uma
            cursor.execute("""
                SELECT id FROM sales
                WHERE store_id = ANY(%s)
                  AND sale_status_desc = 'COMPLETED'
                ORDER BY id
                LIMIT 1
            """, (store_ids,))
            result = cursor.fetchone()
            return result['id'] if result else None
            
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("\n🚀 Buscando exemplo de venda das lojas da Maria (lojas 1, 2, 3)...")
    
    sale_id = find_complex_sale()
    
    if sale_id:
        print(f"\n📋 Exibindo detalhes da venda #{sale_id}:")
        print_sale_details(sale_id)
    else:
        print("\n❌ Nenhuma venda encontrada para as lojas da Maria!")
    
    print("\n💡 Para ver outra venda, execute:")
    print(f"   python show_sale_details.py")
    print("\n   Ou no código Python:")
    print(f"   from show_sale_details import print_sale_details")
    print(f"   print_sale_details(NUMERO_DA_VENDA)")
