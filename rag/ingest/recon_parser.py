"""
Recon Parser — lê output JSON de ferramentas (httpx, nuclei, subfinder, nmap)
e popula automaticamente os nós de infraestrutura no Neo4j.

Suporte:
  httpx   -json    → Subdominio + Endpoint + Tecnologia nodes
  nuclei  -json    → Vulnerabilidade nodes linkados à Tecnologia
  subfinder -json  → Subdominio nodes
  nmap    -oX      → Port/service data adicionada ao Subdominio
  katana  -json    → Endpoint nodes

Uso:
  python3 -m rag.ingest.recon_parser --target example.com \\
    --httpx     /tmp/httpx.json \\
    --nuclei    /tmp/nuclei.json \\
    --subfinder /tmp/subs.txt \\
    --nmap      /tmp/nmap.xml \\
    --katana    /tmp/katana.json
"""
from __future__ import annotations
import sys, json, re, argparse
from pathlib import Path
from urllib.parse import urlparse

RAG_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(RAG_DIR.parent))

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

from rag.graph_store import get_graph
from rag.ingest.entity_extractor import extract_technologies


# ── httpx JSON parser ─────────────────────────────────────────────── #

def parse_httpx(target: str, json_file: str | Path) -> int:
    """
    Parse httpx -json output.
    Each line is a JSON object with keys: url, host, ip, status_code, title, tech, ...
    """
    g   = get_graph()
    path = Path(json_file)
    if not path.exists():
        print(f"  [recon_parser] httpx file not found: {path}")
        return 0

    g.upsert_alvo(target)
    count = 0

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue

        url        = obj.get("url", obj.get("input", ""))
        host       = obj.get("host", obj.get("input", ""))
        ip         = obj.get("a", [obj.get("ip", "")])[0] if isinstance(obj.get("a"), list) else obj.get("ip", "")
        status     = obj.get("status_code", obj.get("status", 0))
        title      = obj.get("title", "")
        tech_list  = obj.get("tech", obj.get("technologies", []))
        webserver  = obj.get("webserver", "")
        cname      = obj.get("cname", "")

        if not host:
            continue

        # Upsert subdominio
        tech_names = [t.get("name", t) if isinstance(t, dict) else str(t) for t in tech_list]
        g.upsert_subdominio(
            fqdn=host, parent_domain=target,
            ip=ip, status=status, title=title, techs=tech_names,
        )

        # Upsert each technology
        for t in tech_list:
            name    = t.get("name", t) if isinstance(t, dict) else str(t)
            version = t.get("version", "") if isinstance(t, dict) else ""
            g.upsert_tecnologia(name=name, version=version, fqdn=host)

        if webserver:
            g.upsert_tecnologia(name=webserver, fqdn=host)

        count += 1

    print(f"  [httpx] {count} subdomínios importados para Neo4j")
    return count


# ── nuclei JSON parser ────────────────────────────────────────────── #

SEVERITY_MAP = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
    "info": "INFO",
    "unknown": "INFO",
}

NUCLEI_TACTIC_MAP = {
    "cve":              "initial-access",
    "misconfiguration": "defense-evasion",
    "exposure":         "discovery",
    "sqli":             "initial-access",
    "xss":              "execution",
    "ssrf":             "discovery",
    "rce":              "execution",
    "lfi":              "discovery",
    "auth-bypass":      "privilege-escalation",
    "default-credentials": "credential-access",
    "takeover":         "resource-development",
}

def parse_nuclei(target: str, json_file: str | Path) -> int:
    g    = get_graph()
    path = Path(json_file)
    if not path.exists():
        print(f"  [recon_parser] nuclei file not found: {path}")
        return 0

    g.upsert_alvo(target)
    count = 0

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue

        template_id = obj.get("template-id", obj.get("templateID", ""))
        name        = obj.get("info", {}).get("name", template_id)
        severity    = SEVERITY_MAP.get(
            obj.get("info", {}).get("severity", "medium").lower(), "MEDIUM"
        )
        tags        = obj.get("info", {}).get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        cve         = next((t for t in tags if t.upper().startswith("CVE-")), "")
        cwe         = obj.get("info", {}).get("classification", {}).get("cwe-id", "")
        host        = obj.get("host", obj.get("matched-at", ""))
        matched_at  = obj.get("matched-at", host)

        # Extract FQDN from matched URL
        try:
            fqdn = urlparse(matched_at).hostname or host
        except Exception:
            fqdn = host

        # Determine tactic from tags
        tactic = "initial-access"
        for tag in tags:
            t = tag.lower()
            if t in NUCLEI_TACTIC_MAP:
                tactic = NUCLEI_TACTIC_MAP[t]
                break

        # Upsert vuln
        vuln_key = cve or f"{template_id}:{host}"[:80]
        g.upsert_vulnerabilidade(
            name=name,
            cve=cve,
            cwe=str(cwe),
            severity=severity,
            tactic=tactic,
            description=f"Nuclei template: {template_id} matched at {matched_at}",
        )

        # Link subdominio to vuln via tech
        if fqdn:
            g.upsert_subdominio(fqdn=fqdn, parent_domain=target)
            # Create a generic tech node for this finding
            tech_name = next((t for t in tags if t not in ("cve", "nuclei", "network")), "generic")
            tkey = tech_name.lower().replace("-", "_")
            g.upsert_tecnologia(name=tech_name, fqdn=fqdn)
            g.link_tech_to_vuln(
                tech_key=f"{tech_name}:".rstrip(":"),
                vuln_key=vuln_key,
            )

        count += 1

    print(f"  [nuclei] {count} findings importados para Neo4j")
    return count


# ── subfinder / plain text subdomain list ────────────────────────────── #

def parse_subfinder(target: str, subs_file: str | Path) -> int:
    g    = get_graph()
    path = Path(subs_file)
    if not path.exists():
        print(f"  [recon_parser] subfinder file not found: {path}")
        return 0

    g.upsert_alvo(target)
    count = 0
    for line in path.read_text().splitlines():
        fqdn = line.strip().lower()
        if not fqdn or not fqdn.endswith(target):
            continue
        g.upsert_subdominio(fqdn=fqdn, parent_domain=target)
        count += 1

    print(f"  [subfinder] {count} subdomínios importados")
    return count


# ── katana JSON parser ─────────────────────────────────────────────── #

def parse_katana(target: str, json_file: str | Path) -> int:
    g    = get_graph()
    path = Path(json_file)
    if not path.exists():
        print(f"  [recon_parser] katana file not found: {path}")
        return 0

    g.upsert_alvo(target)
    count = 0

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            # plain URL
            url = line
            obj = {"request": {"endpoint": url}}

        req    = obj.get("request", {})
        url    = req.get("endpoint", req.get("url", ""))
        method = req.get("method", "GET")
        params_raw = req.get("query", {})

        if not url:
            continue

        try:
            parsed = urlparse(url)
            fqdn   = parsed.hostname or ""
            path_  = parsed.path or "/"
        except Exception:
            continue

        if not fqdn:
            continue

        params = list(params_raw.keys()) if isinstance(params_raw, dict) else []
        # Also extract from query string
        qs_params = re.findall(r'([a-zA-Z_]\w*)=', parsed.query or "")
        params = list(set(params + qs_params))

        g.upsert_subdominio(fqdn=fqdn, parent_domain=target)
        g.upsert_endpoint(
            path=path_[:200], fqdn=fqdn, method=method.upper(),
            params=params[:20],
        )
        count += 1

    print(f"  [katana] {count} endpoints importados")
    return count


# ── nmap XML parser ────────────────────────────────────────────────── #

def parse_nmap(target: str, xml_file: str | Path) -> int:
    try:
        import xml.etree.ElementTree as ET
    except ImportError:
        print("  [nmap] xml module not available")
        return 0

    g    = get_graph()
    path = Path(xml_file)
    if not path.exists():
        print(f"  [recon_parser] nmap file not found: {path}")
        return 0

    g.upsert_alvo(target)
    count = 0

    tree = ET.parse(str(path))
    root = tree.getroot()

    INTERESTING_PORTS = {
        3306: "MySQL",   5432: "PostgreSQL", 6379: "Redis",
        27017: "MongoDB", 9200: "Elasticsearch", 9300: "Elasticsearch",
        5601: "Kibana",  3000: "Grafana",   9090: "Prometheus",
        5672: "RabbitMQ", 9092: "Kafka",    2181: "ZooKeeper",
        6443: "Kubernetes API", 8443: "HTTPS",
        11211: "Memcached", 50070: "Hadoop HDFS",
    }

    for host in root.findall("host"):
        addr = host.find("address")
        ip   = addr.get("addr", "") if addr is not None else ""

        hostnames = host.find("hostnames")
        fqdn_el   = hostnames.find("hostname") if hostnames is not None else None
        fqdn      = fqdn_el.get("name", ip) if fqdn_el is not None else ip

        if not fqdn or not fqdn.endswith(target.lstrip(".")):
            fqdn = ip  # Use IP if no matching FQDN

        g.upsert_subdominio(fqdn=fqdn, parent_domain=target, ip=ip)

        for port in host.findall("ports/port"):
            portid   = int(port.get("portid", 0))
            state_el = port.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue

            service_el = port.find("service")
            service    = service_el.get("name", "") if service_el is not None else ""
            product    = service_el.get("product", "") if service_el is not None else ""
            version_   = service_el.get("version", "") if service_el is not None else ""

            # Map known interesting ports to technology nodes
            tech_name = INTERESTING_PORTS.get(portid, product or service)
            if tech_name:
                g.upsert_tecnologia(name=tech_name, version=version_, fqdn=fqdn)

            count += 1

    print(f"  [nmap] {count} ports/services importados")
    return count


# ── Convenience: parse all at once ───────────────────────────────────── #

def parse_all(
    target: str,
    httpx_file:     str | None = None,
    nuclei_file:    str | None = None,
    subfinder_file: str | None = None,
    katana_file:    str | None = None,
    nmap_file:      str | None = None,
) -> dict:
    results = {}
    if subfinder_file: results["subfinder"] = parse_subfinder(target, subfinder_file)
    if httpx_file:     results["httpx"]     = parse_httpx(target, httpx_file)
    if katana_file:    results["katana"]    = parse_katana(target, katana_file)
    if nuclei_file:    results["nuclei"]    = parse_nuclei(target, nuclei_file)
    if nmap_file:      results["nmap"]      = parse_nmap(target, nmap_file)
    return results


# ── CLI ────────────────────────────────────────────────────────────── #

def main():
    p = argparse.ArgumentParser(description="BountyRAG Recon Parser → Neo4j")
    p.add_argument("--target",     required=True, help="Root domain (e.g. example.com)")
    p.add_argument("--httpx",      default="",    help="httpx -json output file")
    p.add_argument("--nuclei",     default="",    help="nuclei -json output file")
    p.add_argument("--subfinder",  default="",    help="subfinder -o output file (one host per line)")
    p.add_argument("--katana",     default="",    help="katana -json output file")
    p.add_argument("--nmap",       default="",    help="nmap -oX XML output file")
    args = p.parse_args()

    print(f"[recon_parser] Target: {args.target}")
    results = parse_all(
        target=args.target,
        httpx_file=args.httpx or None,
        nuclei_file=args.nuclei or None,
        subfinder_file=args.subfinder or None,
        katana_file=args.katana or None,
        nmap_file=args.nmap or None,
    )
    total = sum(results.values())
    print(f"\n  Total: {total} artefatos importados para Neo4j")

    g = get_graph()
    stats = g.stats()
    print(f"\n  Graph stats: {stats}")


if __name__ == "__main__":
    main()
