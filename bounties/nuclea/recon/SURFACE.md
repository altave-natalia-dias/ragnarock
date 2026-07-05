# Núclea/CIP-BANCOS — Attack Surface (Passo B+C) — 2026-07-05

## Recon summary
- crt.sh passive enum over 17 scope wildcards → **83 unique in-scope hostnames**, **58 resolvable**.
- Split: **45 public/routable**, **13 internal-only DNS leak** (RFC1918 `10.250.254.x`, `172.19.x`, CGNAT `100.72.97.x`).

## Tech stack (AWS-native)
- **Auth**: AWS Cognito everywhere. `auth.crcp.org.br` = Cognito Hosted UI (`x-amz-cognito-request-id`, `cognito-login.css`). redirect_uri validated → no open-redirect.
- **APIs**: custom **gRPC-gateway / Connect-RPC** — `Server: Private Server/1.1.x (MobiUp - NChain/NCotas)`. Errors as `{"code":5,"message":"Not Found"}` (grpc NOT_FOUND). Require auth.
- **api.crcp.org.br**: AWS **API Gateway** (`{"message":"Forbidden"}`).
- **Static**: Angular SPAs on **S3** (`portal.nucleachain.com.br`), `crcp.org.br`→S3 301→www. Akamai fronting several (`interop/hextweb/prdweb.crt4`, `be-*.nucleachain`).
- **institucional.nucleaassociacao.org.br**: Go backend on GCP (404 "page not found").

## Key JS intel (portal.nucleachain.com.br/main.a812c511dffdf108.js)
- Multi-module blockchain platform: modules `log`, `card`, `ecotas` w/ dev/homolog/production Cognito pools.
- **Production APIs**: `api.nucleachain.com.br`, `api.nuclea-cotas.com.br`.
- 3rd-party (OOS): `core.nuclea.*.supermup.com.br`.
- Internal ALB (non-routable): `internal-token-sympho-alb-hint-*.us-east-1.elb.amazonaws.com`.
- **Client-side RBAC**: `permissions.{network,template,transfer,users,workflow}` + `isAdmin` + `/admin` route → candidate for **server-side authz bypass** (needs a session to validate).
- Cognito User Pool IDs / App Client IDs (PUBLIC by design — not a finding alone): prod `sa-east-1_6a0oYxJr3`, `sa-east-1_lgMtHHDD7`, etc.
- reCAPTCHA siteKey (public). No hardcoded secret found (`webhookSecret=this.webhookSecret` = minified code refs, not a leak).

## Priority public API targets
| Host | Tech | Status | Note |
|---|---|---|---|
| api.nucleachain.com.br | MobiUp gRPC-gw | 401/200 | blockchain mint/transfer/workflow |
| api.nuclea-cotas.com.br | MobiUp NCotas | 404 | same framework |
| api.nucleaconecta.com.br | EC2 (98.84.102.192) | 401 JSON | direct EC2, not CDN |
| api-hext.nucleaconecta.com.br | EC2 (18.206.42.179) | 401 JSON | homolog |
| api.crcp.org.br | API Gateway | 403 | route/authorizer |
| auth.crcp.org.br | Cognito Hosted UI | 400 | needs OAuth params |

## Blocker
No test accounts + account creation prohibited → authenticated classes (IDOR/BOLA/privesc on gRPC APIs) hard to validate. Unauth surface is AWS-hardened (Cognito, API GW).

## Candidate leads (need validation / decision)
1. **Internal DNS leak** (13 hosts) — likely OOS ("info sem risco significativo"). Low.
2. **Client-side RBAC** on portal — needs a valid session to test server enforcement.
3. **api.crcp.org.br** API Gateway — unauth route enumeration (careful: scanner-like).
4. **S3 buckets** (nucleachain.com.br, crcp.org.br) — check public read/write ACL, listing.

## Out of scope confirmed
`*.supermup.com.br` (3rd party). Internal ELB. CVEs <45d.

## S3 ACL check (read-only, 2026-07-05)
- `nucleachain.com.br` (us-east-1): bucket EXISTS, list → 403 AccessDenied (hardened).
- `crcp.org.br` (sa-east-1): bucket EXISTS, list → 403 AccessDenied (hardened).
- `www.crcp.org.br`: NoSuchBucket (fronted by Akamai; no takeover).
- Verdict: **No S3 public-read/list misconfig.** No PUT/write attempted (data-safety rule).

## Passo C verdict
Unauthenticated surface is AWS-hardened. No confirmed vuln from unauth pass:
Cognito (redirect validated), API GW (Forbidden), gRPC APIs (auth-gated), S3 (not listable), no JS secrets.
Only low-value candidate: internal DNS leak (likely OOS).

## SPA deep-dive (Passo D, user-directed) — 2026-07-05
### portal.nucleachain.com.br (main.a812…js, 3.5MB)
- Blockchain platform (Rayls). Modules log/card/ecotas. Cognito per-env. Client-side RBAC.
### web-phd.nucleaconecta.com.br "Autoatendimento" (phd-monitoracao-angular)
- Webpack **Module Federation** host; prod remoteEntry hardcoded to `http://localhost:5101/remoteEntry.js` → broken dev-leftover config, NOT exploitable (localhost, not attacker domain). Note only.
- Chunk 879 config leaks:
  - API GW: `ks21eetafj.execute-api.sa-east-1.amazonaws.com/prod/servico_phd` (in-scope alias `api-phd.nucleaconecta.com.br/servico_phd`), + dev/hint/hext GWs (us-east-1).
  - S3: `phd-monitoracao-angular-s3-{dev,hext,hint,prod}` — all **403 AccessDenied on list** (hardened).
  - Cognito hosted domains + clientIds (public by design).
- servico_phd method paths built at runtime (not literal) + Cognito-gated → no unauth endpoint found.

## SESSION VERDICT
Thorough Passo A–D pass. **No confirmed reportable vulnerability.** Target = well-hardened AWS-native fintech (Rayls blockchain + Cognito + API GW + gRPC-gateway + private S3). High-value classes (IDOR/BOLA/privesc/RBAC) require an authenticated session; blocked by no-test-accounts + no-account-creation rule.
Non-findings noted: internal DNS leak (13 hosts, likely OOS), localhost remoteEntry (broken not exploitable).

## Option-2: remaining CDN-fronted SPA deep-dive — 2026-07-05
- Browser-header bypass of Akamai UA filter worked for S3-origin apps via /index.html.
- **renda.nucleaconecta.com.br** "Serviço de Análise de Renda" (income/credit analysis) — Angular Module Federation host. Same `remoteEntry: http://localhost:5101/remoteEntry.js` dev-leftover. Business logic + API config NOT in host chunks (901/705/656/558 = Angular/Material vendor only) → lives in unreachable MF remote. No endpoints/secrets recovered.
- hext-renda (homolog) = same app. web-phd-hext = same as prod web-phd.
- Runtime config probes (mf.manifest.json, assets/config.json, environment.json) → 403 AccessDenied (bucket grants read only on published keys; no ListBucket). Cannot confirm existence.
- Behind-WAF (Akamai Access Denied, no S3-origin bypass): hext-registro-imobiliario, www.nucleaconecta, www.crt4, www.saopauloconsig (302 loop→/home), www.nucleaportabilidade (404).

### Recurring non-finding
Multiple production micro-frontends (web-phd, renda) ship `remoteEntry: http://localhost:5101/remoteEntry.js` — broken dev config, NOT exploitable (localhost, not attacker-controllable). Note only, not reportable.

### Option-2 verdict
No new confirmed vuln. nucleaconecta micro-frontends are MF shells with business logic in an (unreachable) remote; S3 origins deny listing and non-published keys. WAF-fronted apps not bypassed with header trick alone.

## Option-1: WAF bypass → saopauloconsig SCC (Wicket/WebSphere) — 2026-07-05
- No domain-named or `<prod>-angular-s3-prod` origin buckets for saopauloconsig/portabilidade (all NoSuchBucket).
- **www.saopauloconsig.com.br is NOT S3/geo-blocked** — it's a Java app: `X-Powered-By: Servlet/3.1`, `JSESSIONID=0000..:xxxx` (IBM WebSphere), redirect `/home?0` = **Apache Wicket**. Earlier "Access Denied" was just the redirect loop w/o cookie. Reached full app via cookie jar.
- App = **"Serviço de Controle Consignação" (SCC)** — payroll-deduction loan portal. Login via ICP-Brasil cert (Lacuna Web PKI) + CAPTCHA (`/cipCaptchaImg`) + `/csrfTokenS`. Mobile app "SCC Consignado".
- Public flow **`servidor/ativar`** = first-access / account unblock. `metodoDesbloqueio` radio: value 0 = **E-mail**, value 1 = **Perguntas e Respostas** (security questions). Also step-2 Token.
- `functions.js` → `ConsultaAverbacaoPage`, `/consultar`, `/keepAlive`.

### High-value lead — NOT safely testable under RoE
First-access unblock via **security questions** on a payroll-loan portal = classic ATO/weak-recovery surface. Validation blocked: needs a real CPF (no test accounts) → would touch a real person's account (harm/compromise = prohibited); security-question guessing = brute-force (OOS). REQUIRES authorized test identity from program before any active test.

### Minor observations (NOT reportable)
- `X-Content-Security-Policy: default-src 'self'` = DEPRECATED header name → no effective CSP in modern browsers. But "missing security headers" is explicitly OOS.
- Duplicated cookie attributes (`HttpOnly;HttpOnly;Secure;SameSite=Lax;...`) — sloppy, not a vuln.

## Option-1 verdict
Reached a rich legacy Java target (SCC Wicket/WebSphere). Highest-value bug class (first-access ATO) is gated behind needing a test identity that RoE (no accounts, no harm, no brute-force) forbids establishing. No safely-validatable unauth vuln.
