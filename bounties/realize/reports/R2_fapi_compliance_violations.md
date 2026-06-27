# Finding R2 — FAPI 1.0 Compliance Violations no OIDC Discovery (Open Finance Brasil)

**Título:** Violações do FAPI 1.0 Advanced Profile no OIDC Discovery — `implicit` grant + `client_secret_post` em servidor Open Finance Brasil  
**Severidade:** MEDIUM (CVSS 5.3 — AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N) / **Impacto de Negócio: ALTO** (risco regulatório BCB)  
**CWE:** CWE-732 (Incorrect Permission Assignment for Critical Resource) + CWE-285 (Improper Authorization)  
**Status:** Confirmado — OIDC discovery público retorna grant_types e auth_methods proibidos pelo FAPI  
**Escopo originário:** `www.realizesolucoesfinanceiras.com.br` / `api.realizesolucoesfinanceiras.com.br`  
**Target descoberto:** `openfinance.realizesolucoesfinanceiras.com.br/.well-known/openid-configuration`  
**Programa:** Realize Financeira — produção apenas  
**Classificação de impacto:** Primário = regulatório (BCB, Open Finance Brasil) > técnico (CVSS)

---

## Discovery Chain

```
Recon: openfinance.realizesolucoesfinanceiras.com.br identificado via subfinder
  → GET /.well-known/openid-configuration (endpoint público, padrão OIDC)
    → grant_types_supported: ["implicit", ...]
      → FAPI 1.0 Advanced (cláusula 5.2.2-2): "SHALL NOT use the implicit grant type"
    → token_endpoint_auth_methods_supported: ["private_key_jwt", "client_secret_post"]
      → FAPI 1.0 Advanced (cláusula 5.2.2-14): "SHALL NOT support client_secret_post"
        → Duas violações diretas do Open Finance Brasil Security Profile (OFBSP)
```

---

## Sumário Técnico

O endpoint `.well-known/openid-configuration` do servidor de autorização Open Finance Brasil da Realize Financeira expõe publicamente dois valores proibidos pelo **FAPI 1.0 Advanced Profile**, que é mandatório para participantes do Open Finance Brasil (Resolução Conjunta BCB nº 1/2020 + OFBSP):

### Violação 1 — `implicit` grant type listado

O campo `grant_types_supported` inclui `"implicit"`. O FAPI 1.0 Advanced (seção 5.2.2, item 2) proíbe explicitamente o uso do Implicit Flow:

> *"The authorization server ... shall not use the implicit grant type"*

O Implicit Flow retorna tokens diretamente na URL de redirect (fragment `#access_token=...`), sem código de autorização, expondo tokens a:
- Histórico do browser
- Referrer headers
- JavaScript na página
- Proxies e logs de servidor web

### Violação 2 — `client_secret_post` auth method listado

O campo `token_endpoint_auth_methods_supported` inclui `"client_secret_post"`. O FAPI 1.0 Advanced (seção 5.2.2, item 14) proíbe:

> *"The authorization server ... shall not support the client_secret_post method"*

`client_secret_post` envia o `client_secret` como parâmetro de formulário no body da requisição POST — método considerado inseguro pois:
- Secret exposto em logs de servidor
- Secret na URL de debug
- Vulnerável a ataques CSRF se sem PKCE
- Contradiz o requisito de `private_key_jwt` + `tls_client_auth` exigido pelo FAPI

---

## Evidências

### OIDC Discovery — conteúdo completo relevante

```bash
$ curl -sk "https://openfinance.realizesolucoesfinanceiras.com.br/.well-known/openid-configuration" \
  | python3 -m json.tool | grep -A 20 "grant_types\|auth_methods\|response_types\|issuer"

{
    "issuer": "https://openfinance.realizesolucoesfinanceiras.com.br",
    "authorization_endpoint": "https://openfinance.realizesolucoesfinanceiras.com.br/auth",
    "token_endpoint": "https://openfinance.realizesolucoesfinanceiras.com.br/auth/token",
    "introspection_endpoint": "https://openfinance.realizesolucoesfinanceiras.com.br/auth/token/introspection",
    "userinfo_endpoint": "https://openfinance.realizesolucoesfinanceiras.com.br/auth/me",
    "registration_endpoint": "https://mtls-openfinance.realizesolucoesfinanceiras.com.br/auth/reg",
    "jwks_uri": "https://openfinance.realizesolucoesfinanceiras.com.br/auth/jwks",
    
    "grant_types_supported": [
        "implicit",                    ← VIOLAÇÃO FAPI 1.0 Adv. §5.2.2(2)
        "authorization_code",
        "refresh_token",
        "urn:openid:params:grant-type:ciba"
    ],
    
    "response_types_supported": [
        "code id_token",               ← OK (FAPI exige code + id_token como hybrid)
        "code"                         ← OK
    ],
    
    "token_endpoint_auth_methods_supported": [
        "private_key_jwt",             ← OK (FAPI permite)
        "client_secret_post"           ← VIOLAÇÃO FAPI 1.0 Adv. §5.2.2(14)
    ],
    
    "request_object_signing_alg_values_supported": [
        "PS256",                       ← OK (FAPI exige PS256)
        "RS256"                        ← WARN (FAPI 1.0 permite, mas FAPI 2.0 não)
    ]
}
```

> **Nota:** A presença nos `_supported` arrays indica que o servidor **anuncia suporte** a esses métodos. Validação completa requereria teste de autorização real com `response_type=token` para confirmar se o servidor ACEITA o implicit flow.

### Referências normativas violadas

```
Open Finance Brasil Financial-grade API Security Profile 1.0
  └── Baseado em: FAPI 1.0 Advanced (OpenID Foundation)

FAPI 1.0 Advanced, seção 5.2.2 (Authorization Server):
  Item 2:  "shall not use the implicit grant type"
  Item 14: "shall not support the client_secret_post method"
           "shall not support the client_secret_basic method for clients"
           (exceto para clientes que NÃO são apps confidenciais)

Resolução Conjunta BCB + CMN nº 1, de 04/05/2020:
  Art. 15 — Exige conformidade com o OFBSP
  Anexo III — Especificações técnicas de segurança

Open Finance Brasil Security Profile (OFBSP v2):
  §4.3.2: "all participants shall use PS256 algorithms"
  §4.3.1: proíbe implicit flow e client_secret_post
```

---

## Análise de Impacto

### Técnico

**Cenário com `implicit` grant ativo no servidor:**
```
1. Atacante registra cliente Open Finance via /auth/reg (Dynamic Client Registration)
2. Inicia authorization request com response_type=token (implicit)
3. Usuário autentica
4. Token retorna na URL: https://attacker-app.com/callback#access_token=eyJ...
5. Token exposto no Referrer se página carrega subrecursos
6. Token capturável via JavaScript da página (se XSS presente)
7. Token em logs de servidor do attacker-app
```

**Cenário com `client_secret_post`:**
```
1. Aplicativo cliente autentica com client_secret no body do POST:
   POST /auth/token
   client_id=app1&client_secret=s3cr3t&...
2. Secret exposto em:
   - Logs de WAF/proxy (F5 BIG-IP está na infra Realize)
   - Logs de aplicação do cliente
   - Ferramentas de debug (ngrok, Postman)
3. Se secret vaza → cliente inteiro comprometido
```

### Regulatório (principal)

| Risco | Detalhe |
|-------|---------|
| Sanção BCB | BCB pode impor multas por não-conformidade com OFBSP |
| Suspensão Open Finance | Participante pode ser removido do diretório BCB |
| Auditoria obrigatória | Não-conformidade pode disparar auditoria completa do DCRO |
| Responsabilidade civil | Vazamento de dados por implicit flow = responsabilidade da instituição (LGPD) |
| Reputação | Relatório de não-conformidade é público no portal Open Finance |

---

## Matriz de Evidência

| Claim | Evidência | Reproduzível |
|-------|-----------|-------------|
| `implicit` em grant_types_supported | curl /.well-known/openid-configuration | ✅ Público |
| `client_secret_post` em auth_methods | curl /.well-known/openid-configuration | ✅ Público |
| FAPI 1.0 Adv. proíbe implicit | FAPI 1.0 Adv. §5.2.2(2) (normativo) | ✅ Spec pública |
| FAPI 1.0 Adv. proíbe client_secret_post | FAPI 1.0 Adv. §5.2.2(14) (normativo) | ✅ Spec pública |
| OFBSP baseia-se em FAPI 1.0 Adv. | Documentação Open Finance Brasil | ✅ Público |
| Servidor de Realize é participante Open Finance | issuer = openfinance.realizesolucoesfinanceiras.com.br | ✅ Confirmado |

---

## Validação Adicional Recomendada (para o programa)

Para elevar severidade de MEDIUM a HIGH, validar se o servidor ACEITA implicit flow:

```bash
# Testar se servidor processa response_type=token (não fazer sem autorização explícita)
curl -sk "https://openfinance.realizesolucoesfinanceiras.com.br/auth?\
response_type=token\
&client_id=<client_id>\
&redirect_uri=https://test.callback\
&scope=openid" -D - | head -5
# Se retornar 302 com Location contendo #access_token → CONFIRMADO como exploitável
```

---

## Remediação

### Imediata — remover grant types proibidos

No servidor de autorização (node-oidc-provider ou similar), atualizar a configuração:

```javascript
// oidc-provider config (antes):
grantTypes: ['implicit', 'authorization_code', 'refresh_token', 'urn:openid:...ciba']

// oidc-provider config (depois — FAPI compliant):
grantTypes: ['authorization_code', 'refresh_token', 'urn:openid:...ciba']
// NÃO listar implicit
```

### Remover auth methods proibidos

```javascript
// Antes:
tokenEndpointAuthMethods: ['private_key_jwt', 'client_secret_post']

// Depois — FAPI compliant:
tokenEndpointAuthMethods: ['private_key_jwt', 'tls_client_auth']
// NÃO listar client_secret_post
```

### Verificação de conformidade

Usar a ferramenta oficial do Open Finance Brasil para certificação:
```
https://web.conformance.directory.openbankingbrasil.org.br/
→ FAPI 1.0 Advanced Authorization Server Test Plan
```

### Prazo regulatório recomendado

Dado o risco de sanção BCB, remediação em **5 dias úteis** é recomendada para evitar escalonamento para auditoria.
