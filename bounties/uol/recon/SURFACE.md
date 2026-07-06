# UOL (UOLCS) — Attack Surface — 2026-07-05

## Infra / fingerprint (in-scope, curl-accessible, no CF except noticiasdatv)
| Host | Tech | Estado |
|---|---|---|
| conta.uol.com.br | React SPA (CRA) SSO + social JWT + MFA + mcaptcha | login |
| mail.uol.com.br + webmail hosts | login → conta SSO (`?t=uol_webmail&env=visitante&dest=`) | auth-gated |
| meupainelhost.uol.com.br | micro-frontend (SystemJS + import-map-overrides) + mcaptcha | login |
| meupainelhost-api.uol.com.br | **DNS NÃO resolve** (in-scope não-roteável) | n/a |
| partnership/ingress.service.uol.com.br | HTML genérico | in-scope |
| ne10 / brasilescola (nginx), noticiasdatv (CF), caras | CMS conteúdo, busca JS-rendered | in-scope |

## conta.uol.com.br SSO (alvo 0-click ATO R$20k) — testado
### postMessage — SEGURO
- Sender: `window.opener.postMessage("authenticatedUserWithSuccess", window.location.origin)` — targetOrigin = própria origem, sem token no payload.
- Receiver: `addEventListener("message", e => { if("https://conta.uol.com.br"!==e.origin) return; ... })` — origin estrito.
- `postMessage(...,"*")` no vendor = shims axios/setImmediate (não relevante).

### `dest` redirect (open-redirect/XSS) — SEGURO / VALIDADO
- Flui p/ `DoRedirectHandler(dest)` → `window.location.href=dest`, sem filtro de scheme visível no client.
- **MAS servidor valida robustamente** (status codes):
  - `dest=https://mail.uol.com.br/...` (uol) → 200
  - `dest=https://example.com` → 400 ; `dest=//example.com` → 400
  - `dest=javascript:alert(1)` → **403** ; `dest=data:...` → 400
  - `dest=https://evil.uol.com.br.attacker.com` → 400 (sem bypass substring)
- Verdito: allowlist de domínio uol + bloqueio de scheme + anti-substring. Não explorável.

## Content sites
- brasilescola `/busca/?q=` e ne10 `/search/?q=` → reflexão apenas URL-encoded (href canônico); busca renderizada client-side. Sem reflected XSS simples. DOM/API XSS exigiria crawl profundo com browser.

## Blockers → high-value exige autenticação
1. Webmail email-body XSS (R$10k) + email IDOR read (R$20k): precisam de sessão webmail logada. Sanitizer de HTML está em JS pós-login.
2. meupainelhost (painel host): micro-frontend atrás de login (import-map-overrides = vetor potencial pós-auth).
3. conta social-login/OAuth ATO: fluxo interativo pós-conta.
- **Conta de teste BOL grátis** = interativa (mcaptcha `isInvis`, email/CPF) → enabler dos bugs grandes.

## Verdito parcial (não-auth)
SSO conta.uol.com.br bem endurecido (postMessage + dest validados). Superfície não-auth madura. Todo o valor Medium+ (webmail XSS/read, painel host) está auth-gated — precisa da conta de teste.

## Content sites hunt (no-account) — 2026-07-05
- **brasilescola** (Vite/Laravel SPA): `/busca?q=` reflects query **double-HTML-encoded** (`&amp;lt;img`) — proper output encoding, no XSS. Articles = static `.htm` (no numeric-ID SQLi param). `/wp-json` 301.
- **ne10** (v2.2.3): `/search/?q=` no reflection of query in rendered DOM. app.min.js DOM sinks `.html()`×11/`innerHTML`×4 consume JSON from *.ne10.uol.com.br subdomains (api.enem/jc/sjcc — OUT OF SCOPE, only ne10.uol.com.br listed). No injectable in-scope param.
- **noticiasdatv** (Cloudflare): has /busca, /buscar.
- **caras**: DNS 000 (not reachable).
- Verdict: content sites use modern stacks with proper output encoding; no Medium+ reflected/DOM XSS or SQLi surfaced unauth. In-scope is strictly the apex host (subdomain feeds OOS).
