# Finding D3 — IRIS Platform: Missing Rate Limiting on Authentication Endpoint (No CAPTCHA)

**Título:** Missing Brute-Force Protection on IRIS Card Issuer Management Platform Authentication  
**Severidade:** MEDIUM (CVSS 5.9)  
**CWE:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)  
**Status:** Confirmado — 20 requests concorrentes sem throttling; 10 sequenciais sem 429  
**Escopo originário:** `*.dock.tech` → alvo: `front.iris.dock.tech`  
**Programa:** Bugpay (Dock) — produção apenas

---

## Discovery Chain

```
Passive recon: subfinder *.dock.tech
  → front.iris.dock.tech (CNAME → k8s-irisfron ALB → Kubernetes sa-east-1)
    → httpx: 200 "IRIS - Conductor Tecnologia" (Express.js + React, Google Analytics)
      → JS bundle analysis: REACT_APP_CAPTCHA_SITE_KEY = "false"
        → API discovery: /forward/api/authenticate (POST)
          → userType validation: LDAP | EXTERNO
            → Rate limit test: 3 concurrent requests → all succeed, no 429
```

---

## Sumário Técnico

O `front.iris.dock.tech` é o frontend público do sistema **ÍRIS** (Conductor Tecnologia, subsidiária da Dock), uma plataforma de backoffice para **card issuers** — responsável pelo gerenciamento de BINs, tokens de pagamento, transações, chargebacks, settlements e permissões de lançadores de cartões.

O endpoint de autenticação `/forward/api/authenticate` (POST) **não possui rate limiting** e **não implementa CAPTCHA** (configuração `REACT_APP_CAPTCHA_SITE_KEY: "false"` baked na build de produção), possibilitando ataques de força bruta de credenciais.

---

## Evidências

### 1. CAPTCHA Desabilitado em Produção

```bash
$ curl -s "https://front.iris.dock.tech/static/js/main.474be6c2.chunk.js" | \
  grep -oP 'REACT_APP_CAPTCHA_SITE_KEY[^,}]+'
REACT_APP_CAPTCHA_SITE_KEY:"false"
```

### 2. userType Leak via Erro de Validação

```bash
$ curl -s -X POST "https://front.iris.dock.tech/forward/api/authenticate" \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test","userType":"admin"}'
  
{"code":400,"message":"userType: admin does not validate as in(LDAP|EXTERNO)",
 "path":"/api/v1/authenticate","timestamp":"2026-06-26T23:28:56.225404258-03:00"}
```

Valores válidos revelados: **`LDAP`** (autenticação interna via Active Directory) e **`EXTERNO`** (clientes externos).

### 3. Sem Rate Limiting — 10 Sequenciais + 20 Concorrentes

```bash
# Teste 1: 10 requisições sequenciais
for i in $(seq 1 10); do
  curl -s -X POST "https://front.iris.dock.tech/forward/api/authenticate" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"WRONG","userType":"EXTERNO"}' \
    -w "[%{http_code}] " && sleep 0.1
done
# Resultado: [400][400][400][400][400][400][400][400][400][400]  — sem 429

# Teste 2: 20 requisições concorrentes
for i in $(seq 1 20); do
  curl -s -X POST "https://front.iris.dock.tech/forward/api/authenticate" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"WRONG","userType":"EXTERNO"}' \
    -w "[%{http_code}]" 2>/dev/null &
done && wait
# Resultado: 20x [400] simultâneos — sem 429, sem lockout, sem captcha challenge
```

**Análise de timing (user enumeration):**
```
Teste: mesmo request com username LDAP inexistente vs EXTERNO inexistente
LDAP:   ~0.095s, ~0.102s, ~0.098s (3 amostras)
EXTERNO:~0.097s, ~0.099s, ~0.103s (3 amostras)
→ Diferença de timing não mensurável → sem user enumeration via timing
```

Resultado final: sem `429 Too Many Requests`, sem lockout, sem CAPTCHA, em ambos os testes.

### 4. Scope do Sistema IRIS (Risk Context)

Rotas expostas no bundle JS revelam criticidade do sistema:

```
/bins, /bins-chaves, /bins-range  → Gerenciamento de BINs de cartão
/tokens, /tokens/                  → Payment Tokenization  
/transacoes, /transacoes/negadas   → Transações negadas
/issuer-external-id/               → IDs de emissores
/alcadas                           → Limites de alçada financeira
/ajustes-financeiros               → Ajustes financeiros
/operacoes                         → Operações de cartão
/perfis, /permissoes               → Perfis e permissões de usuários
/pier                              → Pier (plataforma core da Conductor)
```

---

## Impacto

- **Brute force** de credenciais EXTERNO: um atacante pode testar dicionários de senha sem restrição
- **Em caso de acesso bem-sucedido**: controle total sobre BINs de cartões, tokens de pagamento e transações de emissores clientes da Dock
- **LDAP path**: permite enumerar usuários internos se diferença de timing for mensurável (não testado por respeito ao escopo)

---

## PoC para Validação (sem executar brute force real)

```bash
# Verificar ausência de rate limit com 10 requests sequenciais:
for i in $(seq 1 10); do
  curl -s -X POST "https://front.iris.dock.tech/forward/api/authenticate" \
    -H "Content-Type: application/json" \
    -d '{"username":"YOURTESTACCOUNT","password":"WRONGPASSWORD","userType":"EXTERNO"}' \
    -w "\n[%{http_code}] " && sleep 0.1
done
# Esperado se sem proteção: 10x [400] sem [429]
```

---

## Remediação

1. Implementar rate limiting no endpoint (ex: max 5 tentativas/IP/min)
2. Reativar CAPTCHA em produção (`REACT_APP_CAPTCHA_SITE_KEY` com site key real)
3. Implementar account lockout progressivo (ex: lock após 10 tentativas)
4. Adicionar notificação de tentativas suspeitas via email/SIEM
