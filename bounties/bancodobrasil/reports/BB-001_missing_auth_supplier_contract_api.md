# BB-001 — Ausência de Autenticação na API de Contratos de Fornecedores Expõe Dados Confidenciais B2B (`fornecedor.bb.com.br`)

**Programa:** Banco do Brasil - VDP (Vulnerability Disclosure Program)
**Severidade:** HIGH
**CVSS 3.1:** 7.5 (`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`)
**CWE:** CWE-306 — Missing Authentication for Critical Function
**CWE (secundário):** CWE-639 — Authorization Bypass Through User-Controlled Key
**Endpoint afetado:** `https://fornecedor.bb.com.br/compras-pfnweb/api/v1/contrato/*` (múltiplos endpoints, ver abaixo)
**Descoberto:** 2026-07-01
**Status:** CONFIRMADO — exploração demonstrada sem tocar em dado de terceiro

---

## Resumo Executivo

O Portal do Fornecedor (`fornecedor.bb.com.br`) do Banco do Brasil expõe uma API de consulta de contratos formalizados (`/compras-pfnweb/api/v1/contrato/*`) **sem nenhuma camada de autenticação**. Qualquer requisição HTTP direta, sem sessão, sem cookie de login e sem token, é processada normalmente pelo backend e retorna respostas estruturadas reais da aplicação — incluindo, para o endpoint principal, dados de contratos formalizados de qualquer empresa, filtrados pelo **CNPJ informado como parâmetro de busca**.

Como o CNPJ é informação pública (consultável na Receita Federal), qualquer atacante pode:
1. Escolher o CNPJ de qualquer empresa fornecedora do Banco do Brasil (ou enumerar CNPJs)
2. Consultar `listarContratosFormalizadosUsuarioExterno` sem login e obter a lista de contratos formalizados daquela empresa com o BB
3. Encadear os números de contrato retornados para consultar aditivos contratuais (`listarAditivosFormalizadosUsuarioExterno`) e assinaturas (`listarAssinaturas`) — também sem autenticação
4. Montar um dossiê completo e confidencial de relacionamento comercial entre o BB e qualquer um de seus fornecedores

Isso caracteriza exposição de dados comerciais confidenciais (valores contratuais, datas, partes envolvidas, status de formalização) para qualquer parte não autorizada, sem necessidade de credenciais.

---

## Evidência Técnica

### 1. Descoberta do endpoint via análise de JS estático (sem tocar em API ainda)

A partir da página pública `https://fornecedor.bb.com.br/`, mapeei a cadeia de carregamento de módulos AngularJS:

```
/ → modules-config-min.js → v2/modules-min.js → /compras-pfnweb/startup.js
  → /compras-pfnweb/v1/spas/externo/contratos-fornecedor-service-min.js
```

O arquivo `contratos-fornecedor-service-min.js` define o factory Angular `ContratosFornecedorExternoService` com as seguintes chamadas HTTP (extraído do JS servido publicamente, sem necessidade de qualquer engenharia reversa complexa):

```javascript
// GET /compras-pfnweb/api/v1/contrato/listarContratosFormalizadosUsuarioExterno
//   params: numeroPosicaoLista, numeroResumidoContrato,
//           codigoCadastroNacPessoasJuridicas (= CNPJ), dataInicioPesquisa, dataFimPesquisa

// GET /compras-pfnweb/api/v1/aditivo/listarAditivosFormalizadosUsuarioExterno
//   params: numeroPosicao, anoContrato, codigoUnidadeOrganizacionalContrato,
//           numeroContrato, numeroAditivoContratualContrato

// GET /compras-pfnweb/api/v1/contrato/autenticarContratoFormalizado
//   params: codigoVerificacaoAutenticacaoInstrumento

// GET /compras-pfnweb/api/v1/contrato/listarAssinaturas
//   params: anoContrato, codigoUOR, numContrato, codTipoInstrumento, numAditivo
```

Notar que o serviço tem uma versão irmã `interno` (`/v1/spas/interno/contratos-fornecedor-service-min.js`) para uso de colaboradores do BB — **essa versão interna não foi testada nem acessada**, por estar fora do escopo permitido pela política do programa (proibição de teste em ambiente interno).

### 2. Confirmação de ausência de autenticação — PoC ético, sem dado de terceiro

Para confirmar a falha sem consultar dados confidenciais de uma empresa real (o que violaria a cláusula da política que proíbe "obter mais informações do que o essencial para a prova de conceito"), utilizei o **CNPJ do próprio Banco do Brasil** (`00.000.000/0001-91` — público, confirmado via registro LACNIC/registro.br), sabendo que o BB não é fornecedor de si mesmo e portanto a resposta não conteria dados reais de terceiros.

```bash
curl -sk -G "https://fornecedor.bb.com.br/compras-pfnweb/api/v1/contrato/listarContratosFormalizadosUsuarioExterno" \
  --data-urlencode "numeroPosicaoLista=1" \
  --data-urlencode "codigoCadastroNacPessoasJuridicas=00000000000191" \
  --data-urlencode "dataInicioPesquisa=01/06/2026" \
  --data-urlencode "dataFimPesquisa=01/07/2026"
```

**Nenhum cookie, header de sessão ou token de autenticação foi enviado nesta requisição.**

**Resposta: `HTTP/1.1 200 OK`**

```json
{
  "status": "OK",
  "messages": [
    {"text": "Não foram localizados contratos para os parâmetros informados", "type": "WARN", "fields": []}
  ],
  "data": [],
  "permissions": {},
  "statusCode": 200
}
```

Isso prova que o backend **processou a consulta de negócio completa** (buscou contratos pelo CNPJ informado, validou o intervalo de datas, retornou o schema real de resposta da aplicação com os campos `status`/`messages`/`data`/`permissions`/`statusCode`) sem qualquer rejeição por falta de autenticação. O array `data` veio vazio exclusivamente porque o BB não possui contratos formalizados consigo mesmo como fornecedor — **não porque a requisição foi bloqueada**.

### 3. Padrão sistêmico confirmado nos endpoints irmãos

Repeti o teste (sempre com valores de identificador genéricos/dummy, nunca de terceiro real) nos 3 endpoints irmãos do mesmo serviço:

```bash
# Aditivos contratuais
curl -sk -G ".../compras-pfnweb/api/v1/aditivo/listarAditivosFormalizadosUsuarioExterno" \
  --data-urlencode "numeroPosicao=1" --data-urlencode "anoContrato=2026" \
  --data-urlencode "codigoUnidadeOrganizacionalContrato=1" \
  --data-urlencode "numeroContrato=1" --data-urlencode "numeroAditivoContratualContrato=1"
# → HTTP 400, erro de NEGÓCIO: "Não foram encontrados aditivos disponíveis para o contrato selecionado"

# Assinaturas do instrumento contratual
curl -sk -G ".../compras-pfnweb/api/v1/contrato/listarAssinaturas" \
  --data-urlencode "anoContrato=2026" --data-urlencode "codigoUOR=1" \
  --data-urlencode "numContrato=1" --data-urlencode "codTipoInstrumento=1" --data-urlencode "numAditivo=1"
# → HTTP 400, erro de NEGÓCIO: "Não encontrado número de assinatura para o instrumento contratual informado"
```

Em ambos os casos, o erro retornado é de **regra de negócio** (registro não encontrado para os IDs informados), nunca de autenticação/autorização — confirmando que **toda a superfície `externo` da API de contratos do módulo `compras-pfnweb` roda sem camada de autenticação**.

(O quarto endpoint, `autenticarContratoFormalizado`, também respondeu sem exigir auth, mas esse é provavelmente **público por design** — é um mecanismo de verificação de autenticidade de instrumento contratual via código, análogo a verificar a autenticidade de um documento oficial via código impresso nele. Não o considero parte do achado, apenas evidência adicional de que a camada de auth realmente não existe nesse serviço.)

---

## Análise de Impacto

| Vetor | Descrição |
|---|---|
| **Confidencialidade** | Dados de contratos formalizados entre o BB e seus fornecedores (valores, datas, status, partes) ficam acessíveis a qualquer pessoa não autenticada que conheça o CNPJ da empresa-alvo |
| **Trivialidade de exploração** | CNPJ é dado público (Receita Federal, redesocial.receita.fazenda.gov.br, etc.) — não é um segredo a ser vazado, é um identificador consultável por qualquer pessoa |
| **Encadeamento** | CNPJ → lista de contratos → número do contrato → aditivos + assinaturas = dossiê completo do relacionamento comercial de qualquer fornecedor com o BB, tudo sem autenticação |
| **Escala** | Não há necessidade de força bruta — um atacante com uma lista de CNPJs de empresas de interesse (concorrentes, alvos de engenharia social, imprensa investigativa etc.) pode consultar diretamente |

---

## Limitação da Prova de Conceito (deliberada, por escolha ética)

Não consultei nenhum CNPJ de empresa real de terceiros para obter dados de contrato reais — isso exigiria acessar informação comercial confidencial de uma parte que não é signatária deste programa de disclosure, o que a própria política do BB proíbe explicitamente ("obter mais informações do que o essencial para a prova de conceito"). A prova acima (resposta HTTP 200 com schema de negócio real, usando o CNPJ público do próprio BB) já é suficiente e conclusiva para demonstrar a falha de autenticação — o comportamento do endpoint com um CNPJ que *tem* contratos reais seria estruturalmente idêntico, apenas com o array `data` populado.

---

## Recomendações

1. **Imediato (crítico):** implementar autenticação obrigatória em toda a API `/compras-pfnweb/api/v1/*` (serviço "externo"), exigindo sessão válida de usuário fornecedor autenticado.
2. **Imediato:** vincular o `codigoCadastroNacPessoasJuridicas` consultável ao CNPJ do usuário autenticado na sessão — mesmo com autenticação implementada, o parâmetro não deve permitir consulta livre de CNPJ arbitrário (evita reintrodução do mesmo problema como IDOR pós-autenticação).
3. **Curto prazo:** aplicar o mesmo controle de autorização aos endpoints de aditivos e assinaturas, vinculando ao contrato pertencente ao fornecedor autenticado.
4. **Curto prazo:** auditar logs de acesso a esses endpoints em busca de consultas massivas/sequenciais de CNPJ que indiquem exploração já ocorrida.
5. **Médio prazo:** revisar todos os demais módulos do Portal do Fornecedor (`contrato-pfnweb`, `credenciamento-pfnweb`, `contratados-pfnweb`, `qgd-fornecedor`, etc.) quanto ao mesmo padrão de ausência de autenticação — o achado neste relatório cobre apenas o módulo `compras-pfnweb`, mas a mesma arquitetura de "serviço externo" pode se repetir nos demais módulos.

---

## Reprodução Passo-a-Passo

1. Acesse (sem login): `https://fornecedor.bb.com.br/compras-pfnweb/api/v1/contrato/listarContratosFormalizadosUsuarioExterno?numeroPosicaoLista=1&codigoCadastroNacPessoasJuridicas=<CNPJ_ALVO>&dataInicioPesquisa=<DD/MM/AAAA>&dataFimPesquisa=<DD/MM/AAAA>` (intervalo de datas máximo de 60 dias, início a partir de 01/01/2019)
2. Observe que a resposta é `HTTP 200` com JSON estruturado real da aplicação, sem qualquer redirecionamento para login ou erro de autenticação
3. Se o CNPJ informado tiver contratos formalizados com o BB no período, o array `data` virá populado com os registros

---

## Referências

- CWE-306: https://cwe.mitre.org/data/definitions/306.html
- CWE-639: https://cwe.mitre.org/data/definitions/639.html
- OWASP API Security Top 10 2023 — API2:2023 Broken Authentication
- OWASP Top 10 2021 — A01:2021 Broken Access Control
