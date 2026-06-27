# Finding R4 — Dangling CNAME Zendesk (parceiros.realizesolucoesfinanceiras.com.br)

**Título:** CNAME Dangling para Zendesk Help Center desativado — Subdomain Confusion potencial  
**Severidade:** LOW (CVSS 3.7 — AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:N)  
**CWE:** CWE-350 (Reliance on Reverse DNS Resolution)  
**Status:** Parcialmente confirmado — CNAME ativo para Zendesk existente (Help Center fechado, NÃO é takeover completo)  
**Escopo originário:** `www.realizesolucoesfinanceiras.com.br` / `api.realizesolucoesfinanceiras.com.br`  
**Target descoberto:** `parceiros.realizesolucoesfinanceiras.com.br`  
**Programa:** Realize Financeira — produção apenas  
**Diferença crítica vs takeover:** A conta Zendesk `parceirorealizecfi.zendesk.com` EXISTE — apenas o Help Center está desativado. Isso NÃO é um subdomain takeover completo.

---

## Discovery Chain

```
Passive recon: subfinder → parceiros.realizesolucoesfinanceiras.com.br
  → dnsx CNAME: parceirorealizecfi.zendesk.com
    → curl: HTTP 301 → https://parceirorealizecfi.zendesk.com/hc/pt-br/signin?return_to=...
      → Destino final: https://parceirorealizecfi.zendesk.com/hc/restricted (Help Center fechado)
        → Conta Zendesk EXISTE → NÃO é takeover (Zendesk não permite claim de conta existente)
          → Porém: CNAME continua ativo para conta que não controla mais ativamente o Help Center
```

---

## Evidências

### 1. CNAME para Zendesk

```bash
$ dig +short parceiros.realizesolucoesfinanceiras.com.br CNAME
parceirorealizecfi.zendesk.com.

$ dig +short parceirorealizecfi.zendesk.com A
104.18.28.162
104.18.29.162
# IPs do Cloudflare (Zendesk usa Cloudflare como CDN)
```

### 2. HTTP 301 → Help Center fechado

```bash
$ curl -sk "https://parceiros.realizesolucoesfinanceiras.com.br" -D - -L | head -20

HTTP/2 301
location: https://parceirorealizecfi.zendesk.com/hc/pt-br/signin?return_to=https%3A%2F%2Fparceirorealizecfi.zendesk.com%2Fhc%2Fpt-br

HTTP/2 301
location: https://parceirorealizecfi.zendesk.com/hc/restricted

HTTP/2 200
# Página: "Acesso restrito / Help Center fechado"
```

### 3. Distinção vs takeover real

```
takeover clássico:
  CNAME → serviço.com
    Conta NÃO existe → serviço permite claim → atacante controla domínio

Situação aqui:
  CNAME → parceirorealizecfi.zendesk.com
    Conta EXISTE (Help Center apenas fechado) → Zendesk NÃO permite claim por terceiros
    Apenas o dono da conta parceirorealizecfi pode reativar o Help Center
```

> **Conclusão:** Não é um subdomain takeover explorável. É um CNAME para serviço com acesso reduzido.

---

## Análise de Impacto

### Risco residual (baixo)

1. **Confusão de subdomain:** `parceiros.realizesolucoesfinanceiras.com.br` redireciona para Zendesk com HTTPS válido — pode enganar parceiros que tentam acessar portal de parceiros da Realize
2. **Abandono de recurso:** Help Center fechado sem remoção do CNAME sugere que esse portal foi descontinuado sem limpeza de DNS
3. **Potencial futuro:** Se a Realize encerrar a conta Zendesk `parceirorealizecfi` no futuro sem remover o CNAME, isso se tornaria um takeover real

---

## Remediação

**Opção A (imediata):** Remover o CNAME `parceiros.realizesolucoesfinanceiras.com.br`  
**Opção B:** Manter o CNAME e reativar o Help Center Zendesk (se ainda necessário para parceiros)  
**Opção C:** Redirecionar `parceiros.realizesolucoesfinanceiras.com.br` para nova URL de portal de parceiros

```bash
# Verificação pós-fix (opção A):
dig +short parceiros.realizesolucoesfinanceiras.com.br CNAME  # deve retornar vazio
```
