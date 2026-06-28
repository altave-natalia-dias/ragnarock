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

| ID | Título | Asset | Sev | CVSS | Status |
|----|--------|-------|-----|------|--------|
| HT-001 | PingFederate Heartbeat — Internal IP/Azure Tenant Disclosure | fd.hilton.com | MEDIUM | 5.3 | Ready to submit |
| HT-002 | LearningLounge Admin Interface Exposed Without Auth | suppliersconnection.hilton.com | MEDIUM | 5.3 | Ready to submit |
| HT-003 | Unauthenticated File Upload Handler (no magic byte check) | suppliersconnection.hilton.com | MEDIUM | 5.3 | Ready to submit |
| HT-004 | GraphQL Introspection Enabled in Production (103 mutations!) | hilton.com/graphql/customer | HIGH | 7.5 | Ready to submit |
| HT-005 | window.__ENV Exposes Internal App Architecture + Microservice Names | hilton.com | LOW | 3.7 | Informational |
| HT-006 | GraphQL Errors Expose Internal REST API Paths + WSO2 Misconfiguration | hilton.com/graphql/customer | MEDIUM | 5.3 | Ready to submit |
| HT-007 | Staging Environment (suppliersconnectionstage) Publicly Accessible | suppliersconnectionstage.hilton.com | MEDIUM | 5.3 | Ready to submit |
| HT-008 | Unauthenticated ASMX Web Service Returns Internal CMS Data + IdentityIQ URL | suppliersconnection.hilton.com | MEDIUM | 5.3 | Ready to submit |
| HT-009 | GraphQL amexSessionToken Returns Real Amex JWT Without Authentication | hilton.com/graphql/customer | HIGH | 7.5 | Ready to submit |
| HT-010 | digitalPaymentSession Query Executes Without guestId/Auth (Apple Pay session endpoint) | hilton.com/graphql/customer | LOW | 3.7 | Informational (null response) |
| HT-011 | CORS Wildcard + Allow-Credentials on CMS Editorial Backend (stories-editor.hilton.com) | stories-editor.hilton.com | HIGH | 8.0 | Ready to submit |
| HT-012 | Unauthenticated Mass Subscription Opt-Out — Any Email or GuestID Without Auth | hilton.com/graphql/customer | HIGH | 7.5 | Ready to submit |
| HT-013 | CRITICAL: Unauth GraphQL Mutations — Username Change, 2FA Remove, Data Destruction | hilton.com/graphql/customer | CRITICAL | 9.1 | Ready to submit |
| HT-014 | Unauthenticated GDPR/CCPA Privacy Request Submission — Mass Account Deletion via Compliance | hilton.com/graphql/customer | HIGH | 7.5 | Ready to submit |
| HT-015 | Unauthenticated Price Match Guarantee Claims — Fraudulent Refund Requests Without Auth | hilton.com/graphql/customer | HIGH | 7.5 | Ready to submit |

### Detalhes por Finding

**HT-001** (`fd.hilton.com/pf/heartbeat.ping`):
- 8 cluster IPs (10.72.40.x, 10.80.40.x)
- Azure tenant ID: `660292d2-cfd5-4a3d-b7a7-e8f7ee458a0a`
- Tenants: `hilton.onmicrosoft.com`, `hiltonprod.onmicrosoft.com`
- Adapter names: HTMLPasswordProd, IdentifyFirst, OTP, kerberosadapter
- Unauthenticated, CVSS 5.3

**HT-002** (`suppliersconnection.hilton.com/learninglounge/home.aspx`):
- Acessível sem autenticação, ?r= não validado
- Campos admin expostos: textAnnouncement, txtClickActionURL, chkEnabled, chkEveryone, fileUploadAnnouncement, textTemplate1/2
- 61 inputs visíveis sem login
- ViewState não criptografado

**HT-003** (`suppliersconnection.hilton.com/Handlers/FileUpload.ashx`):
- Upload sem auth: .jpg, .png aceitos
- SVG com .jpg extension: aceito (sem magic byte check)
- GIFAR payload: aceito
- Possível stored XSS chain se storage for persistente

---

## Header Obrigatório

```
User-Agent: Mozilla/5.0 (...) HackerOne
```

Formato para Burp: Preferences → User Options → Connections → Upstream Proxy → add to UA string
