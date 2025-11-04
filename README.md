# Nola Analytics Platform

## Visao geral
- Plataforma de analytics para redes de restaurantes que entrega visao unificada de vendas, entregas, operacoes, produtos e finanças.
- API em FastAPI aplica camadas de dominio/servico/repositorio para manter regras de negocio isoladas de infraestrutura.
- Frontend em Next.js (App Router) consome endpoints dominios e combina graficos, tabelas e assistentes de IA (Gemini) para gerar insights e detectar anomalias.
- Orquestracao local via Docker Compose sobe PostgreSQL, Cube.js (camada semantica/pre-aggregacoes), API e gerador de dados sintéticos.

## Stack principal
- Backend: Python 3.11, FastAPI 0.111, SQLAlchemy 2, httpx, LangChain + Google Gemini, jose/passlib para JWT.
- Banco e camada semantica: PostgreSQL 15, Cube.js + CubeStore, scripts SQL em `infra/sql` e gerador de dados em `docker/data-generator.Dockerfile`.
- Frontend: Next.js 16, React 19, TanStack Query 5, Zod, Tailwind + Radix UI, Recharts e Sonner.
- Infra: Docker Compose, logs estruturados (`app/core/logging.py`), caching HTTP com ETag, dependencias isoladas por arquivos `.env`.

## Arquitetura em camadas
- `app/core`: configuracao (Pydantic Settings), inicializacao (`ApplicationBuilder`), seguranca/JWT, logging estruturado, helpers de cache/ETag e utilitarios de IA.
- `app/domain`: modelos de dominio (dataclasses), filtros reutilizaveis (`DataFilters`), usuarios demo.
- `app/repositories`: consultas SQL com SQLAlchemy Core, encapsuladas por repositorios especificos (`SalesRepository`, `DeliveryRepository`, etc.).
- `app/services`: regras de negocio agrupadas por dominio, injetadas nas rotas via `dependencies.py`. Destaque para servicos de IA (`ai_insights`, `anomaly_detector`).
- `app/routers`: controladores FastAPI organizados por contexto (sales, delivery, stores, products, finance...). Modulo `specials` mantem endpoints legados com avisos de deprecacao.
- `frontend/src`: organizada por dominos (`app/vendas`, `app/entregas`, `app/operacoes`), entidades, widgets, camada compartilhada (hooks, api, ui).
- `cube/schema`: definicoes de cubos, medidas, dimensoes e pre-aggregacoes (por dia, canal, loja) para acelerar consultas agregadas.

## Fluxo de dados ponta a ponta
1. Base transacional (schema em `infra/sql/database-schema.sql`) persiste vendas, items, entregas, pagamentos.
2. Cube.js exposto em `http://localhost:4000/cubejs-api` gera pre-aggregacoes e serve dados analiticos para o backend.
3. API FastAPI combina consultas diretas no PostgreSQL com agregacoes do Cube, aplica filtros por loja/canal e regras de seguranca (RBAC por papel/loja).
4. Frontend consulta endpoints via axios + TanStack Query, normaliza respostas com Zod e desenha dashboards, tabelas e narrativas.
5. Serviços de IA agregam datasets e chamam Gemini para produzir insights, recomentacoes e alerta de anomalias.

## Funcionalidades principais
### API (FastAPI)
- Endpoints REST agrupados por rotas (`/sales`, `/delivery`, `/stores`, `/ops`, `/finance`, `/products`, `/analytics`) com resposta padronizada via Pydantic.
- Autenticacao com `/auth/login` e `/auth/me` usando usuarios demo e tokens JWT (roles + lojas acessiveis).
- Cache HTTP condicional (`etag_json`) adiciona `ETag`, `Cache-Control: stale-while-revalidate` e suporta `If-None-Match`.
- Health checks em `/healthz` (basico) e `/readyz` (valida conexao com banco).
- Anomalias (`/specials/anomalies`) e insights (`/specials/insights/<secao>`) usando Gemini.
- `ApplicationBuilder` garante inicializacao previsivel de middlewares, rotas, handlers e logging.

### Frontend (Next.js App Router)
- Dashboards interativos por dominio (vendas, entregas, operacoes, produtos, lojas, financeiro, analytics, anomalias).
- Hooks compartilhados (`useRequireAuth`, `useChannelSelection`) e cache de requisicoes com TanStack Query.
- Validacao de contrato com Zod em `frontend/src/shared/api`, evitando divergencia de tipos.
- Componentes reusaveis em `widgets/dashboard` (graficos Recharts, cards, insights), layout com Navbar, Tabs, cards Tailwind/Radix.
- Autenticacao client-side armazena tokens, aplica refresh e restringe acesso via middlewares.
- Integracao com IA: componentes `InsightsCard`, `AnomalyDetector`, e secao Analytics com downloads.

### Inteligencia de dados
- Cube.js com pre-aggregacoes diarias por canal/loja reduz latencia de consultas frequentes.
- Servicos `ai_insights` e `anomaly_detector` montam prompts ricos (com estatisticas, percentis) e usam LangChain + Gemini flash para respostas rapidas.
- Scripts auxiliares em `Scripts/validate_endpoints.py` e `check_routes.py` garantem consistencia de contratos e ajudam na migracao dos endpoints legados.

## Configuracao local
### Dependencias
- Docker Desktop 4.x (compose v2).
- Node 20+ (para Next.js) e npm (ou pnpm/yarn).
- Python 3.11 (caso deseje rodar API fora do container).

### Variaveis de ambiente
- Backend: configurar `.env` na raiz (exemplo ja incluso). Principais chaves:
  - `DATABASE_URL` (postgresql+psycopg), `CUBE_API_URL`, `CUBE_API_TOKEN`.
  - Segredos JWT (`JWT_SECRET`, `JWT_REFRESH_SECRET`, `JWT_SHARE_SECRET`), `CORS_ORIGINS`.
  - `GOOGLE_API_KEY` para habilitar Gemini (obrigatorio para insights/anomalias).
- Frontend: `frontend/.env.local` com `NEXT_PUBLIC_API_BASE_URL` e `NEXT_PUBLIC_APP_NAME`.

### Subindo com Docker Compose
```
cd docker
docker compose up -d postgres cubestore cube
docker compose --profile tools run --rm data-generator   # popula base com dados sinteticos
docker compose up -d api
```
- API disponivel em `http://localhost:8000` (Swagger em `/docs`).
- Cube Playground em `http://localhost:4000`.

### Executando o backend fora do Docker
```
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Ajuste `DATABASE_URL` e `CUBE_API_URL` no `.env` conforme ambiente.

### Executando o frontend
```
cd frontend
npm install
npm run dev   # porta 5173
```
- Aplique `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` para desenvolvimento local.

## Estrutura de pastas
```
app/
  core/         # configuracao, builder, logging, seguranca, cache, IA helpers
  domain/       # modelos e filtros de negocio
  repositories/ # queries SQL por dominio
  services/     # regras de negocio, IA, factory de analytics
  routers/      # rotas FastAPI (sales, delivery, stores, etc.)
  infra/        # conexao com banco, health check, helpers
frontend/
  src/app/      # paginas do Next agrupadas por dominio (vendas, entregas, analytics...)
  src/shared/   # chamadas a API, hooks, componentes UI reutilizaveis
  src/widgets/  # graficos, cards e blocos de dashboard
cube/
  schema/       # cubos e pre-aggregacoes (Sales, Delivery, ProductSales)
docker/
  docker-compose.yml, Dockerfiles para postgres, data-generator e api
infra/sql/      # schema relacional base
Scripts/        # utilitarios de validacao/migracao
```

## Observabilidade, qualidade e seguranca
- Logging estruturado com enriquecimento automatico de request/response (`app/core/logging.py`).
- Rotas com RBAC: `require_roles` garante que somente papeis autorizados alcancem dados sensiveis e restringe lojas via `AccessClaims`.
- Cache HTTP com stale-while-revalidate, etags deterministicas e suporte a 304.
- Health checks integrados usados pelo compose/k8s e por monitoramento externo.
- Scripts automatizados para validar contratos e identificar rotas legadas (`check_routes.py`, `Scripts/validate_endpoints.py`).
- Testes pontuais (`test_insights.py`) cobrem integracao de IA; recomenda-se ampliar com pytest + mocks para repositorios/servicos.

## Documentacao de decisoes
### Separacao em camadas para o backend
- Por que X? Domain models + repositories + services + routers garantem isolacao, testabilidade e troca de infraestrutura sem reescrever regras de negocio.
- Por que nao Y? Colocar SQL diretamente em rotas FastAPI reduziu legibilidade e dificultou reutilizacao/validacao; a arquitetura em camadas evita acoplamento.

### Cube.js como camada semantica
- Por que X? Cube oferece pre-aggregacoes, cache distribuido (CubeStore) e modelo declarativo reutilizavel por API e futuras ferramentas BI.
- Por que nao Y? Consultas SQL puras sobre tabelas transacionais geravam latencia alta e risco de duplicar logica de agregacao em varios pontos; materialized views nativas exigiriam manutencao manual.

### ApplicationBuilder no FastAPI
- Por que X? Builder centraliza middlewares, rotas, handlers e logging, impedindo configuracoes duplicadas e garantindo ordem de execucao durante testes ou scripts.
- Por que nao Y? A funcao `create_app` monolitica anterior dificultava testes unitarios e reaproveitamento de configuracao em workers/background tasks.

### Next.js App Router + TanStack Query
- Por que X? App Router simplifica segmentacao por dominio, suporta streaming/SSR quando necessario e combina bem com layouts aninhados; TanStack Query fornece cache normalizado, estado de carregamento e revalidacao consolidada.
- Por que nao Y? CRA/SPA tradicional exigiria pipeline custom para roteamento, data fetching e code splitting; Pages Router demandaria migracoes futuras.

### JWT + RBAC com escopo por loja
- Por que X? JWT stateless simplifica integracao com frontend e compartilhamento (`share` token). Claims incluem papeis e lojas autorizadas, aplicando filtros no backend de forma centralizada.
- Por que nao Y? Sessions de servidor exigiriam storage externo e sincronizacao entre instancias; API keys nao permitem granularidade por loja/usuario.

### Insights de IA com Gemini flash
- Por que X? Gemini 2.0 flash entrega latencia baixa para prompt ricos, possibilitando insights e anomalias quase em tempo real; LangChain facilita mudanca de provider ou ajustes de prompt.
- Por que nao Y? Regras manuais seriam custosas para manter e dificilmente cobririam casos nao previstos; modelos LLM maiores (Pro) aumentariam custo e tempo de resposta.

### Cache HTTP com ETag + stale-while-revalidate
- Por que X? Caching em nivel HTTP beneficia CDN/navegador e reduz carga no backend sem necessidade de Redis; ETags deterministicas permitem condicionais simples.
- Por que nao Y? Cache em memoria local nao escalaria em multiplas instancias; apenas usar CDN perderia contexto de autorizacao, que aqui e controlado com `Vary: Authorization`.

## Proximos passos sugeridos
- Expandir suite de testes (unitarios para servicos/repositorios + e2e para fluxos principais).
- Automatizar pipeline CI (lint, testes, build frontend) e adicionar husky/pre-commit para padronizacao local.
- Evoluir autenticacao removendo usuarios demo e integrando com identidade real (Keycloak, Auth0, Azure AD).
- Promover gradualmente migracao dos clients legacy dos endpoints `/specials/*` para rotas novas, removendo deprecados na versao 2.0.
- Instrumentar metricas (Prometheus/OpenTelemetry) e dashboards de observabilidade.
