# Red Bull — Bug Bounty (Intigriti)

**Programa:** Intigriti (Red Bull)  
**Recompensa:** Red Bull cans — MEDIUM=1 tray, HIGH=3 trays, CRITICAL=6 trays, Exceptional=Red Bull surprise  
**Regras críticas:** Apenas domínios listados explicitamente, max 5 req/seg, sem scanners automáticos, sem ferramentas de enumeração de domínios

---

## Escopo Explorado

| Domain Group | Status |
|---|---|
| `*.flyingbulls.at` | ✅ Explorado — RB1 encontrado |
| `*.flyingbulls.com` | 🔍 Parcial |
| `*.rbleipzig.com` | 🔍 Parcial — diversas apps mapeadas |
| `*.redbull.com` | ⏳ Pendente |
| `*.redbullracing.com` | ⏳ Pendente |

---

## Findings

### RB1 — Directus 10.11.0: Acesso Anônimo a PII de Pilotos + Aeronaves
**Severidade:** MEDIUM (CVSS 5.3) | **Impacto Negócio:** HIGH — violação GDPR  
**Target:** `directus.flyingbulls.at` (escopo: `*.flyingbulls.at`)  
**CWE:** CWE-284 (Improper Access Control) / CWE-200  
**Arquivo:** `reports/RB1_directus_anonymous_data_exposure_flyingbulls.md`

**Resumo:** CMS Directus 10.11.0 da Flying Bulls (empresa de aviação histórica do Red Bull) expõe coleções sensíveis sem autenticação via API REST pública (`/items/{collection}`):
- **26 pessoas** com dados pessoais: nome completo (`firstname`, `lastname`), tipo (pilot/engineer/friend), horas de voo, ano do primeiro voo
- **25 aeronaves** com número de série (`serial_number`), matricula (`registration`), fabricante, especificações técnicas completas
- **100+ arquivos** incluindo fotos dos pilotos
- **OpenAPI spec completa** acessível sem auth, mapeando todos os 47 endpoints

**GDPR:** Flying Bulls GmbH é empresa austríaca. Art. 25 GDPR (Privacy by Design) e Art. 32 (medidas técnicas de segurança) violados. Penalidade: até €20M ou 4% receita global anual.

**CVEs relevantes na versão 10.11.0:** CVE-2024-34709 (bypass de access control via field permissions, HIGH 8.1) e CVE-2024-38361 (SSRF, HIGH 8.8).

---

## Recon por Domínio

### flyingbulls.at / flyingbulls.com

| Host | Status | Stack | Finding |
|------|--------|-------|---------|
| `directus.flyingbulls.at` | ✅ 200 | Directus 10.11.0 | **RB1** — anonymous API access |
| `directus.flyingbulls.com` | 404 | nginx | — |
| `admin.flyingbulls.at` | 302 | Apache 2.4.58 + PHP 7.4 (EOL) | → webmail.mymagenta.at |
| `kiosk.flyingbulls.at` | 401 | nginx (HTTP Basic Auth) | Kiosk com Basic Auth |
| `api.flyingbulls.at` | 403 Akamai | Akamai WAF + nginx | CORS headers (ACAO: * + ACAC: true) antes do WAF |
| `flyingbulls.at` | — | — | Site público |

### rbleipzig.com

| Host | Status | Stack | Observação |
|------|--------|-------|-----------|
| `api-p.rbleipzig.com` | 200 | Next.js + GCP | GraphQL em `/graphql` (405 GET, 200 POST) |
| `cashless.rbleipzig.com` | 200 | Spring Boot (Profipay) | Pagamento cashless (Adyen, Payone, PayPal, Profipay) |
| `cashless.rbleipzig.com/api/v2/config` | 200 sem auth | — | Config exposição (feature flags, sem credentials) |
| `fanexperience.rbleipzig.com` | 200 | Remix.run + MUI | Payment session + leaderboard sem auth check |
| `b2b-approval-portal.rbleipzig.com` | 200 | SvelteKit + Azure AD | B2B approval portal Microsoft SSO |
| `api.b2b-approval-portal.rbleipzig.com` | 200 | Fastify (GCP) | ACAO: * hardcoded; `/api/health` = 200 |
| `awayportal.rbleipzig.com` | 200 | React (GCS static) | Away ticketing platform |
| `ofc.rbleipzig.com` | 200 | Next.js | OFC fan club portal |
| `guest-management.rbleipzig.com` | 200 | Angular + nginx | Guest management SPA |
| `brand.rbleipzig.com` | 302 | Frontify | Brand management (auth required) |
| `data.rbleipzig.com` | 200 | GetResponse | Email marketing platform |
| `cms.rbleipzig.com` | 401 | Basic Auth | CMS protegido |
| `cdp-api.rbleipzig.com` | — | Bloomreach CDP | — |

### redbull.com

| Host | Status | Stack | Observação |
|------|--------|-------|-----------|
| `iam.redbull.com` | 302→logon | F5 BIG-IP APM | SSO/SAML protegido |
| `iam-api.redbull.com` | 302→logon | F5 BIG-IP APM | SSO/SAML protegido |
| `auth.redbull.com` | — | Okta custom domain | — |
| `login.redbull.com` | — | Auth0 custom domain | — |
| `jenkins-core.redbull.com` | 404 | BigIP | Jenkins não encontrado |
| `jenkins.app.redbull.com` | timeout | — | Sem resposta |

---

## Notas Técnicas

### GraphQL em api-p.rbleipzig.com
- Endpoint: `POST https://api-p.rbleipzig.com/graphql`
- `{ __typename }` → retorna `"Query"` (sem auth)
- `{ __schema { ... } }` → parcialmente bloqueado (intrínseca restrita mas tipo `__typename` funciona)
- Query `news` detectada via erros: `news(language, platform, dateRange, pageNumber)` → `NewsOverviewResponse` com `ArticleCardElementDto`
- `dateRange` é enum `NewsOverviewDateRange` (valores não descobertos)
- Dados: notícias públicas de futebol — NOT sensitive
- **Não é finding reportável** (conteúdo público)

### fanexperience.rbleipzig.com — Remix Routes
- Plataforma multi-tenant de fan experience (RBLeipzig, Bayer04, PSG Qatar, SAP Garden)
- Rotas descobertas via manifest: `/api/createPaymentSession`, `/api/getProductAndPriceData`, `/api/publishLeaderboardScore`, etc.
- Todas retornam "Failed to..." (sem 401/403) — processam sem auth mas falham em lógica de negócio
- Possível manipulação de leaderboard SE formato correto for descoberto

### SAP CDC (Gigya) API Key no OFC Portal
- Key: `4_Y3WsK8FpTngMbKQi3Q2LQA` (EU1 datacenter)
- Acesso público esperado (SAP CDC web SDK design intencional)
- `getSchema` → OK (77 data fields incluindo child.FSC.*, youth accounts)
- `search`, `getAccountInfo`, `getSiteConfig` → 403 (requer secret key)
- **Não é finding** — design esperado do SAP CDC

---

## Targets Prioritários (próximas sessões)

```
directus.flyingbulls.com   → 404 (pode ter vhost diferente) — investigar
medical.redbullperformance.com → F5 BIG-IP (dados médicos de atletas!)
pitwall.redbullracing.com  → Heroku 401 (sistema pit wall F1)
esps.redbullpowertrains.com → Red Bull Powertrains (F1 engines)
account.redbullmediahouse.com → Red Bull Media House accounts
cms.redbullcontentpool.com → Content Pool CMS
partner.redbullmediahouse.com → Partner portal Media House
```

---

## Stack Técnico por Produto

```
flyingbulls.at:
  Directus 10.11.0         (CMS — headless, anonymous read)
  nginx                     (web server)
  Akamai                    (CDN/WAF em api.flyingbulls.at)
  Apache 2.4.58 / PHP 7.4  (admin.flyingbulls.at — EOL!)

rbleipzig.com:
  Next.js + GCP             (api-p — GraphQL)
  Spring Boot (Profipay)    (cashless — Adyen, Payone, PayPal)
  Remix.run + MUI           (fanexperience)
  SvelteKit + Azure AD      (b2b-approval-portal — MSAL.js)
  Angular (AngularCLI)      (guest-management, cashless)
  Frontify                  (brand)
  GetResponse               (data — email marketing)

redbull.com:
  F5 BIG-IP (LB + APM)     (IAM, SSO)
  Okta                      (auth.redbull.com — custom domain)
  Auth0                     (login.redbull.com — custom domain)
  Akamai                    (api.redbull.com, account.redbull.com)
```
