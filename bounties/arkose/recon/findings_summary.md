# Arkose Labs — Recon Session 2026-06-27

## Superfície de Ataque Mapeada

### iframe.arkoselabs.com — FULLY ANALYZED
```
GET / → 200 HTML (4371 bytes)
  Headers:
    content-security-policy: ...'nonce-ea1059e09780776c4a6301e8867454e2'...
    permissions-policy: accelerometer=*, autoplay=*, ...  (permissivo!)
    x-cache: Hit from cloudfront (age: 8645+)
    NO x-frame-options! (pode ser embedded em qualquer site — intencional)
  
  HTML: Completo publicado — contém TODO o código JS inline
    - getLocation(): extrai ancestor origin
    - uuidv4(): gera session ID aleatório
    - observabilityLog(): POST para /metrics/ui
    - getAllUrlParams(): processa theme, mkt, data, nosuppress
    - getClientKey(): extrai publicKey do URL path
    - loadArkoseScript(): carrega client-api.arkoselabs.com/v2/{key}/api.js
    - setupEnforcement(): configura o challenge via setConfig()
    - postMessage("*") em TODOS os 8 eventos!

GET /v2/DEMO/2.17.6/enforcement.cdeb82f474225dff1677448c6bc82e87.html → 200
  nonce: 2e86232d80ec842350915967bb1e356d (TAMBÉM ESTÁTICO)
  x-cache: Miss from cloudfront (mas nonce ainda estático — baked em S3)
```

### client-api.arkoselabs.com — PARTIALLY ANALYZED
```
GET / → 404 (CloudFront error)
  access-control-allow-origin: *
  x-frame-options: SAMEORIGIN
  accept-ch: Device-Memory, Sec-CH-UA, ...  (fingerprinting extensivo)
  
GET /v2/api.js → 200 (73426 bytes proprietário, minificado)
GET /v2/DEMO/api.js → 200 (mesmo conteúdo)
  - versão: 2.17.6
  - enforce URL: .../enforcement.cdeb82f474225dff1677448c6bc82e87.html
  - DOM sinks: NENHUM innerHTML/eval encontrado
  - cssText injection: webpack CSS module (não user-controlled)
  - styleTheme: armazenado em config, não refletido em DOM

GET /metrics/ui → 400 "Bad Request."
POST /metrics/ui (JSON válido) → 200 "OK."  ← AR1!
  access-control-allow-origin: *
  
GET /v2/status → 403 (existe!)
GET /v2/enforce, /v2/session, /v2/verify, /v2/challenge, /v2/token → 403 (existem!)
GET /v2/api.js → 200
```

### verify.arkoselabs.com — ANALYZED
```
GET / → 404
  access-control-allow-origin: *  ← CORS aberto!

OPTIONS /v4/verify → 200
  access-control-allow-origin: *
  access-control-allow-methods: GET, HEAD, POST, OPTIONS
  access-control-allow-headers: Content-Type,Authorization
  access-control-max-age: 86400

POST /api/v4/verify (private_key=test&session_token=test) → 400
  content-type: application/json
  access-control-allow-origin: *
  arkose-verify: solved=false; session=; error=DENIED ACCESS;
  version: 2.0
  sregion: us-east-1
  hackers: www.arkoselabs.com/whitehat/
  {"error":"DENIED ACCESS","verified":"2026-06-27T18:09:53Z"}
  
Endpoint real: /api/v4/verify (retorna 400 com corpo revelador)
```

### portal.arkoselabs.com — PARTIALLY ANALYZED
```
GET /login (curl sem UA) → 403 (WAF blocks bots!)
GET /login (browser UA) → 200 HTML (1454 bytes React SPA)
  
CSP revela:
  auth0: arkoselabs.us.auth0.com
  internal API: portal-prod.arkoselabs.com
  AWS API GW: *.execute-api.us-east-2.amazonaws.com/demo/verify
  
API paths:
  /api → 400 {"errors":[{"message":"Query hash is required..."}]}
  /api/v1 → 400 {"errors":[{"message":"Query hash is required..."}]}
  /graphql → 403
  /auth → 403
  /login → 200
  /.well-known/openid-configuration → 403
  /api/users/me → 400

CORS: API reflete origin apenas para arkoselabs.com origins (correto)
Tech: React SPA, Auth0, Envoy, CloudFront
Auth0 OIDC discovery: arkoselabs.us.auth0.com/.well-known/openid-configuration
  - Grant types: authorization_code, implicit, password, refresh_token, device_code
  - PKCE: S256 + plain (plain é mais fraco)
  - Dynamic client registration: disabled
  - JWKS: 2x RS256
```

### customer-sessions.arkoselabs.com — DEAD END
```
Todos os paths retornam 404
Endpoint provavelmente requer auth ou IP allowlist
CORS: ACAO:* na 404 (equal to client-api pattern)
```

### www.arkoselabs.com — NON-CORE (marketing)
```
Webflow + Cloudflare
Set-Cookie: _cfuvid (Cloudflare)
Sem achados
```

## Achados Confirmados

| ID | Tipo | Sev | Endpoint | Confirmado |
|----|------|-----|----------|------------|
| AR1 | CORS Open + Unauth Data Injection | MEDIUM (5.3) | `client-api.arkoselabs.com/metrics/ui` + todos customer subdomains | Sim |
| AR2 | Static CSP Nonce | LOW (3.7) | `iframe.arkoselabs.com` | Sim |
| AR3 | postMessage("*") sessionToken broadcast | MEDIUM (5.4) | `iframe.arkoselabs.com` | Sim (fonte pública) |
| AR4 | CDN Debug Interface Exposed | LOW (4.3) | `cdn.arkoselabs.com/v2/` | Sim |

## Novos Subdomínios Descobertos (CT Logs — 107 total)

### De interesse (acessíveis):
- `connect.arkoselabs.com` → 302→www.arkoselabs.com (F5 BIG-IP + New Relic + Cloudflare)
- `api.arkoselabs.com` → 404 (mas /v2/api.js → 200)
- `blizzard-api.arkoselabs.com` → /v2/api.js 200, /metrics/ui POST 200 (CORS open)
- `epic-games-api.arkoselabs.com` → /v2/api.js 200, /metrics/ui POST 200 (CORS open)
- `boa-api.arkoselabs.com` → /v2/api.js 200, /metrics/ui POST 200 (CORS open)
- `boa-verify.arkoselabs.com` → /api/v4/verify POST 500 (internal error — sem CORS)
- `verify.azure.arkoselabs.com` → 403 (Azure WAF)
- `client-api.azure.arkoselabs.com` → 403 (Azure WAF)
- `client-api-secondary.azure.arkoselabs.com` → 403 (Azure WAF)

### DNS falhou (provavelmente interno ou removido):
- portal-dev.arkoselabs.com, portal-staging.arkoselabs.com
- argocd.eks.*, sonarqube, grafana.*.development.*
- dashboard, tableau, arkosepremium, smart, secure-ticket

### Análise do portal bundle:
- `portal.arkoselabs.com` main bundle (161KB): webpack chunk lazy-loader
- Auth0 client_id NÃO encontrado no bundle público — está nos chunks privados de portal-account-mgmt.arkoselabs.com (403)
- Module Federation: portal usa `portal-account-mgmt.arkoselabs.com/moduleEntry.js` (142KB, público)
- GTM-WWF97SXH auth=mksZSJ001FPSw_YdROG2wQ: GA IDs (Live: G-JKV91RBM5H, Dev: G-636YPBX3DE, Staging: G-WHCSPSP27P)
- CDN debug page `cdn.arkoselabs.com/v2/` = index.html serve para qualquer diretório /v2/*

## Próximas Investigações (requer conta)

1. **Portal Auth0 client_id** — Necessário para testar:
   - redirect_uri bypass em arkoselabs.us.auth0.com
   - PKCE `plain` downgrade
   - Token reuse

2. **Portal JS bundle** — Acessível apenas via browser autenticado:
   - Buscar por endpoints hardcoded
   - GraphQL queries (para persisted queries bypass)
   - API key / Auth0 client_id embedded

3. **AWS API Gateway** `*.execute-api.us-east-2.amazonaws.com/demo/verify`:
   - Precisa do ID específico da função
   - Pode ter auth bypass no path `/demo/verify`

4. **portal-prod.arkoselabs.com** — IP allowlisted:
   - Se acessível, provavelmente é a API REST sem WAF
   - Tentar via VPN ou proxy AWS us-east-1/2
