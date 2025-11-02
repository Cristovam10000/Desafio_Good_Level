"""
Script para exibir detalhes completos de uma venda do banco de dados.
Usa pg8000 (biblioteca pura Python) para evitar problemas de encoding no Windows.
"""

import sys
import pg8000.native

def get_db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL usando pg8000."""
    try:
        conn = pg8000.native.Connection(
            user="challenge",
            password="challenge123",
            host="localhost",
            port=15432,
            database="challenge_db"
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de dados: {e}")
        sys.exit(1)

def get_sale_header(conn, sale_id: int) -> dict:
    """Obtém informações principais da venda."""
    query = """
        SELECT 
            s.id,
            st.name as store_name,
            c.description as channel,
            s.total_amount,
            s.production_seconds,
            s.delivery_seconds,
            s.sale_status_desc,
            s.customer_id,
            s.created_at
        FROM sales s
        JOIN stores st ON s.store_id = st.id
        JOIN channels c ON s.channel_id = c.id
        WHERE s.id = :sale_id
    """
    
    result = conn.run(query, sale_id=sale_id)
    if not result:
        return None
    
    # pg8000 retorna lista de tuplas, precisamos mapear para dict
    columns = ['id', 'store_name', 'channel', 'total_amount', 'production_seconds', 
               'delivery_seconds', 'sale_status_desc', 'customer_id', 'created_at']
    return dict(zip(columns, result[0]))

def get_sale_products(conn, sale_id: int) -> list:
    """Obtém produtos da venda."""
    query = """
        SELECT 
            ps.id,
            p.name as product_name,
            ps.quantity,
            ps.base_price,
            ps.total_price,
            ps.observations
        FROM product_sales ps
        JOIN products p ON ps.product_id = p.id
        WHERE ps.sale_id = :sale_id
        ORDER BY ps.id
    """
    
    results = conn.run(query, sale_id=sale_id)
    columns = ['id', 'product_name', 'quantity', 'base_price', 'total_price', 'observations']
    return [dict(zip(columns, row)) for row in results]

def get_product_items(conn, product_sale_id: int) -> list:
    """Obtém modificadores/itens adicionais de um produto."""
    query = """
        SELECT 
            i.name as item_name,
            ips.quantity,
            ips.additional_price,
            ips.price,
            ips.amount
        FROM item_product_sales ips
        JOIN items i ON ips.item_id = i.id
        WHERE ips.product_sale_id = :product_sale_id
        ORDER BY ips.id
    """
    
    results = conn.run(query, product_sale_id=product_sale_id)
    columns = ['item_name', 'quantity', 'additional_price', 'price', 'amount']
    return [dict(zip(columns, row)) for row in results]

def get_sale_payments(conn, sale_id: int) -> list:
    """Obtém formas de pagamento da venda."""
    query = """
        SELECT 
            pt.description as payment_type,
            p.value,
            p.is_online
        FROM payments p
        JOIN payment_types pt ON p.payment_type_id = pt.id
        WHERE p.sale_id = :sale_id
        ORDER BY p.id
    """
    
    results = conn.run(query, sale_id=sale_id)
    columns = ['payment_type', 'value', 'is_online']
    return [dict(zip(columns, row)) for row in results]

def get_delivery_address(conn, sale_id: int) -> dict:
    """Obtém endereço de entrega."""
    query = """
        SELECT 
            street,
            number,
            complement,
            neighborhood,
            city,
            state,
            postal_code,
            reference,
            latitude,
            longitude
        FROM delivery_addresses
        WHERE sale_id = :sale_id
    """
    
    result = conn.run(query, sale_id=sale_id)
    if not result:
        return None
    
    columns = ['street', 'number', 'complement', 'neighborhood', 'city', 
               'state', 'postal_code', 'reference', 'latitude', 'longitude']
    return dict(zip(columns, result[0]))

def format_currency(value) -> str:
    """Formata valor como moeda brasileira."""
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_time(seconds) -> str:
    """Formata segundos como tempo legível."""
    if seconds is None or seconds == 0:
        return "0s"
    
    minutes = seconds // 60
    secs = seconds % 60
    
    if minutes > 0 and secs > 0:
        return f"{minutes}min {secs}s"
    elif minutes > 0:
        return f"{minutes}min"
    else:
        return f"{secs}s"

def print_sale_details(sale_id: int):
    """Exibe detalhes completos de uma venda de forma organizada."""
    
    conn = get_db_connection()
    
    try:
        # 1. Informações principais
        print(f"\n{'='*80}")
        print(f"🧾 DETALHES DA VENDA #{sale_id}")
        print(f"{'='*80}\n")
        
        sale = get_sale_header(conn, sale_id)
        if not sale:
            print(f"❌ Venda #{sale_id} não encontrada!")
            return
        
        print(f"🏪 Loja: {sale['store_name']}")
        print(f"📱 Canal: {sale['channel']}")
        print(f"👤 Cliente ID: {sale['customer_id']}")
        print(f"📅 Data: {sale['created_at']}")
        print(f"📊 Status: {sale['sale_status_desc']}")
        print(f"💰 Total: {format_currency(sale['total_amount'])}")
        
        # 2. Produtos
        print(f"\n{'─'*80}")
        print("🍔 PRODUTOS:")
        print(f"{'─'*80}\n")
        
        products = get_sale_products(conn, sale_id)
        products_total = 0
        
        for idx, prod in enumerate(products, 1):
            print(f"  {idx}. {prod['product_name']}")
            print(f"     Quantidade: {prod['quantity']} x {format_currency(prod['base_price'])}")
            print(f"     Subtotal: {format_currency(prod['total_price'])}")
            
            if prod['observations']:
                print(f"     📝 Observações: {prod['observations']}")
            
            # Modificadores/itens adicionais
            items = get_product_items(conn, prod['id'])
            if items:
                print(f"     Personalizações:")
                for item in items:
                    prefix = "+" if item['additional_price'] > 0 else "-"
                    qty_str = f"{item['quantity']}x " if item['quantity'] > 1 else ""
                    price_str = format_currency(item['amount'])
                    print(f"       {prefix} {qty_str}{item['item_name']} ({price_str})")
            
            products_total += float(prod['total_price'])
            print()
        
        print(f"  💵 Total em produtos: {format_currency(products_total)}")
        
        # 3. Pagamentos
        print(f"\n{'─'*80}")
        print("💳 PAGAMENTOS:")
        print(f"{'─'*80}\n")
        
        payments = get_sale_payments(conn, sale_id)
        payments_total = 0
        
        for pmt in payments:
            online_icon = "🌐" if pmt['is_online'] else "🏪"
            payment_mode = "Online" if pmt['is_online'] else "Presencial"
            print(f"  {online_icon} {pmt['payment_type']} ({payment_mode}): {format_currency(pmt['value'])}")
            payments_total += float(pmt['value'])
        
        print(f"\n  💵 Total pago: {format_currency(payments_total)}")
        
        # 4. Tempos
        print(f"\n{'─'*80}")
        print("⏱️  TEMPOS:")
        print(f"{'─'*80}\n")
        
        prep_time = format_time(sale['production_seconds'])
        deliv_time = format_time(sale['delivery_seconds'])
        total_time = format_time((sale['production_seconds'] or 0) + (sale['delivery_seconds'] or 0))
        
        print(f"  👨‍🍳 Preparação: {prep_time}")
        print(f"  🏍️  Entrega: {deliv_time}")
        print(f"  ⏰ Total: {total_time}")
        
        # 5. Endereço de entrega
        address = get_delivery_address(conn, sale_id)
        if address:
            print(f"\n{'─'*80}")
            print("📍 ENDEREÇO DE ENTREGA:")
            print(f"{'─'*80}\n")
            
            street_line = f"{address['street']}, {address['number']}"
            if address['complement']:
                street_line += f" - {address['complement']}"
            
            print(f"  {street_line}")
            print(f"  {address['neighborhood']}")
            print(f"  {address['city']}/{address['state']} - CEP: {address['postal_code']}")
            
            if address['reference']:
                print(f"  🗺️  Referência: {address['reference']}")
            
            if address['latitude'] and address['longitude']:
                print(f"  📌 Coordenadas: {address['latitude']}, {address['longitude']}")
        
        print(f"\n{'='*80}\n")
        
    finally:
        conn.close()

def find_complex_sale(store_ids=[1, 2, 3]):
    """Encontra uma venda com vários produtos das lojas especificadas."""
    
    conn = get_db_connection()
    
    try:
        # Busca venda com múltiplos produtos
        query = """
            SELECT s.id, COUNT(ps.id) as product_count, s.total_amount
            FROM sales s
            JOIN product_sales ps ON s.id = ps.sale_id
            WHERE s.store_id = ANY(:store_ids)
            GROUP BY s.id
            HAVING COUNT(ps.id) >= 2
            ORDER BY COUNT(ps.id) DESC, s.total_amount DESC
            LIMIT 1
        """
        
        result = conn.run(query, store_ids=store_ids)
        
        if result:
            sale_id = result[0][0]
            product_count = result[0][1]
            total = result[0][2]
            print(f"✅ Encontrada venda #{sale_id} com {product_count} produtos (Total: {format_currency(total)})")
            return sale_id
        else:
            print("❌ Nenhuma venda encontrada com múltiplos produtos")
            return None
            
    finally:
        conn.close()

if __name__ == "__main__":
    print("\n🚀 Buscando exemplo de venda das lojas da Maria (lojas 1, 2, 3)...")
    
    sale_id = find_complex_sale()
    
    if sale_id:
        print_sale_details(sale_id)
    else:
        print("\n⚠️  Nenhuma venda complexa encontrada. Tente novamente com outros critérios.")
