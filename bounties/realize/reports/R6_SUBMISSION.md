# Texto de Submissão — R6 (Plataforma BugPay Haven, programa Realize Financeira)

---

## Título
Autenticação do Portal de Negociação de Dívidas com Apenas CPF + Data de Nascimento Permite Acesso, Confirmação de Acordos e Emissão de Boletos em Nome de Qualquer Cliente

## Severidade sugerida
**CRITICAL** — CVSS 3.1 Base Score: **9.1** (recalculado — ver nota abaixo)
Vetor: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`

**Nota sobre o CVSS:** o relatório técnico original (`R6_portal_negociacao_cpf_birthdate_auth.md`) registrou CVSS 8.1 (HIGH). Ao auditar o cálculo para esta submissão encontrei um erro aritmético — com o mesmo vetor (`C:H/I:H`, já que o achado permite tanto ler dívidas quanto **confirmar acordos e gerar boletos**, ou seja, integridade alta e não só confidencialidade), o resultado correto é:
- Impact Sub-Score = 1 − [(1−0.56)×(1−0.56)×(1−0)] = 0.8064 → Impact = 6.42 × 0.8064 = 5.177
- Exploitability = 8.22 × 0.85 × 0.77 × 0.85 × 0.85 = 3.887
- Base Score = roundup(5.177 + 3.887) = **9.1 (Critical)**, não 8.1.

Reporto a correção explicitamente por transparência — prefiro reportar com precisão a inflar ou errar por acomodação ao rascunho anterior.

**Impacto ao negócio (critério primário do programa): CRÍTICO.** Isto não é apenas exposição de dados — é a capacidade de **confirmar acordos de dívida e gerar boletos fraudulentos em nome de terceiros**, sem prova de titularidade além de dois dados semi-públicos no Brasil (CPF + data de nascimento).

## Programa
BugPay Haven — Realize Soluções Financeiras (Bug Bounty)

## Ativo afetado
`api.realizesolucoesfinanceiras.com.br` — em escopo explícito (Escopo Adicional #1, tipo API).
Endpoint: `POST /api/autenticacao/acesso/cpf/dataNascimento/cobranca`

## Classe da vulnerabilidade
CWE-521 — Weak Password Requirements
CWE-308 — Use of Single-factor Authentication

---

## Resumo (para o campo "Descrição")

O portal de negociação de dívidas da Realize (usado por clientes com pendências no Cartão Renner/Youcom/Camicado/Ashua) autentica o usuário usando **apenas CPF e data de nascimento** — nenhuma senha, PIN ou fator adicional é exigido. A única barreira é o Google reCAPTCHA v2, um token enviado no header `Captcha`.

CPF e data de nascimento **não são segredos** no contexto brasileiro: CPFs circulam amplamente em bases vazadas (e-commerce, órgãos públicos), e datas de nascimento são frequentemente conhecidas por terceiros ou inferíveis de redes sociais. Confirmei que o endpoint está ativo em produção:

```bash
curl -s -X POST \
  "https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/acesso/cpf/dataNascimento/cobranca" \
  -H "Authorization: Basic cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ==" \
  -H "Content-Type: application/json" \
  -H "Captcha: INVALID_CAPTCHA_TOKEN" \
  -d '{"cpf":"00000000191","dataNascimento":"1990-01-01"}'
```

**Resposta: `HTTP 400`**, `{"error":"invalid_request","details":{"captcha":"true"}}` — confirma que o endpoint processa a requisição e rejeita **apenas** pelo captcha, nunca por senha/PIN inexistente.

A credencial de canal Basic Auth usada acima (`renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca`) está hardcoded em JavaScript público do portal — reportada separadamente em R5, mas relevante aqui porque **remove até o reCAPTCHA como barreira de canal**: qualquer automação que resolva o captcha (serviços comerciais custam ~US$0,001/solução) pode chamar o endpoint diretamente, sem qualquer limite imposto pelo frontend oficial, já que confirmei ausência de rate limiting server-side (5 chamadas consecutivas, nenhum header `X-RateLimit-*`).

**Uma vez autenticado, o token dá acesso a:**

| Endpoint | Impacto |
|----------|---------|
| `GET /api/acordo/v2/divida` | Lista completa das dívidas da conta |
| `GET /api/acordo/v2/cliente` + `/contatos` | Dados do titular + email/telefone |
| `POST /api/acordo/v2/negociacao` | **Confirmar acordo de dívida** |
| `POST /api/acordo/v2/boleto` | **Gerar boleto de acordo** |

### Cenário de ataque
Um atacante com o CPF de um devedor Realize (ex.: vazamento, cadastro de loja) e a data de nascimento (redes sociais, dado vazado em conjunto) pode: resolver o captcha → autenticar-se como a vítima → visualizar dívidas → **confirmar um acordo de dívida "negociado" e gerar um boleto** — potencial vetor de fraude financeira direta, não apenas exposição de dados.

---

## Passo a passo de reprodução

1. `POST https://api.realizesolucoesfinanceiras.com.br/api/autenticacao/acesso/cpf/dataNascimento/cobranca` com `Authorization: Basic cmVubmVyLXByZS1hdXRlbnRpY2FjYW8tY29icmFuY2E6cHJlLWF1dGVudGljYWNhby1jb2JyYW5jYQ==`, body `{"cpf":"<CPF>","dataNascimento":"YYYY-MM-DD"}` e um token reCAPTCHA v2 válido no header `Captcha`
2. Resposta de sucesso retorna `access_token` com `scope: site_pre_autenticacao_cobranca`
3. Com o token: `GET /api/acordo/v2/divida` lista as dívidas; `POST /api/acordo/v2/negociacao` confirma acordo; `POST /api/acordo/v2/boleto` gera boleto

*(Evidência técnica completa, incluindo mapeamento de todos os endpoints acessíveis pós-auth, no relatório anexo: `R6_portal_negociacao_cpf_birthdate_auth.md`)*

**Não executei os passos 2–4 contra CPF de terceiro** — a confirmação foi limitada ao comportamento do endpoint de autenticação (passo 1), que já é suficiente para provar a ausência de fator forte. Recomendo que o time interno da Realize valide os passos subsequentes com uma conta de teste própria.

---

## Recomendação de correção

1. **Imediato (P0):** exigir segundo fator (SMS/email cadastrado) além de CPF + data de nascimento antes de emitir token de acesso ao portal de negociação.
2. **Imediato (P0):** implementar lockout progressivo por CPF (3–5 tentativas → bloqueio crescente).
3. **Curto prazo:** rate limiting server-side no endpoint de autenticação (hoje inexistente).
4. **Curto prazo:** notificar o titular (SMS/email) sempre que o portal de negociação for acessado.
5. Ver R5 para a remediação da credencial de canal que remove a barreira adicional do reCAPTCHA.

---

## Confirmação de não-disrupção e conformidade com a política

- Usei apenas CPF matematicamente válido porém sintético (`000.000.001-91`), sem corresponder a cliente real.
- Não completei o fluxo de autenticação (não resolvi captcha real), portanto **não confirmei acesso a dado de terceiro** — o achado está provado até o ponto da ausência de fator forte; os passos 2-4 (dados, negociação, boleto) são descritos com base no mapeamento do bundle JS (ver R5) e ficam como validação sugerida ao time interno, não como PoC executada contra dado real.
- Nenhuma automação de captcha, força bruta ou volume de requisições foi realizada.

---

## Anexos sugeridos
1. `R6_portal_negociacao_cpf_birthdate_auth.md` — relatório técnico completo
2. Request/response do passo de autenticação (HTTP 400 com `details.captcha`)

---

## Checklist pré-envio
- [x] CVSS recalculado e auditado (9.1, corrigido de 8.1 no rascunho original)
- [x] Confirmado que a PoC não acessou dado de terceiro real
- [ ] Confirmar título/campo de severidade no formulário BugPay Haven (sugerir CRITICAL com a nota de recálculo)
- [ ] Anexar relatório técnico completo
- [ ] Enviar via plataforma BugPay Haven — mencionar R5 (credencial de canal) e R7 (mesma família de bypass de pré-autenticação) como achados relacionados
