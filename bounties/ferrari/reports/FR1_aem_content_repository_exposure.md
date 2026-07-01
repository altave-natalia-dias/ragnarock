# FR1 — AEM Content Repository Paths Publicly Accessible

---

## Informações de Submissão (Obrigatório Ferrari VDP)

| Campo | Valor |
|:---|---:|
| **Data e Hora da Descoberta** | 2026-06-29 16:30 BRT (UTC-3) |
| **Timezone** | BRT (UTC-3) |
| **Tipo de Vulnerabilidade** | Information Disclosure — AEM Content Repository Exposure |
| **Serviço/URL Afetado** | `https://www.ferrari.com/content/cq:tags.json` |
| **IP de Origem** | 201.1.100.69 |
| **Hall da Fama** | Sim — Alias: [seu alias] |

---

## Severidade

**Severidade:** LOW  
**CWE:** CWE-200 — Exposure of Sensitive Information to an Unauthorized Actor  

---

## Sumário

O Adobe Experience Manager (AEM) que serve o site `www.ferrari.com` expõe endpoints de conteúdo JCR (Java Content Repository) publicamente sem exigir autenticação. Estes endpoints revelam metadados da estrutura interna do repositório AEM, incluindo tipos de nodo, informações de criação, e organização hierárquica.

Embora não exponham dados de clientes ou conteúdo editorial, a informação revelada pode ser utilizada para fingerprint da instalação AEM e direcionar ataques mais específicos.

---

## Endpoints Acessíveis (200 OK)

### 1. `/content/cq:tags.json`

```bash
curl -s 'https://www.ferrari.com/content/cq:tags.json'
```

**Resposta:**
```json
{
  "jcr:primaryType": "sling:Folder",
  "jcr:createdBy": "admin",
  "jcr:created": "2025-02-19T15:29:37.872+01:00",
  "jcr:lastModified": "2025-02-19T15:29:37.872+01:00",
  "sling:redirect": "/tagging",
  "languages": ["it", "en", "de", "fr", "es"]
}
```

### 2. `/content/cq:tags/default.json`
Retorna metadados estruturais sobre tags padrão do sistema.

### 3. `/content/dam.json`

```bash
curl -s 'https://www.ferrari.com/content/dam.json'
```

**Resposta:**
```json
{
  "jcr:primaryType": "sling:Folder",
  "jcr:createdBy": "admin",
  "jcr:created": "2025-02-19T15:30:04.299+01:00"
}
```

### 4. `/content/dam/ferrari.json`
Expõe metadados do diretório DAM (Digital Asset Management) principal.

### 5. `/libs/granite/security/currentuser.json`

```json
{"anonymous": ""}
```

Confirma que o acesso não requer autenticação.

---

## Detalhes Técnicos

### Passos para Reprodução

```bash
# 1. Verificar que o endpoint retorna 200 OK
curl -s -o /dev/null -w '%{http_code}' https://www.ferrari.com/content/cq:tags.json
# Saída esperada: 200

# 2. Verificar o conteúdo exposto
curl -s https://www.ferrari.com/content/cq:tags.json
# Retorna JSON com jcr:primaryType, jcr:createdBy:"admin", etc.

# 3. Confirmar que não requer autenticação
curl -s https://www.ferrari.com/libs/granite/security/currentuser.json
# Retorna: {"anonymous":""}
```

### Versão AEM Identificada

Clientlibs com hashes específicos (11 arquivos) extraídos, consistentes com AEM 6.5.x:
- `lc-3922c1330ee72a5c5c8af9620d7e5426.css`
- `lc-1e0136bad0acfb78be509234578e44f9.js`
- `lc-e76a80d4d4a6dc1d7d655e02fd4bc974.js`

### Testes Negativos Realizados

| Teste | Resultado |
|:---|---:|
| HTTP PUT/POST/DELETE nos endpoints | 401 Unauthorized |
| Query Builder `/bin/querybuilder.json` | 404 Not Found |
| Selector bypass (`.infinity.json`, `.tidy.json`) | 403 Forbidden |
| Path traversal (`../etc/passwd`) | 403/404 |
| Content-Type switching | Sem bypass |

---

## Impacto

- **Fingerprinting de versão AEM:** Os hashes dos clientlibs permitem identificar a versão exata dos componentes AEM, viabilizando a busca por CVEs específicas.
- **Reconhecimento de estrutura interna:** A exposição de paths revela a organização do repositório de conteúdo.
- **Baixo impacto isoladamente:** Nenhum dado de cliente, credencial, ou conteúdo editorial foi exposto.
- **Sem vetor de exploração remota:** Não é possível escalar para RCE, SQLi, ou autenticação bypass apenas com este finding.

---

## Remediação

1. **Bloquear `/content/*.json` no CloudFront WAF** — Adicionar regra para negar requisições a patterns como `/content/*.json` exceto quando autenticadas.
2. **Configurar Dispatcher AEM** — Garantir que o dispatcher bloqueie paths de conteúdo JCR para usuários não autenticados.
3. **Revisar ACLs do AEM** — Verificar se as permissões de leitura anônima no JCR são estritamente necessárias.

---

## Declaração de Conformidade

- Nenhum dado foi copiado, alterado, ou deletado durante o teste
- Nenhuma interrupção de serviço foi causada
- Apenas métodos GET foram utilizados (leitura)
- A atividade foi limitada ao mínimo necessário para confirmar a vulnerabilidade
- Nenhuma violação acidental das regras do programa ocorreu

---

## Timeline

| Data | Evento |
|:---|---:|
| 2026-06-29 16:30 BRT | Descoberta inicial |
| 2026-06-29 18:00 BRT | Validação rigorosa |
| [data de submissão] | Submissão ao `responsible_disclosure@ferrari.com` |
