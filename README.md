# 🏗️ Backend Architecture Patterns — Python

> Coleção de **patterns arquiteturais e frameworks genéricos** que desenvolvi para um sistema de produção real, extraídos e generalizados para demonstrar habilidades de engenharia de software.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Sobre

Este repositório contém **componentes de infraestrutura** que criei ao construir um sistema backend Python multi-domínio com FastAPI. Cada módulo é independente, bem documentado e demonstra um aspecto diferente de engenharia backend.

### Highlights

| Módulo | O que é | Patterns / Conceitos |
|---|---|---|
| [`compiler/`](compiler/) | Framework completo de compilador para DSLs customizadas | Pratt Parser, AST, Visitor, Pipeline |
| [`middleware/`](middleware/) | Stack de middlewares para APIs de produção | Rate Limiting, Idempotência, Sanitização |
| [`integrations/`](integrations/) | Sistema de plugins com auto-discovery | Hexagonal Architecture, Registry, Multi-tenancy |
| [`governance/`](governance/) | Enforcement de invariantes e mediação de domínios | DDD, Mediator, Policy Pattern |
| [`cognitive/`](cognitive/) | Contratos para pipeline de NLP/AI | Strategy, Interceptor, Observabilidade |

---

## 📦 Módulos

### 1. Compiler Framework (`compiler/`)

Um **framework completo de compilação** para Domain-Specific Languages (DSLs), implementando as 4 fases clássicas de compilação:

```
Source Code → [Tokenizer] → Tokens → [Parser] → AST → [Semantic] → Validated AST → [Executor] → Result + Trace
```

**Destaques técnicos:**
- **Pratt Parser** (precedence climbing) — algoritmo elegante para parsing de expressões com precedência de operadores
- **AST imutável** com `frozen=True` dataclasses
- **Visitor Pattern** para execução e análise
- **Trace Tree** — observabilidade total de cada passo de execução
- **Chain of Responsibility** para resolução dinâmica de handlers
- **Cache** com abstração Redis/InMemory
- **Serialização JSON-safe** (evitando pickle inseguro por design)

**🚀 Atualizações de Observabilidade (V1 & V2):**
- **V1 (Métricas e Tokens):** Extração de tokens detalhada, rastreio visual do resultado da execução e **Compilation Stats** (com cálculo de tempo de execução via `perf_counter` no Python / `performance.now` no JS e contagem de nós da AST).
- **V2 (Developer Experience):** Renderização visual de **Árvore ASCII** da AST diretamente em console (Python) e na UI (Javascript), presets interativos e painéis ricos para tratamento de erros sintáticos apontando Linha/Coluna.
- **Paridade JS ↔ Python:** A demonstração live no GitHub Pages conta com uma porta direta do motor Python em Javascript puro executando no navegador do usuário.


```python
# Exemplo: Pipeline de compilação
pipeline = CompilerPipeline(
    tokenizer=MyDSLTokenizer(),
    parser_factory=lambda tokens: MyDSLParser(tokens),
    executor=MyDSLExecutor(),
    semantic_analyzer=MySemanticAnalyzer(),
)

result, trace = pipeline.run(
    source='IF age > 18 AND status == "active" THEN approve',
    context={"age": 25, "status": "active"}
)
# result = True, trace = {type: "block", children: [...]}
```

📖 [Ver código completo →](compiler/)

---

### 2. Middleware Stack (`middleware/`)

Middlewares de produção para APIs FastAPI/Starlette:

- **🛃 Customs (Alfândega)** — Sanitiza payloads de integrações externas, bloqueia campos perigosos (`__import__`, `eval`, `exec`), aplica size limits e adiciona headers de auditoria
- **🔁 Idempotency** — Previne operações duplicadas usando Redis com lock distribuído (`SET NX`) e TTL
- **⏱️ Rate Limiter** — Sliding window com Redis sorted sets, limites diferenciados por tipo de rota (auth, webhook, API geral)

```python
# Idempotência: decorar qualquer endpoint
@idempotence(endpoint="create_order", ttl=10)
async def create_order(request: Request, payload: OrderCreate):
    ...  # Executado no máximo 1 vez por payload idêntico dentro da janela

# Rate Limiting: sliding window automático
# Auth: 10 req/min | Webhooks: 300 req/min | API: 100 req/min
```

📖 [Ver código completo →](middleware/)

---

### 3. Integration Layer (`integrations/`)

Sistema de **plugins com auto-discovery**, baseado em Hexagonal Architecture (Ports & Adapters):

```
Interface (Port)  →  Registry (Decorator)  →  Discovery (Startup)  →  Resolver (Runtime)
     │                      │                        │                       │
  IPaymentGateway    @integration_provider     sync_to_db()        resolve(tenant_id)
  IMessagingProvider  registra adapter         sincroniza com DB    retorna instância
  IShippingProvider   na inicialização         marca órfãos         com credenciais
```

**Features:**
- Decorator `@integration_provider("payment.stripe")` para registro zero-config
- Auto-discovery na inicialização (importa adapters → registra → sincroniza DB)
- Resolução por tenant com fallback para defaults
- Suporte a múltiplos provedores do mesmo tipo (ex: Stripe + MercadoPago)

📖 [Ver código completo →](integrations/)

---

### 4. Governance Layer (`governance/`)

Patterns de **governança e DDD** para sistemas multi-domínio:

- **Constitution** — Regras pétreas (invariantes) que nenhum módulo pode violar, com decorator + enforcement imperativo
- **Mediator (Diplomat)** — Mediação de conflitos entre domínios com resolução por precedência hierárquica

```python
# Regra pétrea: nenhuma venda sem autenticação
@invariant_guard(InvariantRule.REQUIRE_AUTHENTICATION, domain="ordering")
async def create_order(request, current_user=Depends(get_current_user)):
    ...  # Se current_user for None → InvariantViolation automaticamente

# Mediação: conflito entre domínios
verdict = mediator.mediate(
    reason=EscalationReason.CONFLICT,
    source_domain="ordering",
    target_domain="billing",
    conflicting_rules=[rule_a, rule_b],
)
# verdict.decision = ALLOW (regra de nível PLATFORM vence MODULE)
```

📖 [Ver código completo →](governance/)

---

### 5. Cognitive Pipeline (`cognitive/`)

Contratos abstratos para um **pipeline de NLP multi-estágio**:

```
Input → [Interceptors] → [FAISS Cache] → [Intent Classifier] → [LLM Fallback] → [Domain Strategy] → Output
         determinístico    semântico       local                   IA                negócio
```

- Separa **infraestrutura cognitiva** de **lógica de domínio** via `DomainStrategy`
- InterceptHandlers resolvem sem ML (menus, formulários)
- Observabilidade granular por estágio (latências, fonte, fallback_reason)

📖 [Ver código completo →](cognitive/)

---

## 🧪 Executando os Exemplos

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/portfolio-backend-python.git
cd portfolio-backend-python

# Instale dependências (mínimas)
pip install -r requirements.txt

# Execute os exemplos
python -m examples.compiler_demo
python -m examples.middleware_demo
```

---

## 🏛️ Decisões Arquiteturais

### Por que um Pratt Parser em vez de regex simples?
Regex funciona para regras triviais (`IF x == y`), mas quebra com precedência de operadores (`a AND b OR c`), parênteses aninhados, e expressões compostas. O Pratt Parser escala elegantemente e permite extensão sem reescrever a gramática.

### Por que Hexagonal Architecture nas integrações?
Trocar um provedor de pagamento (ex: Stripe → MercadoPago) deve ser uma operação de **configuração**, não de **código**. Os Ports (interfaces) garantem que todos os adapters implementam o mesmo contrato, e o Resolver escolhe qual usar em runtime baseado no tenant.

### Por que "Regras Pétreas" como pattern?
Em sistemas com múltiplos domínios, módulos e agentes, existem invariantes que **nunca** podem ser violadas — independente de quem está executando. A Constitution centraliza essas invariantes e fornece enforcement via decorator (declarativo) ou imperativo (check manual), garantindo segurança mesmo quando novos módulos são adicionados.

---

## 📝 Stack Utilizada

- **Python 3.11+** — Typing moderno com `dict[str, Any]`, `list[str]`, `tuple[T, ...]`
- **FastAPI / Starlette** — Framework web async (usado nos middlewares)
- **Redis** — Cache, rate limiting, idempotência, sessões
- **SQLAlchemy** — ORM async (mencionado na discovery)
- **ABC + dataclasses** — Contratos tipados e imutáveis
- **FAISS** — Busca vetorial para similaridade semântica (mencionado no cognitive)

---

## 📄 Licença

MIT — Sinta-se livre para usar, modificar e distribuir.
