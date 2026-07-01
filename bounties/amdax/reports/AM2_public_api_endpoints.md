# AM2 — API Endpoints Publicamente Acessiveis + CORS Aberto

---

## Informacoes de Submissao

| Campo | Valor |
|:---|---:|
| **Data da Descoberta** | 2026-06-29 18:30 BRT (UTC-3) |
| **Tipo de Vulnerabilidade** | Information Disclosure + Security Misconfiguration |
| **Servico/URL Afetado** | `https://my.amdax.com/api/hera/countries` |
| **IP de Origem** | 201.1.100.69 |

---

## Severidade

**Severidade:** MEDIUM  
**CWE:** CWE-200 — Exposure of Sensitive Information

---

## Sumario

O subdominio `my.amdax.com` expoe endpoints de API internos sem autenticacao. Os endpoints `/api/hera/countries` e `/api/hera/residence-countries` retornam dados estruturados sem exigir qualquer token de autenticacao.

---

## Passos para Reproduzir

```bash
curl -s "https://my.amdax.com/api/hera/countries"
curl -s "https://my.amdax.com/api/hera/residence-countries"
```

**Resposta:** Ambos retornam HTTP 200 com JSON contendo lista de paises.

---

## Impacto

Exposicao de dados internos da API sem autenticacao. Embora sejam dados de paises, o endpoint confirma que a API interna da Amdax pode ser acessada sem autenticacao, abrindo precedente para exploracao de outros endpoints.

---

## Remediacao

Exigir autenticacao em todos os endpoints da API, incluindo `/api/hera/*`.

---

## Confirmacao

Nenhuma atividade foi realizada para interromper os servicos ou sistemas. Nenhum dado foi copiado, alterado, vazado ou deletado.

IP de Teste: 201.1.100.69
