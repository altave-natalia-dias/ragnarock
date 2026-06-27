# Zomato / Eternal — Bug Bounty Recon (HackerOne)

**Programa:** Eternal (HackerOne) — Zomato, Blinkit, Hyperpure, District, runnr.in  
**Campanha Ativa:** IDOR + LLM/AI — **1.5x bônus até June 29, 2026**  
**Data da Sessão:** 2026-06-27

---

## Superfície de Ataque Mapeada

### mcp-server.zomato.com — MCP OAuth + AI Integration

| Endpoint | Status | Notas |
|----------|--------|-------|
| `/.well-known/oauth-authorization-server` | 200 | OAuth metadata completo exposto |
| `/authorize` | 307 → /consent | Valida `state` param |
| `/token` | 200 | Token exchange |
| `/register` | 403 (WAF) | Dynamic Client Registration — testável via browser |
| `/mcp` | 401 | MCP endpoint — uvicorn (Python FastAPI) |
| `/staging/mcp` | 401 | Staging ativo em produção! |
| `/health` | 200 | `{"status":"healthy"}` público |
| `/login` | 200 | JS inline com bugs de segurança |
| `/mcp` OPTIONS | 200 `ACAO:*` | CORS aberto + todos os métodos |

**Server Stack:** uvicorn (Python ASGI), Akamai Bot Manager (`_abck`, `bm_sz` cookies)

**Tools MCP Confirmadas (via análise estática do consent page JS):**
- `get_saved_addresses_for_user` — PII (endereços salvos)
- `checkout_cart(cart_id)` — financeiro (checkout não autorizado)
- `bind_user_number` — ATO (vincula telefone)
- `get_all_restaurants` — **ponto de injeção** (retorna dados DB Zomato)
- `search_restaurants` — **ponto de injeção**

---

### api.hyperpure.com — B2B Food Supply Platform

**Descoberta Chave:** APIVersion padrão = **`12.1`** (extraído do Next.js bundle `_app-20be4c355a52a43d.js`)

**Header Stack Necessário:**
```
APIVersion: 12.1
AppType: consumer (ou supplier, partner_web)
X-Client: consumer
HeaderRoute: v2
```

**Public Token (encontrado em bundle anterior):** `pub944c743a8bd2f89f03a2ef396117435b`

| Endpoint | Status sem Auth | Notas |
|----------|-----------------|-------|
| `/consumer/v2/categories` | **200** | Dados de categorias públicos |
| `/consumer/cities/serviceable` | **200** | Cidades atendidas |
| `/consumer/logout/config` | **200** | Config da UI (tracking metadata) |
| `/consumer/logout/landing-page-details` | **200** | Marketing content |
| `/consumer/entities?type=SEARCH` | **200** | Empty search state |
| `/consumer/v1/digital_pod` | **400** | "Invalid order delivery action link" — requer token assinado |
| `/consumer/ownerDetails` | 401 | Owner PII — requer auth |
| `/consumer/zomato_credit_line/dues` | 401 | Financial — requer auth |
| `/consumer/zomato_credit_line/transactions` | 401 | Financial — requer auth |
| `/account/paymentinfo?outletId=1` | 401 | Payment info — requer auth |
| `/consumer/payment/details?identifier=1` | 401 | Payment details — requer auth |
| `/public/api/scm_app/wms/power_rangers/groups` | 404 | Endpoint não encontrado |
| `devapi.hyperpure.com/*` | 475 sem APIVersion / 4xx com | Dev API acessível externamente |

**Server:** Envoy (prod), hp-http-kuma-gateway (dev)  
**CDN:** CloudFront (`d3uc069fcn7uxw.cloudfront.net`)

---

### runnr.in — Delivery Logistics (Ruby on Rails)

| Endpoint | Status | Notas |
|----------|--------|-------|
| `/admin/login` | 200 (403 no body) | Admin panel — IP restricted |
| `/tracking/*` | Redirect → /admin/login | Admin-only |
| `bugbounty.runnr.in` | 500 | Dedicated test env — broken |

**Stack:** Ruby on Rails + Token realm auth

---

## Achados Confirmados

| ID | Arquivo | Sev | CVSS | Target | Campanha | Status |
|----|---------|-----|------|--------|----------|--------|
| ZO1 | `ZO1_mcp_indirect_prompt_injection.md` | HIGH | 8.1 | `mcp-server.zomato.com/mcp` via `get_all_restaurants` | LLM/AI 1.5x | Rascunho |
| ZO2 | `ZO2_mcp_dynamic_client_registration_open.md` | HIGH | 8.1 | `mcp-server.zomato.com/register` | - | Necessita confirmação (Postman) |
| ZO3 | `ZO3_mcp_consent_param_injection.md` | MEDIUM | 6.1 | `mcp-server.zomato.com/login` JS | - | Rascunho |
| ZO4 | `ZO4_staging_mcp_endpoint_production.md` | LOW | 4.3 | `mcp-server.zomato.com/staging/mcp` | - | Confirmado |

---

## Próximas Investigações (Antes do Deadline June 29)

### Imediatas (Alta Prioridade)

1. **[ZO2] Testar /register via Postman** — abrir `mcp-server.zomato.com/register` via browser com UA real, registrar cliente com redirect_uri malicioso → confirmar se aceita sem auth
2. **[ZO3] PoC do param override** — abrir `mcp-server.zomato.com/login?otp=000000` e capturar POST no DevTools, verificar se URL param substitui o OTP digitado
3. **[IDOR Hyperpure] Criar conta Hyperpure** — login com conta própria, capturar token → testar `/consumer/ownerDetails`, `/consumer/zomato_credit_line/transactions` com `outletId` de outra conta

### Secundárias

4. **runnr.in Rails endpoints** — a app Rails tem uma superfície de ataque clássica, precisa de acesso via VPN India ou proxy
5. **MCP checkout_cart IDOR** — criar dois carts com contas diferentes, testar cross-checkout com token de Account A no cart_id de Account B
6. **Zomato main API IDOR** — `api.zomato.com` (separado do MCP) pode ter IDOR em order/address endpoints

---

## Estimativa de Recompensa

| Finding | Base Tier | Campanha 1.5x | Estimativa |
|---------|-----------|---------------|------------|
| ZO1 — MCP Prompt Injection (LLM/AI HIGH) | $2k-$4k | 1.5x | **$3k-$6k** |
| ZO2 — Dynamic Client Registration (HIGH) | $2k-$4k | - | **$2k-$4k** |
| ZO3 — Param Injection (MEDIUM) | $500-$1k | - | **$500-$1k** |
| ZO4 — Staging Exposure (LOW) | $100-$300 | - | **$100-$300** |

**Total potencial: $5.6k-$11.3k**

---

## Recon Técnico Chave

### OAuth Flow Completo

```
1. GET /authorize?client_id=X&redirect_uri=CLIENT_URI&response_type=code&scope=mcp:tools&state=S&code_challenge=C&code_challenge_method=S256
→ 307 /consent?error=... (sem params válidos)
→ 200 /login (com params válidos) — HTML+JS consent page

2. POST /login → envia phone/email → OTP via SMS
3. POST /verify-otp → verifica OTP → completa auth → retorna redirect com code
4. GET redirect_uri?code=AUTH_CODE → cliente captura code
5. POST /token grant_type=authorization_code&code=AUTH_CODE&... → Bearer token
6. POST /mcp Authorization: Bearer TOKEN → chama tools
```

### JS Vulnerabilidades Confirmadas (Consent Page)

```javascript
// 1. Spread operator vulnerability
body: JSON.stringify({ otp, id, type, login_challenge, ...queryParams })

// 2. Staging detection em produção
if (currentPath.startsWith('/staging')) return `/staging${path}`;

// 3. Hardcoded fallback
return urlParams.get('login_challenge') || 'default_challenge';

// 4. Open redirect (dois vetores em sendOTP)
window.location.href = response.url;
window.location.href = result.redirect_uri || result.redirect_url;
```

### Hyperpure Next.js Bundle Key Constants

```javascript
// _app-20be4c355a52a43d.js — extraído
let y = 12.1;  // DEFAULT API VERSION
// ...
p.APIVersion = y;
p.AppType = "partner_web" || "consumer" || "web";
headers: {
    "X-Client": "consumer",
    "X-TrackingId": randomUUID(),
    "HeaderRoute": "v2",
    "APIVersion": 12.1,
    "AppType": "consumer"
}
```
