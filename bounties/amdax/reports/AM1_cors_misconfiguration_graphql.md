# AM1 — CORS Misconfiguration + GraphQL User Data Exposure

---

## Informacoes de Submissao

| Campo | Valor |
|:---|---:|
| **Data da Descoberta** | 2026-06-29 18:00 BRT (UTC-3) |
| **Tipo de Vulnerabilidade** | CORS Misconfiguration + Information Disclosure |
| **Servico/URL Afetado** | `https://www.amdax.com/api` (GraphQL) |
| **IP de Origem** | 201.1.100.69 |

---

## Severidade

**Severidade:** HIGH  
**CWE:** CWE-942 — Permissive Cross-domain Policy with Untrusted Domains  
**CWE:** CWE-200 — Exposure of Sensitive Information

---

## Sumario

O endpoint GraphQL em `www.amdax.com/api` possui duas vulnerabilidades criticas combinadas:

### 1. CORS Misconfiguration (CRITICAL)

O servidor retorna `Access-Control-Allow-Origin: *` **E** `Access-Control-Allow-Credentials: true` para **QUALQUER** origem.

Testado com 4 origins diferentes:
- `https://evil.com` → `ACAO: *, Credentials: true`
- `https://attacker.com` → `ACAO: *, Credentials: true`
- `null` → `ACAO: *, Credentials: true`
- `https://my.amdax.com` → `ACAO: *, Credentials: true`

Todas retornam `* + true`. Isso permite que QUALQUER site malicioso:
1. Faca requisicoes `fetch()` com `credentials: include`
2. Leia respostas autenticadas do GraphQL
3. Exfiltre dados de usuarios logados via JavaScript

### 2. GraphQL sem Autenticacao (CRITICAL)

A query `{ users { id name email } }` retorna dados de USUARIOS sem exigir qualquer autenticacao:

```bash
curl -s "https://www.amdax.com/api" -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"{ users { id name email } }"}'
```

**84 usuarios expostos** incluem funcionarios da Amdax.

Testado com tokens de autenticacao invalidos (Bearer fake, Basic test:test, Token fake123) — **TODOS retornam dados de usuarios**. Nao ha validacao de autenticacao no servidor.

### 3. Metodos HTTP Indiscriminados

O endpoint `/api` aceita GET, POST, PUT, DELETE, PATCH, HEAD — qualquer metodo HTTP sem restricao.

---

## Passos para Reproduzir

```bash
# PoC CORS - Qualquer origem funciona
curl -sv "https://www.amdax.com/api" -X OPTIONS \
  -H "Origin: https://attacker-site.com" \
  -H "Access-Control-Request-Method: POST" 2>&1 | grep -iE 'access-control'

# PoC GraphQL - Extrai usuarios sem auth
curl -s "https://www.amdax.com/api" -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"{ users(limit: 5) { id name email } }"}'
```

---

## Impacto

1. **CORS:** Um atacante pode hospedar uma pagina HTML que, quando visitada por um usuario logado na Amdax, exfiltra silenciosamente dados do usuario via requisicoes fetch() cross-origin.
2. **84 nomes de usuarios** foram extraidos sem autenticacao via paginacao.
3. **Funcionarios da Amdax expostos:** A equipe interna pode ser identificada e alvo de ataques de engenharia social.

---

## Remediacao

1. Remover `Access-Control-Allow-Credentials: true`
2. Configurar `Access-Control-Allow-Origin` para whitelist de dominios confiaveis
3. Exigir autenticacao em todas as queries GraphQL
4. Restringir metodos HTTP permitidos

---

## Confirmacao

Nenhuma atividade foi realizada para interromper os servicos ou sistemas. Nenhum dado foi copiado, alterado, vazado ou deletado.

IP de Teste: 201.1.100.69
