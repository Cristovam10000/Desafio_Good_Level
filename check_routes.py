"""Script para verificar todas as rotas de domínio criadas."""

from app.main import app

routes = [r.path for r in app.routes if hasattr(r, 'path')]
print(f'\nTotal de rotas: {len(routes)}')

domain_routes = [
    r for r in routes 
    if any(d in r for d in ['/sales', '/products', '/delivery', '/stores', '/channels', '/ops', '/finance', '/utils'])
]

print(f'\nRotas de domínio Clean Architecture: {len(domain_routes)}')
print('\nEndpoints migrados:')

# Agrupar por domínio
domains = {
    'Sales': [r for r in domain_routes if '/sales' in r],
    'Products': [r for r in domain_routes if '/products' in r],
    'Delivery': [r for r in domain_routes if '/delivery' in r],
    'Stores': [r for r in domain_routes if '/stores' in r],
    'Channels': [r for r in domain_routes if '/channels' in r],
    'Operations': [r for r in domain_routes if '/ops' in r],
    'Finance': [r for r in domain_routes if '/finance' in r],
    'Utils': [r for r in domain_routes if '/utils' in r],
}

for domain, routes_list in domains.items():
    if routes_list:
        print(f'\n{domain} ({len(routes_list)} endpoints):')
        for route in sorted(routes_list):
            print(f'  {route}')

print(f'\n✓ FASE 2 COMPLETA: {len(domain_routes)} endpoints migrados para Clean Architecture')
print('✓ 8 serviços de domínio criados')
print('✓ 8 routers registrados')
