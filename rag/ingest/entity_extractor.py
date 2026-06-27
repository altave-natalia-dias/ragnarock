"""
Entity Extractor — extracts structured entities from writeup text
sem dependência de LLM. Puro regex + dicionários curados.

Extrai:
  - CVEs (CVE-YYYY-NNNNN)
  - CWEs (CWE-NNN)
  - MITRE technique IDs (T1234, T1234.001)
  - Tecnologias (Node.js, React, Laravel, etc.)
  - Tipos de vulnerabilidade (IDOR, XSS, SQLi, SSRF, etc.)
  - Severidade (CRITICAL/HIGH/MEDIUM/LOW)
  - Cadeias de exploit (vuln A → vuln B patterns)
"""
from __future__ import annotations
import re

# ── Patterns ───────────────────────────────────────────────────────── #

RE_CVE       = re.compile(r'CVE-\d{4}-\d{4,7}', re.I)
RE_CWE       = re.compile(r'CWE-\d{2,4}', re.I)
RE_TECHNIQUE = re.compile(r'\bT\d{4}(?:\.\d{3})?\b')
RE_SEVERITY  = re.compile(
    r'\b(CRITICAL|HIGH|MEDIUM|LOW|P1|P2|P3|P4)\b', re.I
)
RE_CHAIN     = re.compile(
    r'(?:chain|leading to|escalat|pivot|combined with|then|→|->)\s+([A-Z][a-z\-]+)',
    re.I,
)

# ── Technology Dictionary ──────────────────────────────────────────── #
# (name_in_text, canonical_name, version_pattern)
TECH_PATTERNS: list[tuple[str, str]] = [
    # Languages
    (r'node\.?js(?:\s+v?(\d[\d.]+))?',      "Node.js"),
    (r'python(?:\s+(\d[\d.]+))?',            "Python"),
    (r'php(?:\s+(\d[\d.]+))?',               "PHP"),
    (r'ruby(?:\s+on\s+rails)?(?:\s+(\d[\d.]+))?', "Ruby/Rails"),
    (r'java(?:\s+(\d[\d.]+))?',              "Java"),
    (r'golang|go\s+(\d[\d.]+)',              "Go"),
    (r'rust(?:\s+(\d[\d.]+))?',              "Rust"),
    (r'\.net(?:\s+(\d[\d.]+))?',             ".NET"),
    # Frameworks
    (r'express(?:\.js)?(?:\s+v?(\d[\d.]+))?', "Express"),
    (r'laravel(?:\s+(\d[\d.]+))?',           "Laravel"),
    (r'django(?:\s+(\d[\d.]+))?',            "Django"),
    (r'flask(?:\s+(\d[\d.]+))?',             "Flask"),
    (r'spring(?:\s+boot)?(?:\s+(\d[\d.]+))?', "Spring Boot"),
    (r'rails(?:\s+(\d[\d.]+))?',             "Rails"),
    (r'next\.?js(?:\s+v?(\d[\d.]+))?',       "Next.js"),
    (r'nuxt(?:\s+(\d[\d.]+))?',              "Nuxt"),
    (r'react(?:\s+(\d[\d.]+))?',             "React"),
    (r'angular(?:\s+(\d[\d.]+))?',           "Angular"),
    (r'vue(?:\.js)?(?:\s+v?(\d[\d.]+))?',    "Vue.js"),
    (r'fastapi(?:\s+(\d[\d.]+))?',           "FastAPI"),
    (r'gin(?:\s+(\d[\d.]+))?',               "Gin"),
    # Databases
    (r'mysql(?:\s+(\d[\d.]+))?',             "MySQL"),
    (r'postgresql|postgres(?:\s+(\d[\d.]+))?', "PostgreSQL"),
    (r'mongodb(?:\s+(\d[\d.]+))?',           "MongoDB"),
    (r'redis(?:\s+(\d[\d.]+))?',             "Redis"),
    (r'elasticsearch(?:\s+(\d[\d.]+))?',     "Elasticsearch"),
    (r'cassandra(?:\s+(\d[\d.]+))?',         "Cassandra"),
    (r'dynamodb',                             "DynamoDB"),
    (r'firebase',                             "Firebase"),
    # Message queues / Observability
    (r'kafka(?:\s+(\d[\d.]+))?',             "Kafka"),
    (r'rabbitmq(?:\s+(\d[\d.]+))?',          "RabbitMQ"),
    (r'grafana(?:\s+(\d[\d.]+))?',           "Grafana"),
    (r'prometheus(?:\s+(\d[\d.]+))?',        "Prometheus"),
    (r'kibana(?:\s+(\d[\d.]+))?',            "Kibana"),
    # Cloud
    (r'aws\s+lambda',                         "AWS Lambda"),
    (r'aws\s+s3',                             "AWS S3"),
    (r'kubernetes|k8s',                       "Kubernetes"),
    (r'docker(?:\s+(\d[\d.]+))?',            "Docker"),
    (r'nginx(?:\s+(\d[\d.]+))?',             "Nginx"),
    (r'apache(?:\s+(\d[\d.]+))?',            "Apache"),
    (r'iis(?:\s+(\d[\d.]+))?',               "IIS"),
    (r'cloudflare',                           "Cloudflare"),
    (r'graphql',                              "GraphQL"),
    (r'grpc',                                 "gRPC"),
    (r'wordpress(?:\s+(\d[\d.]+))?',         "WordPress"),
    (r'drupal(?:\s+(\d[\d.]+))?',            "Drupal"),
    (r'jira(?:\s+(\d[\d.]+))?',              "Jira"),
    (r'confluence(?:\s+(\d[\d.]+))?',        "Confluence"),
    (r'sharepoint',                           "SharePoint"),
    (r'jenkins(?:\s+(\d[\d.]+))?',           "Jenkins"),
    (r'gitlab(?:\s+(\d[\d.]+))?',            "GitLab"),
    (r'github\s+actions?',                   "GitHub Actions"),
    (r'terraform',                            "Terraform"),
    (r'jwt|json web token',                  "JWT"),
    (r'oauth(?:\s+2\.0)?',                   "OAuth"),
    (r'saml',                                 "SAML"),
    (r'graphql',                              "GraphQL"),
]

# ── Vulnerability Types ────────────────────────────────────────────── #
VULN_PATTERNS: list[tuple[str, str, str]] = [
    # (pattern, canonical_name, typical_severity)
    (r'\bRCE\b|remote code execut',            "RCE",                 "CRITICAL"),
    (r'\bsql\s*inject',                         "SQLi",                "HIGH"),
    (r'\bnosql\s*inject',                       "NoSQLi",              "HIGH"),
    (r'\bXXE\b|xml external entit',             "XXE",                 "HIGH"),
    (r'\bSSRF\b|server.side request forg',      "SSRF",                "HIGH"),
    (r'\bSST[Ii]\b|server.side template',       "SSTI",                "HIGH"),
    (r'\bIDD?OR\b|insecure direct object',      "IDOR",                "HIGH"),
    (r'\bXSS\b|cross.site script',              "XSS",                 "MEDIUM"),
    (r'\bCSRF\b|cross.site request forg',       "CSRF",                "MEDIUM"),
    (r'\bcors\b|cross.origin',                  "CORS",                "MEDIUM"),
    (r'\bauthentication bypass\b',              "Auth Bypass",         "CRITICAL"),
    (r'\bprivilege escalat',                    "Privilege Escalation","HIGH"),
    (r'\baccount takeover\b|ATO\b',             "ATO",                 "CRITICAL"),
    (r'\bopen redirect\b',                      "Open Redirect",       "MEDIUM"),
    (r'\bpath traversal\b|directory traversal', "Path Traversal",      "HIGH"),
    (r'\bfile upload\b|unrestricted upload',    "File Upload",         "HIGH"),
    (r'\bdeserial',                             "Deserialization",     "CRITICAL"),
    (r'\bjwt\b.*?(bypass|attack|forge|none|alg)', "JWT Attack",        "HIGH"),
    (r'\bprototype pollut',                     "Prototype Pollution", "HIGH"),
    (r'\brace condition\b',                     "Race Condition",      "HIGH"),
    (r'\bhttp.*smuggl',                         "HTTP Smuggling",      "CRITICAL"),
    (r'\bcache\s*poison',                       "Cache Poisoning",     "HIGH"),
    (r'\bsubdomain\s*takeover',                 "Subdomain Takeover",  "HIGH"),
    (r'\bmass\s*assign',                        "Mass Assignment",     "HIGH"),
    (r'\bcommand\s*inject|OS inject',           "Command Injection",   "CRITICAL"),
    (r'\bldap\s*inject',                        "LDAP Injection",      "HIGH"),
    (r'\bxml\s*inject',                         "XML Injection",       "HIGH"),
    (r'\bclickjack',                            "Clickjacking",        "LOW"),
    (r'\bhost\s*header\s*inject',               "Host Header Injection","MEDIUM"),
    (r'\bbrute\s*force\b|rate\s*limit',         "Rate Limit Bypass",   "MEDIUM"),
    (r'\bmfa\s*bypass\b|2fa\s*bypass',          "MFA Bypass",          "HIGH"),
    (r'\boauth\b.*?(bypass|flaw|attack|misconfigur)', "OAuth Flaw",    "HIGH"),
    (r'\bpassword\s*reset\b.*?(bypass|flaw|token)', "Password Reset Flaw","HIGH"),
    (r'\bsecret\b.*?(leak|expos|found)',        "Secret Exposure",     "HIGH"),
    (r'\bsource\s*code\b.*?(leak|expos)',       "Source Code Leak",    "HIGH"),
    (r'\binsecure\s*deserialization',           "Deserialization",     "CRITICAL"),
    (r'\bxxs\b|reflected\s+xss',               "Reflected XSS",       "MEDIUM"),
    (r'\bstored\s+xss|persistent\s+xss',       "Stored XSS",          "HIGH"),
    (r'\bdom\s+xss',                            "DOM XSS",             "MEDIUM"),
    (r'\bsql.*?blind',                          "Blind SQLi",          "HIGH"),
    (r'\bssrf.*?cloud|cloud.*?ssrf',            "Cloud SSRF",          "CRITICAL"),
    (r'\bimds\b|metadata.*?ssrf',              "SSRF→IMDS",           "CRITICAL"),
    (r'\bweb.*?shell',                          "Web Shell",           "CRITICAL"),
    (r'\blfi\b|local file inclus',              "LFI",                 "HIGH"),
    (r'\brfi\b|remote file inclus',             "RFI",                 "HIGH"),
    (r'\bxxe.*?ssrf|ssrf.*?xxe',               "XXE+SSRF Chain",      "CRITICAL"),
]

# Known exploit chain pairs (vuln A → vuln B)
CHAIN_PAIRS: list[tuple[str, str, str]] = [
    ("Open Redirect", "OAuth Flaw",      "open redirect → OAuth token theft"),
    ("IDOR",          "Privilege Escalation", "IDOR + mass assignment → privesc"),
    ("SSRF",          "SSRF→IMDS",       "SSRF → cloud metadata"),
    ("SSRF→IMDS",     "ATO",             "cloud credentials → full account takeover"),
    ("Stored XSS",    "ATO",             "XSS → session hijack → ATO"),
    ("Path Traversal","LFI",             "path traversal → local file inclusion"),
    ("LFI",           "RCE",             "LFI → log poisoning → RCE"),
    ("JWT Attack",    "Auth Bypass",     "JWT none/confusion → admin bypass"),
    ("Auth Bypass",   "ATO",             "auth bypass → account takeover"),
    ("Race Condition","ATO",             "race condition on tokens → takeover"),
    ("Mass Assignment","Privilege Escalation","mass assign role:admin → privesc"),
    ("XXE",           "SSRF",            "XXE external entity → SSRF"),
    ("Prototype Pollution", "RCE",       "prototype pollution → RCE via lodash"),
    ("HTTP Smuggling","ATO",             "HTTP smuggling → steal next user session"),
    ("Cache Poisoning","XSS",            "cache poisoning → stored XSS delivery"),
    ("Subdomain Takeover","ATO",         "subdomain takeover → cookie theft → ATO"),
]


# ── Extraction functions ───────────────────────────────────────────── #

def extract_cves(text: str) -> list[str]:
    return list(set(RE_CVE.findall(text)))


def extract_cwes(text: str) -> list[str]:
    return list(set(RE_CWE.findall(text)))


def extract_techniques(text: str) -> list[str]:
    return list(set(RE_TECHNIQUE.findall(text)))


def extract_severity(text: str) -> str:
    """Return the highest severity found in text."""
    order = {"CRITICAL": 4, "HIGH": 3, "P1": 4, "P2": 3,
             "MEDIUM": 2, "P3": 2, "LOW": 1, "P4": 1}
    found = RE_SEVERITY.findall(text.upper())
    if not found:
        return "MEDIUM"
    return max(found, key=lambda x: order.get(x.upper(), 0))


def extract_technologies(text: str) -> list[dict]:
    """
    Returns list of {name, version, pattern_matched}.
    Deduplicates by canonical name.
    """
    seen: set[str] = set()
    results: list[dict] = []
    tl = text.lower()
    for pat, canonical in TECH_PATTERNS:
        m = re.search(pat, tl, re.I)
        if m and canonical not in seen:
            seen.add(canonical)
            version = m.group(1) if m.lastindex else ""
            results.append({"name": canonical, "version": version or ""})
    return results


def extract_vuln_types(text: str) -> list[dict]:
    """
    Returns list of {name, severity, matched_text}.
    Deduplicates by name.
    """
    seen: set[str] = set()
    results: list[dict] = []
    for pat, name, default_sev in VULN_PATTERNS:
        if re.search(pat, text, re.I) and name not in seen:
            seen.add(name)
            results.append({"name": name, "severity": default_sev})
    return results


def extract_chains(text: str, found_vulns: list[str]) -> list[tuple[str, str, str]]:
    """
    Return list of (vuln_a, vuln_b, label) chains detected from text
    AND from known chain pairs matching found vulns.
    """
    chains: list[tuple[str, str, str]] = []
    found_set = set(found_vulns)
    for a, b, label in CHAIN_PAIRS:
        if a in found_set and b in found_set:
            chains.append((a, b, label))
        elif a in found_set:
            # Still suggest the chain even if B wasn't found — it's a known path
            chains.append((a, b, f"{label} [inferred]"))
    return chains


def extract_all(text: str, title: str = "") -> dict:
    """
    Full extraction: CVEs, CWEs, techniques, technologies, vuln types, chains.
    Returns structured dict ready for graph ingestion.
    """
    full = f"{title} {text}"
    vulns  = extract_vuln_types(full)
    vnames = [v["name"] for v in vulns]
    return {
        "cves":       extract_cves(full),
        "cwes":       extract_cwes(full),
        "techniques": extract_techniques(full),
        "severity":   extract_severity(full),
        "techs":      extract_technologies(full),
        "vulns":      vulns,
        "chains":     extract_chains(full, vnames),
    }
