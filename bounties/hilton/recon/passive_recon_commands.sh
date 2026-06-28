#!/bin/bash
# Hilton Bug Bounty — Passive Recon Pipeline
# UA OBRIGATÓRIO: HackerOne adicionado ao User-Agent
# NUNCA exceder 100 req/min por site

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 HackerOne"
OUTDIR="/home/altave/.bughunter/bounties/hilton/recon"

echo "[*] Hilton Passive Recon — $(date)"
echo "[*] Output: $OUTDIR"

# ─── 1. Subdomain Enumeration ─────────────────────────────────────────────────
echo "[+] Subdomain enum..."
subfinder -d hilton.com -all -recursive -silent -o "$OUTDIR/subs_subfinder.txt" 2>/dev/null &
amass enum -passive -d hilton.com -o "$OUTDIR/subs_amass.txt" 2>/dev/null &
wait

curl -s "https://crt.sh/?q=%.hilton.com&output=json" | \
  python3 -c "import sys,json; [print(n) for e in json.load(sys.stdin) for n in e['name_value'].split('\n')]" 2>/dev/null | \
  sort -u > "$OUTDIR/subs_crt.txt"

cat "$OUTDIR"/subs_*.txt | sort -u | \
  grep -v -E "^(eis|pim|jobs|onqinsider|hiltonnet|guestfeedback)\.(hilton\.com)" | \
  grep -v "hiltongrandvacations\|hgv\|hiltonhotels\.jp" > "$OUTDIR/subs_all.txt"

echo "[+] Total subs: $(wc -l < $OUTDIR/subs_all.txt)"

# ─── 2. DNS Resolution ─────────────────────────────────────────────────────────
echo "[+] DNS resolution..."
dnsx -l "$OUTDIR/subs_all.txt" -a -cname -resp -silent -o "$OUTDIR/resolved.txt" 2>/dev/null

# Dangling CNAME candidates (subdomain takeover)
echo "[+] Dangling CNAMEs..."
grep "CNAME" "$OUTDIR/resolved.txt" | \
  grep -v "hilton\.\(com\|io\|net\|org\)" | \
  tee "$OUTDIR/dangling_cname.txt"

# Filter out Rackspace IPs (known OOS)
# Rackspace ranges: 104.130.x.x, 198.101.x.x, 162.242.x.x, 72.3.x.x, 50.56.x.x
cat "$OUTDIR/resolved.txt" | grep -v -E "(104\.130\.|198\.101\.|162\.242\.|72\.3\.|50\.56\.)" > "$OUTDIR/resolved_in_scope.txt"

# ─── 3. HTTP Probing ────────────────────────────────────────────────────────────
echo "[+] HTTP probing..."
httpx -l "$OUTDIR/resolved_in_scope.txt" \
  -title -tech-detect -status-code -follow-redirects \
  -H "User-Agent: $UA" \
  -silent -o "$OUTDIR/live_hosts.txt" 2>/dev/null

echo "[+] Live hosts: $(wc -l < $OUTDIR/live_hosts.txt)"

# ─── 4. Historical URL Discovery ────────────────────────────────────────────────
echo "[+] Historical URLs (gau + wayback)..."
gau --subs hilton.com 2>/dev/null | sort -u > "$OUTDIR/gau_urls.txt" &
waybackurls hilton.com 2>/dev/null | sort -u > "$OUTDIR/wayback_urls.txt" &
wait

cat "$OUTDIR/gau_urls.txt" "$OUTDIR/wayback_urls.txt" | sort -u > "$OUTDIR/all_urls.txt"

# Filter interesting endpoints
grep -iE "(login|auth|oauth|sso|reset|password|account|member|honors|api)" \
  "$OUTDIR/all_urls.txt" | sort -u > "$OUTDIR/auth_urls.txt"

grep "?" "$OUTDIR/all_urls.txt" | sort -u > "$OUTDIR/param_urls.txt"

grep -oE "https://[a-zA-Z0-9._-]+\.(hilton|hhonors)\.(com|io)/[a-zA-Z0-9/_-]+" \
  "$OUTDIR/all_urls.txt" | sort -u > "$OUTDIR/api_endpoints.txt"

echo "[+] Auth-related URLs: $(wc -l < $OUTDIR/auth_urls.txt)"
echo "[+] Parametric URLs: $(wc -l < $OUTDIR/param_urls.txt)"

# ─── 5. JavaScript Bundle Analysis ──────────────────────────────────────────────
echo "[+] JS bundle analysis..."

# Fetch hilton.com and extract JS bundle URLs
curl -sA "$UA" "https://www.hilton.com/en/hilton-honors/join/" | \
  grep -oE '/_next/static/[^"]+\.js' | sort -u > "$OUTDIR/js_bundles.txt"

mkdir -p "$OUTDIR/js/"
while read jsfile; do
  fname=$(echo "$jsfile" | tr '/' '_')
  curl -sA "$UA" "https://www.hilton.com$jsfile" > "$OUTDIR/js/$fname" 2>/dev/null
done < "$OUTDIR/js_bundles.txt"

# Search for secrets in all JS files
echo "--- API Keys / Tokens ---" > "$OUTDIR/js_secrets.txt"
grep -rhoE '(apikey|api_key|client_secret|clientSecret|AUTH_TOKEN|HONORS)["\s]*[=:]["\s]*["\x27][^"\x27]{8,}["\x27]' \
  "$OUTDIR/js/" 2>/dev/null | sort -u >> "$OUTDIR/js_secrets.txt"

echo "--- JWTs ---" >> "$OUTDIR/js_secrets.txt"
grep -rhoE '"[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"' \
  "$OUTDIR/js/" 2>/dev/null | sort -u >> "$OUTDIR/js_secrets.txt"

echo "--- API Endpoints ---" >> "$OUTDIR/js_secrets.txt"
grep -rhoE "https://[a-zA-Z0-9._/-]+/api/[a-zA-Z0-9./_-]+" \
  "$OUTDIR/js/" 2>/dev/null | sort -u >> "$OUTDIR/js_secrets.txt"

echo "--- Hilton Honors API Base URLs ---" >> "$OUTDIR/js_secrets.txt"
grep -rhoE "https://[a-z0-9._-]*(honors|hhonors|hilton)[a-z0-9._-]*\.(com|io|net)" \
  "$OUTDIR/js/" 2>/dev/null | sort -u >> "$OUTDIR/js_secrets.txt"

cat "$OUTDIR/js_secrets.txt"

# ─── 6. GitHub Dorking ──────────────────────────────────────────────────────────
echo "[+] GitHub dorks (manual — run in browser):"
cat << 'DORKS'
Search these on GitHub:
  site:github.com "hilton.com" "api_key"
  site:github.com "hhonors" "secret"
  site:github.com "hiltonhonors" apikey OR token
  site:github.com filename:.env "hilton"
  site:github.com "hilton" "client_secret"
DORKS

# ─── 7. Shodan/Censys for CIDR ranges ───────────────────────────────────────────
echo "[+] CIDR probe commands (manual execution):"
cat << 'CIDR'
# 167.187.0.0/16 — most active (37 resolved reports)
# Quick HTTP scan:
nmap -p 80,443,8080,8443,8888,3000,4000 --open --min-rate 500 \
  -H "User-Agent: HackerOne" \
  167.187.0.0/16 -oG - | grep "open" | awk '{print $2}' > /tmp/hilton_cidr_open.txt

# Shodan search (if API available):
shodan search 'net:167.187.0.0/16 http.title:"Hilton"' --fields ip_str,port,http.title
CIDR

echo "[*] Passive recon complete!"
echo "[*] Check $OUTDIR/ for results"
echo ""
echo "NEXT STEPS:"
echo "1. Review subs_all.txt for interesting subdomains (supplier, admin, api, staging)"
echo "2. Review dangling_cname.txt for takeover opportunities"
echo "3. Review live_hosts.txt for interesting apps"
echo "4. Review js_secrets.txt for API keys/endpoints"
echo "5. Review auth_urls.txt for authentication endpoints to test"
