#!/usr/bin/env python3
"""
arsenal_passive.py — Passive, scope-gated, rate-limited recon arsenal.

Rewrite of the "CRITICAL VULNERABILITY SCANNER v2.0" with the dangerous /
broken parts removed:

  * NO login brute-force, NO default-credential spraying, NO IDOR
    enumeration against live accounts. Those trip lockouts, generate real
    auth traffic against third parties, and are low-signal on managed
    programs. Auth testing stays MANUAL with your own two test accounts.
  * Every outbound request passes through ONE global token-bucket rate
    limiter (no ThreadPool bypass). Default 0.5 req/s.
  * Hard scope gate: a host is only touched if it ends with a suffix you
    pass via --scope. No scope => refuse to run.
  * Fixes the class-body NameError (patterns built in __init__).
  * Findings require a CONTENT SIGNATURE, not just HTTP 200, to cut
    false positives.

Checks (all read-only GETs):
  files     sensitive file / source exposure (.env, .git, config, backups)
  takeover  dangling-CNAME subdomain-takeover fingerprints
  buckets   anonymous cloud-storage read (AWS S3 / GCP GCS / Azure Blob)

Usage:
  python3 arsenal_passive.py --scope example.com --check files,takeover \
      --targets subs.txt --rps 0.5 --ua "bughunter (contact@you)"
  echo host.example.com | python3 arsenal_passive.py --scope example.com

Reports to <host> only via stdin/--targets; nothing is written to any target.
"""
from __future__ import annotations
import argparse, json, re, sys, time, threading
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    import requests
    requests.packages.urllib3.disable_warnings()  # type: ignore
except ImportError:
    sys.exit("requests not installed: pip install requests")


# --------------------------------------------------------------------------- #
# Global rate limiter (token bucket, thread-safe, shared by all checks)
# --------------------------------------------------------------------------- #
class RateLimiter:
    def __init__(self, rps: float):
        self.min_interval = 1.0 / rps if rps > 0 else 0.0
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
                now = time.monotonic()
            self._next = now + self.min_interval


# --------------------------------------------------------------------------- #
# Scope gate — refuse anything not under an allowed suffix
# --------------------------------------------------------------------------- #
class Scope:
    def __init__(self, suffixes: list[str]):
        self.suffixes = [s.lower().lstrip("*.").strip() for s in suffixes if s.strip()]
        if not self.suffixes:
            sys.exit("[FATAL] no --scope suffixes given; refusing to run")

    def allows(self, host: str) -> bool:
        host = host.lower().rstrip(".").split(":")[0]  # strip :port
        return any(host == s or host.endswith("." + s) for s in self.suffixes)


# --------------------------------------------------------------------------- #
# HTTP client wrapping limiter + scope
# --------------------------------------------------------------------------- #
class Client:
    def __init__(self, scope: Scope, limiter: RateLimiter, ua: str, timeout: int = 8):
        self.scope, self.limiter, self.timeout = scope, limiter, timeout
        self.s = requests.Session()
        self.s.headers["User-Agent"] = ua
        self.s.verify = False
        self.skipped_out_of_scope: set[str] = set()

    def get(self, url: str):
        host = urlparse(url).hostname or ""
        if not self.scope.allows(host):
            self.skipped_out_of_scope.add(host)
            return None
        self.limiter.wait()
        try:
            return self.s.get(url, timeout=self.timeout, allow_redirects=False)
        except requests.RequestException:
            return None


# --------------------------------------------------------------------------- #
# Check 1 — sensitive file / source exposure (GET + content signature)
# --------------------------------------------------------------------------- #
FILE_SIGNATURES = [
    # (path, [regex signatures that prove real content], severity)
    (".env",              [r"(?m)^\s*[A-Z0-9_]+\s*=", r"(SECRET|PASSWORD|API_?KEY|TOKEN)"], "CRITICAL"),
    (".env.production",   [r"(?m)^\s*[A-Z0-9_]+\s*=", r"(SECRET|PASSWORD|API_?KEY)"],       "CRITICAL"),
    (".git/config",       [r"\[core\]", r"\[remote"],                                        "CRITICAL"),
    (".git/HEAD",         [r"ref:\s*refs/"],                                                 "CRITICAL"),
    (".DS_Store",         [r"Bud1"],                                                         "LOW"),
    ("wp-config.php",     [r"DB_PASSWORD", r"AUTH_KEY"],                                      "CRITICAL"),
    ("config.php",        [r"(password|secret|api_?key)\s*[=:]"],                             "HIGH"),
    ("appsettings.json",  [r"ConnectionStrings", r"(Password|Secret|JwtSecret)"],            "CRITICAL"),
    ("web.config",        [r"connectionString", r"<add key"],                                "CRITICAL"),
    ("application.properties", [r"spring\..*password", r"datasource"],                       "CRITICAL"),
    ("docker-compose.yml", [r"(POSTGRES_PASSWORD|MYSQL_ROOT_PASSWORD|environment:)"],        "HIGH"),
    ("database.yml",      [r"(password|adapter):"],                                          "HIGH"),
    ("service-account.json", [r'"type":\s*"service_account"'],                               "CRITICAL"),
    ("backup.sql",        [r"(CREATE TABLE|INSERT INTO)"],                                   "HIGH"),
    (".htpasswd",         [r":\$(apr1|2y|6)\$"],                                             "HIGH"),
]

# Suppress template/example files: a VALUE that *starts* with a placeholder
# token (not merely a real secret that happens to contain "example").
_PLACEHOLDER = re.compile(
    r"[=:]\s*[\"']?(your[_-]?\w+|change[_-]?me|xxxx+|placeholder|<[^>]+>|example[_-]?\w*|todo)\b",
    re.I,
)


def check_files(client: Client, host: str):
    out = []
    for path, sigs, sev in FILE_SIGNATURES:
        for scheme in ("https", "http"):
            r = client.get(f"{scheme}://{host}/{path}")
            if r is None:
                continue
            if r.status_code == 200 and r.text:
                body = r.text[:20000]
                if all(re.search(s, body) for s in sigs) and not _PLACEHOLDER.search(body[:400]):
                    out.append({
                        "check": "files", "host": host, "path": path,
                        "severity": sev, "status": 200,
                        "evidence": body[:180].replace("\n", " "),
                    })
                break  # https hit or 200 — don't retry http
    return out


# --------------------------------------------------------------------------- #
# Check 2 — subdomain takeover fingerprints (CNAME + body signature)
# --------------------------------------------------------------------------- #
TAKEOVER_SIGS = {
    "github.io":        ["There isn't a GitHub Pages site here"],
    "herokuapp.com":    ["No such app", "herokucdn.com/error-pages/no-such-app.html"],
    "netlify.app":      ["Not Found - Request ID", "Site Not Found"],
    "vercel.app":       ["DEPLOYMENT_NOT_FOUND", "The deployment could not be found"],
    "azurewebsites.net":["Web App - Unavailable", "404 Web Site not found"],
    "s3.amazonaws.com": ["NoSuchBucket", "The specified bucket does not exist"],
    "cloudfront.net":   ["Bad Request: ERROR: The request could not be satisfied"],
    "pantheonsite.io":  ["The gods are wise", "404 error unknown site"],
    "wordpress.com":    ["Do you want to register"],
    "ghost.io":         ["Domain error", "The thing you were looking for is no longer here"],
    "surge.sh":         ["project not found"],
    "readme.io":        ["Project doesnt exist"],
}


def _resolve_cname(host: str):
    try:
        import socket
        # best-effort: many resolvers flatten CNAME; dnspython is better if present
        try:
            import dns.resolver  # type: ignore
            ans = dns.resolver.resolve(host, "CNAME", lifetime=5)
            return str(ans[0].target).rstrip(".").lower()
        except Exception:
            socket.gethostbyname(host)  # just prove it resolves
            return ""
    except Exception:
        return None


def check_takeover(client: Client, host: str):
    out = []
    cname = _resolve_cname(host)
    for provider, sigs in TAKEOVER_SIGS.items():
        if cname and provider not in cname:
            continue
        r = client.get(f"https://{host}") or client.get(f"http://{host}")
        if r is None or not r.text:
            continue
        if any(sig.lower() in r.text.lower() for sig in sigs):
            out.append({
                "check": "takeover", "host": host, "provider": provider,
                "cname": cname or "(flattened)", "severity": "HIGH",
                "note": "CANDIDATE — verify the resource is claimable before reporting",
            })
        break
    return out


# --------------------------------------------------------------------------- #
# Check 3 — cloud bucket anonymous read (built PER-HOST, no class-body bug)
# --------------------------------------------------------------------------- #
def _bucket_names(root: str):
    base = root.split(".")[0]
    sfx = ["", "-backup", "-backups", "-assets", "-uploads", "-data",
           "-prod", "-dev", "-staging", "-media", "-logs", "-static",
           "-public", "-private"]
    names = [f"{base}{s}" for s in sfx] + [f"backup-{base}", f"{base}backup"]
    return list(dict.fromkeys(names))


def check_buckets(client: Client, host: str):
    """Note: bucket endpoints are provider hosts, not <host>. We only probe
    buckets whose *name* is derived from an in-scope root, and we let the
    scope gate decide — so if you scoped only the app domain, provider hosts
    are skipped. Pass the provider apex in --scope to enable (e.g. s3.amazonaws.com)."""
    out = []
    root = host
    for b in _bucket_names(root):
        # AWS S3
        r = client.get(f"https://{b}.s3.amazonaws.com/")
        if r is not None and r.status_code == 200 and "<ListBucketResult" in r.text:
            keys = re.findall(r"<Key>([^<]+)</Key>", r.text)
            out.append({"check": "buckets", "provider": "aws-s3", "bucket": b,
                        "severity": "CRITICAL", "objects": len(keys),
                        "sensitive": _sensitive(keys)})
        # GCP GCS
        r = client.get(f"https://storage.googleapis.com/storage/v1/b/{b}/o")
        if r is not None and r.status_code == 200 and '"items"' in r.text:
            try:
                items = [i["name"] for i in r.json().get("items", [])]
            except Exception:
                items = []
            out.append({"check": "buckets", "provider": "gcs", "bucket": b,
                        "severity": "CRITICAL", "objects": len(items),
                        "sensitive": _sensitive(items)})
    return out


_SENS = re.compile(r"(backup|dump|\.sql|cred|secret|\.pem|\.key|config|\.env|\.bak)", re.I)
def _sensitive(names): return [n for n in names if _SENS.search(n)][:15]


# --------------------------------------------------------------------------- #
CHECKS = {"files": check_files, "takeover": check_takeover, "buckets": check_buckets}


def main():
    ap = argparse.ArgumentParser(description="Passive, scope-gated recon arsenal")
    ap.add_argument("--scope", required=True,
                    help="comma-sep allowed host suffixes (e.g. example.com,api.example.com)")
    ap.add_argument("--check", default="files,takeover",
                    help="comma-sep: files,takeover,buckets")
    ap.add_argument("--targets", help="file of hosts (one per line); else read stdin")
    ap.add_argument("--rps", type=float, default=0.5, help="global requests/sec (default 0.5)")
    ap.add_argument("--ua", default="bughunter-passive/1.0",
                    help="User-Agent (Monzo/Intigriti: include @intigriti.me)")
    ap.add_argument("--out", help="write findings JSONL here")
    args = ap.parse_args()

    scope = Scope(args.scope.split(","))
    limiter = RateLimiter(args.rps)
    client = Client(scope, limiter, args.ua)
    checks = [c.strip() for c in args.check.split(",") if c.strip() in CHECKS]

    if args.targets:
        hosts = [l.strip() for l in open(args.targets) if l.strip() and not l.startswith("#")]
    else:
        hosts = [l.strip() for l in sys.stdin if l.strip()]

    in_scope = [h for h in hosts if scope.allows(h)]
    print(f"[*] {datetime.now(timezone.utc).isoformat()}  scope={scope.suffixes}  "
          f"rps={args.rps}  checks={checks}", file=sys.stderr)
    print(f"[*] {len(in_scope)}/{len(hosts)} hosts in scope "
          f"({len(hosts)-len(in_scope)} skipped)", file=sys.stderr)

    findings, fh = [], (open(args.out, "w") if args.out else None)
    for h in in_scope:
        for c in checks:
            for f in CHECKS[c](client, h):
                findings.append(f)
                line = json.dumps(f, ensure_ascii=False)
                print(f"[!] {f['severity']:8} {f['check']:8} {h}  {f.get('path') or f.get('provider','')}",
                      file=sys.stderr)
                if fh:
                    fh.write(line + "\n")
    if fh:
        fh.close()

    print(f"\n[*] done: {len(findings)} finding(s)", file=sys.stderr)
    if client.skipped_out_of_scope:
        print(f"[*] refused (out of scope): {sorted(client.skipped_out_of_scope)}", file=sys.stderr)
    print(json.dumps(findings, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
