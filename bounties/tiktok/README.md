# TikTok Bug Bounty — HackerOne

**Plataforma:** HackerOne  
**Data de início:** 2026-06-29  
**Avg bounty CRITICAL:** $13,500  
**Total pago:** $3,907,176  
**Response efficiency:** 95%

---

## Escopo

| Asset | Tipo | Reports | Prioridade |
|-------|------|---------|-----------|
| *.tiktokv.com | Other | 185 (11%) | ⭐ ALTA (explicitamente prioritário) |
| *.tiktok.com | Other | 378 (23%) | ⭐ ALTA |
| ads.tiktok.com | Domain | 458 (28%) | MÉDIA (muito testado) |
| **soundon.global** | Domain | **0 (0%)** | ⭐⭐ CRÍTICA (fresh scope, Jun 8 2026) |
| ***.soundon.global** | Wildcard | **0 (0%)** | ⭐⭐ CRÍTICA |
| ***.pipopay.com** | Wildcard | **1 (0%)** | ⭐⭐ ALTA (payment infrastructure) |
| ***.tiktokpublishers.com** | Wildcard | **1 (0%)** | ALTA |
| *.tiktokcdn.com | Wildcard | 1 (0%) | MÉDIA |
| com.zhiliaoapp.musically | Android | 89 (5%) | ALTA (prioridade declarada) |
| com.ss.android.ugc.trill | Android | 35 (2%) | ALTA (prioridade declarada) |
| shop.tiktok.com | Domain | 12 (1%) | ALTA |
| seller-id.tokopedia.com | Domain | 52 (3%) | MÉDIA |
| **pay.tokopediax.com** | Domain | **5 (0%)** | ⭐ ALTA (payment) |

**EXCLUÍDOS (não testar):**
- USDS JV scope (excluído Jun 29, 2026)
- FBT Platform (excluído Mai 13, 2026)
- CSRF em qualquer produto (excluído Jul 2023)
- IDOR no TikTok Partner Shop API (excluído Mar 2024)
- TikTok One / Business Center access control (excluído Dez 2024)

**SSRF:** Usar APENAS `https://ssrf-bait.byted.org/full-read-ssrf`  
**Headers obrigatórios:** `X-HackerOne-Handle: <handle>` em todos os requests

---

## Stack Descoberta

| Componente | Tech |
|-----------|------|
| soundon.global | React SPA / Node.js backend |
| CDN | Akamai (soundon.global), TLB (ByteDance) |
| Auth | TikTok OAuth 2.0 + Google OAuth |
| Upload | ByteDance VOD (`vod-upload-sg.tiktok.com`) |
| Notification | JWT-based "feelgood" platform events |
| pipopay.com | ByteDance payment infrastructure |
| Banks integrados | JPMorgan, Citibank, DBS, Barclays, BNP Paribas, KBank, Maybank, UOB, StcPay, PayPay, Itau, WorldPay |

---

## Subdomínios Descobertos

### soundon.global
| Subdomínio | Status |
|-----------|--------|
| www.soundon.global | 200 |
| us.soundon.global | 301 → www |
| sf-soundon-ug.soundon.global | 403 (CDN UGC) |
| sf-soundon-fe.soundoncdn-us.com | CDN |
| sf-web-static.soundoncdn-us.com | CDN |
| artists-test.bytedance.net | 000 (não público — leak no JWT!) |

### pipopay.com (Global Payment Network)
```
callback-sg.pipopay.com       → PayPal callbacks (SG)
callback-va.pipopay.com       → PayPal callbacks (VA/US)
callback-sg-itau.pipopay.com  → Itau callbacks (403)
callback-sg-worldpay.pipopay.com → WorldPay callbacks (403)
callback-va-itau.pipopay.com  → Itau callbacks (VA)
callback-va-worldpay.pipopay.com → WorldPay callbacks (403)
cashier-my4a.pipopay.com      → 3DS checkout (200 ACTIVE!)
autofill-sg.pipopay.com       → Card autofill (Akamai protected)
fp-sg.pipopay.com             → Fingerprinting
gpn-be-jpm-prod-row.pipopay.com → JPMorgan GPN backend
gpn-be-citi-prod-sg.pipopay.com → Citibank GPN backend
[+ 30 outros gpn-be-*]
```

---

## Findings

### 🔴 TK-001 — soundon.global: Unauthenticated JWT Platform Token Issuance (MEDIUM/HIGH)
**Status:** REPORT COMPLETO em `reports/TK-001_soundon_feelgood_token_unauth.md`  
**Endpoint:** `GET https://www.soundon.global/api/open/feelgood/token`  
**CVSS:** ~6.5 MEDIUM → upgrade para HIGH se token permite cross-user event subscription  
**Evidência:** JWT Bearer confirmado, payload decodificado

### 🟡 TK-002 — soundon.global: Royalty Split / Revenue IDOR (HIGH potential — precisa de conta)
**Status:** PoC preparado, aguardando teste autenticado  
**Endpoints de risco:**
- `POST /api/split/update-user-split-song` — Atualizar splits de royalties
- `POST /api/revenue/withdraw` — Solicitar retirada de receitas
- `POST /api/monetization/contract/create` — Criar contratos de monetização
- `POST /api/publishing/registration` — Registrar publicação musical
**CVSS potencial:** 7.5–9.1 HIGH/CRITICAL (financial fraud)

### 🟡 TK-003 — pay.tokopediax.com: Admin JWT em URLs públicas (Wayback Machine)
**Status:** REPORT COMPLETO em `reports/TK-003_tokopediax_admin_jwt_url_exposure.md`  
**Evidência:** Tokens com `"ro":"ADMIN"` capturados pelo Wayback Machine em URLs  
**CVSS:** ~4.3 MEDIUM (expired tokens, informação sensível em URL)

### 🟠 TK-004 — soundon.global: OAuth Token Exposure via BroadcastChannel + Deprecated Implicit Grant (MEDIUM)
**Status:** REPORT COMPLETO em `reports/TK-004_soundon_broadcastchannel_oauth_token_leak.md`  
**Evidência:** Canal BroadcastChannel "bc_channel_third_oauth" hardcoded em bundle de produção; Google OAuth usa response_type=id_token token (deprecated, RFC 9700)  
**CVSS:** 6.5 MEDIUM → HIGH se XSS confirmado

### 🔴 TK-005 — cashier-my4a.pipopay.com: ACTIVE Admin JWTs + Stripe Secrets em Wayback (HIGH URGENTE)
**Status:** REPORT COMPLETO em `reports/TK-005_pipopay_admin_jwt_stripe_secret_wayback.md`  
**⚠️ URGENTE — tokens ativos, expiram 2027-06-15 (350 dias restantes)**  
**Evidência:**
- JWT INVOICE_DOWNLOAD (ro=ADMIN, sc=INVOICE_DOWNLOAD) indexado Wayback 2026-06-15, **ainda ativo**
- JWT INVOICE_APPLY (ro=ADMIN, sc=INVOICE_APPLY) indexado Wayback 2026-06-15, **ainda ativo**
- 2x Stripe `payment_intent_client_secret` em URLs de 3DS landing page
**CVSS:** 8.1 HIGH

---

## soundon.global API Surface Map (Completo)

### Endpoints "open" (sem autenticação esperada)
```
GET  /api/open/config              → 200 (VOD config, app IDs)
GET  /api/open/ping                → 200 (env info: isProd=true, version)
GET  /api/open/region              → 200 (região do usuário)
GET  /api/open/feelgood/token      → 200 (JWT Bearer — TK-001!)
GET  /api/open/fg                  → 200 (feature gates)
GET  /api/open/feedback/upload/token → 500 (crash sem auth — suspeito!)
POST /api/open/feedback/form       → 400 (precisa params)
POST /api/open/unsubs-feat         → 400 (precisa params)
GET  /api/open/subscribe/confirm   → 400 (precisa params)
```

### Endpoints financeiros (requerem auth — alto potencial de IDOR)
```
GET  /api/revenue/balance             → Saldo
GET  /api/revenue/statement/list      → Extratos
POST /api/revenue/withdraw            → ⚠️ RETIRADA (alto risco IDOR!)
GET  /api/revenue/royalty/trend       → Tendência de royalties
GET  /api/revenue/royalty/list        → Histórico de royalties
GET  /api/revenue/royalty/total       → Total de ganhos
POST /api/revenue/royalty/report/generate → Gerar relatório
GET  /api/revenue/royalty/deductions/list → Deduções de royalties
GET  /api/revenue/rfi/list            → RFI list
GET  /api/revenue/recoup/detail       → Recoupment detail
```

### Royalty Splits (IDOR potencial — HIGH)
```
POST /api/split/album/create          → Criar split de álbum
POST /api/split/verify/split-code     → Verificar código de convite
POST /api/split/send/email-code       → Enviar código de email
GET  /api/split/search-user-split-song → Buscar split songs de usuário
GET  /api/split/list-user-split-song  → Listar splits de usuário
POST /api/split/update-user-split-song → ⚠️ ATUALIZAR SPLIT (alto risco!)
POST /api/split/resend-invite-v2      → Reenviar convite
```

### Monetização (IDOR potencial — HIGH)
```
POST /api/monetization/contract/create → Criar contrato
POST /api/monetization/breakthrough/batch/create → Batch breakthrough
POST /api/monetization/batch/create   → Batch monetização
POST /api/monetization/breakthrough/batch/update → Atualizar breakthrough
GET  /api/monetization/statistic      → Estatísticas
GET  /api/monetization/list/track     → Listar tracks monetizadas
```

### Publicação Musical (copyright — IDOR potencial)
```
POST /api/publishing/registration     → ⚠️ Registrar publicação
POST /api/publishing/songwrite        → Registrar compositor
POST /api/publishing/track            → Publicar track
GET  /api/publishing/songwrite/list   → Listar compositores
GET  /api/publishing/track/list       → Listar tracks publicadas
```

### AIGC / AI Processing (SSRF potencial com conta)
```
POST /api/song/auto-mastering/analyse → Analisar (URL-based? SSRF?)
POST /api/song/auto-mastering/process → Processar
POST /api/audio/remix/process         → Remix de áudio (SSRF?)
GET  /api/audio/remix/result          → Resultado do remix
```

### OAuth Integration
```
POST /api/oauth/google/register       → Registrar Google OAuth
POST /api/oauth/google/verify         → Verificar Google OAuth
POST /api/oauth/spotify/register      → Registrar Spotify OAuth
GET  /api/spotify/release-info        → Info de release Spotify
GET  /api/oauth/spotify/instant-access → Acesso Spotify
```

---

## Próximos Passos

### Sem conta (estático)
1. **[PRONTO]** Submeter TK-001 (feelgood/token)
2. **[PRONTO]** Submeter TK-003 (admin JWT em URLs)
3. Análise mais profunda de `cashier-my4a.pipopay.com`
4. Análise da APK Android (com.zhiliaoapp.musically) para endpoints *.tiktokv.com

### Com conta soundon.global (criada como artista teste)
1. **[ALTA PRIORIDADE]** Testar IDOR em `/api/split/update-user-split-song`
2. **[ALTA PRIORIDADE]** Testar IDOR em `/api/revenue/withdraw`
3. **[ALTA PRIORIDADE]** Testar IDOR em `/api/publishing/registration`
4. Testar SSRF em `/api/song/auto-mastering/analyse` e `/api/audio/remix/process`
5. Testar `/api/open/feedback/upload/token` com conta (clarificar 500 vs 401)

### Com conta TikTok padrão
1. Testar endpoints `*.tiktokv.com` (API mobile)
2. Testar `live-backstage.tiktok.com` live streaming APIs
3. Testar `creatormarketplace.tiktok.com` brand/creator deal APIs

---

**Data:** 2026-06-29  
**Hunter:** @nataliadias1
