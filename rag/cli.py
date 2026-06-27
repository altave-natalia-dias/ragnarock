#!/usr/bin/env python3
"""
BountyRAG CLI — Hybrid Graph+Vector Bug Bounty Intelligence

Commands:
  build         Full initial build (MITRE + writeups + pentest KB)
  update        Refresh writeups from live sources
  add-report    Retroalimentação: add a new bounty report
  query         Semantic query (vector)
  plan          Hybrid Attack Plan for a domain (Graph+Vector)
  graph-import  Import recon tool output → Neo4j
  stats         Show ChromaDB + Neo4j counts
  technique     Look up a MITRE ATT&CK technique
  graph-clear   Remove a target's nodes from Neo4j

Usage:
  python3 -m rag.cli build
  python3 -m rag.cli plan target.com --tech node graphql
  python3 -m rag.cli query "JWT algorithm confusion auth bypass"
  python3 -m rag.cli graph-import --target example.com --httpx /tmp/httpx.json
  python3 -m rag.cli add-report --title "..." --url "..." --content "..." --vuln IDOR
  python3 -m rag.cli technique T1190
  python3 -m rag.cli stats
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path

RAG_DIR = Path(__file__).parent
sys.path.insert(0, str(RAG_DIR.parent))

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)


def cmd_build(args):
    print("=== BountyRAG HYBRID BUILD ===\n")
    from rag.store import get_rag
    r = get_rag()

    print("[1/3] MITRE ATT&CK + D3FEND")
    from rag.ingest.mitre import ingest_attack, ingest_defend
    ingest_attack(r)
    ingest_defend(r)

    print("\n[2/3] Bug-bounty writeups")
    from rag.ingest.writeups import ingest_all_writeups
    ingest_all_writeups(r)

    print("\n[3/3] Pentest KB + CySA+")
    from rag.ingest.knowledge import ingest_knowledge
    ingest_knowledge(r)

    # Seed base vuln→vuln chains in Neo4j
    print("\n[4/4] Seeding exploit chains in Neo4j …")
    _seed_base_chains()

    from rag.retrieve import rag_stats
    print("\n" + rag_stats())
    print("\nBuild completo.")


def _seed_base_chains():
    """Populate known exploit chain pairs in Neo4j from entity_extractor."""
    try:
        from rag.graph_store import get_graph
        from rag.ingest.entity_extractor import CHAIN_PAIRS, VULN_PATTERNS
        g = get_graph()
        if not g.ok:
            print("  Neo4j offline — chains not seeded")
            return

        # Upsert all known vulnerability types
        for pat, name, sev in VULN_PATTERNS:
            vk = name.lower().replace(" ", "_")[:80]
            g.upsert_vulnerabilidade(name=name, severity=sev)

        # Upsert chain relationships
        for a, b, label in CHAIN_PAIRS:
            ka = a.lower().replace(" ", "_")[:80]
            kb = b.lower().replace(" ", "_")[:80]
            g.link_vuln_to_vuln(ka, kb, label)

        print(f"  {len(VULN_PATTERNS)} tipos de vuln + {len(CHAIN_PAIRS)} cadeias seeded")
    except Exception as e:
        print(f"  [seed chains] {e}")


def cmd_update(args):
    print("=== BountyRAG UPDATE (writeups) ===\n")
    from rag.store import get_rag
    from rag.ingest.writeups import ingest_all_writeups
    ingest_all_writeups(get_rag())
    from rag.retrieve import rag_stats
    print("\n" + rag_stats())


def cmd_add_report(args):
    from rag.ingest.writeups import add_report
    doc_id = add_report(
        title=args.title,
        url=args.url or "",
        content=args.content,
        platform=args.platform or "",
        vuln_type=args.vuln or "",
        severity=args.severity or "",
        program=args.program or "",
    )
    print(f"Added: {doc_id}")


def cmd_query(args):
    from rag.retrieve import query_for_target, format_context
    ctx = query_for_target(args.text, tech_stack=args.tech or [])
    print(format_context(ctx))


def cmd_plan(args):
    from rag.retrieve import hybrid_search, format_hybrid_plan
    print(f"\nBuscando intel híbrida para {args.domain} …\n")
    hs = hybrid_search(args.domain, tech_stack=args.tech or [])
    print(format_hybrid_plan(hs))


def cmd_graph_import(args):
    from rag.ingest.recon_parser import parse_all
    results = parse_all(
        target=args.target,
        httpx_file=args.httpx or None,
        nuclei_file=args.nuclei or None,
        subfinder_file=args.subfinder or None,
        katana_file=args.katana or None,
        nmap_file=args.nmap or None,
    )
    total = sum(results.values())
    print(f"\nTotal importado: {total} artefatos")

    from rag.graph_store import get_graph
    g = get_graph()
    if g.ok:
        print(f"Graph stats: {g.stats()}")


def cmd_technique(args):
    from rag.retrieve import query_technique
    results = query_technique(args.id)
    for r in results:
        meta = r.get("metadata", {})
        print(f"\n--- {meta.get('tech_id','')} {meta.get('name','')} (score={r['score']}) ---")
        print(r["text"][:800])


def cmd_stats(args):
    from rag.retrieve import rag_stats
    print(rag_stats())


def cmd_graph_clear(args):
    from rag.graph_store import get_graph
    g = get_graph()
    if not g.ok:
        print("Neo4j offline")
        return
    g.clear_target(args.domain)
    print(f"Nós do alvo '{args.domain}' removidos do grafo")


def main():
    p   = argparse.ArgumentParser(description="BountyRAG Hybrid CLI")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("build",  help="Full build (MITRE + writeups + KB + Neo4j seed)")
    sub.add_parser("update", help="Refresh writeups")
    sub.add_parser("stats",  help="ChromaDB + Neo4j counts")

    p_report = sub.add_parser("add-report", help="Retroalimentação")
    p_report.add_argument("--title",    required=True)
    p_report.add_argument("--url",      default="")
    p_report.add_argument("--content",  required=True)
    p_report.add_argument("--platform", default="")
    p_report.add_argument("--vuln",     default="")
    p_report.add_argument("--severity", default="")
    p_report.add_argument("--program",  default="")

    p_query = sub.add_parser("query", help="Semantic query")
    p_query.add_argument("text")
    p_query.add_argument("--tech", nargs="*", default=[])

    p_plan = sub.add_parser("plan", help="Hybrid Attack Plan (Graph+Vector)")
    p_plan.add_argument("domain")
    p_plan.add_argument("--tech", nargs="*", default=[])

    p_gi = sub.add_parser("graph-import", help="Import recon output → Neo4j")
    p_gi.add_argument("--target",    required=True)
    p_gi.add_argument("--httpx",     default="")
    p_gi.add_argument("--nuclei",    default="")
    p_gi.add_argument("--subfinder", default="")
    p_gi.add_argument("--katana",    default="")
    p_gi.add_argument("--nmap",      default="")

    p_tech = sub.add_parser("technique", help="ATT&CK technique lookup")
    p_tech.add_argument("id")

    p_gc = sub.add_parser("graph-clear", help="Remove target from Neo4j")
    p_gc.add_argument("domain")

    args = p.parse_args()

    dispatch = {
        "build":        cmd_build,
        "update":       cmd_update,
        "add-report":   cmd_add_report,
        "query":        cmd_query,
        "plan":         cmd_plan,
        "graph-import": cmd_graph_import,
        "technique":    cmd_technique,
        "stats":        cmd_stats,
        "graph-clear":  cmd_graph_clear,
    }

    if args.cmd not in dispatch:
        p.print_help()
        sys.exit(1)

    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
