# AM3 — Auth0 Logout Default Redirect para localhost

---

## Informacoes de Submissao

| Campo | Valor |
|:---|---:|
| **Data da Descoberta** | 2026-06-29 18:30 BRT (UTC-3) |
| **Tipo de Vulnerabilidade** | Open Redirect / Security Misconfiguration |
| **Servico/URL Afetado** | `https://auth.amdax.com/logout` |
| **IP de Origem** | 201.1.100.69 |

---

## Severidade

**Severidade:** MEDIUM  
**CWE:** CWE-601 — URL Redirection to Untrusted Site

---

## Sumario

O endpoint `/logout` do servico de autenticacao Auth0 da Amdax redireciona por padrao para `https://localhost:44379`. Alem disso, as configuracoes OIDC estao publicamente acessiveis revelando detalhes da infraestrutura de autenticacao.

---

## Passos para Reproduzir

```bash
curl -sv "https://auth.amdax.com/logout" 2>&1 | grep -i location
```

**Resposta:** `location: https://localhost:44379`

---

## Configuracoes OIDC Expostas

```bash
curl -s "https://auth.amdax.com/.well-known/openid-configuration" | python3 -m json.tool
```

Revela:
- issuer, authorization_endpoint, token_endpoint, jwks_uri
- scopes_supported, response_types_supported
- `backchannel_logout_supported: true`
- `token_endpoint_auth_methods_supported`

---

## Impacto

O redirect padrao para localhost:44379 e uma configuracao de desenvolvimento/debug que foi enviada para producao. Embora o redirect_uri validation esteja ativo para dominios externos, o redirect para localhost pode ser explorado em cenarios de SSRF ou ataques locais.

---

## Remediacao

Remover o redirect padrao para localhost e configurar um redirect padrao seguro. Revisar as configuracoes de logout para exigir um returnTo valido.

---

## Confirmacao

Nenhuma atividade foi realizada para interromper os servicos ou sistemas. Nenhum dado foi copiado, alterado, vazado ou deletado.

IP de Teste: 201.1.100.69
