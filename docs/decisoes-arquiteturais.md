# Documento de Decisoes Arquiteturais

Este registro consolida as principais decisoes arquiteturais do projeto Nola Analytics Platform. Cada entrada segue o formato ADR (Architectural Decision Record), destacando contexto, opcoes avaliadas, justificativa e impactos.

---

## ADR-001: Camadas Dominio -> Servico -> Repositorio no backend

### Contexto
O backend precisava isolar modelos de negocio das dependencias externas (banco relacional, HTTP, IA) enquanto mantinha reuso de filtros e regras entre dominios (vendas, entregas, produtos). O desafio original era um monolito de rotas direto no FastAPI, com SQL e regras espalhadas.

### Decisao
Adotar separacao em camadas: `app/domain` guarda modelos e filtros puros (`app/domain/models.py:13`, `app/domain/filters.py:9`); `app/services` concentra regras de negocio (`app/services/sales_service.py:19`); `app/repositories` encapsula SQL (`app/repositories/sales_repository.py:21`). As rotas usam dependencias para instanciar servicos (`app/services/dependencies.py:5`).

### Alternativas Consideradas
1. Manter rotas FastAPI com SQL direto.
2. Criar camada unica orientada a ORMs (SQLAlchemy ORM completo).

### Racional
- Reduz acoplamento com infraestrutura, facilitando testes unitarios de servicos e troca de fonte de dados.
- Reuso de filtros (`DataFilters`) evita divergencia de clausulas SQL (`app/domain/filters.py:26`).
- Simplifica injecao de IA e caches na camada de servico.

### Consequencias
- Maior numero de arquivos, exigindo disciplina em nomeacao/organizacao.
- Facilita mocks em testes e substituicao de repositorios por implementacoes especializadas.
- Possibilita migracao gradual dos endpoints legados em `specials.py` para rotas novas mantendo logicas reaproveitaveis.

---

## ADR-002: ApplicationBuilder para inicializar FastAPI
- **Status:** Aceita (2025-11-03)

### Contexto
A funcao `create_app` original agregava middlewares, rotas, handlers e configuracoes de log em um unico bloco, dificultando reutilizacao e testes. Precisavamos padronizar a ordem de inicializacao e prevenir registro duplicado de componentes.

### Decisao
Implementar `ApplicationBuilder` que encadeia metodos explicitos para cada preocupacao (`app/core/application.py:37`). A funcao `create_application` compoe os passos em ordem previsivel e valida pre-condicoes antes de devolver a instancia (`app/core/application.py:222`, `app/main.py:8`).

### Alternativas Consideradas
1. Manter `create_app` monolitica.
2. Usar framework externo de bootstrap (ex.: FastAPI-Service).

### Racional
- Builder impede middlewares/rotas duplicadas por meio de flags internas (`app/core/application.py:54`).
- Facilita testes unitarios de cada passo e futura extensao (ex.: adicionar middlewares condicionais).
- Permite logging padronizado (`app/core/logging.py`) antes de montar rotas.

### Consequencias
- Equipe precisa seguir o contrato (chamar `finalize_middlewares()` antes de `add_routes()`).
- Documento de onboarding deve destacar o fluxo builder para novos contribuidores.

---

## ADR-003: Uso de Cube.js + CubeStore como camada semantica


### Contexto
Consultas agregadas sobre vendas, canais e lojas apresentavam alta latencia quando executadas diretamente sobre tabelas transacionais. Era necessario fornecer pre-aggregacoes reutilizaveis e cache multi-instancia.

### Decisao
Introduzir Cube.js com CubeStore via Docker Compose (`docker/docker-compose.yml:46`, `docker/docker-compose.yml:67`) e definir cubos/pre-aggregacoes em `cube/schema` (`cube/schema/Sales.js:96`). O backend autentica com JWT e consulta `/v1/load` usando cliente dedicado (`app/infra/cube_client.py:92`).

### Alternativas Consideradas
1. Materialized views gerenciadas manualmente em PostgreSQL.
2. Lakehouse/warehouse externo (BigQuery, Snowflake).

### Racional
- Cube oferece camada semantica declarativa e cache distribuido com minima manutencao.
- Compose garante ambiente padrao local, alinhado ao pipeline de dados sinteticos (`docker/data-generator.Dockerfile`).
- Cliente interno adiciona retries e renovacao de token sob demanda (`app/infra/cube_client.py:34`).

### Consequencias
- Necessidade de monitorar CubeStore (latencia, memoria) em producao.
- Ajustes de `preAggregations` tornam-se parte da gestao de performance.
- Requer alinhamento de schema entre base OLTP e definicoes Cube.

---

## ADR-004: Insights e detecao de anomalias com Google Gemini


### Contexto
Stakeholders desejavam narrativas e alertas inteligentes sem construir regras estatisticas manualmente. Havia requisito de baixa latencia e custo controlado.

### Decisao
Integrar Google Gemini 2.0 Flash via LangChain para insights (`app/services/ai_insights.py:12`) e detecao de anomalias (`app/services/anomaly_detector.py:19`). Prompts ricos descrevem missao/formatos e incluem dados serializados; a chave API e configurada via `.env` (`.env:33`).

### Alternativas Consideradas
1. Regras heuristicas (SQL + Pandas) por dominio.
2. Modelos OpenAI (GPT-4) ou Anthropic Claude.

### Racional
- Gemini Flash oferece equilibrio entre custo e latencia, atendendo dashboards em tempo quase real.
- LangChain abstrai formatacao de prompt e facilita troca futura de provedor.
- Implementacao assicrona com httpx suporta retries, logs e controle de tokens.

### Consequencias
- Dependencia forte de `GOOGLE_API_KEY`; rotas devem lidar com fallback quando nao configurada (`app/services/anomaly_detector.py:43`).
- Necessidade de auditoria de respostas para garantir consistencia e evitar alucinacoes.
- Custos variam conforme volume de chamadas; monitoramento e cache sao recomendados.

---

## ADR-005: Cache HTTP com ETag e stale-while-revalidate

### Contexto
APIs de analytics servem respostas pesadas e relativamente estaveis. Precisavamos reduzir carga no banco e acelerar navegacao sem introduzir Redis ou outra camada externa.

### Decisao
Criar helper `etag_json` que gera resposta deterministica com ETag, `Cache-Control` com `stale-while-revalidate` e suporte a `If-None-Match` (`app/core/cache.py:39`, `app/core/cache.py:61`). As rotas analytics aplicam o helper (`app/routers/analytics.py:56`, `app/routers/analytics.py:213`).

### Alternativas Consideradas
1. Cache in-memory com TTL local por processo.
2. Adotar Redis/KeyDB como cache distribuido.

### Racional
- Evita dependencia externa adicional mantendo conformidade HTTP padrao.
- Permite que CDNs/proxies reaproveitem conteudo (com `Vary: Authorization`).
- Ajusta tempos por endpoint via parametros `max_age` e `swr`.

### Consequencias
- Necessario garantir determinismo das respostas (ordenacao/serializacao).
- Clientes devem respeitar cabecalhos para obter beneficios; documentacao precisa destacar comportamento.
- Para dados altamente dinamicos (tempo real) pode exigir bypass.

---

## ADR-006: Autenticacao JWT com escopo por papel e loja


### Contexto
Painel precisa limitar acesso por papel (viewer, analyst, manager, admin) e por lojas autorizadas, incluindo compartilhamento seguro de consultas.

### Decisao
Emitir tokens JWT contendo roles e IDs de lojas (`app/core/security.py:34`, `app/core/security.py:119`). O login demo gera pares access/refresh (`app/routers/auth.py:54`), e as rotas utilizam `require_roles` para validar autorizacao (`app/core/security.py:139`, `app/routers/sales.py:73`).

### Alternativas Consideradas
1. Sessions com armazenamento servidor (Redis).
2. API Keys por usuario.

### Racional
- JWT e stateless, simplificando escala horizontal e compartilhamento (`create_share_token`).
- Claims com lojas permitem aplicar filtros automaticamente nas rotas (ex.: `_validate_user_store_access` em `app/routers/sales.py:45`).
- Integra facilmente com frontend Next.js (headers Authorization Bearer).

### Consequencias
- Segredos JWT precisam ter 32+ caracteres (`app/core/config.py:28`).
- Rotas devem invalidar tokens quando lojas mudarem (requer new login).
- Compartilhamento exige expiracao curta para evitar vazamento.

---

## ADR-007: Next.js App Router com TanStack Query e validacao via Zod


### Contexto
Frontend precisava entregar dashboards ricos por dominio mantendo SSR/SSG opcionais e controle de estado de requisicoes. Versoes anteriores com CRA dificultavam modularizacao e code-splitting.

### Decisao
Adotar Next.js 16 com App Router, organizando paginas por dominios (`frontend/src/app/vendas`, `frontend/src/app/entregas`). TanStack Query gerencia cache/fetch (`frontend/src/app/entregas/page.tsx:14`, `frontend/src/app/entregas/page.tsx:92`), e contratos sao validados com Zod (`frontend/src/shared/api/sections.ts:6`).

### Alternativas Consideradas
1. SPA com Vite/CRA + React Query manual.
2. Next.js Pages Router (legacy).

### Racional
- App Router facilita layouts aninhados, carregamento progressivo e breadcrumb consistente (`frontend/src/app/layout.tsx:11`).
- TanStack Query trata estados de carregamento/erro automaticamente e suporta revalidacao de dados.
- Zod garante que variacoes na API quebrem perto da origem com mensagens claras.

### Consequencias
- Configuracao inicial mais complexa (requires Node 20, features experimentais).
- Devs precisam seguir padrao de pastas e hooks compartilhados (`frontend/src/shared/hooks`).
- SSR parcial exige cuidado com uso de APIs apenas cliente (hook `use client`).

---

## Proximas Decisoes Candidatas
- Estrategia de testes automatizados (unitarios x e2e) e coverage minimo.
- Observabilidade padronizada (logging estruturado + tracing + metricas).
- Evolucao dos endpoints legados em `app/routers/specials.py`.
