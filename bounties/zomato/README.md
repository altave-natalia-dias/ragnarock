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

| ID | Título | Sev | CVSS | Pronto? |
|----|--------|-----|------|---------|
| ZO1 | MCP Indirect Prompt Injection | HIGH | 8.1 | ✅ Rascunho pronto |
| ZO2 | OAuth Dynamic Client Registration | HIGH | 8.1 | ⚠️ Necessita teste Postman |
| ZO3 | Consent Page URL Param Injection | MEDIUM | 6.1 | ✅ Rascunho pronto |
| ZO4 | Staging MCP Endpoint em Produção | LOW | 4.3 | ✅ Confirmado |

## Próximos Passos (Deadline: June 29)

1. **[URGENTE]** Testar ZO2 via Postman — `POST /register` com browser UA
2. **[URGENTE]** Submeter ZO1 ao HackerOne (maior ROI — 1.5x LLM/AI)
3. Criar conta Hyperpure para testar IDOR em endpoints 401
4. Testar ZO3 PoC no browser — capturar POST em DevTools

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
