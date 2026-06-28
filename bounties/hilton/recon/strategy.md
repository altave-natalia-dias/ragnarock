# Hilton — Estratégia de Ataque e Recon

## Análise do Programa (Intelligence Gathering)

### Sinais de Alta Oportunidade

```
SINAL 1: POST-based XSS explicitamente OOS
  → Eles recebem muitos e estão cansados
  → Oportunidade: DOM XSS / Reflected GET XSS / Stored XSS via campos de perfil
  → Menos competição porque hunters menos experientes só submitem POST XSS

SINAL 2: suppliersconnection.hilton.com CSRF em remediação
  → App tem práticas de segurança fracas (CSRF existe)
  → Outros vuln classes (IDOR, auth bypass, XSS) ainda em scope
  → Alvo rico porque está com dívida técnica de segurança

SINAL 3: iOS e Android apps com 0 resolved reports
  → Apps foram adicionados ao scope Jun 24, 2026 (recente!)
  → 3 dias de programa — ninguém chegou lá ainda
  → OPORTUNIDADE CRÍTICA — rush aqui

SINAL 4: Hilton Honors authentication é Tier A ($1k-$10k)
  → Explicitly highlighted: https://www.hilton.com/en/hilton-honors/join/
  → Loyalty program de 200M+ membros
  → ATO aqui = CRITICAL fácil

SINAL 5: Platform Standard não comprometido para IDOR com UUID
  → Só paga IDOR com IDs sequenciais/previsíveis
  → Foco em Hilton Honors member numbers (provavelmente numéricos)
  → Ou IDOR com impacto claro sem depender de UUID imprevisível
```

---

## Priority Matrix (ROI × Effort)

```
TIER         | ASSET                           | VULN CLASSES        | ROI
-------------|--------------------------------|---------------------|-----
CRÍTICO      | iOS/Android app (0 reports)   | Hardcoded keys, deep | ⭐⭐⭐⭐⭐
             |                                | links, WebView XSS  |
CRÍTICO      | Hilton Honors auth (Tier A)   | ATO, pre-hijack,    | ⭐⭐⭐⭐⭐
             |                                | session fixation    |
ALTO         | suppliersconnection.hilton.com| XSS, IDOR, authz   | ⭐⭐⭐⭐
ALTO         | *.hilton.com subdomains       | Recon → low-hanging | ⭐⭐⭐
MÉDIO        | 167.187.0.0/16 CIDR           | Exposed services   | ⭐⭐
```

---

## Fase 1 — Setup e Passive Recon

### Test Account Setup
```
URL: https://www.hilton.com/en/hilton-honors/join/
First Name: Test-Hackerone
Last Name:  Test-Hackerone

UA: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36 HackerOne
```

### Passive Subdomain Enum
```bash
# Subdomains do *.hilton.com
subfinder -d hilton.com -all -recursive -o /home/altave/.bughunter/bounties/hilton/recon/subs.txt
amass enum -passive -d hilton.com -o /home/altave/.bughunter/bounties/hilton/recon/amass.txt
cat <(curl -s "https://crt.sh/?q=%.hilton.com&output=json" | jq -r '.[].name_value' | sed 's/\*\.//' | sort -u) >> /home/altave/.bughunter/bounties/hilton/recon/subs.txt
sort -u /home/altave/.bughunter/bounties/hilton/recon/subs.txt -o /home/altave/.bughunter/bounties/hilton/recon/subs.txt

# Filter OOS: remove Rackspace IPs, eis.hilton.com, pim.hilton.com, etc.
grep -v -E "^(eis|pim|jobs|onqinsider|hiltonnet|guestfeedback)\." /home/altave/.bughunter/bounties/hilton/recon/subs.txt > /home/altave/.bughunter/bounties/hilton/recon/subs_in_scope.txt

# Historical URLs (foco na autenticação)
gau --subs hilton.com | grep -E "(login|auth|oauth|sso|reset|password|account|member|honors)" | sort -u > /home/altave/.bughunter/bounties/hilton/recon/auth_urls.txt
```

### JavaScript Bundle Analysis
```bash
# Download _app bundles de hilton.com
curl -s https://www.hilton.com | grep -oP '/_next/static/[^"]+\.js' | head -20 | while read f; do
  curl -s "https://www.hilton.com$f" > /tmp/hilton_$(basename $f)
done

# Buscar em todos os bundles
cat /tmp/hilton_*.js | grep -oE '"[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"' | sort -u  # JWTs
cat /tmp/hilton_*.js | grep -iE "(apikey|api_key|client_secret|honors|hhonors)" | head -40
cat /tmp/hilton_*.js | grep -oE 'https://[a-zA-Z0-9._/-]+/api/[a-zA-Z0-9./_-]+' | sort -u  # API endpoints
```

### CIDR 167.187.0.0/16 Probe
```bash
# Rápido sweep de portas abertas (HTTP/HTTPS)
nmap -p 80,443,8080,8443 --open -oG - 167.187.0.0/16 | grep "open" | awk '{print $2}' > /home/altave/.bughunter/bounties/hilton/recon/cidr_http.txt
httpx -l /home/altave/.bughunter/bounties/hilton/recon/cidr_http.txt -title -tech-detect -status-code -o /home/altave/.bughunter/bounties/hilton/recon/cidr_live.txt
```

---

## Fase 2 — Authentication Attacks (Tier A Priority)

### Target: Hilton Honors Join Flow

**URL:** `https://www.hilton.com/en/hilton-honors/join/`

```
Attack 1 — Account Pre-Hijacking
Step 1: Register test account with first.last name pattern
Step 2: Check if email is verified BEFORE account is active
Step 3: If NOT verified → account is created but "pending"
Step 4: Victim tries to register same email → "email in use" error
Step 5: If attacker can trigger verification email to go to attacker → ATO

Observe: Does registration flow reveal if email is in use before completing?
→ YES: account enumeration + pre-hijack primitive confirmed

Attack 2 — OAuth/SSO Linking (ATO)
- Find if Hilton Honors can link: Google, Apple, Facebook
- During linking: check if state param is validated
- Try session fixation: initiate OAuth from one session, complete in another
- Check if linking requires email match (if not → account merge → ATO)

Attack 3 — Password Reset Chain
- POST /forgot-password with Host: attacker.com → reset link to attacker?
- Request reset for own account → check URL structure of reset link
- Try requesting reset twice → can older token still be used?
- Check token lifetime

Attack 4 — Session Management
- Login → capture session token → logout → does token invalidate?
- Concurrent session limit? Two sessions simultaneously?
- Session cookie flags: HttpOnly? Secure? SameSite?
- sessionStorage vs localStorage (XSS impact)

Attack 5 — Hilton Honors Number IDOR
- After creating account → note your Honors number
- Try sequential: your_number ± 1 → /api/member/{honorsNumber}/profile
- Try API calls that expose other members' data
- Check if member number is in URL/API and sequentially enumerable
```

### API Mapping from Browser DevTools
```
Open https://www.hilton.com/en/hilton-honors/join/ in Burp
Complete registration → capture ALL API calls

Look for:
- POST /api/account/register → registration endpoint
- POST /api/auth/login → login endpoint  
- GET /api/member/{id}/profile → member data endpoint
- POST /api/auth/forgot-password → password reset
- GET /api/auth/oauth/google → OAuth linking

For each endpoint:
1. Can I access without auth? (auth bypass)
2. Can I use my token to access another user's {id}? (IDOR)
3. Does it accept mass assignment params? (add role, tier, points)
```

---

## Fase 3 — Mobile Apps (RUSH — Apps adicionados Jun 24)

### Android APK
```bash
# Download APK
adb shell pm list packages | grep hilton
adb pull /data/app/com.hilton.android.hhonors-*/base.apk /tmp/hilton.apk

# Ou via APKPure/APKMirror
# Decompile
apktool d /tmp/hilton.apk -o /tmp/hilton_apk/
jadx -d /tmp/hilton_jadx/ /tmp/hilton.apk

# Search for secrets
grep -r "apikey\|api_key\|client_secret\|password\|AWS\|firebase" /tmp/hilton_apk/ --include="*.xml" --include="*.smali" -l
grep -rE '"[A-Za-z0-9+/]{20,}=="' /tmp/hilton_apk/res/values/ | head -20  # base64 encoded secrets

# Network security config (certificate pinning)
cat /tmp/hilton_apk/res/xml/network_security_config.xml 2>/dev/null

# Exported activities/services
grep -r 'exported="true"' /tmp/hilton_apk/AndroidManifest.xml

# Deep link schemes
grep -r 'scheme\|host\|pathPrefix' /tmp/hilton_apk/AndroidManifest.xml

# Hardcoded URLs / API endpoints
grep -rE "https://[a-z0-9._-]+\.(hilton|hhonors|hiltonhonors)\.(com|io)" /tmp/hilton_jadx/sources/ --include="*.java" | sort -u
```

### iOS IPA (se tiver Mac/jailbroken device)
```bash
# Via frida-ios-dump ou objection
frida-ps -Ua | grep hilton
objection -g "Hilton Honors" explore
# > ios sslpinning disable  (bypass certificate pinning)
# > ios keychain dump        (dump keychain)
# > ios nsuserdefaults get   (insecure storage)

# Class dump
class-dump HiltonHonors.app/HiltonHonors > /tmp/hilton_headers.h
grep -i "api\|key\|secret\|token\|endpoint" /tmp/hilton_headers.h | head -40
```

---

## Fase 4 — suppliersconnection.hilton.com

```
CSRF excluído temporariamente = app tem segurança fraca
Outros vuln classes EM SCOPE

Attack surface:
1. Login → é B2B supplier portal → provavelmente credenciais fracas
2. POST /login sem CSRF check → se estiver excluído, mas outras rotas?
3. XSS em campos de fornecedor (nome empresa, endereço)
4. IDOR em IDs de supplier contracts/orders
5. File upload para documentos de supplier
6. API endpoints expostos

Fingerprint:
curl -si https://suppliersconnection.hilton.com -H "User-Agent: HackerOne"
→ Que tecnologia? ASP.NET? Java? Node?
→ Headers de resposta → WAF? CDN?
```

---

## Fase 5 — XSS via Campos de Perfil (Stored)

```
Target: Nome, sobrenome, endereço no perfil Hilton Honors
(POST XSS é OOS, mas Stored XSS via input que é RENDERERIZADO é diferente)

Wait — "POST-based XSS" na regra = XSS refletido via método POST
Stored XSS em campos de perfil que renderiza em outra página = DIFERENTE

Payloads para testar em campos de nome (test account):
<img src=x onerror=alert(1)>  → verifica rendering
"><script>alert(1)</script>
{{7*7}}                        → SSTI
${7*7}                         → SSTI alternativo

Se campo de nome aparece em:
- Email de confirmação (CSP fora do email?)
- PDF de reserva (PDF XSS → SSRF)
- Admin panel mostrando clientes (XSS → admin ATO)
- Receipt/invoice gerado
```

---

## Checklist Rápido de Início

```
□ Criar conta Hilton Honors com "Test-Hackerone" no nome
□ Mapear todos os requests da registration flow no Burp
□ Baixar APK Android via APKMirror/APKPure → decompile
□ Passive recon: subfinder + crt.sh em hilton.com
□ curl suppliersconnection.hilton.com → fingerprint
□ Verificar se Hilton tem /.well-known/ (algum serviço tipo MCP/OAuth?)
□ Testar password reset: Host header injection
□ Testar registration: email enumeration na sign-up page
□ Verificar cookies de sessão pós-login (flags, scope)
□ Buscar "api" em bundles JS de hilton.com
□ Verificar hilton.io, hiltonlocalbiz.com, hiltonbusinessonline.com
```
