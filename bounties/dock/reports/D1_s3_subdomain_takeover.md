# Finding D1 — S3 Subdomain Takeover: cfsec.dock.tech

**Título:** Subdomain Takeover via S3 Static Website Hosting — cfsec.dock.tech  
**Severidade:** HIGH (CVSS 7.5 — AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)  
**CWE:** CWE-350 (Reliance on Reverse DNS Resolution)  
**Status:** Confirmado — bucket não existe, CNAME ativo  
**Limitação de protocolo:** Takeover restrito a HTTP (S3 static website não suporta HTTPS nativo)  
**Escopo originário:** `*.dock.tech` → alvo: `cfsec.dock.tech`  
**Programa:** Bugpay (Dock) — produção apenas

---

## Discovery Chain

```
Passive recon: subfinder *.dock.tech
  → cfsec.dock.tech identificado
    → dnsx CNAME: cfsec.dock.tech.s3-website-us-west-2.amazonaws.com
      → HTTP: AWS S3 error "NoSuchBucket: cfsec.dock.tech"
```

---

## Sumário Técnico

O subdomínio `cfsec.dock.tech` possui um registro DNS CNAME apontando para um bucket S3 que **não existe mais**. Qualquer pessoa com uma conta AWS pode criar um bucket chamado `cfsec.dock.tech` na região `us-west-2` e habilitar static website hosting, passando a servir conteúdo arbitrário sob o domínio `cfsec.dock.tech` — incluindo JavaScript malicioso.

---

## Evidências

### DNS

```
$ dig +short cfsec.dock.tech CNAME
cfsec.dock.tech.s3-website-us-west-2.amazonaws.com.
cfsec.dock.tech.s3-website-us-west-2.amazonaws.com.
s3-website.us-west-2.amazonaws.com.
```

### AWS NoSuchBucket Error

```
$ curl -sk "http://cfsec.dock.tech"

<html>
<head><title>404 Not Found</title></head>
<body>
<h1>404 Not Found</h1>
<ul>
<li>Code: NoSuchBucket</li>
<li>Message: The specified bucket does not exist</li>
<li>BucketName: cfsec.dock.tech</li>
<li>RequestId: SJXNWCHEWWB2EB1A</li>
<li>HostId: n5rdueIZjs5BfIsGwqVHhBtFidzIMJ6T...</li>
</ul>
</body>
</html>
```

### Prova de Exploitabilidade (PoC a validar pelo programa)

O ataque requer somente:
1. Criar bucket S3: `aws s3 mb s3://cfsec.dock.tech --region us-west-2`
2. Habilitar website hosting e definir Block Public Access = OFF
3. Upload de `index.html` com conteúdo malicioso
4. `cfsec.dock.tech` passa a servir o conteúdo do atacante

> **Nota:** O PoC NÃO foi executado para preservar o ambiente. O `NoSuchBucket` é prova suficiente e irrefutável.

---

## Limitação Importante — HTTP Only

```bash
# HTTPS: timeout (S3 website endpoint não suporta TLS)
$ curl -vsk "https://cfsec.dock.tech" -m 8
* Closing connection  ← sem resposta; S3 website binding é HTTP-only

# HTTP: responde com NoSuchBucket
$ curl -sk "http://cfsec.dock.tech"
<li>Code: NoSuchBucket</li>
```

**O atacante pode servir apenas HTTP** sob `cfsec.dock.tech`. HTTPS não é possível porque:
1. S3 static website hosting só responde na porta 80
2. O atacante não controla o DNS de `dock.tech` para emitir certificado TLS válido
3. Adicionar CloudFront com TLS próprio não resolve — sem controle DNS, não há CNAME/A record

**Implicações práticas:**
- Browsers modernos exibem "Not Secure" / warning para `http://cfsec.dock.tech`
- Cookies com flag `Secure` de outros domínios `.dock.tech` **não** são enviados via HTTP → roubo de sessão limitado
- Links `http://` em e-mails/documentos da Dock podem chegar ao servidor do atacante sem aviso perceptível ao usuário leigo

## Impacto

- **Phishing HTTP** sob domínio oficial `*.dock.tech` (alta credibilidade, sem warning óbvio em links de email)
- **Credential harvesting** via página de login falsa — o domínio `dock.tech` é reconhecido e confiável
- **Malware hosting** com conteúdo aparentemente legítimo da Dock (downloads de SDKs, PDFs, etc.)
- **CSP bypass** se outros sistemas da Dock confiarem em `cfsec.dock.tech` como fonte
- **Cookie theft limitado** — apenas cookies SameSite=None sem flag Secure (raros em produção financeira)
- O nome `cfsec` sugere uso anterior como asset de segurança/infra — aumenta credibilidade de phishing direcionado (ataques a funcionários Dock via email interno)

---

## Matriz de Evidência

| Item | Status | Prova |
|------|--------|-------|
| CNAME apontando para S3 website | ✅ Provado | `dig` output |
| Bucket não existe | ✅ Provado | `NoSuchBucket` error com `BucketName: cfsec.dock.tech` |
| Região: us-west-2 | ✅ Provado | CNAME → `s3-website-us-west-2.amazonaws.com` |
| Criação de bucket por terceiro possível | ✅ Confirmado por política AWS S3 |
| Conteúdo servido | ❌ Não testado (preservação de escopo) |
| HTTPS suportado | ❌ Não suportado — S3 website HTTP-only, curl timeout em HTTPS |
| Impacto reduzido vs full HTTPS takeover | ✅ Confirmado — somente HTTP serving possível |

---

## Remediação

Opção A (imediata): Remover o registro DNS CNAME para `cfsec.dock.tech`  
Opção B (preferida): Recriar o bucket S3 e configurar ACL corretamente, removendo o website hosting se não for necessário
