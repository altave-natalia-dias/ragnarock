# Arkose Labs — Bug Bounty (HackerOne)

**Programa:** HackerOne — Arkose Labs  
**Plataforma:** HackerOne  
**Período:** 2026-06-27  

## Recompensas

| Tier | Low | Medium | High | Critical |
|------|-----|--------|------|----------|
| Core Apps | $100-300 | $301-750 | $2,500-5,000 | $5,001-7,000 |
| Non-Core | $50-100 | $101-300 | $301-500 | $501-750 |

## Scope

**Core:**
- `client-api.arkoselabs.com`
- `portal.arkoselabs.com`
- `iframe.arkoselabs.com`
- `verify.arkoselabs.com`
- `cdn.arkoselabs.com`
- `customer-sessions.arkoselabs.com`

**Non-Core:**
- `www.arkoselabs.com` (Webflow — marketing)
- `demo.arkoselabs.com` (marketing)

**OOS:**
- `status.arkoselabs.com`
- `developer.arkoselabs.com` (3rd party)

## Findings

| ID | Arquivo | Sev | Target | Status |
|----|---------|-----|--------|--------|
| AR1 | `AR1_metrics_ui_cors_injection.md` | MEDIUM | `client-api.arkoselabs.com/metrics/ui` | Rascunho |
| AR2 | `AR2_static_csp_nonce_iframe.md` | LOW | `iframe.arkoselabs.com` | Rascunho |

## Arquitetura Técnica

### Fluxo Arkose CAPTCHA
```
Integrador (ex: Roblox) → carrega api.js via publicKey
  → script: client-api.arkoselabs.com/v2/{publicKey}/api.js
  → cria iframe: iframe.arkoselabs.com/v2/{publicKey}/2.17.6/enforcement.*.html
    → iframe carrega challenge UI
    → usuário resolve
    → postMessage({"eventId":"challenge-complete","sessionToken":T}, "*")
  → integrador recebe token
  → servidor integrador chama verify API com privateKey + sessionToken
    → verify.arkoselabs.com/api/v4/verify
    → result: solved=true/false
```

### Stack por endpoint

| Endpoint | CDN | Server | Auth | CORS |
|----------|-----|--------|------|------|
| `client-api.arkoselabs.com` | CloudFront | — | publicKey via URL path | `ACAO: *` |
| `iframe.arkoselabs.com` | CloudFront | — | None | — |
| `verify.arkoselabs.com` | CloudFront | Envoy (us-east-1) | privateKey (form) | `ACAO: *` |
| `portal.arkoselabs.com` | CloudFront | Auth0 | Auth0 bearer | Reflected (allowlist) |
| `www.arkoselabs.com` | Cloudflare | Webflow | — | — |

### Portal Auth0 Discovery
- Tenant: `arkoselabs.us.auth0.com`
- JWKS: 2 RS256 keys (`CDv52bCRk_FzqZl8eBszA`, `9V6pFs7I07ZNKc_wEjrOT`)
- Grant types: `authorization_code`, `client_credentials`, `implicit`, `password`, `refresh_token`, `device_code`
- PKCE: `S256` + `plain`
- Registration: disabled
- Internal API: `portal-prod.arkoselabs.com` (timeout — possivelmente IP-restricted)

### iframe.arkoselabs.com — Arquitetura
- Root `/` → HTML 4371 bytes estático, `x-cache: Hit`, `age: 8645+`
- CSP nonce `ea1059e09780776c4a6301e8867454e2` (ESTÁTICO — baked em S3)
- Enforcement HTML `/v2/{key}/2.17.6/enforcement.*.html` → `x-cache: Miss`, nonce `2e86232d80ec842350915967bb1e356d` (TAMBÉM ESTÁTICO)
- `postMessage(data, "*")` em TODOS os 8 eventos (challenge-complete, loaded, shown, failed, suppressed, error, warning, iframeSize)
- Sem `X-Frame-Options` → pode ser embedded em qualquer site

### verify.arkoselabs.com
- Endpoint ativo: `POST /api/v4/verify`
- `ACAO: *` em todos os responses
- `OPTIONS /v4/verify` → `access-control-allow-headers: Content-Type`
- Response header revelador: `arkose-verify: solved=false; session=; error=DENIED ACCESS;`
- CORS permite verificação browser-side (intended ou não?)

### client-api.arkoselabs.com
- `/v2/api.js` → 200 (base JS)
- `/v2/DEMO/api.js` → 200 com 73KB de JS proprietário
- `/v2/enforce`, `/v2/session`, `/v2/verify`, `/v2/challenge`, `/v2/token` → 403
- `/metrics/ui` → **400 (GET), 200 OK. (POST válido)** — ACAO: *
- `/v2/status` → 403

## Recon Salvo

- `/tmp/arkose_api.js` — 73426 bytes (DEMO/api.js completo)
- `/tmp/portal_login.html` — 1454 bytes (portal login HTML)
