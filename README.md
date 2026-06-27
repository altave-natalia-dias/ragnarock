# BugHunter — Setup RAG + Bounty Workflow

> Setup pessoal de bug bounty com inteligência híbrida Graph+Vector (Neo4j + ChromaDB).  
> Acelera recon, correlaciona técnicas ATT&CK, sugere cadeias de exploit e armazena findings para retroalimentação contínua.

---

## Estrutura de pastas

```
/home/altave/.bughunter/
├── rag/                          # Motor de inteligência
│   ├── cli.py                    # CLI principal
│   ├── store.py                  # ChromaDB (vector)
│   ├── graph_store.py            # Neo4j (graph)
│   ├── retrieve.py               # Busca híbrida
│   ├── ingest/
│   │   ├── mitre.py              # ATT&CK + D3FEND
│   │   ├── writeups.py           # Writeups públicos + retroalimentação
│   │   ├── knowledge.py          # OWASP KB + CySA+
│   │   ├── recon_parser.py       # Parseia httpx/nuclei/katana → Neo4j
│   │   └── entity_extractor.py   # Extrai CVEs, CWEs, techs, vuln chains
│   └── data/
│       ├── chroma_db/            # Banco vetorial (persistente)
│       ├── raw/                  # Cache de fontes externas
│       └── retroalimentacao.jsonl
├── bounties/                     # Findings por programa
│   └── dock/                     # Dock Tecnologia (Bugpay)
│       ├── reports/              # D1–D4 prontos para submissão
│       ├── recon/                # dnsx, httpx, subfinder outputs
│       └── PENTEST_NOTES.md
└── config.json                   # Configuração de provider LLM
```

---

## Pré-requisitos

```bash
# Dependências do sistema (Ubuntu/Debian)
sudo apt install -y python3 python3-pip golang-go

# Go tools (recon)
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install github.com/projectdiscovery/katana/cmd/katana@latest

# Neo4j (Docker)
docker run -d \
  --name gotham-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/changeme \
  neo4j:5

# Python venv
python3 -m venv /home/altave/venv
/home/altave/venv/bin/pip install -q \
  chromadb requests beautifulsoup4 \
  neo4j python-dotenv
```

---

## Ativar RAG em nova sessão

```bash
# 1. Garantir que o Neo4j está rodando
docker start gotham-neo4j

# 2. Verificar stats do RAG (deve mostrar ~918 ATT&CK + 1628+ bb_writeups)
cd /home/altave/.bughunter
/home/altave/venv/bin/python3 -W ignore -m rag.cli stats

# Se o banco estiver vazio (primeira vez ou reset):
/home/altave/venv/bin/python3 -W ignore -m rag.cli build
```

**Output esperado do `stats` (estado atual):**
```
ChromaDB (Vector):
  mitre_attack   : 918 docs
  mitre_defend   : 271 docs
  bb_writeups    : 1628 docs
  pentest_kb     :  15 docs
  cysa_kb        :   4 docs
  bounty_reports :   4 docs   ← D1-D4 Dock indexados

Neo4j (Graph):
  Alvo           :   3
  Subdominio     : 236
  Tecnologia     :  53
  Vulnerabilidade:  45
  Writeup_Ref    :   2
  Relationships  : 578
```

---

## Workflow completo por bounty

### Fase 1 — Recon passivo

```bash
TARGET="dock.tech"
OUTDIR="/tmp/bounty/$TARGET"
mkdir -p "$OUTDIR"

# Subfinder — enumeração de subdomínios
subfinder -d "$TARGET" -silent -o "$OUTDIR/subs.txt"
# Se programa tiver wildcards múltiplos:
subfinder -dL <(echo -e "dock.tech\ncaradhras.io\nconductor.com.br") \
  -silent -o "$OUTDIR/subs_all.txt"

# Resolução DNS
/home/altave/go/bin/dnsx -l "$OUTDIR/subs_all.txt" \
  -r 8.8.8.8,1.1.1.1 -a -cname -o "$OUTDIR/dnsx.txt" -silent

# Filtrar OOS (dev/hml/sandbox)
grep -viE '\.(dev|hml|sandbox|staging|homolog|qa)\.' "$OUTDIR/subs_all.txt" \
  > "$OUTDIR/prod.txt"
```

### Fase 2 — Fingerprint ativo

```bash
# httpx — detecção de tech, status, title
/home/altave/go/bin/httpx \
  -l "$OUTDIR/prod.txt" \
  -json -title -tech-detect -status-code -follow-redirects \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36" \
  -o "$OUTDIR/httpx.json" -silent

# Importar para Neo4j
cd /home/altave/.bughunter
/home/altave/venv/bin/python3 -W ignore -m rag.cli graph-import \
  --target "$TARGET" \
  --httpx "$OUTDIR/httpx.json" \
  --subfinder "$OUTDIR/subs_all.txt"
```

### Fase 3 — Attack plan híbrido (Graph + Vector)

```bash
cd /home/altave/.bughunter

# Plano de ataque completo
/home/altave/venv/bin/python3 -W ignore -m rag.cli plan "$TARGET" \
  --tech node express kong aws s3

# Query semântica específica
/home/altave/venv/bin/python3 -W ignore -m rag.cli query \
  "subdomain takeover S3 static website"

# Buscar writeups por categoria
/home/altave/venv/bin/python3 -W ignore -m rag.cli query \
  "CORS bypass API gateway wildcard"

# Lookup de técnica ATT&CK
/home/altave/venv/bin/python3 -W ignore -m rag.cli technique T1190
```

### Fase 4 — JS analysis (alvos com React/SPA)

```bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"

# Buscar bundle principal
curl -sk -H "User-Agent: $UA" "https://TARGET/static/js/main.*.chunk.js" \
  -o /tmp/main.js

# Extrair env vars baked no bundle
grep -oP 'REACT_APP_[A-Z_]+:[^,}]+' /tmp/main.js

# Buscar endpoints internos
grep -oP '["'\'']/[a-z][a-z0-9/_-]{3,}[^"'\'']{0,60}' /tmp/main.js | sort -u

# Buscar templates não expandidos (padrão Muxi/RequireJS)
grep -cP '#\{' /tmp/config.js   # conta placeholders
grep -oP '#\{"([^"]+)"' /tmp/config.js | head -30
```

### Fase 5 — Exploração dirigida (checklist)

```bash
# S3 takeover — verificar CNAME dangling
dig +short TARGET.dock.tech CNAME
curl -sk "http://TARGET.dock.tech" | grep -i "NoSuchBucket\|nosuchbucket"

# CORS bypass via API Gateway
curl -sk -X OPTIONS "https://api.TARGET.com/endpoint" \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -D - | grep -i "access-control"

# Rate limit check
for i in $(seq 1 20); do
  curl -sk -X POST "https://TARGET/auth" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}' \
    -w "[%{http_code}]" 2>/dev/null &
done && wait

# Stack trace / error disclosure
curl -sk -X POST "https://TARGET/api/endpoint" \
  -H "Content-Type: application/json" \
  -d '{"invalid":true}' | grep -i "at "

# OIDC discovery
curl -sk "https://auth.TARGET.com/.well-known/openid-configuration" | python3 -m json.tool
```

### Fase 6 — Escrever finding

Usar template obrigatório (em `memory/feedback_finding_template.md`):
- Título + Severidade + CWE + **Escopo originário**
- Discovery chain (cada seta = um passo real)
- Evidências com comandos copiáveis
- Análise de root cause
- PoC executável (sem causar dano)
- Matriz de evidência (claim → prova → reproduzível?)
- Remediação priorizada

### Fase 7 — Retroalimentação RAG (OBRIGATÓRIO após submeter)

```bash
cd /home/altave/.bughunter
/home/altave/venv/bin/python3 -W ignore -m rag.cli add-report \
  --title "PROGRAMA: Título do Finding" \
  --url "https://bugpay.com/reports/ID" \
  --program "Nome do Programa" \
  --platform "Bugpay" \
  --vuln "Tipo de Vuln" \
  --severity "HIGH" \
  --content "Descrição completa: root cause, técnica, bypass, impacto..."
```

Isso adiciona ao ChromaDB (`bb_writeups` + `bounty_reports`) E ao Neo4j (entidades extraídas automaticamente).

---

## Continuando bounty Dock (próxima sessão)

O programa Dock tem escopo em `*.dock.tech`, `*.caradhras.io` e `*.conductor.com.br`.  
4 findings já encontrados e documentados (D1–D4, todos em `*.dock.tech`).  
Os escopos `*.caradhras.io` e `*.conductor.com.br` estão quase inexplorados.

### Retomar de onde parou

```bash
# 1. Ativar RAG
docker start gotham-neo4j
cd /home/altave/.bughunter
/home/altave/venv/bin/python3 -W ignore -m rag.cli stats

# 2. Ver findings existentes
ls /home/altave/.bughunter/bounties/dock/reports/

# 3. Ver notas de pentest da sessão anterior
cat /home/altave/.bughunter/bounties/dock/PENTEST_NOTES.md

# 4. Ver recon já feito
wc -l /home/altave/.bughunter/bounties/dock/recon/all_prod.txt   # 314 hosts
cat /home/altave/.bughunter/bounties/dock/recon/dnsx_all.txt | grep caradhras

# 5. Targets prioritários inexplorados
echo "
infrastructure-services-atlantis.dock.tech → Atlantis Terraform (IPs: 18.228.255.104, 54.232.195.72)
3ds.caradhras.io                           → 3DS payment system (18.231.85.71, 18.230.93.1)
portalfraude.conductor.com.br              → Portal antifraude (201.20.14.32)
pierflex.conductor.com.br                  → Cloudflare 409 (incomum)
pierpro.conductor.com.br                   → Cloudflare 409 (incomum)
datalake.caradhras.io                      → GoDaddy IP (possível misconfiguration)
docs.caradhras.io                          → API docs (CNAME apenas)
"

# 6. Pedir attack plan para caradhras
/home/altave/venv/bin/python3 -W ignore -m rag.cli plan "caradhras.io" \
  --tech fapi openbanking oauth2 kong express
```

---

## Atalhos úteis

```bash
# Alias recomendados (adicionar ao ~/.bashrc)
alias rag='cd /home/altave/.bughunter && /home/altave/venv/bin/python3 -W ignore -m rag.cli'
alias rag-stats='rag stats'
alias rag-query='rag query'
alias rag-plan='rag plan'

# Após adicionar aliases:
rag stats
rag query "JWT algorithm confusion"
rag plan "target.com" --tech node graphql
rag add-report --title "..." --content "..." --vuln "SSRF" --severity "HIGH"
```

---

## Findings Dock — Referência rápida

| ID | Arquivo | Sev | CVSS | Target | Escopo |
|----|---------|-----|------|--------|--------|
| D1 | `reports/D1_s3_subdomain_takeover.md` | HIGH | 7.5 | `cfsec.dock.tech` | `*.dock.tech` |
| D2 | `reports/D2_acquiring_config_exposure.md` | MEDIUM | 5.3 | `*.acquiring.dock.tech` | `*.dock.tech` |
| D3 | `reports/D3_iris_auth_missing_ratelimit.md` | MEDIUM | 5.9 | `front.iris.dock.tech` | `*.dock.tech` |
| D4 | `reports/D4_openbanking_cors_bypass_and_500.md` | MEDIUM | 6.1 | `auth.openbanking.dock.tech` | `*.dock.tech` |

**D4 nota:** Dois bugs encadeados — Kong CORS plugin global (`access-control-allow-origin: *` em TODA resposta) + Express `corsOptions.js` usa `throw` em vez de `callback(err)` → HTTP 500 com stack trace Node.js legível cross-origin de qualquer origem.

---

## Troubleshooting

```bash
# RAG não acha dados / stats zerado
cd /home/altave/.bughunter
/home/altave/venv/bin/python3 -W ignore -m rag.cli build   # rebuild completo (~5 min)

# Neo4j offline
docker ps | grep neo4j
docker start gotham-neo4j
# Verificar: http://localhost:7474 (user: neo4j, pass: changeme)

# Import de recon falha
/home/altave/venv/bin/python3 -W ignore -m rag.cli graph-import \
  --target "dock.tech" \
  --httpx "/home/altave/.bughunter/bounties/dock/recon/httpx_full.json"

# Venv corrompido
rm -rf /home/altave/venv
python3 -m venv /home/altave/venv
/home/altave/venv/bin/pip install chromadb requests beautifulsoup4 neo4j
cd /home/altave/.bughunter && /home/altave/venv/bin/python3 -W ignore -m rag.cli build
```
# ragnarock
