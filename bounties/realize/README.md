# Realize Financeira (CFI) — Bug Bounty

**Empresa:** Realize Soluções Financeiras (CFI) — braço financeiro do Grupo Renner  
**Escopo explícito:**
- `www.realizesolucoesfinanceiras.com.br`
- `api.realizesolucoesfinanceiras.com.br`

**Assets adicionais descobertos (recon):**
- `openfinance.realizesolucoesfinanceiras.com.br` — servidor FAPI Open Finance Brasil (Kong + Express + Opus Software OOF)
- `sc-openfinance.realizesolucoesfinanceiras.com.br` — Spring Boot app (Actuator /health exposto)
- `parceiros.realizesolucoesfinanceiras.com.br` — CNAME para Zendesk (Help Center fechado)
- `meucartao.realizesolucoesfinanceiras.com.br` — portal de cartão do cliente

**OOS automático:** dev/hml/sandbox/staging

**Impacto primário:** Este programa usa **IMPACTO AO NEGÓCIO** como critério principal de triagem (não CVSS).

---

## Findings

| ID | Arquivo | Sev | CVSS | Impacto Negócio | Target | Status |
|----|---------|-----|------|-----------------|--------|--------|
| R1 | `R1_openfinance_cors_wildcard_and_stack_trace.md` | MEDIUM | 6.1 | **ALTO** (FAPI server) | `openfinance.*` | Pronto — checar scope antes de enviar |
| R2 | `R2_fapi_compliance_violations.md` | MEDIUM | 5.3 | **ALTO** (BCB regulatório) | `openfinance.*` | Pronto — checar scope antes de enviar |
| R3 | `R3_swagger_ui_exposed_production.md` | LOW | 5.3 | Médio | `api.*` | Pronto |
| R4 | `R4_zendesk_dangling_cname.md` | LOW | 3.7 | Baixo | `parceiros.*` | Pronto — checar scope antes de enviar |
| R5 | `R5_hardcoded_channel_credentials_in_js_bundle.md` | MEDIUM | 6.5 | Alto (habilita R6/R7) | `www.*` + `api.*` | **Texto de submissão pronto** (`R5_SUBMISSION.md`) |
| R6 | `R6_portal_negociacao_cpf_birthdate_auth.md` | **CRITICAL** (corrigido de HIGH/8.1 → 9.1, ver submission) | 9.1 | **CRÍTICO** (fraude em dívida, boleto) | `api.*` | **Texto de submissão pronto** (`R6_SUBMISSION.md`) |
| R7 | `R7_preauth_token_any_cpf_user_enumeration.md` | MEDIUM/HIGH (potencial) | 7.5 | Alto | `api.*` | **Texto de submissão pronto** (`R7_SUBMISSION.md`) |

---

## Destaque: R1 — Sistêmico Opus Software

O R1 é o finding mais crítico e tem contexto especial:

- **Mesma vulnerabilidade** do Dock D4 (`auth.openbanking.dock.tech`)
- Ambos usam **Kong Enterprise 3.10.0.7** + **Express `corsOptions.js`** com `throw` em vez de `callback`
- Plataforma: **Opus Software OpenFinance Framework (OOF)** — SaaS compartilhado
- Linhas diferentes: Dock `corsOptions.js:30` vs Realize `corsOptions.js:32` → mesma lógica, versão levemente diferente

**→ Se já submetido ao Dock, citar no relatório Realize como vulnerabilidade sistêmica de plataforma.**

---

## Notas de Scope — openfinance subdomain

`openfinance.realizesolucoesfinanceiras.com.br` **NÃO está na lista explícita** de escopo do programa. Porém:
1. É claramente parte da infraestrutura Realize (servidor de autorização Open Finance Brasil oficial)
2. R1 e R2 se aplicam a este host
3. Recomendação: submeter com nota explicando a descoberta e pedir confirmação de scope

---

## Stack Técnico

```
openfinance.realizesolucoesfinanceiras.com.br:
  Kong Enterprise 3.10.0.7 (API Gateway)
  Express.js + Node.js (backend FAPI)
  node-oidc-provider (OIDC server)
  @opentelemetry/instrumentation-express
  Opus Software OOF (OpenFinance Framework SaaS)

api.realizesolucoesfinanceiras.com.br:
  Spring Boot (versão exata desconhecida)
  SpringFox 2.9.2 (Swagger)
  Azion CDN (xufzemrit5.map.azionedge.com)
  Spring Boot Actuator (403 — protegido)

www.realizesolucoesfinanceiras.com.br:
  F5 BIG-IP (LBSessionID cookie)
  F5 ASM (WAF, TS cookies)
  PHP (detect via tech-detect)
  Cloudflare (não — F5 diretamente)
```

---

## Recon Salvo

| Arquivo | Descrição |
|---------|-----------|
| `recon/subs.txt` | 23 subdomínios (subfinder) |
| `recon/prod.txt` | 18 subdomínios de produção (OOS filtrado) |
| `recon/dnsx.txt` | Resolução DNS (A, CNAME) |
| `recon/httpx.json` | Fingerprint HTTP dos hosts vivos |

---

## Próximos Passos

- [x] Redigir texto de submissão para R5, R6, R7 (`*_SUBMISSION.md`) — prontos para envio na plataforma
- [ ] **Enviar R5, R6, R7 na BugPay Haven** (todos em escopo explícito, sem ressalva)
- [ ] Submeter R1 e R2 (notar scope de openfinance na submissão)
- [ ] R3 e R4 submeter como LOW
- [ ] Investigar `api.realizesolucoesfinanceiras.com.br` endpoints financeiros (Spring Boot)
- [ ] Tentar encontrar spec Swagger em paths não-padrão (`/realize/v2/api-docs`, etc.)
- [ ] Testar `/meu-cartao` authentication flow para logic flaws
- [ ] Analisar bundle sc-openfinance Angular mais profundamente (`sc_main.js` 1.6MB)
- [ ] Verificar se `implicit` flow é realmente aceito pelo servidor (validação R2)
- [ ] Auditar `/home/altave/realize/findings.md` (achados soltos contra `openfinance-hml` — OOS por regra do programa; ver se reproduzem em produção antes de descartar)

---

## Referências Regulatórias (Open Finance Brasil)

- [Resolução Conjunta BCB nº 1/2020](https://www.bcb.gov.br/estabilidadefinanceira/openfinance)
- [FAPI 1.0 Advanced Profile](https://openid.net/specs/openid-financial-api-part-2-1_0.html)
- [Open Finance Brasil Security Profile](https://openfinancebrasil.atlassian.net/wiki/spaces/OF/pages/17378535/)
- [Diretório de Participantes](https://web.conformance.directory.openbankingbrasil.org.br/)
