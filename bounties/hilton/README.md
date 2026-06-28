# Hilton Bug Bounty — HackerOne

**Plataforma:** HackerOne  
**Programa:** Hilton (bounty desde Mar 2023)  
**Total pago:** $273,975 | Bounty médio: $100–$300 | Top: $750–$6,000  
**Response efficiency:** 90% | First response: ~2h | Triage: ~23h  

---

## Estrutura

```
bounties/hilton/
├── README.md                    — Este arquivo (estratégia + regras)
├── reports/                     — Relatórios formais de findings
├── recon/                       — Notas de recon e discovery
└── poc/                         — Proof of Concept files
```

---

## Regras Críticas do Programa

| Regra | Detalhe |
|-------|---------|
| **User Agent** | Adicionar `"HackerOne"` ao UA em TODO tráfego de teste |
| **Test accounts** | Prepend `"Test-Hackerone"` ao First e Last name de todas as contas criadas |
| **Reservas** | Booking de reservas = OOS — não fazer |
| **Rate limit** | Máximo 100 req/min por site |
| **Dados** | Zero armazenamento de dados Hilton em serviços públicos |
| **Disclosure** | Não discutir vulns fora do programa sem consentimento expresso |

---

## Tiers e Assets

### Tier A — Alta Prioridade ($1k–$10k)
| Asset | Observação Estratégica |
|-------|----------------------|
| `hilton.com` (domain) | Auth + Hilton Honors sign-up — **MAIS LUCRATIVO** |
| iOS app (id635150066) | 0 resolved reports — **TERRITÓRIO VIRGEM** |
| Android app (com.hilton.android.hhonors) | 0 resolved reports — **TERRITÓRIO VIRGEM** |

### Tier B — Médio ($75–$6k)
| Asset | Observação Estratégica |
|-------|----------------------|
| `*.hilton.com` (wildcard) | 161 resolved — mais ativo |
| `suppliersconnection.hilton.com` | CSRF excluído temporariamente mas OUTROS vulns OK |
| `167.187.0.0/16` | 37 resolved — range com histórico |
| Outros CIDRs | Maioria 0 resolved — potencial não explorado |

### Tier C ($50–$1k)
| Asset | Detalhe |
|-------|---------|
| Hilton Third Party Applications | 0 resolved |
| Hilton Franchised Properties | 0 resolved |

---

## O Que É OOS (Armadilhas)

```
✗ POST-based XSS            → Foca em GET/DOM XSS
✗ Open Redirect             → Não usar como primitivo de cadeia
✗ Clickjacking sem ação sensível
✗ Login/logout CSRF          → Mas CSRF em ações autenticadas ainda é válido
✗ CSRF em suppliersconnection.hilton.com  → temporariamente excluído
✗ Booking de reservas
✗ Rate limiting sem divulgação de PII
✗ eis.hilton.com, pim.hilton.com, jobs.hilton.com  → explicitamente OOS
✗ Subdomínios que resolvem para IPs da Rackspace organization
✗ Hiltongrandvacations.com / hgv.com  → empresa separada
✗ guestfeedback.hilton.com  → Qualtrics (reportar a eles)
✗ Relatórios somente de scanners automatizados (sem PoC manual)
```

**Platform Standards NÃO comprometidos (cuidado ao ratar):**
- IDOR com IDs imprevisíveis (UUIDs) → pode ser downgraded
- PII leakage severity → pode ser downgraded
- Self-sign-up flow severity → pode ser downgraded
- Third-party component vulns → sem garantia de bounty

---

## Findings

| ID | Arquivo | Sev | CVSS | Status |
|----|---------|-----|------|--------|
| *(em branco)* | | | | Iniciando recon |

---

## Header Obrigatório

```
User-Agent: Mozilla/5.0 (...) HackerOne
```

Formato para Burp: Preferences → User Options → Connections → Upstream Proxy → add to UA string
