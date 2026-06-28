# Zomato / Eternal Bug Bounty

**Plataforma:** HackerOne — Eternal Program  
**Scope:** Zomato, Blinkit, Hyperpure, District, runnr.in  
**Campanha Ativa:** IDOR + LLM/AI — 1.5x bônus até **June 29, 2026**

## Estrutura

```
bounties/zomato/
├── README.md                           — Este arquivo
├── reports/                            — Relatórios formais de findings
│   ├── ZO1_mcp_indirect_prompt_injection.md     — HIGH 8.1 (LLM/AI 1.5x)
│   ├── ZO2_mcp_dynamic_client_registration.md  — HIGH 8.1 (OAuth ATO)
│   ├── ZO3_mcp_consent_param_injection.md       — MEDIUM 6.1
│   └── ZO4_staging_mcp_endpoint_production.md  — LOW 4.3
├── recon/                              — Notas de recon e discovery
│   └── findings_summary.md             — Resumo de toda superfície mapeada
└── poc/                                — Proof of Concept files
    └── poc_zo1_prompt_injection.html   — Demo visual do ataque ZO1
```

## Findings Summary

| ID | Título | Sev | CVSS | Status |
|----|--------|-----|------|--------|
| ZO1 | MCP Indirect Prompt Injection | HIGH | 8.1 | ✅ Pronto — submeter com 1.5x LLM/AI bonus |
| ZO2 | OAuth Dynamic Client Registration | HIGH→CRIT | 8.1→9.1 | ✅ Confirmado via Postman; triage rebuttal escrito |
| ZO3 | Consent Page URL Param Injection | MEDIUM | 6.1 | ✅ Confirmado (código público em 60KB HTML) |
| ZO4 | Staging MCP Endpoint em Produção | LOW | 4.3 | ✅ Confirmado |
| ZO2+ZO3 | Combined CRITICAL ATO Chain | CRITICAL | 9.1 | ✅ Report combinado pronto |

## Estrutura Atual

```
bounties/zomato/
├── README.md
├── reports/
│   ├── ZO1_mcp_indirect_prompt_injection.md     — HIGH 8.1 (LLM/AI 1.5x)
│   ├── ZO2_mcp_dynamic_client_registration_open.md  — HIGH 8.1 (OAuth ATO)
│   ├── ZO2_triage_response.md                   — Rebuttal com HTTP evidence
│   ├── ZO2_ZO3_combined_critical_final.md       — CRITICAL 9.1 combined
│   ├── ZO3_mcp_consent_param_injection.md       — MEDIUM 6.1
│   └── ZO4_staging_mcp_endpoint_production.md  — LOW 4.3
├── recon/
│   └── findings_summary.md
└── poc/
    └── poc_zo1_prompt_injection.html
```

## Credenciais de Teste (Attacker Client — Para Uso Próprio)

```
client_id:     fd37dd28-254b-42b7-a55a-c85369d625c8
client_secret: Z-MCP
redirect_uri:  https://natnasd-attacker.requestcatcher.com/callback
login_challenge (gerado 2026-06-26): dce3ac2e9ffa4b60a9a023e71102d999
code_verifier: dx2ixcSoiMJa_r6LiJ9dbHZsE-0CWG4XAwgiUB2YhbUi8UNnolDLWhcN3hl6D1UDChJYbxlwahetdFUCWAG6jQ
code_challenge: idVnk34r4wuU_cNn4AiFHkrCno-NJo2Ri9D1kFkn-5Q
```

## Próximos Passos (Deadline: June 29, 2026)

1. **[URGENTE]** Submeter ZO1 ao HackerOne — maior ROI (1.5x LLM/AI)
2. **[URGENTE]** Submeter ZO2+ZO3 combined CRITICAL (`ZO2_ZO3_combined_critical_final.md`)
3. **[Bloqueado]** Criar conta Hyperpure → IDOR em `/consumer/ownerDetails`, `/account/paymentinfo?outletId=X` com `APIVersion: 12.1`
4. **[Bloqueado]** Passo 4 do exploit ZO2 requer conta Zomato com número de telefone indiano

## Referências Técnicas

- MCP Spec: https://spec.modelcontextprotocol.io/
- OAuth Dynamic Registration RFC 7591: https://tools.ietf.org/html/rfc7591
- OWASP LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- PortSwigger Prompt Injection: https://portswigger.net/research/prompt-injection

## Header Obrigatório

Incluir em todos os requests de teste:
```
X-Hackerone: natnasd
```
