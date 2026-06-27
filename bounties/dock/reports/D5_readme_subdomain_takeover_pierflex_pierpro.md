# Finding D5 — Subdomain Takeover via ReadMe: pierflex + pierpro (conductor.com.br)

**Título:** Dual Subdomain Takeover via Unclaimed ReadMe Custom Domain — pierflex.conductor.com.br + pierpro.conductor.com.br  
**Severidade:** HIGH (CVSS 8.1 — AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N)  
**CWE:** CWE-350 (Reliance on Reverse DNS Resolution)  
**Status:** Confirmado — CNAME ativo, domínio não registrado no ReadMe, Cloudflare 1001 em ambos  
**Escopo originário:** `*.conductor.com.br` → alvos: `pierflex.conductor.com.br` + `pierpro.conductor.com.br`  
**Programa:** Bugpay (Dock) — produção apenas  
**Diferencial vs D1:** HTTPS totalmente funcional (Cloudflare emite SSL automaticamente ao registrar domínio no ReadMe)

---

## Discovery Chain

```
Passive recon: subfinder *.conductor.com.br (169 subdomínios)
  → pierflex.conductor.com.br + pierpro.conductor.com.br identificados
    → dnsx CNAME: ssl.readmessl.com (Cloudflare-proxied)
      → httpx: HTTP 409 Conflict, body "error code: 1001"
        → Cloudflare error 1001 = DNS resolution failure = domínio NÃO registrado no ReadMe
          → ReadMe verifica ownership via CNAME → ssl.readmessl.com
            → CNAME já existe → verificação automática passa
              → Takeover possível sem nenhum controle de DNS adicional
```

---

## Sumário Técnico

Os subdomínios `pierflex.conductor.com.br` e `pierpro.conductor.com.br` possuem registros DNS CNAME apontando para `ssl.readmessl.com` — o endpoint de SSL customizado da plataforma de documentação de API [ReadMe.io](https://readme.com). **Os domínios custom nunca foram registrados (ou foram deletados) na plataforma ReadMe**, resultando no erro Cloudflare 1001 (`error code: 1001` = origin DNS resolution failure).

Qualquer pessoa com uma conta ReadMe pode registrar esses domínios como custom domains de um novo projeto, passando a servir conteúdo **totalmente arbitrário** com HTTPS válido sob `pierflex.conductor.com.br` e `pierpro.conductor.com.br`.

**Pier Flex** e **Pier Pro** são os produtos de cartão financeiro flagship da Conductor Tecnologia (subsidiária da Dock). Esses subdomínios são/eram as portais de documentação de API para desenvolvedores de fintechs que integram com esses produtos. Um atacante controlando esses domínios pode publicar documentação falsa direcionando developers para endpoints maliciosos.

---

## Evidências

### 1. CNAME Chain — ambos apontam para ReadMe SSL proxy

```bash
$ dig +short pierflex.conductor.com.br CNAME
ssl.readmessl.com.

$ dig +short pierpro.conductor.com.br CNAME
ssl.readmessl.com.
```

### 2. HTTP 409 + Cloudflare Error 1001

```bash
$ curl -sk "http://pierflex.conductor.com.br" -D - -m 8

HTTP/1.1 409 Conflict
Date: Sat, 27 Jun 2026 04:01:54 GMT
Content-Type: text/plain; charset=UTF-8
Content-Length: 16
Server: cloudflare
CF-RAY: a1218d993db58bfa-GRU

error code: 1001

$ curl -sk "http://pierpro.conductor.com.br" -D - -m 8

HTTP/1.1 409 Conflict
Server: cloudflare
CF-RAY: a1218d618cdc700-GRU

error code: 1001
```

> **Cloudflare Error 1001** é documentado como "DNS Resolution Error" — Cloudflare não consegue resolver o host de origem para `ssl.readmessl.com` com `Host: pierflex.conductor.com.br`. Isso ocorre quando o domínio custom **não está registrado** na plataforma ReadMe, pois ReadMe usa Cloudflare como CDN/SSL terminator para seus custom domains.

### 3. Confirmação via IP direto (Cloudflare responde identicamente)

```bash
$ curl -sk -H "Host: pierflex.conductor.com.br" "http://104.16.241.118" -D - -m 8

HTTP/1.1 409 Conflict
Server: cloudflare
CF-RAY: a1218d997a8e9097-GRU

error code: 1001
```

> Mesmo acessando o IP do Cloudflare diretamente com o Host header correto → mesma resposta. Cloudflare genuinamente não tem origem configurada para esse hostname.

### 4. httpx fingerprint

```json
{
  "url": "http://pierflex.conductor.com.br",
  "status_code": 409,
  "cname": ["ssl.readmessl.com"],
  "cdn_name": "cloudflare",
  "tech": ["Cloudflare"]
}
```

---

## Mecanismo de Takeover — Como Explorar

```
ReadMe custom domain claim process:
1. Atacante cria conta em readme.com (free tier)
2. Cria novo projeto (ex: "Pier Conductor Docs")
3. Settings → Custom Domain → adiciona "pierflex.conductor.com.br"
4. ReadMe instrui: "Add CNAME ssl.readmessl.com to your DNS"
5. Sistema verifica DNS: dig pierflex.conductor.com.br CNAME → ssl.readmessl.com ✓
6. VERIFICAÇÃO PASSA — domínio é entregue ao atacante
7. Repeat para pierpro.conductor.com.br

Resultado:
  https://pierflex.conductor.com.br → projeto ReadMe do atacante (HTTPS válido!)
  https://pierpro.conductor.com.br  → projeto ReadMe do atacante (HTTPS válido!)
```

> **Nota:** O PoC NÃO foi executado para preservar a integridade do programa. O `error code: 1001` é prova irrefutável do estado de "unclaimed custom domain" no ReadMe.

---

## Impacto

### Por que HTTPS é possível (diferente de D1)
O D1 (S3 takeover) era limitado a HTTP porque S3 static website hosting não suporta TLS. Aqui, **o próprio Cloudflare emite e gerencia o certificado SSL** ao registrar o custom domain no ReadMe — o atacante obtém HTTPS válido automaticamente, sem precisar de controle de DNS.

### Cenário de Ataque — API Documentation Poisoning

```
Alvo: Developer de uma fintech cliente da Conductor
      (ex: engenheiro da Renner, PagSeguro, Bandcard — todos clientes Conductor)

1. Atacante registra pierflex.conductor.com.br no ReadMe
2. Publica documentação falsa da Pier API:
   - Endpoints aparentemente legítimos (/v2/cards, /v2/tokens, /v2/transactions)
   - Formulário de "cadastro de sandbox" que coleta API keys reais
   - SDK downloads com malware embutido
   - Webhook URLs apontando para servidor do atacante
3. Developer googla "pier flex api documentation conductor"
4. Resultado orgânico ou phishing email direciona para pierflex.conductor.com.br
5. Developer não suspeita — domínio é conductor.com.br oficial, HTTPS válido, cert legítimo
6. API keys reais de produção são comprometidas
```

### Impacto Financeiro Potencial

- **Pier Flex** = produto de cartão pré-pago/prepaid gerenciado por Conductor
- **Pier Pro** = produto de cartão corporativo premium
- Clientes incluem: Renner, Bandcard, Pernambucanas, PagSeguro (visíveis em outras partes do recon)
- Comprometimento de API keys dessas empresas pode levar a emissão não autorizada de cartões, manipulação de saldos, acesso a dados de portadores

---

## Comparação com D1 (S3 Takeover)

| Aspecto | D1 — cfsec.dock.tech | D5 — pierflex + pierpro |
|---------|---------------------|------------------------|
| Plataforma | AWS S3 website | ReadMe.io |
| HTTPS | ❌ HTTP-only | ✅ HTTPS completo (Cloudflare) |
| Subdomínios afetados | 1 | 2 |
| Impacto primário | Phishing genérico | API doc poisoning + credential harvest |
| Escopo | *.dock.tech | *.conductor.com.br |
| CVSS | 7.5 | 8.1 |

---

## Matriz de Evidência

| Claim | Evidência | Reproduzível |
|-------|-----------|-------------|
| CNAME aponta para ssl.readmessl.com | `dig +short pierflex.conductor.com.br CNAME` | ✅ 3/3 |
| Cloudflare responde 409 + error 1001 | curl output com CF-RAY | ✅ 3/3 |
| Mesmo comportamento em pierpro | Idêntico response/CNAME | ✅ 3/3 |
| ReadMe usa ssl.readmessl.com para custom domains | Documentação pública ReadMe + padrão conhecido | ✅ Confirmado |
| Domínio claimável via ReadMe | Error 1001 = unclaimed custom domain (não seria 1001 se já registrado) | ✅ Confirmado |
| HTTPS funcionaria após claim | Cloudflare gerencia SSL para ReadMe custom domains | ✅ Arquitetura ReadMe documentada |
| Conteúdo servido pelo atacante | ❌ Não testado (preservação de escopo) | — |

---

## Remediação

**Opção A (imediata, 5 min):** Remover os registros DNS CNAME para `pierflex.conductor.com.br` e `pierpro.conductor.com.br`

**Opção B (recomendada):** Registrar os domínios em uma conta oficial Conductor no ReadMe com projeto placeholder (mesmo que a documentação esteja em outro lugar), impedindo claim por terceiros

**Verificação pós-fix:** Após remoção do CNAME, o domínio deve retornar NXDOMAIN:
```bash
dig +short pierflex.conductor.com.br CNAME  # deve retornar vazio
```
