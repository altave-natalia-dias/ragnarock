"""
BountyRAG — Hybrid Retrieval Engine (Vector ChromaDB + Graph Neo4j)

Funções principais:
  hybrid_search(domain, tech_stack)  → Attack Plan estruturado
  query_for_target(desc, tech_stack) → contexto semântico puro
  query_technique(id)                → lookup ATT&CK por ID
  query_writeups(vuln_class)         → writeups por classe de vuln
  format_attack_plan(domain, techs)  → output colorido para terminal
"""
from __future__ import annotations
import sys, json, textwrap
from pathlib import Path

RAG_DIR = Path(__file__).parent
if str(RAG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(RAG_DIR.parent))

from rag.store import get_rag, COLLECTIONS

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# ANSI colors
C = {
    "RED":    "\033[91m", "YLW":  "\033[93m", "GRN": "\033[92m",
    "BLU":    "\033[94m", "MAG":  "\033[95m", "CYN": "\033[96m",
    "BOLD":   "\033[1m",  "DIM":  "\033[2m",  "RST": "\033[0m",
    "BG_RED": "\033[41m", "BG_YLW": "\033[43m",
}

SEV_COLOR = {
    "CRITICAL": C["BG_RED"] + C["BOLD"],
    "HIGH":     C["RED"],
    "MEDIUM":   C["YLW"],
    "LOW":      C["GRN"],
    "INFO":     C["DIM"],
}


def _sev(s: str) -> str:
    return SEV_COLOR.get(s.upper(), "") + s.upper() + C["RST"]


def _lazy_graph():
    try:
        from rag.graph_store import get_graph
        g = get_graph()
        return g if g.ok else None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────
# VECTOR search (ChromaDB)
# ──────────────────────────────────────────────────────────────────────

def query_for_target(
    description: str,
    tech_stack: list[str] | None = None,
    n: int = 12,
) -> dict:
    r    = get_rag()
    query = description + (" " + " ".join(tech_stack) if tech_stack else "")
    return {
        "query":      description,
        "tech_stack": tech_stack or [],
        "attack":     r.query(query, collections=["mitre_attack"],  n_results=6),
        "defend":     r.query(query, collections=["mitre_defend"],  n_results=3),
        "writeups":   r.query(query, collections=["bb_writeups","bounty_reports"], n_results=8),
        "kb":         r.query(query, collections=["pentest_kb"],    n_results=6),
        "cysa":       r.query(query, collections=["cysa_kb"],       n_results=3),
    }


def query_technique(technique_id: str) -> list[dict]:
    r       = get_rag()
    semantic = r.query(technique_id, collections=["mitre_attack"], n_results=5)
    bm25_r  = r.keyword_search(
        f"{technique_id} Exploit Public-Facing Application",
        collections=["mitre_attack"], n_results=3,
    )
    seen, merged = set(), []
    for item in semantic + bm25_r:
        key = item["text"][:100]
        if key not in seen:
            seen.add(key); merged.append(item)
    return merged


def query_writeups(vuln_class: str, n: int = 10) -> list[dict]:
    r        = get_rag()
    semantic = r.query(vuln_class, collections=["bb_writeups","bounty_reports"], n_results=n)
    keyword  = r.keyword_search(vuln_class, collections=["bb_writeups","bounty_reports"], n_results=n//2)
    seen, merged = set(), []
    for item in semantic + keyword:
        key = item.get("metadata", {}).get("url", item["text"][:60])
        if key not in seen:
            seen.add(key); merged.append(item)
    return merged[:n]


# ──────────────────────────────────────────────────────────────────────
# HYBRID search: Graph → Vector
# ──────────────────────────────────────────────────────────────────────

def hybrid_search(domain: str, tech_stack: list[str] | None = None) -> dict:
    """
    Motor híbrido:
      A. Neo4j → infra map + attack paths + exploit chains (structural)
      B. ChromaDB → payloads + writeups para cada vuln do grafo (semantic)
      C. MITRE ATT&CK lookup para cada técnica encontrada

    Returns:
      {
        domain, tech_stack,
        infra:   [...],          # lista de subdomínios + techs
        paths:   [...],          # attack paths grafo (tech → vuln)
        chains:  [...],          # exploit chains (vuln→vuln)
        payloads: {vuln: [...]}, # ChromaDB payloads por vuln
        mitre:   [...],          # ATT&CK techniques correlacionadas
        fallback: {...}          # vector-only se grafo vazio
      }
    """
    g   = _lazy_graph()
    r   = get_rag()
    ts  = tech_stack or []
    result: dict = {
        "domain":    domain,
        "tech_stack": ts,
        "infra":     [],
        "paths":     [],
        "chains":    [],
        "payloads":  {},
        "mitre":     [],
        "fallback":  {},
        "graph_ok":  g is not None and g.ok,
    }

    # ── A: Graph queries ──────────────────────────────────────────── #
    if g and g.ok:
        # Ensure alvo exists (upsert lazily)
        g.upsert_alvo(domain)

        result["infra"]  = g.infra_map(domain)
        result["paths"]  = g.attack_paths_for_domain(domain)
        result["chains"] = g.exploit_chains(domain)

        # Collect unique vuln names from paths
        vulns_in_graph = list({p["vuln"] for p in result["paths"] if p.get("vuln")})

        # ── B: Vector payloads for each graph vuln ────────────────── #
        for vuln in vulns_in_graph[:8]:
            hits = r.query(
                f"{vuln} exploit payload bypass technique",
                collections=["pentest_kb", "bb_writeups", "bounty_reports"],
                n_results=4,
            )
            result["payloads"][vuln] = hits

        # ── C: MITRE lookup for ATT&CK technique IDs from paths ───── #
        tech_ids = list({p.get("technique_id") for p in result["paths"] if p.get("technique_id")})
        for tid in tech_ids[:5]:
            hits = query_technique(tid)
            result["mitre"].extend(hits[:2])

    # ── Fallback: vector-only if graph empty / offline ────────────── #
    if not result["paths"]:
        query_str = f"bug bounty {domain} " + " ".join(ts)
        result["fallback"] = query_for_target(query_str, tech_stack=ts)

        # Also inject tech stack directly from httpx/tech_stack arg
        if ts and g and g.ok:
            g.upsert_alvo(domain)
            for tech in ts:
                tk = f"{tech.lower()}:".rstrip(":")
                g.upsert_tecnologia(name=tech)
                # Pull known vulns for this tech from KB
                kb_hits = r.query(
                    f"{tech} vulnerability exploit",
                    collections=["pentest_kb"], n_results=5,
                )
                result["payloads"][tech] = kb_hits

    return result


# ──────────────────────────────────────────────────────────────────────
# Formatters
# ──────────────────────────────────────────────────────────────────────

def _box(title: str, width: int = 70) -> str:
    top = "╔" + "═" * (width - 2) + "╗"
    mid = "╠" + "═" * (width - 2) + "╣"
    ttl = "║ " + C["BOLD"] + title.center(width - 4) + C["RST"] + " ║"
    return f"{C['CYN']}{top}\n{ttl}\n{mid}{C['RST']}"


def _section(title: str, width: int = 70) -> str:
    return f"{C['BLU']}╠{'═' * (width-2)}╣{C['RST']}\n{C['BLU']}║ {C['BOLD']}{title}{C['RST']}{C['BLU']} {'║'.rjust(width - len(title) - 3)}  {C['RST']}"


def _line(content: str = "", width: int = 70) -> str:
    return f"{C['BLU']}║{C['RST']} {content}"


def _bot(width: int = 70) -> str:
    return f"{C['CYN']}╚{'═' * (width-2)}╝{C['RST']}"


def format_hybrid_plan(hs: dict, verbose: bool = True) -> str:
    """
    Formata o resultado do hybrid_search() em um Attack Plan estruturado
    com boxes ASCII, cores e seções claras.
    """
    domain = hs["domain"]
    ts     = hs.get("tech_stack", [])
    lines  = []

    # ── Header ──────────────────────────────────────────────────────── #
    lines.append(_box(f"BOUNTYRAG HYBRID ATTACK PLAN: {domain}"))
    if ts:
        lines.append(_line(f"Tech Stack detectado: {C['MAG']}{', '.join(ts)}{C['RST']}"))
    if hs.get("graph_ok"):
        lines.append(_line(f"{C['GRN']}● Neo4j ONLINE — modo Hybrid Graph+Vector{C['RST']}"))
    else:
        lines.append(_line(f"{C['YLW']}⚠ Neo4j offline — modo Vector-only{C['RST']}"))
    lines.append("")

    # ── Infrastructure Map ───────────────────────────────────────────── #
    infra = hs.get("infra", [])
    if infra:
        lines.append(f"{C['BLU']}╠{'═'*68}╣{C['RST']}")
        lines.append(_line(f"{C['BOLD']}INFRASTRUCTURE MAP (Neo4j){C['RST']}"))
        lines.append(_line())
        for sub in infra[:15]:
            fqdn  = sub.get("fqdn", "")
            ip    = sub.get("ip", "")
            stat  = sub.get("status", "")
            title = sub.get("title", "")[:40]
            techs = sub.get("techs", [])
            if isinstance(techs, str):
                techs = json.loads(techs) if techs.startswith("[") else [techs]
            eps   = sub.get("endpoints", [])
            if isinstance(eps, str):
                eps = json.loads(eps) if eps.startswith("[") else [eps]

            scolor = C["GRN"] if stat == 200 else (C["YLW"] if stat in (301,302,403) else C["RED"])
            lines.append(_line(f"  {C['CYN']}├── {fqdn}{C['RST']} [{scolor}{stat}{C['RST']}] {C['DIM']}{ip} {title}{C['RST']}"))
            if techs:
                lines.append(_line(f"  │     {C['MAG']}⚙  {', '.join(t for t in techs if t and t != ':?')}{C['RST']}"))
            for ep in (eps[:5] if eps else []):
                lines.append(_line(f"  │     {C['DIM']}└ {ep}{C['RST']}"))
        lines.append(_line())

    # ── Attack Paths ─────────────────────────────────────────────────── #
    paths = hs.get("paths", [])
    if paths:
        lines.append(f"{C['BLU']}╠{'═'*68}╣{C['RST']}")
        lines.append(_line(f"{C['BOLD']}ATTACK PATHS (Graph: Tech → Vuln){C['RST']}"))
        lines.append(_line())
        for i, p in enumerate(paths[:12], 1):
            fqdn    = p.get("fqdn", "")
            tech    = p.get("tech", "?")
            ver     = p.get("version", "")
            vuln    = p.get("vuln", "?")
            sev     = p.get("severity", "MEDIUM")
            cve     = p.get("cve", "")
            tactic  = p.get("tactic", "")
            tid     = p.get("technique_id", "")

            tech_str = f"{tech} {ver}".strip()
            sev_str  = _sev(sev)
            cve_str  = f" [{C['YLW']}{cve}{C['RST']}]" if cve else ""
            tid_str  = f" {C['DIM']}{tid}{C['RST']}" if tid else ""

            lines.append(_line(
                f"  PATH {i:02d} [{sev_str}]  "
                f"{C['MAG']}{tech_str}{C['RST']} → {C['RED']}{vuln}{C['RST']}"
                f"{cve_str}{tid_str}"
            ))
            if fqdn:
                lines.append(_line(f"         {C['DIM']}host: {fqdn}  tactic: {tactic}{C['RST']}"))
        lines.append(_line())

    # ── Exploit Chains ───────────────────────────────────────────────── #
    chains = hs.get("chains", [])
    if chains:
        lines.append(f"{C['BLU']}╠{'═'*68}╣{C['RST']}")
        lines.append(_line(f"{C['BOLD']}EXPLOIT CHAINS (vuln → vuln → impact){C['RST']}"))
        lines.append(_line())
        for i, ch in enumerate(chains[:8], 1):
            s1 = ch.get("step1", "?"); se1 = ch.get("sev1", "")
            s2 = ch.get("step2", "?"); se2 = ch.get("sev2", "")
            s3 = ch.get("step3");      se3 = ch.get("sev3", "")
            steps = f"{C['YLW']}{s1}{C['RST']} → {C['RED']}{s2}{C['RST']}"
            if s3:
                steps += f" → {C['BG_RED']}{s3}{C['RST']}"
            lines.append(_line(f"  CHAIN {i}: {steps}"))
        lines.append(_line())

    # ── Payloads + Writeups ──────────────────────────────────────────── #
    payloads = hs.get("payloads", {})
    if payloads:
        lines.append(f"{C['BLU']}╠{'═'*68}╣{C['RST']}")
        lines.append(_line(f"{C['BOLD']}EXPLOIT PAYLOADS + WRITEUPS (Vector){C['RST']}"))
        lines.append(_line())
        for vuln_name, hits in list(payloads.items())[:6]:
            lines.append(_line(f"  {C['RED']}▶ {vuln_name}{C['RST']}"))
            for h in hits[:3]:
                src   = h.get("metadata", {}).get("source", "")
                url   = h.get("metadata", {}).get("url", "")
                score = h.get("score", 0)
                text  = h["text"][:300].replace("\n", " ")
                lines.append(_line(f"    {C['DIM']}[{src}] score={score:.2f}{C['RST']}"))
                if url:
                    lines.append(_line(f"    {C['BLU']}{url}{C['RST']}"))
                lines.append(_line(f"    {text}"))
                lines.append(_line())

    # ── MITRE ATT&CK Correlation ─────────────────────────────────────── #
    mitre = hs.get("mitre", [])
    if mitre:
        lines.append(f"{C['BLU']}╠{'═'*68}╣{C['RST']}")
        lines.append(_line(f"{C['BOLD']}MITRE ATT&CK CORRELATION{C['RST']}"))
        lines.append(_line())
        seen_t: set = set()
        for m in mitre[:4]:
            meta = m.get("metadata", {})
            tid  = meta.get("tech_id", "")
            name = meta.get("name", "")
            tacs = meta.get("tactics", "[]")
            if tid in seen_t: continue
            seen_t.add(tid)
            try:
                tacs_list = json.loads(tacs) if isinstance(tacs, str) else tacs
            except Exception:
                tacs_list = []
            lines.append(_line(f"  {C['CYN']}{tid}{C['RST']} {name}"))
            if tacs_list:
                lines.append(_line(f"       {C['DIM']}tactics: {', '.join(tacs_list)}{C['RST']}"))
        lines.append(_line())

    # ── Fallback / Vector-only ────────────────────────────────────────── #
    fallback = hs.get("fallback", {})
    if fallback and not paths:
        lines.append(f"{C['BLU']}╠{'═'*68}╣{C['RST']}")
        lines.append(_line(f"{C['BOLD']}VECTOR KNOWLEDGE (sem grafo — ainda não mapeado){C['RST']}"))
        lines.append(_line())

        for section, items in [
            ("Pentest KB",     fallback.get("kb", [])),
            ("Writeups",       fallback.get("writeups", [])),
            ("ATT&CK",         fallback.get("attack", [])),
        ]:
            for item in items[:3]:
                meta  = item.get("metadata", {})
                score = item.get("score", 0)
                text  = item["text"][:250].replace("\n", " ")
                url   = meta.get("url", "")
                lines.append(_line(f"  {C['GRN']}[{section}]{C['RST']} score={score:.2f} {C['DIM']}{url}{C['RST']}"))
                lines.append(_line(f"  {text}"))
                lines.append(_line())

    # ── Recommendations ──────────────────────────────────────────────── #
    lines.append(f"{C['BLU']}╠{'═'*68}╣{C['RST']}")
    lines.append(_line(f"{C['BOLD']}RECOMENDAÇÕES DE AÇÃO{C['RST']}"))
    lines.append(_line())

    # Priority based on severity in paths
    crits  = [p for p in paths if p.get("severity") in ("CRITICAL",)]
    highs  = [p for p in paths if p.get("severity") == "HIGH"]

    if crits:
        lines.append(_line(f"  {_sev('CRITICAL')} {len(crits)} caminhos críticos — prioridade máxima:"))
        for p in crits[:3]:
            lines.append(_line(f"    → {p.get('tech','')} ({p.get('fqdn','')}) → {p.get('vuln','')}"))
    if highs:
        lines.append(_line(f"  {_sev('HIGH')} {len(highs)} caminhos high — testar em sequência:"))
        for p in highs[:3]:
            lines.append(_line(f"    → {p.get('tech','')} ({p.get('fqdn','')}) → {p.get('vuln','')}"))
    if chains:
        lines.append(_line(f"  {C['MAG']}⛓  {len(chains)} cadeia(s) de exploit detectadas — alta probabilidade de P1{C['RST']}"))
    if not crits and not highs:
        lines.append(_line(f"  {C['YLW']}⚠ Infra ainda não mapeada. Execute recon e alimente a RAG:{C['RST']}"))
        lines.append(_line(f"    {C['DIM']}python3 -m rag.ingest.recon_parser --target {domain} --httpx /tmp/httpx.json{C['RST']}"))
        lines.append(_line(f"    {C['DIM']}Depois: /rag-bounty {domain} para re-executar com grafo{C['RST']}"))

    lines.append(_line())
    lines.append(_line(f"  {C['DIM']}Após submeter: python3 -m rag.retroalimentar --target-domain {domain} ...{C['RST']}"))
    lines.append(_bot())

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# Legacy / compat wrappers
# ──────────────────────────────────────────────────────────────────────

def format_attack_plan(domain: str, tech_stack: list[str] | None = None) -> str:
    """Wrapper: hybrid_search → format_hybrid_plan."""
    hs = hybrid_search(domain, tech_stack=tech_stack)
    return format_hybrid_plan(hs)


def format_context(results: dict, max_chars: int = 8000) -> str:
    """Legacy vector-only formatter (compat)."""
    lines: list[str] = []
    lines.append(f"# RAG Context — {results.get('query','')}")
    if results.get("tech_stack"):
        lines.append(f"Tech stack: {', '.join(results['tech_stack'])}")
    lines.append("")
    sections = [
        ("## MITRE ATT&CK",    results.get("attack",  [])),
        ("## Writeups",        results.get("writeups",[])),
        ("## Pentest KB",      results.get("kb",      [])),
        ("## CySA+",           results.get("cysa",    [])),
        ("## D3FEND",          results.get("defend",  [])),
    ]
    total = 0
    for heading, items in sections:
        if not items: continue
        lines.append(heading)
        for item in items:
            meta  = item.get("metadata", {})
            score = item.get("score", 0)
            src   = meta.get("source", meta.get("type", ""))
            url   = meta.get("url", "")
            text  = item["text"][:600]
            snippet = f"[{src}] score={score:.2f}"
            if url: snippet += f" | {url}"
            snippet += f"\n{text}\n"
            lines.append(snippet)
            total += len(snippet)
            if total > max_chars:
                lines.append("... (truncated)")
                break
        lines.append("")
    return "\n".join(lines)


def query_asn_surface(domain: str) -> str:
    r = get_rag()
    results = r.query(
        f"ASN BGP subdomain enumeration certificate transparency recon {domain}",
        collections=["pentest_kb"], n_results=4,
    )
    return format_context({"query": f"ASN recon: {domain}", "kb": results})


def rag_stats() -> str:
    r = get_rag()
    v = r.stats()
    g = _lazy_graph()
    gs = g.stats() if g and g.ok else {"Neo4j": "offline"}
    lines = [f"{C['BOLD']}BountyRAG — Stats{C['RST']}"]
    lines.append(f"\n  {C['CYN']}ChromaDB (Vector):{C['RST']}")
    lines += [f"    {n:25s}: {c:>6} docs" for n, c in v.items()]
    lines.append(f"\n  {C['GRN']}Neo4j (Graph):{C['RST']}")
    lines += [f"    {n:25s}: {c:>6}" for n, c in gs.items()]
    return "\n".join(lines)


if __name__ == "__main__":
    print(rag_stats())
