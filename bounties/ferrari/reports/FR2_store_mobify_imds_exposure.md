# FR2 — IMDS Endpoint Reference + Demandware Version in store.ferrari.com JS Bundles

---

## Informações de Submissão (Obrigatório Ferrari VDP)

| Campo | Valor |
|:---|---:|
| **Data e Hora da Descoberta** | 2026-06-29 17:00 BRT (UTC-3) |
| **Timezone** | BRT (UTC-3) |
| **Tipo de Vulnerabilidade** | Information Disclosure — SSRF Primitive + Software Version Disclosure |
| **Serviço/URL Afetado** | `https://store.ferrari.com` (JS bundles em `/mobify/bundle/9982/`) |
| **IP de Origem** | 201.1.100.69 |
| **Hall da Fama** | Sim — Alias: [seu alias] |

---

## Severidade

**Severidade:** LOW (Information Disclosure)  
**Nota:** A severidade é LOW porque a exposição está em bundles JavaScript client-side. Para exploração completa, seria necessário um vetor SSRF adicional no servidor. O principal risco é o fingerprint de versão do Demandware 21.7.  
**CWE:** CWE-200 — Exposure of Sensitive Information  
**CWE:** CWE-1104 — Use of Unmaintained Third-Party Components (Demandware 21.7)  

---

## Sumário

O frontend da loja online Ferrari (`store.ferrari.com`), construído sobre as plataformas Mobify e Salesforce Commerce Cloud (Demandware 21.7), expõe em seus bundles JavaScript públicos (3.9 MB de código analyzado):

1. **IMDS Endpoint Reference** — URL do Azure Instance Metadata Service (`http://169.254.169.254/metadata/instance/compute/location`) em texto claro
2. **Demandware 21.7 desatualizado** — Versão lançada em 2021 ainda em produção
3. **Rotas internas de API de e-commerce** — Endpoints para carrinho, pedidos, busca

---

## Evidências

### 1. IMDS Endpoint Reference

**Arquivo:** `/mobify/bundle/9982/vendor.js` (1.5 MB)
```javascript
IMDS_ENDPOINT: "http://169.254.169.254/metadata/instance/compute/location"
```

**Contexto:** A URL faz parte do código de detecção de região cloud. Embora esteja em código client-side (não executável diretamente), sua presença indica que o backend pode fazer requisições ao IMDS, representando um **primitive para SSRF** caso exista outro vetor no servidor.

### 2. Demandware/Salesforce Commerce Cloud 21.7

**Arquivo:** `/on/demandware.static/Sites-ferrari-Site/-/en/v1762575999871/internal/jscript/dwac-21.7.js`

Indicações de versão desatualizada:
- Demandware 21.7 foi lançado em 2021
- URL contém `v1762575999871` — timestamp de build
- Versão atual disponível: 24.x ou superior

### 3. Rotas Internas Identificadas nos Bundles

```
/basket/upsertAbandonedCart
/orders
/track-order
/search-no-result
/register
/token
/manage/videos
```

---

## Bundles Analisados

Foram baixados e analisados 12 bundles JavaScript totalizando 3.9 MB de código:

| Bundle | Tamanho | Conteúdo |
|:---|---:|:---|
| `/mobify/bundle/9982/main.js` | 2.1 MB | Aplicação principal Mobify |
| `/mobify/bundle/9982/vendor.js` | 1.5 MB | Dependências (IMDS + MSAL) |
| `/mobify/bundle/9982/custom-bundle.swiper.js` | 149 KB | Carrossel |
| `/mobify/bundle/9982/runtime.js` | 9 KB | Runtime |
| `/on/demandware.static/.../dwac-21.7.js` | 7 KB | Demandware OCAPI |
| `/on/demandware.static/.../dwanalytics-22.2.js` | 11 KB | Analytics |

---

## Passos para Reprodução

```bash
# 1. Verificar que o bundle vendor.js contém IMDS_ENDPOINT
curl -s 'https://store.ferrari.com/mobify/bundle/9982/vendor.js' | grep -o 'IMDS_ENDPOINT[^,]*'
# Saída: IMDS_ENDPOINT:"http://169.254.169.254/metadata/instance/compute/location"

# 2. Verificar versão do Demandware
curl -sI 'https://store.ferrari.com/on/demandware.static/Sites-ferrari-Site/-/en/v1762575999871/internal/jscript/dwac-21.7.js'
# Saída: HTTP/2 200

# 3. Verificar rotas internas
curl -s 'https://store.ferrari.com/mobify/bundle/9982/main.js' | grep -oE '"/(basket|orders|track-order|search-no-result|register|token|manage)[^"]*"' | sort -u
```

---

## Impacto

- **SSRF Primitive (LOW):** A IMDS URL está em código client-side. Para exploração completa, seria necessário um vetor SSRF no servidor que pudesse fazer requisições arbitrárias. Sem este vetor adicional, o risco é limitado.
- **Software Desatualizado (LOW):** Demandware 21.7 está 3-4 versões atrás. Versões antigas podem ter vulnerabilidades não divulgadas publicamente que a Salesforce corrigiu em versões posteriores.
- **Rotas Internas Expostas (INFO):** Endpoints como `/basket/upsertAbandonedCart` e `/orders` podem ser alvo de ataques se não tiverem autenticação adequada.

---

## Remediação

1. **Remover IMDS endpoint references dos bundles públicos** — URLs de metadata service não devem estar em JavaScript client-side.
2. **Atualizar Demandware 21.7** — Versão desatualizada desde 2023. Atualizar para a versão mais recente do Salesforce Commerce Cloud.
3. **Revisar bundles JavaScript periodicamente** — Garantir que configurações sensíveis (API keys, endpoints internos) não sejam expostas.

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
| 2026-06-29 17:00 BRT | Descoberta inicial |
| 2026-06-29 18:30 BRT | Validação rigorosa |
| [data de submissão] | Submissão ao `responsible_disclosure@ferrari.com` |
