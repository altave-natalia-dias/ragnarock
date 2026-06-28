# Hilton Android APK — Analysis Playbook

**Target:** com.hilton.android.hhonors (Google Play Store)  
**Tier:** A — 0 resolved reports (adicionado Jun 24, 2026)  
**Bounty:** $1k–$10k  
**Razão do rush:** Apps adicionados há 3 dias — território completamente virgem

---

## Step 1 — Obter o APK

```bash
# Opção A: Via ADB (se tiver device Android)
adb shell pm list packages | grep -i hilton
# com.hilton.android.hhonors

adb shell pm path com.hilton.android.hhonors
# /data/app/com.hilton.android.hhonors-XXXXX/base.apk

adb pull /data/app/com.hilton.android.hhonors-XXXXX/base.apk /tmp/hilton.apk

# Opção B: APKPure / APKMirror (sem necessidade de device)
# https://apkpure.com/hilton-honors-hotel-rooms-more/com.hilton.android.hhonors
# https://www.apkmirror.com/?s=hilton+honors

# Opção C: Pull via emulador (Genymotion / Android Studio AVD)
# 1. Abrir emulador com Play Store
# 2. Instalar Hilton Honors
# 3. adb pull como acima
```

---

## Step 2 — Decompile

```bash
mkdir -p /tmp/hilton_apk_analysis

# Apktool — smali + resources (manifesto, strings.xml, network_security_config.xml)
apktool d /tmp/hilton.apk -o /tmp/hilton_apk_analysis/apktool/ --no-res --no-src 2>/dev/null
apktool d /tmp/hilton.apk -o /tmp/hilton_apk_analysis/apktool_full/ 2>/dev/null

# JADX — Java source code (melhor para leitura)
jadx -d /tmp/hilton_apk_analysis/jadx/ /tmp/hilton.apk --show-bad-code 2>/dev/null

echo "[*] Decompile complete"
ls /tmp/hilton_apk_analysis/
```

---

## Step 3 — AndroidManifest Analysis

```bash
# Atividades exportadas (pode ser invocado por qualquer app)
echo "=== EXPORTED ACTIVITIES ==="
cat /tmp/hilton_apk_analysis/apktool_full/AndroidManifest.xml | \
  python3 -c "
import sys, xml.etree.ElementTree as ET
tree = ET.parse(sys.stdin)
ns = '{http://schemas.android.com/apk/res/android}'
for e in tree.iter():
    if e.get(ns+'exported') == 'true':
        print(f'{e.tag}: {e.get(ns+\"name\", \"?\")}')
"

# Deep link schemes (intent filters com scheme)
echo "=== DEEP LINK SCHEMES ==="
grep -A5 "scheme\|data android:scheme" /tmp/hilton_apk_analysis/apktool_full/AndroidManifest.xml | \
  grep "scheme\|host\|pathPrefix\|path"

# Services e Broadcast Receivers exportados
echo "=== EXPORTED SERVICES/RECEIVERS ==="
grep -B2 'android:exported="true"' /tmp/hilton_apk_analysis/apktool_full/AndroidManifest.xml

# Permissions declaradas
echo "=== PERMISSIONS ==="
grep "uses-permission" /tmp/hilton_apk_analysis/apktool_full/AndroidManifest.xml
```

---

## Step 4 — Network Security Config (Certificate Pinning)

```bash
echo "=== NETWORK SECURITY CONFIG ==="
cat /tmp/hilton_apk_analysis/apktool_full/res/xml/network_security_config.xml 2>/dev/null || \
  echo "Arquivo não encontrado — sem pinning custom, usa defaults"

# Se tem certificados pinados, precisará de Frida para bypass:
# frida -U -l ssl_bypass.js com.hilton.android.hhonors
# Usar: https://github.com/httptoolkit/frida-android-unpinning
```

---

## Step 5 — Secret Hunting

```bash
echo "=== HARDCODED SECRETS SEARCH ==="

# API keys genéricos
grep -rhoEi \
  "(apikey|api_key|client_secret|clientsecret|APP_SECRET|HILTON_KEY|HONORS_TOKEN|AUTH_TOKEN)\s*[=:]\s*['\"][^'\"]{8,}['\"]" \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | sort -u | tee /tmp/hilton_secrets.txt

# Firebase config (muito comum em apps Android)
grep -rhoE '"firebase[a-zA-Z]*"\s*:\s*"[^"]{8,}"' \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | sort -u | tee -a /tmp/hilton_secrets.txt

# Google Services credentials
cat /tmp/hilton_apk_analysis/apktool_full/res/values/google-services.json 2>/dev/null | jq . | head -30

# AWS keys
grep -rhoE "AKIA[0-9A-Z]{16}" /tmp/hilton_apk_analysis/ 2>/dev/null | sort -u | tee -a /tmp/hilton_secrets.txt

# Long base64 strings (possíveis secrets encoded)
grep -rhoE '"[A-Za-z0-9+/]{40,}={0,2}"' \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | \
  sort -u | head -20 | tee -a /tmp/hilton_secrets.txt

# Hardcoded URLs e API base URLs
echo "=== API ENDPOINTS ==="
grep -rhoE "https://[a-zA-Z0-9._/-]+\.(hilton|hhonors|hiltonhonors)\.(com|io|net)[/a-zA-Z0-9._/?=&-]*" \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | sort -u | tee /tmp/hilton_api_endpoints.txt

# Staging/dev endpoints
grep -rhoE "https://[a-zA-Z0-9._/-]*(staging|dev|qa|test|preprod|sandbox)[a-zA-Z0-9._/-]*" \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | sort -u | tee /tmp/hilton_staging.txt

cat /tmp/hilton_secrets.txt
cat /tmp/hilton_api_endpoints.txt
cat /tmp/hilton_staging.txt
```

---

## Step 6 — Authentication Logic Analysis

```bash
# Buscar classes de autenticação
echo "=== AUTH CLASSES ==="
find /tmp/hilton_apk_analysis/jadx/sources/ -name "*.java" | \
  xargs grep -l -iE "(login|auth|oauth|sso|token|session|honors)" 2>/dev/null | head -20

# Verificar como tokens são armazenados
echo "=== TOKEN STORAGE ==="
grep -rhoE "(SharedPreferences|getSharedPreferences|MODE_PRIVATE|EncryptedSharedPreferences|SQLiteDatabase)\." \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | \
  sort | uniq -c | sort -rn | head -20

# SharedPreferences sem EncryptedSharedPreferences = insecure storage
# Verificar quais keys são stored:
grep -rhoE 'putString\("[^"]+",|getString\("[^"]+' \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | sort -u | head -30

# WebView JavaScript enabled (XSS via webview)
echo "=== WEBVIEW JS ENABLED ==="
grep -rn "setJavaScriptEnabled(true)\|addJavascriptInterface" \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null

# Deep link handling — como URIs são processados
echo "=== DEEP LINK HANDLING ==="
grep -rn "getIntent\|getData\|getScheme\|handleDeepLink" \
  /tmp/hilton_apk_analysis/jadx/sources/ 2>/dev/null | head -20
```

---

## Step 7 — Dynamic Analysis (com device/emulador)

```bash
# Instalar ferramentas (se não tiver)
# pip install frida-tools objection

# Bypass SSL Pinning
adb push ssl_bypass.js /data/local/tmp/
frida -U -f com.hilton.android.hhonors \
  -l /data/local/tmp/ssl_bypass.js \
  --no-pause

# Ou via objection
objection -g com.hilton.android.hhonors explore
# > android sslpinning disable
# > android hooking list activities
# > android hooking list services
# > android keystore list
# > env  (mostra paths de armazenamento)

# Após bypass, interceptar tráfego via Burp/mitmproxy
# Configurar proxy no emulador: 127.0.0.1:8080
# Capturar APIs reais do app → testar IDOR, auth bypass, mass assignment

# Verificar armazenamento inseguro
adb shell run-as com.hilton.android.hhonors ls /data/data/com.hilton.android.hhonors/
adb shell run-as com.hilton.android.hhonors cat /data/data/com.hilton.android.hhonors/shared_prefs/*.xml
# Se tiver token/session armazenado em plaintext = Medium finding

# Intent spoofing (deep links exportados)
adb shell am start -a android.intent.action.VIEW \
  -d "hilton://login?token=ATTACKER_TOKEN" \
  com.hilton.android.hhonors

adb shell am start -n com.hilton.android.hhonors/.ui.activity.MainActivity \
  --es "redirect_url" "https://attacker.com"
```

---

## Findings Esperados (por probabilidade)

```
ALTA probabilidade:
□ Hardcoded staging/dev API endpoint (LOW-MEDIUM)
□ Firebase config exposed (token, project ID) → test anonymous signup
□ Insecure SharedPreferences (session token em plaintext) → MEDIUM
□ Deep link mishandling → redirect/open redirect dentro do app → MEDIUM

MÉDIA probabilidade:
□ WebView com JavaScript enabled + addJavascriptInterface → XSS → HIGH
□ Exported activity sem intent filter validation → intent spoofing → MEDIUM/HIGH
□ Certificate pinning bypassável → MEDIUM (baixo sozinho, alto combinado)
□ API endpoint em staging sem auth → HIGH

BAIXA probabilidade (mas HIGH valor):
□ OAuth token em URL em WebView → Referer leak → MEDIUM
□ Auth token não expira → MEDIUM
□ IDOR em API de membros via número Honors → HIGH
□ Private key / certificate hardcoded → CRITICAL
```

---

## Reporting Note

O programa NÃO comprometeu com o Platform Standard para:
- "Vulnerabilities involving a self-sign-up flow" → conta criada via Play Store = sign-up flow
- "Sensitive PII leakage" → pode ser downgraded

Foco em: impacto de **account takeover** e **unauthorized access to other users' data** — não apenas "PII exposed" sem contexto.
