# SF-002 — `/api/v1/countries` Sem Autenticação Expõe Configuração Interna do Sistema

**Programa:** BugHunt — Grupo Smart Fit Bug Bounty Público  
**Severidade:** MEDIUM  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)  
**CWE:** CWE-200 — Exposure of Sensitive Information to an Unauthorized Actor  
**Endpoint afetado:** `https://espacodocliente.smartfit.com.br/api/v1/countries`  
**Descoberto:** 2026-07-01  
**Status:** Confirmado — reproduzível sem autenticação

---

## Resumo

O endpoint `/api/v1/countries` do portal do cliente retorna um JSON com **configurações internas de negócio** da Smart Fit para múltiplos países sem exigir qualquer autenticação. Os dados incluem limites de allowance financeiro, taxas de inflação, códigos de analytics internos, endereços de e-mail de sistemas e lógica de negócio sensível.

---

## Evidência

```bash
curl -sk "https://espacodocliente.smartfit.com.br/api/v1/countries"
```

**Resposta (parcial — dados reais):**
```json
[
  {
    "brazil": {
      "id": 1,
      "name": "Brasil",
      "require_zone": false,
      "zip_size": 8,
      "locale": "pt-BR",
      "url": ".smartfit.com.br",
      "facebook_locale": "pt_BR",
      "analytics_code": "UA-9925058-1",
      "allowance_limit": "500.0",
      "allowance_per_person_limit": 200,
      "inflation": "3.16",
      "charges_credit_card": true,
      "charges_debit": true,
      "currency": "BRL",
      "mailer_from": "email@smartfit.com.br",
      "deadline_notification": 0,
      "ddi": 55,
      "bacen_code": null,
      "active": true
    }
  },
  {
    "mexico": {
      "id": 2,
      "name": "México",
      "analytics_code": "UA-27301595-1",
      "allowance_limit": "1500.0",
      "allowance_per_person_limit": 200,
      "inflation": "3.94",
      "currency": "MXN",
      "mailer_from": "email@smartfit.com.mx",
      "deadline_notification": null,
      "ddi": 52
    }
  },
  {
    "chile": {
      "id": 3,
      "analytics_code": "UA-47459836-1",
      "allowance_limit": "0.0",
      "inflation": "3.9",
      "currency": "CLP",
      "mailer_from": "email@smartfit.com.cl",
      "deadline_notification": 45,
      "ddi": 56
    }
  }
  // ... 10+ países com dados equivalentes
]
```

---

## Dados Sensíveis Expostos

| Campo | Valor Exemplo | Sensibilidade |
|---|---|---|
| `allowance_limit` | `"500.0"` (BRL) | Limite financeiro interno do sistema |
| `allowance_per_person_limit` | `200` | Lógica de negócio — limite por pessoa |
| `inflation` | `"3.16"` | Taxa de ajuste financeiro interno |
| `analytics_code` | `UA-9925058-1` | ID interno de analytics (legado UA) |
| `mailer_from` | `email@smartfit.com.br` | Endereço de e-mail do sistema |
| `deadline_notification` | `0` / `45` | Lógica de notificações internas |
| `bacen_code` | `null` | Referência ao código do Banco Central |
| `charges_credit_card` | `true` | Lógica de negócio de pagamentos |

---

## Impacto

- **Reconhecimento:** Expõe a arquitetura interna multi-país do sistema SmartFit, facilitando ataques direcionados
- **Limites financeiros:** O `allowance_limit` e `allowance_per_person_limit` revelam lógica financeira que pode ser explorada em ataques de business logic
- **Endereços de e-mail:** O `mailer_from` pode ser usado para phishing direcionado ou análise de configuração de e-mail
- **IDs internos:** Os `analytics_code` (Google UA legado) revelam o histórico de configuração de analytics

---

## Reprodução

```bash
curl -sk "https://espacodocliente.smartfit.com.br/api/v1/countries" | python3 -m json.tool
```

Resposta inclui dados de: Brasil, México, Chile, Colômbia, Argentina, Peru, Paraguai, Uruguai, El Salvador, Guatemala, Honduras, Costa Rica, República Dominicana, Equador, Panamá.

---

## Recomendações

1. Adicionar autenticação ao endpoint `/api/v1/countries` ou torná-lo disponível apenas após login
2. Se dados precisam ser públicos para funcionamento do front-end, remover campos sensíveis (`allowance_limit`, `inflation`, `mailer_from`, `analytics_code`) da resposta
3. Implementar rate limiting para evitar varredura de dados
