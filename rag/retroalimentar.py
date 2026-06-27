"""
Retroalimentação — Feed a new completed bounty back into the RAG.

Called automatically or manually after a bounty is submitted / disclosed.

Usage:
  python3 -m rag.retroalimentar \
    --title "IDOR in /api/users/{id} on HackerOne Program X" \
    --url "https://hackerone.com/reports/XXXXX" \
    --program "ProgramX" \
    --platform "HackerOne" \
    --vuln "IDOR" \
    --severity "HIGH" \
    --content "Full writeup text here..."

Or interactively:
  python3 -m rag.retroalimentar --interactive

The RAG auto-learns:
  - Vulnerability class patterns from this engagement
  - Specific bypass techniques that worked
  - Target tech-stack fingerprints
  - Chain combinations that led to impact
"""
from __future__ import annotations
import sys, json, argparse, textwrap
from pathlib import Path
from datetime import datetime

RAG_DIR = Path(__file__).parent
sys.path.insert(0, str(RAG_DIR.parent))

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

LOG_FILE = RAG_DIR / "data" / "retroalimentacao.jsonl"


def log_entry(entry: dict):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def retroalimentar(
    title: str,
    url: str,
    content: str,
    platform: str = "",
    vuln_type: str = "",
    severity: str = "",
    program: str = "",
    target_domain: str = "",
    tech_stack: list[str] | None = None,
    chain: str = "",
    impact: str = "",
    bypass: str = "",
    lessons: str = "",
):
    from rag.ingest.writeups import add_report
    from rag.store import get_rag

    # Build enriched content chunk
    enriched = textwrap.dedent(f"""
        BOUNTY REPORT: {title}
        Program: {program} | Platform: {platform}
        Target: {target_domain}
        Vulnerability: {vuln_type} | Severity: {severity}
        Tech stack: {', '.join(tech_stack or [])}
        Date: {datetime.utcnow().strftime('%Y-%m-%d')}

        --- DESCRIPTION ---
        {content[:3000]}

        --- ATTACK CHAIN ---
        {chain}

        --- IMPACT ---
        {impact}

        --- BYPASS TECHNIQUES ---
        {bypass}

        --- LESSONS LEARNED ---
        {lessons}
    """).strip()

    r = get_rag()

    # Store in both writeups + bounty_reports collections
    meta = {
        "type":    "bounty_report",
        "source":  "retroalimentacao",
        "title":   title[:200],
        "url":     url,
        "vuln":    vuln_type[:100],
        "platform": platform,
        "severity": severity,
        "program":  program,
        "target":   target_domain,
        "date":     datetime.utcnow().isoformat(),
    }
    doc_id = r.upsert("bb_writeups",    enriched, meta)
    r.upsert("bounty_reports", enriched, meta)

    # Also log to JSONL for audit trail
    log_entry({
        "id": doc_id, "title": title, "url": url,
        "platform": platform, "vuln": vuln_type, "severity": severity,
        "program": program, "target": target_domain,
        "tech_stack": tech_stack or [],
        "date": datetime.utcnow().isoformat(),
    })

    print(f"[Retroalimentação] Added: {doc_id}")
    print(f"  Title:    {title}")
    print(f"  Vuln:     {vuln_type} | Severity: {severity}")
    print(f"  Program:  {program} | Platform: {platform}")
    print(f"  Collections updated: bb_writeups + bounty_reports")
    return doc_id


def interactive_mode():
    print("=== BountyRAG Retroalimentação (interactive) ===\n")
    data = {}
    fields = [
        ("title",         "Report title",            True),
        ("url",           "URL (report/disclosure)",  False),
        ("program",       "Bug bounty program name",  False),
        ("platform",      "Platform (H1/BC/Intigriti)", False),
        ("target_domain", "Target domain",            False),
        ("vuln_type",     "Vulnerability type",       False),
        ("severity",      "Severity (CRITICAL/HIGH/MEDIUM/LOW)", False),
        ("tech_stack",    "Tech stack (space-separated)", False),
        ("chain",         "Attack chain (steps)",     False),
        ("impact",        "Business impact",          False),
        ("bypass",        "Bypass techniques used",   False),
        ("lessons",       "Lessons learned",          False),
    ]
    for key, label, required in fields:
        val = input(f"{label}{'*' if required else ''}: ").strip()
        if required and not val:
            print(f"  {label} is required.")
            sys.exit(1)
        data[key] = val

    print("\nPaste full report content (end with a line containing only 'END'):")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    data["content"] = "\n".join(lines)

    if "tech_stack" in data and data["tech_stack"]:
        data["tech_stack"] = data["tech_stack"].split()

    retroalimentar(**data)


def main():
    p = argparse.ArgumentParser(description="BountyRAG retroalimentação")
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--title",         default="")
    p.add_argument("--url",           default="")
    p.add_argument("--content",       default="")
    p.add_argument("--program",       default="")
    p.add_argument("--platform",      default="")
    p.add_argument("--target-domain", default="")
    p.add_argument("--vuln",          default="")
    p.add_argument("--severity",      default="")
    p.add_argument("--tech",          nargs="*", default=[])
    p.add_argument("--chain",         default="")
    p.add_argument("--impact",        default="")
    p.add_argument("--bypass",        default="")
    p.add_argument("--lessons",       default="")

    args = p.parse_args()

    if args.interactive:
        interactive_mode()
        return

    if not args.title or not args.content:
        p.print_help()
        print("\nError: --title and --content are required")
        sys.exit(1)

    retroalimentar(
        title=args.title,
        url=args.url,
        content=args.content,
        platform=args.platform,
        vuln_type=args.vuln,
        severity=args.severity,
        program=args.program,
        target_domain=getattr(args, "target_domain", ""),
        tech_stack=args.tech or [],
        chain=args.chain,
        impact=args.impact,
        bypass=args.bypass,
        lessons=args.lessons,
    )


if __name__ == "__main__":
    main()
