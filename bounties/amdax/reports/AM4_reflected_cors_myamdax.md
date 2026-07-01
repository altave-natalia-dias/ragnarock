# AM4 — Reflected CORS Misconfiguration on my.amdax.com

---

## Informacoes de Submissao

| Campo | Valor |
|:---|---:|
| **Data da Descoberta** | 2026-06-29 19:00 BRT (UTC-3) |
| **Tipo de Vulnerabilidade** | CORS Misconfiguration |
| **Servico/URL Afetado** | `https://my.amdax.com/api/*` |
| **IP de Origem** | 201.1.100.69 |

---

## Severidade

**Severidade:** MEDIUM  
**CWE:** CWE-942 — Permissive Cross-domain Policy with Untrusted Domains

---

## Sumario

O subdominio `my.amdax.com` reflete o header `Origin` da requisicao no header `Access-Control-Allow-Origin` da resposta. Isso permite que QUALQUER dominio faca requisicoes cross-origin contra os endpoints da API.

---

## Passos para Reproduzir

```bash
curl -sv "https://my.amdax.com/api/hera/countries" -X OPTIONS \
  -H "Origin: https://qualquer-site-malicioso.com" \
  -H "Access-Control-Request-Method: GET" 2>&1 | grep -iE 'access-control'
```

**Resposta esperada:**
```
access-control-allow-origin: https://qualquer-site-malicioso.com
access-control-allow-credentials: true
```

---

## Impacto

Qualquer site malicioso pode fazer requisicoes autenticadas aos endpoints da API interna, incluindo `/api/auth/user`, `/api/hera/countries`, e `/api/hera/residence-countries`.

---

## Remediacao

Configurar whitelist de origins permitidas em vez de refletir o Origin header.

---

## Confirmacao

Nenhuma atividade foi realizada para interromper os servicos ou sistemas. Nenhum dado foi copiado, alterado, vazado ou deletado.

IP de Teste: 201.1.100.69
