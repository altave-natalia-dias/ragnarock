# Finding D2 — Exposição de Templates de Build Não Expandidos em Portais de Produção

**Título:** Production Acquiring Portals Serving Unexpanded Build Templates Exposing Dev API Endpoints and Internal IPs  
**Severidade:** MEDIUM (CVSS 5.3)  
**CWE:** CWE-215 (Insertion of Sensitive Information into Log/Configuration File)  
**Status:** Confirmado em 5 portais de produção  
**Escopo originário:** `*.dock.tech` → alvos: `*.acquiring.dock.tech` (assai, aqpago, anademprime, bancosc, credisis)  
**Programa:** Bugpay (Dock) — produção apenas

---

## Discovery Chain

```
Passive recon: subfinder *.dock.tech + crt.sh
  → *.acquiring.dock.tech (assai, aqpago, anademprime, bancosc, credisis)
    → httpx: todos retornam HTTP 200 "Portal" (nginx 1.25.4, CloudFront)
      → Source analysis: /config.js servido com placeholders não expandidos
        → Exposição: dev hostnames, IPs internos, CORS proxy
```

---

## Sumário Técnico

Cinco portais de produção da plataforma Acquiring da Dock (todos em `*.acquiring.dock.tech`) servem um arquivo `config.js` com **templates de build não expandidos** no formato `#{"VARIAVEL", "valor_default_dev"}`. Isso expõe:
- Hostnames de ambiente de desenvolvimento (`*.acquiring.dev.dock.tech`)
- Dois IPs raw com portas (`54.88.43.10:8096`, `18.209.161.234:8083`)
- Um proxy CORS público (`cors-anywhere.herokuapp.com`) usado para acessar o serviço de senhas de produção
- Arquitetura completa de microservices internos

---

## Evidências

### Portais Afetados

```
https://assai.acquiring.dock.tech       [200 OK - MD5: efb5b078b89b2e99f72dce57b36fd781]
https://aqpago.acquiring.dock.tech      [200 OK - mesmo MD5]
https://anademprime.acquiring.dock.tech [200 OK - mesmo MD5]
https://bancosc.acquiring.dock.tech     [200 OK - mesmo MD5]
https://credisis.acquiring.dock.tech    [200 OK - mesmo MD5]
```

Todos os portais servem idêntica `config.js` (v1.122.13).

### Templates Não Expandidos em /config.js

```bash
$ curl -s "https://assai.acquiring.dock.tech/config.js" | grep -E '("_server"|GATEWAY|API_HOST|PASSWORD)'
```

**Dev API endpoints expostos:**
```javascript
'_server': '#{"AUTHENTICATION_HOST", "https://ids.acquiring.dev.dock.tech"}',
'_server': '#{"MERCHANT_HOST",        "https://merchant.acquiring.dev.dock.tech"}',
'_server': '#{"TRANSACTION_HOST",     "https://transaction.acquiring.dev.dock.tech"}',
'_server': '#{"SETTLEMENT_HOST",      "https://settlement.acquiring.dev.dock.tech"}',
'_server': '#{"CHARGEBACK_HOST",      "https://chargeback.acquiring.dev.dock.tech"}',
'_server': '#{"TERMINAL_HOST",        "https://terminal.acquiring.dev.dock.tech"}',
'_server': '#{"ACCOUNTING_HOST",      "https://accounting.acquiring.dev.dock.tech"}',
'_server': '#{"AUTHORIZER_HOST",      "https://authorizer.acquiring.dev.dock.tech"}',
'_server': '#{"REGULATORY_HOST",      "https://regulatory.acquiring.dev.dock.tech"}',
'_server': '#{"WALLET_HOST",          "https://wallet.acquiring.dev.dock.tech"}',
```

**IPs Internos com Porta:**
```javascript
'_server': '#{"GATEWAY_HOST", "http://54.88.43.10:8096"}',  // AWS us-east-1
'_server': '#{"API_HOST",     "http://18.209.161.234:8083"}'// AWS us-east-1
```

**CORS Proxy Público para Serviço de Senhas:**
```javascript
'_server': '#{"PASSWORD_HOST", "https://cors-anywhere.herokuapp.com/https://passwords.muxipay.com"}'
```

### Template não expandido em require.config.js

```bash
$ curl -s "https://assai.acquiring.dock.tech/require.config.js"
require(["./configFinal.#[VERSION]","./deps.config.#[VERSION]"],...)
```

A variável `#[VERSION]` também está não expandida.

### APIs de Produção Acessíveis (Descobertas pelo config.js)

```
serviceorder.acquiring.dock.tech/v1/products → 401 (rota existe)
gw-caradhras.acquiring.dock.tech             → 404 JSON (live)
multiacq-ecommerce.acquiring.dock.tech       → 403 "Missing Authentication Token" (AWS API Gateway)
```

---

## Impacto

1. **Mapeamento de arquitetura** — Atacante obtém nomes de todos os 11 microservices internos
2. **IPs privados expostos** — Dois servidores AWS identificados por IP:porta (54.88.43.10:8096, 18.209.161.234:8083)
3. **CORS proxy como attack surface** — O `cors-anywhere.herokuapp.com` é um serviço de terceiros usado para contornar CORS no acesso a `passwords.muxipay.com`. Um atacante com account no Heroku poderia potencialmente interceptar requests de senha se o proxy fosse comprometido
4. **Portais quebrados** — Se os portais de produção realmente chamam as APIs dev, dados transacionais de produção podem estar fluindo para ambientes não auditados

---

## Remediação

- Implementar substituição adequada de variáveis de ambiente no pipeline de build (CI/CD)
- Não usar defaults de dev em config.js — fail-fast se variáveis não estiverem definidas
- Remover referências a `cors-anywhere.herokuapp.com` de configurações de produção
- Usar secrets manager para URLs de serviços críticos
