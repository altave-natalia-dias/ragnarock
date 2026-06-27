# ZO4 — Staging MCP Endpoint Active on Production Server

**Título:** `/staging/mcp` Endpoint Accessible on Production `mcp-server.zomato.com`  
**Severidade:** LOW (CVSS 4.3)  
**CVSS Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` → **4.3 LOW**  
**CWE:** CWE-749 (Exposed Dangerous Method or Function)  
**Target:** `https://mcp-server.zomato.com/staging/mcp`  
**Status:** Confirmado — retorna 401 (não 404)

---

## Summary

O endpoint `/staging/mcp` existe e responde com `401 Unauthorized` no servidor de produção `mcp-server.zomato.com`. Isto confirma que:

1. O ambiente de staging está sendo executado no mesmo servidor de produção (ou é routeado para o mesmo backend)
2. O endpoint está acessível externamente com autenticação — não está isolado em uma rede interna
3. O JavaScript do consent page em produção tem código explícito para detectar e rotear para `/staging/`

---

## Evidência

```bash
# Produção /mcp — esperado, 401
$ curl -si https://mcp-server.zomato.com/mcp
HTTP/2 401
www-authenticate: Bearer error="invalid_token", error_description="Authentication required"
server: uvicorn

# Staging /staging/mcp — deveria retornar 404 em produção, mas retorna 401
$ curl -si https://mcp-server.zomato.com/staging/mcp
HTTP/2 401
www-authenticate: Bearer error="invalid_token", error_description="Authentication required"
server: uvicorn

# Routing diferente confirmado — mesmo uvicorn, mesma estrutura de resposta
```

### Código no Consent Page (Produção) que Confirma

```javascript
getApiPath(path) {
    const currentPath = window.location.pathname;
    if (currentPath.startsWith('/staging')) {
        return `/staging${path}`;
    }
    return path;
}
```

Este código de produção roteia `/login` → `/staging/verify-otp` e `/staging/mcp` quando acessado via `/staging/*`.

---

## Riscos

### 1. Staging pode ter proteções mais fracas
Ambientes de staging frequentemente têm:
- Tokens com validade estendida
- Rate limiting desativado
- Debug logging ativo
- Versões menos auditadas do código

### 2. Token de staging pode acessar dados de produção
Se `/staging/mcp` compartilha o backend com `/mcp` mas aceita tokens de teste com permissões mais amplas, um atacante com um token de staging pode acessar dados reais de usuários.

### 3. Superfície de ataque adicional
Um endpoint extra em produção é mais surface para bruteforce de tokens, timing attacks, e versão diferente do código.

---

## Proof of Concept

```bash
# Confirmar que /staging/mcp retorna 401 (não 404)
curl -si https://mcp-server.zomato.com/staging/mcp \
  -H "User-Agent: Mozilla/5.0" \
  -H "X-Hackerone: natnasd"
# Esperado: HTTP/2 401 (não 404)

# Com token de staging (se obtido):
curl -si https://mcp-server.zomato.com/staging/mcp \
  -H "Authorization: Bearer STAGING_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1,"params":{}}'
# Verificar se tools list difere de /mcp (debug tools expostos?)
```

---

## Remediation

1. Remover rotas `/staging/*` do servidor de produção — staging deve rodar em `staging.mcp-server.zomato.com` ou em rede interna
2. Remover o `if (currentPath.startsWith('/staging'))` do código JavaScript de produção
3. Configurar network policy para bloquear acesso externo a qualquer endpoint `/staging/*`
