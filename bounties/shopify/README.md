# Shopify — Bug Bounty (HackerOne)

**Programa:** HackerOne (Shopify)  
**Recompensa:** $500–$200K | Média top tier: $57,533 | Total pago: $9.375M  
**Stats 90 dias:** $644,270 pagos, 2011 reports recebidos, last resolved: 2 dias atrás  
**Adição recente:** `Authentication & ATO` — adicionado **05 Jun 2026** (3 semanas atrás)  

---

## Escopo Mapeado

| Domain | Prioridade | Status |
|--------|-----------|--------|
| `accounts.shopify.com` | **CRÍTICO** (Authentication & ATO) | ✅ Explorado |
| `shopify.com` | HIGH | ⏳ Pendente |
| `admin.shopify.com` | HIGH | ⏳ Pendente (CF bloqueado) |
| `*.myshopify.com` | MEDIUM | ⏳ Pendente |
| `partners.shopify.com` | HIGH | ⏳ Pendente |

---

## Findings Identificados

### S1 — Pre-Auth Session Fixation Precondition (accounts.shopify.com)

**Status:** Parcialmente confirmado — necessita conta real para verificar rotação pós-login  
**Severidade Estimada:** HIGH (se sessão não rotar após login)

**Comportamento observado:**
1. `GET /oauth/authorize` com qualquer parâmetro → define `_identity_session` cookie
2. O servidor ACEITA e ECOA qualquer session ID fornecido pelo cliente:
   ```
   Request:  Cookie: _identity_session=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1
   Response: Set-Cookie: _identity_session=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1
   ```
3. `_identity_session` é definido com **`SameSite=None`** (UNIVERSALMENTE para TODOS os requests ao `/oauth/authorize`)
4. Cookie paralelo `__Host-_identity_session_same_site` tem `SameSite=Lax` (mais seguro)

**Por que SameSite=None é importante aqui:**
- `SameSite=None` → cookie enviado em TODOS os requests cross-origin  
- Se o session ID não rotacionar após login: attacker pode fixar sessão e aguardar vítima fazer login
- A protection `__Host-` no variant Lax mitiga parcialmente, mas o cookie sem `__Host-` (SameSite=None) ainda existe

**PoC para o usuário verificar:**
```bash
# 1. Obter um session ID como "attacker"
curl -sk -D - "https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=TEST&redirect_uri=https://example.com&scope=openid&state=xyz123" | grep "_identity_session"
# Anota o valor: _identity_session=SESSION_ID_A

# 2. No mesmo browser ou outro device:
#    - Setar manualmente Cookie: _identity_session=SESSION_ID_A  
#    - Ir para accounts.shopify.com e fazer login com conta própria
#    - Checar se SESSION_ID_A agora retorna sessão autenticada

# 3. Verificar com Burp Suite ou browser devtools:
#    - Login via accounts.shopify.com
#    - Antes do login: anotar _identity_session=X
#    - Após o login: checar se _identity_session MUDOU (rotação = seguro) ou é o mesmo (vulnerável)
```

**Indicador de vulnerabilidade confirmada:**  
Se após login o `_identity_session` tiver o MESMO valor que antes do login → Session Fixation confirmado.

---

### S2 — Session-Service JWKS sem campo `alg` (RFC 7517 violation)

**URL:** `https://accounts.shopify.com/session-service/.well-known/jwks.json`  
**Severidade Estimada:** LOW/INFO (sem exploração direta conhecida)

**Detalhes:**
```json
{
  "keys": [
    {
      "kid": "O6cGs_GDJfHXGWdm1ebI30h-pfrKCeToDWrHWsUjRC8",
      "kty": "OKP",
      "use": "sig",
      "crv": "Ed25519",
      "x": "vsGBkIzVtwmJBfGSLi0TOZOEfUfEDyjTRUgPsg2P..."
      // ← sem "alg" field
    }
    // + 2 chaves adicionais sem "alg"
  ]
}
```

RFC 7517 §4.4: campo `alg` é RECOMENDADO. A ausência pode causar:
- Algoritmo inferido apenas por `kty` + `crv` (Ed25519 → EdDSA)
- JWT libraries que não validam `alg` header vs key type → algorithm confusion

---

### S3 — CSP com `unsafe-inline` + `unsafe-eval` no enforce

**URL:** `https://accounts.shopify.com/oauth/authorize`  
**Severidade:** INFO (sem XSS exploitable confirmado)

```
content-security-policy: ... 'unsafe-inline' 'unsafe-eval' ... 'nonce-...'
```

Note: O CSP report-only é MAIS restrito que o enforced. Se XSS for encontrado no `accounts.shopify.com`, inline scripts executariam diretamente.

---

## Stack Técnico

```
accounts.shopify.com:
  Framework:    Ruby on Rails (meta[name=csrf-token] = authenticity_token)
  Session:      EncryptedCookie (_merchant_essential) + SessionID (_identity_session)
  CDN:          Cloudflare (CF-Ray, CF-Cache-Status, managed challenge)
  Assets CDN:   shopify-assets.shopifycdn.com / shopifycdn.com
  Monitoring:   Bugsnag (key: 424330c435072c4c39f8e66cf77d504f, appversion: 164506e7b2)
  Error CSP:    security-reports.shopifysvc.com/reporting-api (source_app=Identity)
  
Cookie Architecture:
  _merchant_essential: SameSite=Lax; Domain=.shopify.com; HttpOnly; Secure (encrypted blob)
  _identity_session:   SameSite=NONE; Secure; HttpOnly (session ID)
  __Host-_identity_session_same_site: SameSite=Lax; Secure; HttpOnly (__Host- prefix)
```

---

## OIDC Discovery (accounts.shopify.com)

```
token_endpoint:       https://accounts.shopify.com/oauth/token
userinfo_endpoint:    https://accounts.shopify.com/oauth/userinfo  (→ 401)
introspection:        https://accounts.shopify.com/oauth/introspection
revocation:           https://accounts.shopify.com/oauth/revoke
end_session:          https://accounts.shopify.com/logout  (→ 403)
jwks:                 https://accounts.shopify.com/oauth/discovery/keys

grant_types:
  - authorization_code
  - refresh_token
  - client_credentials
  - urn:ietf:params:oauth:grant-type:token-exchange  ← RFC 8693

scopes_supported: openid profile email phone address
                  device employee legacy privacy  ← CUSTOM SCOPES

claims_supported: iss sub aud exp iat nonce auth_time
                  device_uuid sid dest amr anum idp  ← CUSTOM CLAIMS

token_auth_methods: client_secret_basic, client_secret_post, none
backchannel_logout_supported: true
backchannel_logout_session_supported: true

subject_types: public, pairwise
id_token_signing_alg: RS256
code_challenge_methods: S256  (PKCE → enforcement não confirmado sem client real)
```

---

## Recon Técnico Realizado

| Endpoint | Método | Resultado |
|---------|--------|-----------|
| `/.well-known/openid-configuration` | GET | ✅ 200 — config completa |
| `/oauth/authorize` | GET | 400 (invalid_client sem client_id válido) — mas cookies + HTML funcionam |
| `/oauth/token` | POST (token-exchange) | `invalid_client` (precisa client_id real) |
| `/oauth/introspection` | POST | `invalid_client` sem auth |
| `/oauth/userinfo` | GET | 401 (endpoint existe) |
| `/oauth/discovery/keys` | GET | ✅ 200 — 1 chave RS256 com `alg` |
| `/session-service/.well-known/jwks.json` | GET | ✅ 200 — 3 chaves Ed25519 SEM `alg` |
| `/logout` | GET | 403 (protected) |

---

## Próximos Passos (com conta real)

### 1. Verificar Session Fixation (S1) — PRIORIDADE ALTA
```bash
# Criar conta de dev em partners.shopify.com
# Criar uma app de teste → obter client_id real
# Testar se _identity_session rotaciona após login
```

### 2. Testar Token Exchange com `employee` scope
```bash
curl -X POST "https://accounts.shopify.com/oauth/token" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  -d "client_id=SEU_CLIENT_ID" \
  -d "subject_token=SEU_ID_TOKEN" \
  -d "subject_token_type=urn:ietf:params:oauth:token-type:id_token" \
  -d "requested_token_type=urn:ietf:params:oauth:token-type:access_token" \
  -d "scope=employee"
```

### 3. Verificar PKCE enforcement
```bash
# Com client_id real, verificar se code_challenge é OBRIGATÓRIO
# para clientes públicos (auth_method=none)
```

### 4. Testar backchannel logout
```bash
# Precisa registrar um backchannel_logout_uri para o app
# Verificar se CSRF protection está presente
# Testar se logout token é validado corretamente
```

### 5. Explorar `dest` claim behavior
```bash
# Com flow real, verificar se dest= aceita URLs externas
# Potencial open redirect pós-login
```
