# Texto de Submissão — BB-001 (Plataforma BugHunt, programa Banco do Brasil - VDP)

---

## Título
Ausência de Autenticação na API de Contratos de Fornecedores (`fornecedor.bb.com.br`) Expõe Dados Comerciais Confidenciais B2B

## Severidade
**HIGH** — CVSS 3.1 Base Score: **7.5**
Vetor: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`

Cálculo (auditável, não estimado):
- Impact Sub-Score = 1 − [(1−0.56)×(1−0)×(1−0)] = 0.56
- Impact = 6.42 × 0.56 = 3.5952
- Exploitability = 8.22 × 0.85 × 0.77 × 0.85 × 0.85 = 3.8870
- Base Score = roundup(3.5952 + 3.8870) = **7.5**

Não classifiquei como Critical: o endpoint é somente leitura (`GET`), sem impacto demonstrado em Integridade ou Disponibilidade — só Confidencialidade Alta. Reportar com precisão em vez de inflar.

## Programa
Banco do Brasil - VDP (Vulnerability Disclosure Program)

## Ativo afetado
`https://fornecedor.bb.com.br/compras-pfnweb/api/v1/contrato/*` (Portal do Fornecedor)
IP: `170.66.14.91` — confirmado dentro do escopo declarado do programa (ASN 11993 / AS11993 = BANCO DO BRASIL S.A., verificado via LACNIC)

## Classe da vulnerabilidade
CWE-306 — Missing Authentication for Critical Function
CWE-639 — Authorization Bypass Through User-Controlled Key (secundário, se autenticação for adicionada sem vincular o CNPJ à sessão)

---

## Descrição (resumo para o campo da plataforma)

O Portal do Fornecedor do Banco do Brasil expõe a API `/compras-pfnweb/api/v1/contrato/*` **sem nenhuma camada de autenticação**. Requisições HTTP diretas, sem sessão, cookie de login ou token, são processadas normalmente pelo backend e retornam respostas estruturadas reais da aplicação.

O endpoint principal, `listarContratosFormalizadosUsuarioExterno`, filtra contratos formalizados por **CNPJ informado livremente como parâmetro de busca** (`codigoCadastroNacPessoasJuridicas`). Como CNPJ é dado público (consultável na Receita Federal), qualquer pessoa pode consultar os contratos formalizados de **qualquer empresa fornecedora do BB**, sem autenticação.

Confirmei o padrão como **sistêmico**, não isolado: os 3 endpoints irmãos do mesmo serviço (`listarAditivosFormalizadosUsuarioExterno`, `listarAssinaturas`, `autenticarContratoFormalizado`) respondem da mesma forma — processam a consulta e retornam erro de **regra de negócio** ("registro não encontrado"), nunca erro de autenticação.

**Encadeamento de impacto:** CNPJ (público) → lista de contratos → número do contrato → aditivos contratuais + assinaturas = dossiê comercial confidencial completo de qualquer fornecedor do BB, tudo sem login.

---

## Prova de Conceito (ética — nenhum dado de terceiro foi acessado)

Para confirmar a falha sem consultar dados confidenciais de uma empresa real, usei o **CNPJ do próprio Banco do Brasil** (`00.000.000/0001-91`), sabendo que o BB não é fornecedor de si mesmo — a resposta, portanto, não poderia conter dado real de terceiro.

```bash
curl -sk -G "https://fornecedor.bb.com.br/compras-pfnweb/api/v1/contrato/listarContratosFormalizadosUsuarioExterno" \
  --data-urlencode "numeroPosicaoLista=1" \
  --data-urlencode "codigoCadastroNacPessoasJuridicas=00000000000191" \
  --data-urlencode "dataInicioPesquisa=01/06/2026" \
  --data-urlencode "dataFimPesquisa=01/07/2026"
```

**Nenhum cookie, header de sessão ou token foi enviado.**

**Resposta: `HTTP/1.1 200 OK`**
```json
{"status":"OK","messages":[{"text":"Não foram localizados contratos para os parâmetros informados","type":"WARN","fields":[]}],"data":[],"permissions":{},"statusCode":200}
```

O array `data` vem vazio **porque o BB não tem contratos consigo mesmo** — não porque a requisição foi bloqueada. A resposta prova que o backend executou a lógica de negócio completa (busca por CNPJ, validação de intervalo de datas) e retornou o schema real da aplicação (`status`/`messages`/`data`/`permissions`/`statusCode`), sem qualquer rejeição de autenticação. Revalidado nesta data — vulnerabilidade ainda ativa.

**Por que não usei um CNPJ de terceiro real para "provar melhor":** a política do programa proíbe explicitamente obter mais informações do que o essencial para a PoC. A resposta estrutural com o CNPJ do próprio BB já é prova suficiente e conclusiva — o comportamento com um CNPJ que possui contratos reais seria estruturalmente idêntico, apenas com o array `data` populado.

---

## Passo a passo de reprodução

1. Sem login, enviar `GET https://fornecedor.bb.com.br/compras-pfnweb/api/v1/contrato/listarContratosFormalizadosUsuarioExterno` com parâmetros `numeroPosicaoLista`, `codigoCadastroNacPessoasJuridicas` (CNPJ, 14 dígitos sem máscara), `dataInicioPesquisa` e `dataFimPesquisa` (formato `DD/MM/AAAA`, intervalo máximo de 60 dias, início a partir de 01/01/2019)
2. Observar `HTTP 200` com JSON estruturado da aplicação — sem redirecionamento para login, sem erro de autenticação
3. Se o CNPJ consultado tiver contratos formalizados com o BB no período informado, o array `data` retorna preenchido com os registros

*(Evidência técnica completa, incluindo os testes nos 3 endpoints irmãos, no relatório anexo: `BB-001_missing_auth_supplier_contract_api.md`)*

---

## Recomendação de correção

1. **Imediato:** exigir sessão de usuário fornecedor autenticado em toda a API `/compras-pfnweb/api/v1/*` (serviço "externo").
2. **Imediato:** vincular `codigoCadastroNacPessoasJuridicas` ao CNPJ do usuário autenticado na sessão — mesmo após implementar autenticação, o parâmetro não deve aceitar CNPJ arbitrário livre (evita reintroduzir o mesmo problema como IDOR pós-login).
3. **Curto prazo:** aplicar o mesmo controle nos endpoints de aditivos e assinaturas.
4. **Curto prazo:** auditar logs de acesso em busca de consultas massivas/sequenciais de CNPJ.
5. **Sugestão de investigação adicional (não testado, não faz parte do achado provado):** verificar se o mesmo padrão de "serviço externo sem autenticação" se repete nos demais módulos do Portal do Fornecedor (`credenciamento-pfnweb`, `contratados-pfnweb`, `qgd-fornecedor`, etc.).

---

## Confirmação de não-disrupção e conformidade com a política

- Todas as requisições respeitaram o limite de 60 req/min do programa (testes feitos manualmente, poucas dezenas de requisições no total, espaçadas).
- Nenhum teste foi feito em ambiente intranet/interno — o serviço `interno` irmão (`/v1/spas/interno/contratos-fornecedor-service-min.js`), identificado durante o recon, **não foi acessado**.
- Nenhuma credencial vazada foi utilizada — a falha é de ausência total de autenticação, não de uso de credencial de terceiro.
- Nenhum dado confidencial de terceiro foi acessado — PoC construída inteiramente com o CNPJ público do próprio Banco do Brasil.
- Nenhuma atividade de força bruta, DoS ou scan recorrente foi realizada.

---

## Anexos sugeridos
1. `BB-001_missing_auth_supplier_contract_api.md` — relatório técnico completo
2. Headers de resposta completos (sem cookie de sessão enviado na requisição, confirmando ausência de autenticação)

---

## Checklist pré-envio
- [x] CVSS recalculado e auditado (7.5, não superestimado)
- [x] PoC revalidada no dia da submissão — vulnerabilidade ainda ativa
- [x] Confirmado zero acesso a dado confidencial de terceiro
- [x] Confirmado zero teste em ativo intranet/fora do ASN 11993
- [ ] Confirmar título/campo de severidade no formulário da plataforma BugHunt
- [ ] Anexar relatório técnico completo
- [ ] Enviar via plataforma BugHunt
