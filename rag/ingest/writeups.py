"""
Bug-bounty public writeup ingestion from three sources:

  1. https://pentester.land/writeups/          (JSON API — best structured)
  2. https://github.com/devanshbatham/Awesome-Bugbounty-Writeups  (README.md links)
  3. https://www.bugbountyhunting.com/         (HTML scrape)

Also scrapes individual writeup URLs to get full content (summary + title stored
even when full fetch fails).

Run: python3 -m rag.ingest.writeups
"""
from __future__ import annotations
import sys, json, re, time, textwrap, hashlib
from pathlib import Path

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

import requests
from bs4 import BeautifulSoup

# Graph integration (lazy import — OK if Neo4j offline)
def _get_graph():
    try:
        from rag.graph_store import get_graph
        g = get_graph()
        return g if g.ok else None
    except Exception:
        return None

def _get_extractor():
    try:
        from rag.ingest.entity_extractor import extract_all
        return extract_all
    except Exception:
        return None

RAG_DIR  = Path(__file__).parent.parent
DATA_DIR = RAG_DIR / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}
TIMEOUT    = 15
SLEEP_SECS = 0.4   # polite crawl delay


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _get(url: str, retries: int = 2) -> requests.Response | None:
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            return r
        except Exception as e:
            if i == retries - 1:
                print(f"    WARN: {url}: {e}")
    return None


def _to_text(html: str) -> str:
    """Strip HTML tags to plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text(" ")).strip()


def _chunk_writeup(title: str, url: str, text: str, platform: str = "", vuln_type: str = "") -> str:
    return textwrap.dedent(f"""
        BUG BOUNTY WRITEUP: {title}
        URL: {url}
        Platform: {platform}
        Vulnerability type: {vuln_type}

        {text[:3000]}
    """).strip()


# ------------------------------------------------------------------ #
# Source 1 — pentester.land                                           #
# ------------------------------------------------------------------ #

PLAND_API = "https://pentester.land/writeups/"
PLAND_JSON = "https://pentester.land/writeups.json"


def _ingest_pentesterland(rag) -> int:
    """
    Fetch the JSON index from pentester.land.
    Falls back to HTML scrape if JSON unavailable.
    """
    cache = DATA_DIR / "pentesterland.json"
    count = 0
    items: list[tuple[str, dict]] = []

    # Try JSON index first
    r = _get(PLAND_JSON)
    if r and r.status_code == 200:
        try:
            data = r.json()
            cache.write_text(json.dumps(data))
        except Exception:
            data = json.loads(cache.read_text()) if cache.exists() else []
    elif cache.exists():
        data = json.loads(cache.read_text())
    else:
        data = []

    # pentester.land format: {"data": [{Links:[{Title,Link}], Authors, Programs, Bugs, Types, Date},...]}
    raw_entries = data.get("data", data) if isinstance(data, dict) else data
    entries = raw_entries if isinstance(raw_entries, list) else []

    for entry in entries[:1000]:   # cap at 1000 for initial run
        # Extract link + title from Links array
        links   = entry.get("Links", [])
        primary = links[0] if links else {}
        title   = primary.get("Title", entry.get("title", entry.get("name", "")))
        url     = primary.get("Link", entry.get("url", entry.get("link", "")))

        summary  = entry.get("description", entry.get("summary", entry.get("excerpt", "")))
        bugs    = entry.get("Bugs", entry.get("tags", []))
        types   = entry.get("Types", [])
        authors = entry.get("Authors", [])
        programs= entry.get("Programs", [])
        date    = entry.get("Date", "")
        platform = ", ".join(programs[:3]) if programs else entry.get("platform", "")
        vuln    = ", ".join(bugs[:5] if bugs else types[:5])[:100]

        if not title:
            continue

        extra = f"Authors: {', '.join(authors[:3])}\nDate: {date}" if authors else ""
        text  = (summary[:2500] if summary else "") or extra or f"See: {url}"
        chunk = _chunk_writeup(title, url, text, platform=platform, vuln_type=vuln)
        items.append((chunk, {
            "type":     "bb_writeup",
            "source":   "pentester.land",
            "title":    title[:200],
            "url":      url,
            "vuln":     vuln[:100],
            "platform": platform,
        }))
        count += 1

    if items:
        rag.upsert_batch("bb_writeups", items)
    print(f"    pentester.land: {count} writeups")
    return count


# ------------------------------------------------------------------ #
# Source 2 — Awesome-Bugbounty-Writeups (GitHub README)               #
# ------------------------------------------------------------------ #

AWESOME_RAW = (
    "https://raw.githubusercontent.com/devanshbatham/"
    "Awesome-Bugbounty-Writeups/master/README.md"
)


def _ingest_awesome(rag) -> int:
    cache = DATA_DIR / "awesome_writeups.md"
    r = _get(AWESOME_RAW)
    if r and r.status_code == 200:
        cache.write_text(r.text)
        md = r.text
    elif cache.exists():
        md = cache.read_text()
    else:
        print("    awesome-writeups: unavailable, skipping")
        return 0

    # Extract markdown links: [title](url)
    pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
    matches = pattern.findall(md)

    items: list[tuple[str, dict]] = []

    # Determine vuln type from section headers
    current_section = ""
    lines = md.split("\n")
    link_idx = 0
    for line in lines:
        h = re.match(r'^#{1,4}\s+(.+)', line)
        if h:
            current_section = h.group(1).strip()
        ms = pattern.findall(line)
        for title, url in ms:
            chunk = _chunk_writeup(title, url, f"See: {url}", vuln_type=current_section)
            items.append((chunk, {
                "type":    "bb_writeup",
                "source":  "awesome-bugbounty-writeups",
                "title":   title[:200],
                "url":     url,
                "vuln":    current_section[:100],
                "platform": "",
            }))

    if items:
        rag.upsert_batch("bb_writeups", items)
    print(f"    awesome-writeups: {len(items)} entries")
    return len(items)


# ------------------------------------------------------------------ #
# Source 3 — bugbountyhunting.com                                     #
# ------------------------------------------------------------------ #

BBH_URL = "https://www.bugbountyhunting.com/"


def _ingest_bbhunting(rag) -> int:
    cache = DATA_DIR / "bugbountyhunting.html"
    r = _get(BBH_URL)
    if r and r.status_code == 200:
        cache.write_bytes(r.content)
        html = r.text
    elif cache.exists():
        html = cache.read_text(errors="replace")
    else:
        print("    bugbountyhunting.com: unavailable, skipping")
        return 0

    soup  = BeautifulSoup(html, "html.parser")
    items: list[tuple[str, dict]] = []

    # Try to find article/post links
    for a in soup.find_all("a", href=True)[:600]:
        href  = a["href"]
        if not href.startswith("http"):
            if href.startswith("/"):
                href = "https://www.bugbountyhunting.com" + href
            else:
                continue
        if "bugbountyhunting.com" not in href:
            continue
        title = a.get_text(strip=True)
        if len(title) < 10:
            continue

        chunk = _chunk_writeup(title, href, f"See: {href}")
        items.append((chunk, {
            "type":    "bb_writeup",
            "source":  "bugbountyhunting.com",
            "title":   title[:200],
            "url":     href,
            "vuln":    "",
            "platform": "",
        }))

    # deduplicate by url
    seen: set[str] = set()
    deduped = []
    for item in items:
        url = item[1]["url"]
        if url not in seen:
            seen.add(url)
            deduped.append(item)

    if deduped:
        rag.upsert_batch("bb_writeups", deduped)
    print(f"    bugbountyhunting.com: {len(deduped)} entries")
    return len(deduped)


# ------------------------------------------------------------------ #
# Graph sync helper                                                    #
# ------------------------------------------------------------------ #

def _sync_to_graph(doc_id: str, title: str, url: str, content: str,
                   vuln_type: str, platform: str, severity: str) -> None:
    """
    After adding a writeup to ChromaDB, extract entities and create
    Neo4j nodes + relationships.
    """
    g  = _get_graph()
    ex = _get_extractor()
    if not g or not ex:
        return

    full_text = f"{title} {vuln_type} {content}"
    entities  = ex(full_text, title=title)

    # Upsert Writeup_Ref node
    g.upsert_writeup_ref(
        chroma_id=doc_id, title=title, url=url,
        vuln_type=vuln_type, platform=platform, severity=severity,
    )

    # Upsert each vulnerability type found
    for vuln in entities["vulns"]:
        g.upsert_vulnerabilidade(
            name=vuln["name"],
            cve=", ".join(entities["cves"][:3]),
            cwe=", ".join(entities["cwes"][:2]),
            severity=vuln["severity"],
            description=f"Extracted from writeup: {title}",
        )
        vuln_key = (entities["cves"][0] if entities["cves"] else
                    vuln["name"].lower().replace(" ", "_"))[:80]
        g.link_vuln_to_writeup(vuln_key, doc_id)

    # Upsert technologies and link to vulns
    for tech in entities["techs"]:
        tk = f"{tech['name'].lower()}:{tech.get('version','')}".rstrip(":")
        g.upsert_tecnologia(name=tech["name"], version=tech.get("version", ""))
        for vuln in entities["vulns"]:
            vk = vuln["name"].lower().replace(" ", "_")[:80]
            g.link_tech_to_vuln(tech_key=tk, vuln_key=vk)

    # Create explicit exploit chains from known chain pairs
    for vuln_a, vuln_b, label in entities["chains"]:
        ka = vuln_a.lower().replace(" ", "_")[:80]
        kb = vuln_b.lower().replace(" ", "_")[:80]
        g.link_vuln_to_vuln(ka, kb, label)


# ------------------------------------------------------------------ #
# Retroalimentação — add a single new report                          #
# ------------------------------------------------------------------ #

def add_report(
    title: str,
    url: str,
    content: str,
    platform: str = "",
    vuln_type: str = "",
    severity: str = "",
    program: str = "",
    rag=None,
) -> str:
    """
    Called after a new bounty is reported/disclosed.
    Adds to both 'bb_writeups' and 'bounty_reports' collections
    AND syncs entities to the Neo4j graph.
    """
    from rag.store import get_rag
    r = rag or get_rag()

    chunk = textwrap.dedent(f"""
        NEW BOUNTY REPORT (Retroalimentação): {title}
        URL: {url}
        Platform: {platform}
        Program: {program}
        Vulnerability type: {vuln_type}
        Severity: {severity}

        {content[:4000]}
    """).strip()

    meta = {
        "type":     "bounty_report",
        "source":   "user_submitted",
        "title":    title[:200],
        "url":      url,
        "vuln":     vuln_type[:100],
        "platform": platform,
        "severity": severity,
        "program":  program,
    }
    doc_id  = r.upsert("bb_writeups",    chunk, meta)
    doc_id2 = r.upsert("bounty_reports", chunk, meta)

    # Sync to Neo4j graph
    _sync_to_graph(doc_id, title, url, content, vuln_type, platform, severity)

    print(f"  Report added: {doc_id} / {doc_id2} (vector + graph)")
    return doc_id


# ------------------------------------------------------------------ #
# Main                                                                 #
# ------------------------------------------------------------------ #

def ingest_all_writeups(rag=None):
    from rag.store import get_rag
    r = rag or get_rag()

    print("[pentester.land]")
    _ingest_pentesterland(r)

    print("[awesome-bugbounty-writeups]")
    _ingest_awesome(r)

    print("[bugbountyhunting.com]")
    _ingest_bbhunting(r)


if __name__ == "__main__":
    sys.path.insert(0, str(RAG_DIR.parent))
    ingest_all_writeups()
    print("Done.")
