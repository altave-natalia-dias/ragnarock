# Anthropic Bug Bounty — HackerOne

**Plataforma:** HackerOne
**Data de início:** Maio 2026
**Resposta eficiência:** 98%
**Total pago:** $770,785
**Bounty médio:** $750–$1,400
**Top bounty range:** $3,700–$8,300

---

## Escopo

### Core Assets (Critical, Eligible)
| Asset | Reports | % |
|-------|---------|---|
| claude.ai | 53 | 16% |
| Claude Code (CLI) | 134 | 40% |
| api.anthropic.com | 5 | 2% |
| API & SDKs | 14 | 4% |
| Official Clients (iOS/Android/Desktop) | 23 | 7% |
| console.anthropic.com → platform.claude.com | 3 | 1% |

### Non-Core Assets (Critical, Eligible)
| Asset | Reports | % |
|-------|---------|---|
| Infrastructure & Internal Apps/Services | 21 | 6% |
| github.com/anthropics (92 repos) | 13 | 4% |
| support.anthropic.com → support.claude.com (Intercom) | **0** | **0%** |
| docs.anthropic.com → platform.claude.com/docs | 1 | 0% |
| Leaked Employee API Keys | 1 | 0% |
| Claude in Chrome (Extension) | 3 | 1% |
| Claude Desktop Extensions & MCP Servers | 3 | 1% |

---

## Infrastructure & Stack

| Info | Details |
|------|---------|
| **CDN/WAF** | Cloudflare (todos os principais subdomínios) |
| **api.anthropic.com** | Express (Node.js) via Cloudflare |
| **claude.ai** | Next.js SPA via Cloudflare |
| **platform.claude.com** | Next.js 14+ SPA |
| **resources.anthropic.com** | Next.js SPA via Cloudflare |
| **support.claude.com** | Intercom (Next.js help center) |
| **trust.anthropic.com** | Vanta (Soc 2 compliance) |
| **CloudFront CDN** | d20xtzwzcl0ceb.cloudfront.net, d3uc069fcn7uxw.cloudfront.net |
| **Analytics/Monitoring** | Datadog RUM + Browser Agent, GrowthBook (feature flags) |
| **CMS** | Sanity.io (headless CMS) |
| **Internal comms** | Slack (anthropic.enterprise.slack.com) |

---

## Subdomínios Descobertos

### anthropic.com (77 subdomínios — subfinder)

Key highlights:
| Subdomínio | Status | Notas |
|------------|--------|-------|
| www.anthropic.com | 200 | Site principal (Next.js) |
| api.anthropic.com | 403 | **ALVO PRINCIPAL** — OAuth, register, authorize |
| console.anthropic.com | 301 → platform.claude.com | Console API |
| platform.claude.com | 200 | Platform docs (Next.js) |
| support.anthropic.com | 301 → support.claude.com | **0 reports HackerOne** |
| support.claude.com | 200 | Intercom help center |
| docs.anthropic.com | 301 → platform.claude.com/docs | 1 report |
| resources.anthropic.com | 200 | Newsroom (Next.js) |
| trust.anthropic.com | 200 | Vanta compliance portal |
| research.anthropic.com | DNS | Research subdomain |
| staging.anthropic.com | DNS | Staging |
| status.anthropic.com | DNS | Status page? |
| billing.anthropic.com | DNS | Billing |
| partnerportal.anthropic.com | DNS | Partner portal |
| earlyaccess.anthropic.com | 403 | Early access (Cloudflare) |
| legal.anthropic.com | 302 | Legal (Cloudflare) |
| red.anthropic.com | 301 | Red team? (Cloudflare) |
| claude.anthropic.com | DNS | Claude subdomain |
| *.titanium.api.anthropic.com | DNS | STT inference farm (12 endpoints) |
| internal.api.anthropic.com | DNS | Internal API |
| api-backend.anthropic.com | DNS | Backend API |
| atlantis.c.anthropic.com | DNS | Atlantis (internal) |
| slackbot.anthropic.com | DNS | Slack bot |
| s3-frontend.he.anthropic.com | DNS | S3 frontend |
| artifactory.he.anthropic.com | DNS | Artifactory |
| metrics.anthropic.com | DNS | Metrics |
| www-cdn.anthropic.com | 404 | CDN |

### claude.ai (14 subdomínios — subfinder + crt.sh)
| Subdomínio | Status | Notas |
|------------|--------|-------|
| claude.ai | 200 | Chat principal |
| a-cdn.claude.ai | DNS | CDN |
| api.claude.ai | DNS | Internal API |
| a.preview.claude.ai | DNS | Preview |
| assets.claude.ai | DNS | Assets |
| downloads.claude.ai | DNS | Downloads |
| preview.claude.ai | DNS | Preview |
| staging.claude.ai | DNS | Staging |
| livepreview.claude.ai | DNS | Live preview |
| pivot.claude.ai | DNS | Pivot |
| www.claude.ai | 301 | Redirect |

---

## 🔴 Finding #1: ANTH-001 → Upgraded to AN-001 — DCR + Wildcard *.claude.ai

**Status:** Report COMPLETO em `reports/AN-001_unauth_dynamic_client_registration_oauth_ato.md`
**Endpoint:** `POST https://api.anthropic.com/register` + `/authorize`
**CVSS:** 7.5 HIGH (AC:H — backend MCP deprecated; seria 9.1 CRITICAL se ativo)
**Asset:** api.anthropic.com (Core — API)

**Novo vs ANTH-001:**
- ✅ ANTH-001 perdeu: `/authorize` aceita **qualquer** `*.claude.ai` subdomain (incl. `evil.claude.ai`, `attacker.claude.ai`)
- ✅ ANTH-001 afirmou "whitelist firme" — INCORRETO para subdomínios de claude.ai
- ✅ `/token` → 500 (não 400) para client_id válido + código falso — confirma DCR wired ao token exchange
- ⚠️ MCP gdrive backend → 410 deprecated — cadeia completa bloqueada no step 3
- ✅ Systemic design flaws: any future MCP server Anthropic deploys inherits same vulnerability

**Status do envio:** READY TO SUBMIT (mas atenção: ANTH-001 pode já estar triado)

---

## 🔴 Finding #2: AN-002 — Artifact Sandbox Escape (allow-same-origin + ProxyFetch)

**Status:** Report COMPLETO em `reports/AN-002_artifact_sandbox_escape_proxyfetch_storage.md`
**Asset:** `claude.ai` / `claudeusercontent.com` (Core)
**CVSS:** 8.2 HIGH
**Vulnerabilidade:** `sandbox="allow-scripts allow-same-origin"` na iframe de artifacts

**Cadeia de ataque:**
1. `allow-same-origin` + `allow-scripts` = artifact tem acesso ao `window.parent` (mesmo origin)
2. `window.parent.claude.sendConversationMessage()` — artifact injeta mensagens na conversa do usuário
3. `proxyFetch` bridge — sem allowlist de URL: artifact faz `fetch()` para QUALQUER URL via parent
4. `storageGet/List` — artifact lê/escreve todo o localStorage de `claudeusercontent.com`

**PoC pronto (ver report)**. Imediato — não depende de infraestrutura depreciada.
**Status do envio:** READY TO SUBMIT

---

## 🔍 Finding #3 (renamed): ANTH-002 — Internal Event Logging Endpoint Exposed

**Status:** PARA INVESTIGAR (precisa de conta)
**Endpoint:** `POST https://api.anthropic.com/api/event_logging/v2/batch`
**Descoberto via:** JS bundle analysis em platform.claude.com
**Evidência:** GET → 405 (Method Not Allowed), POST → 400 `events: Field required`
**Potencial:** Se aceitar eventos sem auth → data injection, se aceitar com auth → pode ser explorado com token obtido via DCR

---

## 📝 Finding #3: ANTH-003 — Slack Internal URL Leaked in JS Bundle

**Status:** INFO (não vulnerabilidade per se, mas OSINT)
**URL:** `https://anthropic.enterprise.slack.com/archives/C04MN212NQN`
**Descoberto em:** `platform.claude.com` JS bundle `18258-39a2bbd1953c331c.js`
**Channel ID:** `C04MN212NQN`

---

## 📝 Finding #4: ANTH-004 — CloudFront Distribution URLs Exposed

**Status:** INFO
**URLs:** `d20xtzwzcl0ceb.cloudfront.net` e `d3uc069fcn7uxw.cloudfront.net`
**Ambos retornam 403** (bloqueados)

---

## 📊 Análise de Ataque Potencial

### Cadeias Aplicáveis da sua RAG

| Chain | Aplicabilidade | Status |
|-------|---------------|--------|
| **Chain 13: DCR + Session Fixation → ATO** | api.anthropic.com | Parcial (DCR funciona, /consent 404, redirect_uri whitelist firme) |
| **Chain 14: URL Param Spread** | Não encontrado nos bundles JS de platform.claude.com | Not applicable |
| **Chain 15: MCP Indirect Prompt Injection** | Claude Code tem MCP tools (134 reports) | Alta concorrência |
| **OAuth Metadata Discovery** | Confirmado (/.well-known retorna metadados completos) | Completo |
| **Next.js Bundle API Extraction** | platform.claude.com bundles baixados e analisados | Completo |
| **CORS Misconfiguration** | Todos os testados são seguros (sem wildcard) | Testado |
| **Host Header Injection** | Cloudflare bloqueia (403) | Testado |

### Vector Grid

| Attack Vector | Asset | Dificuldade | Impacto | Prioridade |
|---------------|-------|------------|---------|-----------|
| DCR → Token Issuance | api.anthropic.com | Média (precisa conta) | HIGH | ⭐⭐⭐ |
| Claude Code Permission Bypass | Claude Code CLI | Alta (concorrência) | CRITICAL | ⭐⭐ |
| IDOR em event_logging | api.anthropic.com | Alta (precisa auth) | MEDIUM | ⭐⭐ |
| Support Portal (0 reports!) | support.claude.com | Baixa | HIGH | ⭐⭐⭐ |
| Dangling CNAME takeover | status.anthropic.com | Média | HIGH | ⭐⭐ |

---

## Próximos Passos (Precisa de Conta)

1. **[PENDENTE ANTH-001]** Aguardar review do HackerOne
2. **[PRECISA DE CONTA]** Criar conta claude.ai → testar event_logging endpoint com token real
3. **[PRECISA DE CONTA]** Testar IDOR em event_logging (vazar eventos de outros usuários?)
4. **[PRECISA DE CONTA]** Testar consent page com conta real (session fixation)
5. **[PRECISA DE CONTA]** Verificar se event_logging endpoint pode ser usado para SSRF ou data injection
6. **[PRECISA DE CONTA]** Explorar support.claude.com com conta de suporte para IDOR
7. **[NÃO PRECISA DE CONTA]** Monitorar subdomain takeover candidates periodicamente

---

## Estrutura de Arquivos

```
anthropic/
├── README.md                          # ← Este arquivo
├── recon/
│   ├── all_subs.txt                   # 99+ subdomínios merged
│   ├── all_subs_merged.txt            # Subdomínios + crt.sh merged
│   ├── anthropic_subs.txt             # 77 subdomínios anthropic.com
│   ├── claude_subs.txt                # 14 subdomínios claude.ai
│   ├── crtsh_claude.txt               # 12 subdomínios claude.ai (crt.sh)
│   ├── crtsh_all.txt                  # crt.sh merged
│   └── httpx.json                     # HTTP fingerprinting
├── scans/
│   ├── ferox_api_anthropic.txt        # Content discovery
│   ├── api_anthropic_wayback.txt      # 327 URLs do Wayback
│   ├── claude_ai_wayback.txt          # URLs do Wayback claude.ai
│   ├── nuclei_results.txt             # Nuclei scan results
│   └── subzy_results.txt              # Subdomain takeover scan
├── reports/
│   └── ANTH-001_mcp_dynamic_client_registration_open.md  # Report formal
├── github/
│   └── all_repos.txt                  # 92 repos listados
├── poc/
├── notes/
└── js/
    └── *.js                           # JS bundles de platform.claude.com
```

---

**Data:** 2026-06-28
**Hunter:** @altave
**Programa:** Anthropic HackerOne Bug Bounty
