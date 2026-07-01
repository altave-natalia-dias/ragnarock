# Texto de Submissão — SF-004 (Plataforma BugHunt)

---

## Título
Braze CRM SDK Key exposta em `window.__RUNTIME_CONFIG__` permite escrita não-autenticada e cross-user no CRM (14M+ clientes)

## Severidade sugerida
**HIGH** — CVSS 3.1: **8.2** (`AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:L`)

## Programa
BugHunt — Grupo Smart Fit Bug Bounty Público

## Ativo afetado
`https://espacodocliente.smartfit.com.br` (origem da exposição) → `https://sdk.iad-07.braze.com/api/v3/data` (endpoint explorado)

## Classe da vulnerabilidade
CWE-862 (Missing Authorization) encadeado com CWE-522 (Insufficiently Protected Credentials)

---

## Resumo (para o campo "Descrição")

O portal `espacodocliente.smartfit.com.br` expõe a chave `brazeApiKey` do CRM Braze em `window.__RUNTIME_CONFIG__`, presente em **todas as páginas do site, incluindo 404**, acessível sem qualquer autenticação.

Diferente de uma simples exposição de chave client-side (que por si só não seria um achado, já que SDK keys do Braze são desenhadas para uso no navegador), o problema real é que o endpoint REST do Braze (`/api/v3/data`) **não vincula a escrita ao usuário da sessão que originou a chamada**. Qualquer chamador que possua a chave pode enviar um `external_id` **arbitrário** — diferente do usuário autenticado no navegador — e a API aceita a escrita (HTTP 201) sem nenhuma prova de posse daquela sessão/usuário.

Isso foi confirmado na prática enviando requisições diretas ao Braze com a chave extraída, para três tipos de operação distintos: eventos customizados, atributos de perfil (incluindo `email_subscribe`) e registros de compra (`purchases`) — todos retornando `HTTP 201 Created`, com rate limit de **20.000.000 requisições/hora** (burst de 1.296/3s).

**Impacto:** um atacante não-autenticado pode, em escala massiva:
- Corromper analytics e funis de marketing (eventos falsos)
- Opt-out de comunicação de clientes reais (bloqueio de faturas/alertas via `email_subscribe`)
- Distorcer relatórios de revenue/BI com compras falsas
- Disparar automações de marketing indevidas (campanhas de retenção, welcome flows) se a SmartFit usa Braze Canvas/Connected Content baseado em eventos

A limitação da PoC é que o `external_id` usado nos testes foi um valor sintético — não temos acesso ao painel Braze da SmartFit para confirmar visualmente a alteração de um cliente real. O que está tecnicamente provado (e já é suficiente para caracterizar CWE-862) é que **a API aceita qualquer `external_id`, sem checar vínculo com a sessão de origem** — resposta HTTP 201 idêntica independente do valor enviado.

---

## Passo a passo de reprodução

1. Acessar sem autenticação: `https://espacodocliente.smartfit.com.br/pt-BR/v2/login`
2. No DevTools → Console:
   ```javascript
   window.__RUNTIME_CONFIG__.brazeApiKey
   // → "4a0a6c8c-27bc-486d-a08e-ab144b7d5864"
   ```
3. Escrever no CRM com a chave extraída:
   ```bash
   curl -sk -D - "https://sdk.iad-07.braze.com/api/v3/data" -X POST \
     -H "Content-Type: application/json" \
     -d '{"api_key":"4a0a6c8c-27bc-486d-a08e-ab144b7d5864","device_id":"poc","events":[{"name":"poc_test","time":"2026-07-01T00:00:00Z"}]}'
   ```
4. Resposta observada: `HTTP/2 201 Created`, `x-ratelimit-limit: 20000000`
5. Repetir substituindo `events` por `attributes`/`purchases` com um `external_id` de teste diferente do usuário da sessão → mesmo resultado `201 Created`, confirmando ausência de vínculo sessão↔escrita.

*(Evidências completas com todos os requests/responses no relatório técnico anexo: `SF-004_braze_sdk_key_exposed_crm_write.md`)*

---

## Recomendação de correção

1. **Imediato:** revogar/rotacionar a chave `4a0a6c8c-27bc-486d-a08e-ab144b7d5864` no painel Braze
2. **Imediato:** remover `brazeApiKey` do `window.__RUNTIME_CONFIG__` renderizado server-side
3. **Curto prazo:** mover a inicialização do Braze SDK para um fluxo que não exponha a chave em HTML público
4. **Curto prazo:** auditar logs do Braze em busca de escrita anômala nas últimas semanas
5. **Longo prazo:** avaliar CSP restringindo chamadas não autorizadas ao domínio do Braze

---

## Confirmação de não-disrupção
Nenhuma atividade foi realizada para interromper sistemas ou serviços. As escritas de teste usaram `external_id` sintéticos (não correspondentes a clientes reais conhecidos) e nomes de evento claramente identificáveis como PoC (`poc_test`, `test_event`). Nenhum dado de cliente real foi lido, alterado ou exfiltrado.

---

## Anexos sugeridos
1. `SF-004_braze_sdk_key_exposed_crm_write.md` — relatório técnico completo com todas as evidências (curl + responses)
2. Screenshot do DevTools Console mostrando `window.__RUNTIME_CONFIG__.brazeApiKey` (capturar antes de enviar, se a plataforma exigir evidência visual)

---

## Checklist pré-envio
- [ ] Confirmar título/campo de severidade no formulário da plataforma BugHunt
- [ ] Anexar relatório técnico completo
- [ ] Capturar screenshot do DevTools (evidência visual do `window.__RUNTIME_CONFIG__`)
- [ ] Revisar se a chave ainda está ativa antes de enviar (revalidar 1 request de leitura, não escrever novamente)
- [ ] Enviar via plataforma BugHunt (confirmar URL/processo do programa antes do envio)
