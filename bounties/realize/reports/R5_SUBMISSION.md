# Texto de Submissão — R5 (Plataforma BugPay Haven, programa Realize Financeira)

---

## Título
Múltiplas Credenciais de Canal (Client Secrets) Hardcoded em JavaScript Público Permitem Bypass Total do Frontend e Chamadas Diretas à API de Autenticação

## Severidade sugerida
**MEDIUM** — CVSS 3.1 Base Score: **6.5**
Vetor: `AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N`

Cálculo (auditável):
- Impact Sub-Score = 1 − [(1−0.56)×(1−0)×(1−0)] = 0.56 → Impact = 6.42 × 0.56 = 3.595
- Exploitability = 8.22 × 0.85 × 0.77 × 0.85 × 0.62 = 2.835
- Base Score = roundup(3.595 + 2.835) = **6.5**

**Impacto ao negócio (critério primário do programa): ALTO** — estas credenciais são o que torna R6 e R7 exploráveis sem qualquer barreira do frontend. Reporto os três juntos porque a causa raiz é a mesma: nenhuma dessas rotas de autenticação deveria ser alcançável com um segredo estático extraído de HTML/JS público.

## Programa
BugPay Haven — Realize Soluções Financeiras (Bug Bounty)

## Ativo afetado
`www.realizesolucoesfinanceiras.com.br` (origem da exposição) + `api.realizesolucoesfinanceiras.com.br` (API explorada) — ambos em escopo explícito do programa.

## Classe da vulnerabilidade
CWE-798 — Use of Hard-Coded Credentials

---

## Resumo (para o campo "Descrição")

O portal `/cartoes-renner/` expõe **três credenciais Basic Auth de canal** (client secrets do gateway de API) em código acessível a qualquer visitante sem ferramentas especializadas — uma delas está inline no HTML da página de login (visível com `Ctrl+U`), as outras duas dentro do bundle JavaScript principal (`2.bundle-bb220f919f078e20c42e.js`, 2.1MB):

| Credencial | Uso | Onde apareceu no meu teste |
|-----------|-----|------|
| `renner-site:site` | Canal geral (`AUTHORIZATION_CANAL`) | HTML inline de `/cartoes-renner/login` |
| `renner-site-dataNascimento:siteDatanascimento` | Login por data de nascimento | Bundle JS |
| `renner-pre-autenticacao-cobranca:pre-autenticacao-cobranca` | Login do portal de negociação (ver R6) | Bundle JS |

Com qualquer uma delas, chamadas diretas à API de produção funcionam **sem passar pelo SPA** — ou seja, sem qualquer rate limiting, throttling ou lógica de proteção que exista apenas no lado do cliente.

Confirmei isso na prática, extraindo a credencial 1 automaticamente do HTML público e usando-a para chamar um endpoint real da API:

```bash
AUTHB64=$(curl -s "https://www.realizesolucoesfinanceiras.com.br/cartoes-renner/login" \
  | grep -oP 'AUTHORIZATION_CANAL.*?Basic \K[A-Za-z0-9+/=]+')

curl -s "https://api.realizesolucoesfinanceiras.com.br/api/parametro/ddds" \
  -H "Authorization: Basic ${AUTHB64}"
```

**Resposta: `HTTP 200`**, retornando a lista completa de DDDs ativos da plataforma — confirmando que a credencial extraída do HTML público é aceita pela API de produção sem qualquer verificação adicional.

Testei também ausência de rate limiting no endpoint de pré-autenticação usando a mesma credencial (5 chamadas consecutivas, nenhum header `X-RateLimit-*`/`Retry-After` na resposta), o que amplia o impacto: um atacante pode automatizar tentativas de autenticação (credential stuffing com CPFs vazados, força bruta de data de nascimento) diretamente contra a API, sem qualquer limite imposto pelo frontend.

---

## Passo a passo de reprodução

1. Acessar `https://www.realizesolucoesfinanceiras.com.br/cartoes-renner/login` sem autenticação
2. Ver código-fonte (`Ctrl+U`) → localizar `window.constants.AUTHORIZATION_CANAL = 'Basic cmVubmVyLXNpdGU6c2l0ZQ=='`
3. Decodificar: `echo "cmVubmVyLXNpdGU6c2l0ZQ==" | base64 -d` → `renner-site:site`
4. Chamar `GET https://api.realizesolucoesfinanceiras.com.br/api/parametro/ddds` com `Authorization: Basic cmVubmVyLXNpdGU6c2l0ZQ==` → `HTTP 200` com dado real da aplicação
5. Repetir o processo para o bundle `js/2.bundle-*.js` → localizar as outras duas credenciais no mapeamento `tokenTypeMap`

*(Evidência técnica completa, incluindo mapa de uso das 3 credenciais por endpoint, no relatório anexo: `R5_hardcoded_channel_credentials_in_js_bundle.md`)*

---

## Recomendação de correção

1. **Imediato:** rotacionar as três credenciais (`renner-site`, `renner-site-dataNascimento`, `renner-pre-autenticacao-cobranca`).
2. **Imediato:** implementar rate limiting server-side (`429` + `Retry-After`) em todos os endpoints de autenticação — hoje a única proteção de fato é client-side.
3. **Curto prazo:** remover client secrets do código executado no navegador; usar arquitetura BFF (Backend-for-Frontend) para intermediar chamadas à API, mantendo credenciais apenas no servidor.

---

## Confirmação de não-disrupção e conformidade com a política

- A única chamada de escrita/consulta real foi a um endpoint público de parâmetros (`/api/parametro/ddds`), que não retorna dado de cliente.
- O teste de ausência de rate limiting usou CPF sintético inválido (`00000000191`), sem alcançar dado de terceiro.
- Nenhuma credencial de terceiro, força bruta real ou automação em volume foi executada — apenas confirmação pontual do comportamento.

---

## Anexos sugeridos
1. `R5_hardcoded_channel_credentials_in_js_bundle.md` — relatório técnico completo com as 3 credenciais, localização exata e PoC de cada uma
2. Trecho do bundle JS com o `tokenTypeMap` (evidência de código-fonte)

---

## Checklist pré-envio
- [x] CVSS recalculado e auditado (6.5)
- [ ] Revalidar que as 3 credenciais ainda funcionam no dia do envio
- [ ] Confirmar título/campo de severidade no formulário BugPay Haven
- [ ] Anexar relatório técnico completo
- [ ] Enviar via plataforma BugPay Haven — considerar enviar **junto com R6 e R7** ou referenciá-los explicitamente (mesma causa raiz, achados encadeados)
