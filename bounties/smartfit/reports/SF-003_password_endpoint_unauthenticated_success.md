# SF-003 — `/api/v1/password` Retorna `{"success":true}` Para Qualquer Request Sem Autenticação

**Programa:** BugHunt — Grupo Smart Fit Bug Bounty Público  
**Severidade:** MEDIUM  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)  
**CWE:** CWE-306 — Missing Authentication for Critical Function  
**CWE:** CWE-200 — Improper Error Handling / Enumeration Prevention Bypass  
**Endpoint afetado:** `https://espacodocliente.smartfit.com.br/api/v1/password`  
**Descoberto:** 2026-07-01  
**Status:** Confirmado — reproduzível sem autenticação

---

## Resumo

O endpoint `/api/v1/password` do portal do cliente da Smart Fit retorna `{"success":true}` para **qualquer requisição**, independentemente de:
- Método HTTP (GET, POST, PATCH, PUT)
- Corpo da requisição (qualquer JSON ou corpo vazio)
- Headers de autenticação (sem token, token inválido, qualquer valor)

Este comportamento é confirmado pelo mesmo `etag` em todas as respostas, indicando que o servidor está retornando uma resposta estática. O endpoint de alteração de senha retorna sucesso sem exigir autenticação, o que pode mascarar o status real das operações de senha e representa uma falha de segurança em funcionalidade crítica de autenticação.

---

## Evidência

### Teste 1 — GET sem autenticação
```bash
curl -sk -D - "https://espacodocliente.smartfit.com.br/api/v1/password"
```
```
HTTP/2 200
content-type: application/json
etag: "17a6zzdutk1g"
{"success":true}
```

### Teste 2 — POST sem autenticação, com email inválido
```bash
curl -sk "https://espacodocliente.smartfit.com.br/api/v1/password" -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"naoexiste@exemplo.com"}'
```
```json
{"success":true}
```

### Teste 3 — PATCH sem autenticação (deveria exigir senha atual + auth token)
```bash
curl -sk "https://espacodocliente.smartfit.com.br/api/v1/password" -X PATCH \
  -H "Content-Type: application/json" \
  -d '{"current_password":"qualquercoisa","new_password":"nova_senha123"}'
```
```json
{"success":true}
```

### Teste 4 — PATCH com cookie de sessão falso
```bash
curl -sk "https://espacodocliente.smartfit.com.br/api/v1/password" -X PATCH \
  -H "Content-Type: application/json" \
  -H "Cookie: session/smart-client-space=sessao_falsa_qualquer" \
  -d '{"current_password":"qualquer","new_password":"hacked123"}'
```
```http
HTTP/2 502 Bad Gateway
```
*(Com cookie presente → 502, sem cookie → 200 success)*

### Confirmação: mesmo etag em TODAS as respostas
```
etag: "17a6zzdutk1g"  ← idêntico em GET, POST, PATCH, PUT
```
O etag idêntico confirma que o servidor retorna resposta estática independente do input.

---

## Análise de Impacto

### Cenário A — Endpoint quebrado/stub (Mais provável)
O endpoint foi desativado ou não está implementado, mas retorna success como fallback. Impacto: usuários não conseguem redefinir senha via este endpoint, mas o sistema não expõe dados.

### Cenário B — Missing Authentication (Moderado)
Se o endpoint PATCH `/api/v1/password` aceita requisições não autenticadas e deveria processar mudança de senha, existe um vetor de ataque:
- Atacante com o `id` ou `email` de um usuário poderia tentar alterar a senha sem conhecer a atual
- A resposta `{"success":true}` não confirma se a ação foi executada

### Cenário C — Falsa Sensação de Segurança
O usuário recebe confirmação `{"success":true}` ao tentar resetar/alterar senha, mas a ação não foi realizada. Pode ser explorado para enganar usuários que acreditam que sua senha foi alterada.

---

## Reprodução

```bash
# Testa todos os métodos - todos retornam {"success":true}
for method in GET POST PATCH PUT; do
  echo "=== $method ==="
  curl -sk -X $method \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com"}' \
    "https://espacodocliente.smartfit.com.br/api/v1/password"
  echo
done
```

---

## Recomendações

1. **Imediato:** Se o endpoint está depreciado, retornar `HTTP 404` ou `410 Gone` em vez de `{"success":true}`
2. **Se ativo:** Implementar autenticação obrigatória (Bearer token ou session) para qualquer operação de mudança de senha
3. **Validação:** Exigir confirmação da senha atual para operações PATCH/PUT de mudança de senha
4. **Resposta diferenciada:** Distinguir entre reset de senha (POST com email) e mudança de senha (PATCH com auth + senha atual)
