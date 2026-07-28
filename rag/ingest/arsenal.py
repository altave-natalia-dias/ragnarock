"""
Catalog of the personal tool arsenal in ~/lovableExpl/tools/ (author: ofjaaah),
surveyed and safety-triaged on 28/07/2026. Documents WHAT each tool does, its
risk profile, and the passive-only invocation pattern to prefer — so future
engagements can pull the right tool for the right job without re-discovering
this from scratch, and without accidentally invoking an active/intrusive mode.

Standalone: PYTHONPATH=/home/altave/.bughunter /home/altave/venv/bin/python3 -m rag.ingest.arsenal
"""
from __future__ import annotations
import sys
from pathlib import Path

RAG_DIR = Path(__file__).parent.parent

ARSENAL_KB: list[tuple[str, dict]] = []


def _kb(text: str, tags: list[str], category: str = "arsenal"):
    ARSENAL_KB.append((text.strip(), {
        "type":     "pentest_kb",
        "category": category,
        "tags":     ",".join(tags),
    }))


_kb("""
ARSENAL — Visão geral (~/lovableExpl/tools/, autor ofjaaah)

Kit pessoal de ~25 ferramentas Rust/Go/Python/Node pra bug bounty. A maioria
são scanners de recon passivo/semi-ativo com banner ASCII e README próprio.
Categorias: subdomain/infra enum (enuminfra, enumrust, monrust/monrust3,
nagliEnum), takeover (blh, dnsdangling), open redirect (crawOPENREDIRECT),
dependency confusion (dependencyRust, firebaseEx), cloud storage (s3Scan,
CrawlCognito p/ AWS Cognito), JS analysis (jsRealtime, jsrealtime-server,
JSSandBox/JSHunter), OSINT (postEvil p/ Postman público, github-intelligence),
fuzzing (fuffing = wrapper de ffuf), Mongo (mongoDBCRAWL), Lambda (lemma).

REGRA: antes de rodar QUALQUER uma contra um alvo real, ler o --help e o
README primeiro — várias têm flag de modo ativo (--test, --fuzz, --test-admin,
--exploit) que cruza a linha de "recon passivo" pra "teste ativo/intrusivo".
Só usar a flag mínima necessária pro objetivo (descoberta), nunca o "full scan"
por padrão.
""", ["arsenal", "tool-catalog", "ofjaaah", "recon"], "arsenal")

_kb("""
ARSENAL — postEvil (Postman public library search)

O QUE FAZ: busca a biblioteca PÚBLICA do Postman por coleções/workspaces que
mencionem o domínio alvo — pode revelar endpoint de API vazado, header de
auth, token de exemplo deixado em request salva publicamente. 100% OSINT
contra serviço de terceiro (Postman), não toca a infra do alvo.

LIMITAÇÃO CONFIRMADA (28/07, testado contra farfetch.com): a API de busca do
Postman retorna 401 sem uma API key válida (`-k PMAK-xxx`); o fallback de
"public web-index" não achou nada sem key. **Precisa de conta/API key do
Postman pra funcionar de verdade** — sem isso, roda mas não retorna resultado
útil.

INVOCAÇÃO SEGURA: `postevil -d target.com` (busca básica). NÃO usar
`--test`/`--fuzz`/`--test-admin` sem necessidade — essas testam URLs/tokens
extraídos contra o alvo real, o que é ativo, não mais puro OSINT.
""", ["arsenal", "postevil", "postman", "osint", "api-key-required"], "arsenal")

_kb("""
ARSENAL — github-intelligence: NÃO é scanner de segredo em repo de terceiro

CUIDADO: o nome sugere "buscar segredo vazado no GitHub do alvo", mas na
prática é uma app full-stack (React+FastAPI) que conecta o SEU PRÓPRIO
Personal Access Token do GitHub pra analisar SUA conta (postura de segurança,
repos, SSH keys). Não pesquisa repositório público de terceiro por domínio.

RED FLAG: o backend (`api.py`) tem endpoint `DeployKeyRequest`/`SSHKeyRequest`
com título default `"ofjaaah-persistence"`/`"ofjaaah-deploy"` — ou seja, a
ferramenta foi desenhada pra ADICIONAR chave SSH/deploy key numa conta/repo já
acessível via token, o que é uma técnica de persistência pós-comprometimento,
não descoberta. **Nunca rodar essa função contra token de terceiro/alvo.**

PRA BUSCAR SEGREDO VAZADO DE UM ALVO NO GITHUB, usar em vez disso:
  trufflehog github --org=targetorg --only-verified
(técnica já documentada no chunk "WEB RECON — Passive + Active Pipeline").
""", ["arsenal", "github-intelligence", "red-flag", "persistence", "not-for-target-scanning"], "arsenal")

_kb("""
ARSENAL — blh (Broken Link Hijacking Hunter) + dnsdangling

O QUE FAZEM: detectam subdomínio/link com DNS apontando pra recurso que não
existe mais (CNAME morto, bucket S3 deletado, perfil social removido) — se
reivindicável, um atacante registra o recurso e serve conteúdo malicioso sob
autoridade do domínio confiável. Pipeline: enum → probe → crawl → detecção →
validação de hijack.

QUANDO USAR: contra lista de subdomínios já conhecida que tenha hosts
NÃO-RESOLVENDO (candidato clássico a CNAME dangling) — ex.: no engajamento
Farfetch, 6 hosts de `*.farfetch-apps.com` não resolvem
(almir/clickstream/dermio/my/prelive-storm-inventory/storm-inventory) —
candidatos naturais pra rodar blh/dnsdangling em cima.

CUIDADO: `dnsdangling` tem um `dnsdangle_exploit.py` separado do scanner —
isso é a etapa de EXPLORAÇÃO (reivindicar o recurso pra provar o take over),
que é uma ação ativa com efeito real (registra algo em nome do pesquisador).
Só rodar a etapa de exploit depois de confirmar candidato real E ler
exatamente o que o script faz — nunca direto no "modo scanner".
""", ["arsenal", "blh", "dnsdangling", "subdomain-takeover", "cname-dangling"], "arsenal")

_kb("""
ARSENAL — Resto do kit (referência rápida)

- enuminfra / enumrust / monrust / monrust3 / nagliEnum: enum de
  subdomínio/infra, redundante com subfinder+amass+httpx já usados —
  só vale rodar se algum desses tiver fonte passiva que o subfinder não
  cobre (checar --help antes).
- crawOPENREDIRECT (ORSCAN): enum de subdomínio + crawl profundo + descoberta
  de parâmetro oculto + fuzz + auto-validação de open redirect. Aplicável
  em fluxo de checkout/login com parâmetro de retorno/redirect.
- dependencyRust / firebaseEx: dependency confusion (pacote interno
  squattable em registry público) e enum/extração específica de Firebase
  (Firestore/RTDB mal configurado). Só relevante se o alvo usa Firebase
  (não é o caso da Farfetch, que é AWS/Azure).
- s3Scan / CrawlCognito: scanner de bucket S3 mal configurado / postura de
  segurança AWS Cognito. Só relevante se o alvo usa esses serviços AWS
  especificamente (verificar antes de rodar às cegas).
- jsRealtime / jsrealtime-server / JSSandBox (JSHunter): análise de JS por
  segredo/source map/dependency confusion. Temos parte disso coberto pelo
  cloud_finder (com taxa de falso-positivo alta já documentada) — essas
  ferramentas podem ter heurística diferente, vale comparar resultado.
- mongoDBCRAWL: crawler de MongoDB exposto — só relevante com evidência
  prévia de Mongo no alvo.
- lemma: recon de AWS Lambda — só relevante se o alvo expõe função Lambda
  publicamente identificável.
- fuffing: wrapper de ffuf (`ffuf_master.sh`) — utilitário de conveniência,
  sem lógica nova além do ffuf puro.

REGRA GERAL: antes de rodar qualquer um contra um alvo pago, confirmar que a
tecnologia é aplicável (não gastar tempo em scanner de Firebase/Cognito/S3
num alvo que não usa esses serviços).
""", ["arsenal", "tool-catalog", "s3scan", "cognito", "firebase", "js-analysis", "dependency-confusion", "open-redirect"], "arsenal")


def ingest_arsenal(rag=None):
    from rag.store import get_rag
    r = rag or get_rag()
    print(f"  Upserting {len(ARSENAL_KB)} arsenal-catalog KB records → pentest_kb …")
    r.upsert_batch("pentest_kb", ARSENAL_KB)
    print("  Arsenal catalog ingested.")


if __name__ == "__main__":
    sys.path.insert(0, str(RAG_DIR.parent))
    ingest_arsenal()
    print("Done.")
