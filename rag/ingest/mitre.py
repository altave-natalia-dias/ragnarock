"""
MITRE ATT&CK (Enterprise + ICS + Mobile) + MITRE D3FEND ingestion.

Sources:
  ATT&CK STIX: https://github.com/mitre/cti (raw JSON)
  D3FEND:       https://d3fend.mitre.org/api/d3fend-full-mappings.json

Run: python3 -m rag.ingest.mitre
"""
from __future__ import annotations
import sys, json, time, textwrap
from pathlib import Path

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

import requests

RAG_DIR  = Path(__file__).parent.parent
DATA_DIR = RAG_DIR / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ATTACK_URLS = {
    "enterprise": "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json",
    "ics":        "https://raw.githubusercontent.com/mitre/cti/master/ics-attack/ics-attack.json",
    "mobile":     "https://raw.githubusercontent.com/mitre/cti/master/mobile-attack/mobile-attack.json",
}
D3FEND_URL  = "https://d3fend.mitre.org/ontologies/d3fend.csv"

HEADERS = {"User-Agent": "BountyRAG/1.0 (+https://github.com/altave)"}


# ------------------------------------------------------------------ #
# Download helpers                                                     #
# ------------------------------------------------------------------ #

def _fetch(url: str, cache_path: Path, max_age_h: int = 168) -> dict:
    """Return parsed JSON, using cache file if fresh enough."""
    if cache_path.exists():
        age_h = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_h < max_age_h:
            try:
                return json.loads(cache_path.read_text())
            except Exception:
                pass

    print(f"  Downloading {url} ...", flush=True)
    r = requests.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    data = r.json()
    cache_path.write_text(json.dumps(data))
    return data


def _fetch_text(url: str, cache_path: Path, max_age_h: int = 168) -> str:
    """Return raw text, using cache file if fresh enough."""
    if cache_path.exists():
        age_h = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_h < max_age_h:
            return cache_path.read_text()

    print(f"  Downloading {url} ...", flush=True)
    r = requests.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    cache_path.write_text(r.text)
    return r.text


# ------------------------------------------------------------------ #
# ATT&CK                                                               #
# ------------------------------------------------------------------ #

def _parse_attack(domain: str, stix: dict) -> list[tuple[str, dict]]:
    """
    Extract techniques + subtechniques from a STIX bundle.
    Returns list of (text_chunk, metadata).
    """
    items: list[tuple[str, dict]] = []
    obj_map: dict[str, dict] = {o["id"]: o for o in stix.get("objects", [])}

    for obj in stix.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("x_mitre_deprecated") or obj.get("revoked"):
            continue

        name        = obj.get("name", "")
        desc        = obj.get("description", "")[:2000]
        ext_refs    = obj.get("external_references", [])
        tech_id     = next((r["external_id"] for r in ext_refs if r.get("source_name") == "mitre-attack"), "")
        url         = next((r.get("url","") for r in ext_refs if r.get("source_name") == "mitre-attack"), "")
        tactics     = [p["phase_name"] for p in obj.get("kill_chain_phases", [])]
        platforms   = obj.get("x_mitre_platforms", [])
        permissions = obj.get("x_mitre_permissions_required", [])
        detection   = obj.get("x_mitre_detection", "")[:1000]
        data_sources= obj.get("x_mitre_data_sources", [])
        is_sub      = obj.get("x_mitre_is_subtechnique", False)

        chunk = textwrap.dedent(f"""
            MITRE ATT&CK {domain.upper()} — {tech_id}: {name}
            Tactics: {', '.join(tactics)}
            Platforms: {', '.join(platforms)}
            Permissions: {', '.join(permissions)}
            Data sources: {', '.join(str(d) for d in data_sources)}
            URL: {url}

            Description:
            {desc}

            Detection:
            {detection}
        """).strip()

        items.append((chunk, {
            "type":       "mitre_attack",
            "domain":     domain,
            "tech_id":    tech_id,
            "name":       name,
            "tactics":    json.dumps(tactics),
            "platforms":  json.dumps(platforms),
            "is_sub":     str(is_sub),
            "url":        url,
        }))

    print(f"    {domain}: {len(items)} techniques parsed")
    return items


def ingest_attack(rag=None):
    from rag.store import get_rag
    r = rag or get_rag()
    all_items: list[tuple[str, dict]] = []

    for domain, url in ATTACK_URLS.items():
        cache = DATA_DIR / f"mitre_attack_{domain}.json"
        stix  = _fetch(url, cache)
        items = _parse_attack(domain, stix)
        all_items.extend(items)

    print(f"  Upserting {len(all_items)} ATT&CK records …", flush=True)
    r.upsert_batch("mitre_attack", all_items)
    print("  ATT&CK done.")


# ------------------------------------------------------------------ #
# D3FEND                                                               #
# ------------------------------------------------------------------ #

def ingest_defend(rag=None):
    from rag.store import get_rag
    import csv, io
    r = rag or get_rag()

    cache = DATA_DIR / "mitre_d3fend.csv"
    csv_text = _fetch_text(D3FEND_URL, cache)

    items: list[tuple[str, dict]] = []
    reader = csv.DictReader(io.StringIO(csv_text))

    seen: set[str] = set()
    for row in reader:
        d_id    = row.get("ID", "").strip()
        tactic  = row.get("D3FEND Tactic", "").strip()
        tech_l0 = row.get("D3FEND Technique Level 0", "").strip()
        tech_l1 = row.get("D3FEND Technique Level 1", "").strip()
        name    = row.get("D3FEND Technique", "").strip() or tech_l0 or tech_l1
        definition = row.get("Definition", "").strip()

        if not d_id or not name:
            continue
        if d_id in seen:
            continue
        seen.add(d_id)

        chunk = textwrap.dedent(f"""
            MITRE D3FEND — {name}
            D3FEND ID: {d_id}
            Tactic: {tactic}
            Technique Level 0: {tech_l0}
            Technique Level 1: {tech_l1}

            Definition:
            {definition[:1500]}
        """).strip()

        items.append((chunk, {
            "type":    "mitre_defend",
            "d3_id":   d_id,
            "d_label": name[:200],
            "tactic":  tactic,
        }))

    if not items:
        print("  D3FEND: no entries parsed from CSV, storing header row")
        items = [(f"MITRE D3FEND CSV (raw):\n{csv_text[:3000]}", {"type": "mitre_defend", "d3_id": "raw"})]

    print(f"  Upserting {len(items)} D3FEND records …", flush=True)
    r.upsert_batch("mitre_defend", items)
    print("  D3FEND done.")


# ------------------------------------------------------------------ #
# CLI entry                                                            #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    sys.path.insert(0, str(RAG_DIR.parent))
    print("[MITRE ATT&CK ingestion]")
    ingest_attack()
    print("\n[MITRE D3FEND ingestion]")
    ingest_defend()
    print("\nDone.")
