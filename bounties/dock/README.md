# Dock Tecnologia — Bug Bounty (Bugpay)

**Programa:** Bugpay  
**Alvo:** Dock Tecnologia — infraestrutura BaaS, issuing, acquiring e Open Finance Brasil  
**Status:** 5 findings documentados (D1-D5); `*.caradhras.io` ainda inexplorado  

---

## Escopo

| Wildcard | Descrição | Status |
|----------|-----------|--------|
| `*.dock.tech` | Plataforma principal Dock | 🔍 Explorado (314 hosts) |
| `*.caradhras.io` | Open Finance Brasil (Caradhras) | ⏳ Pendente |
| `*.conductor.com.br` | IRIS/Pier — card issuer (Conductor) | ✅ D5 encontrado (pierflex + pierpro takeover) |

**OOS automático:** qualquer subdomínio com `dev`, `hml`, `sandbox`, `staging`, `homolog`, `qa`.

---

## Findings

### D1 — S3 Subdomain Takeover `cfsec.dock.tech`
**Severidade:** HIGH (CVSS 7.5) | **CWE:** CWE-350  
**Escopo originário:** `*.dock.tech` → `cfsec.dock.tech`  
**Resumo:** CNAME ativo apontando para bucket S3 inexistente na região us-west-2. Qualquer conta AWS pode criar o bucket e servir conteúdo arbitrário sob o domínio `cfsec.dock.tech`.  
**Limitação:** HTTP-only (S3 static website não suporta HTTPS nativo).  
**Arquivo:** `reports/D1_s3_subdomain_takeover.md`

### D2 — Config Exposure + 155 Client Slugs
**Severidade:** MEDIUM (CVSS 5.3) | **CWE:** CWE-215  
**Escopo originário:** `*.dock.tech` → `*.acquiring.dock.tech` (5 portais)  
**Resumo:** Portais de produção Acquiring servem `config.js` (Muxi v1.122.13) com 213 templates de build não expandidos (`#{"VAR","default"}`). Expõe 10 hostnames de dev, 2 IPs raw com porta, proxy CORS público e lista completa de 155 clientes (ASSAI, ELECTROLUX, ZROBANK, DLOCAL, BANESE...). Portal quebrado em produção (`#[VERSION]` não expandido).  
**Arquivo:** `reports/D2_acquiring_config_exposure.md`

### D3 — IRIS: Missing Rate Limit + No CAPTCHA
**Severidade:** MEDIUM (CVSS 5.9) | **CWE:** CWE-307  
**Escopo originário:** `*.dock.tech` → `front.iris.dock.tech`  
**Resumo:** Endpoint `POST /forward/api/authenticate` sem rate limiting (20 concorrentes sem 429) e sem CAPTCHA (`REACT_APP_CAPTCHA_SITE_KEY: "false"` baked no bundle). Sistema IRIS gerencia BINs, tokens de pagamento, transações e permissões de emissores. userType enum vazado via mensagem de erro (`LDAP|EXTERNO`).  
**Arquivo:** `reports/D3_iris_auth_missing_ratelimit.md`

### D4 — Kong CORS `*` + Stack Trace Cross-Origin (OpenBanking FAPI)
**Severidade:** MEDIUM (CVSS 6.1) | **CWE:** CWE-942 + CWE-209  
**Escopo originário:** `*.dock.tech` → `auth.openbanking.dock.tech`  
**Resumo:** Dois bugs encadeados:  
1. Kong API Gateway tem plugin CORS global com `allow_origins: *` — responde `access-control-allow-origin: *` em **toda** requisição (incluindo preflight OPTIONS → 200)  
2. Express `corsOptions.js:30` usa `throw new Error(...)` em vez de `callback(err)` → HTTP 500 com stack trace Node.js completo. Kong adiciona `ACAO: *` ao 500 → browser lê o stack trace cross-origin.  
PoC: qualquer site faz `fetch()` à URL e lê `file:///app/helpers/corsOptions.js` + `@opentelemetry/instrumentation-express` paths.  
**Arquivo:** `reports/D4_openbanking_cors_bypass_and_500.md`

### D5 — Dual Subdomain Takeover via ReadMe (pierflex + pierpro)
**Severidade:** HIGH (CVSS 8.1) | **CWE:** CWE-350  
**Escopo originário:** `*.conductor.com.br` → `pierflex.conductor.com.br` + `pierpro.conductor.com.br`  
**Resumo:** Ambos os subdomínios possuem CNAME ativo para `ssl.readmessl.com` (ReadMe custom domain endpoint via Cloudflare). Os domínios nunca foram registrados na plataforma ReadMe — Cloudflare retorna 409 + error 1001. Qualquer conta ReadMe pode registrar esses domínios e servir conteúdo arbitrário com **HTTPS válido** (Cloudflare emite SSL automaticamente). Superior ao D1 porque HTTPS funciona. Pier Flex e Pier Pro são os produtos de cartão flagship da Conductor.  
**Arquivo:** `reports/D5_readme_subdomain_takeover_pierflex_pierpro.md`

---

## Targets prioritários para próximas sessões

```
infrastructure-services-atlantis.dock.tech
  → Atlantis Terraform UI (18.228.255.104:4141?, 54.232.195.72)
  → Risco: painel de Terraform com acesso a infra AWS exposto publicamente

3ds.caradhras.io                           → escopo *.caradhras.io
  → Sistema 3DS (18.231.85.71, 18.230.93.1)
  → Risco: protocolo de autenticação de transações

portalfraude.conductor.com.br              → escopo *.conductor.com.br
  → 201.20.14.32 (sem header HTTP ainda)
  → Risco: portal antifraude sem proteção de borda

pierflex.conductor.com.br                  → escopo *.conductor.com.br
pierpro.conductor.com.br                   → escopo *.conductor.com.br
  → Cloudflare 409 (HTTP 409 em Cloudflare = misconfiguration rara)

datalake.caradhras.io                      → escopo *.caradhras.io
  → IP GoDaddy (possível bucket/storage mal configurado)

docs.caradhras.io                          → escopo *.caradhras.io
  → Documentação de API (buscar endpoints não documentados, auth bypass)
```

---

## Recon salvo

| Arquivo | Descrição |
|---------|-----------|
| `recon/all_prod.txt` | 314 hosts de produção (filtrado OOS) |
| `recon/dnsx_all.txt` | 278 linhas — resolução DNS (A, CNAME) |
| `recon/httpx_full.json` | Fingerprint HTTP de todos os hosts vivos |
| `recon/httpx_tier1.json` | 13 hosts high-priority fingerprinted |
| `recon/tier1_targets.txt` | 56 targets tier-1 |
| `PENTEST_NOTES.md` | Notas brutas da sessão |

---

## Stack técnico Dock

```
Kong Enterprise 3.10.0.7-enterprise-edition  (API Gateway — OpenBanking cluster)
Express.js + Node.js                          (backends OpenBanking)
React (CRA)                                   (IRIS frontend — Conductor)
RequireJS AMD / Muxi v1.122.13               (Acquiring portals)
AWS CloudFront + S3                           (CDN + static hosting)
Amazon EKS (k8s ALBs k8s-irisfron-*)        (IRIS backend — sa-east-1)
AWS ELB (opus-software.com.br)               (OpenBanking auth backend)
FAPI 1.0 Advanced Profile                    (Open Finance Brasil)
```
