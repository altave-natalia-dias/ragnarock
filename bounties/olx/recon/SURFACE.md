# OLX Brasil — Attack Surface — 2026-07-05

## Recon / fingerprint (in-scope hosts)
| Host | Fronting | Root status | Note |
|---|---|---|---|
| apigw.olx.com.br | Cloudflare | 403 CF (curl) / **GraphQL /graphql = 401 auth** | API gateway; GraphQL (Apollo) + REST `/delivery/`, `/v1/redirect/` |
| conta.olx.com.br | Cloudflare | 403 CF | OAuth/OIDC + PKCE; `/identifique-se`, `/pagamentos`, `/confirmacao-telefone` |
| wallet.olx.com.br / wallet-api | Cloudflare | 403 CF | ★ money |
| payment.olx.com.br | nginx | **543** (direct, no CF) | reachable |
| goldpayments / payment-by-chat-api / api-transaction | Cloudflare | 403 CF | ★ money |
| delivery-tracking / delivery-quote | nginx | **405** (direct, POST-only) | reachable |
| olx.com.br / www | Cloudflare | 403 CF (curl) | main web app |

## KEY UNLOCK: Cloudflare bypass
- curl is JA3-blocked by CF Bot Management (403 "Attention Required").
- **headless Chrome (`google-chrome --headless=new`) PASSES CF** → got real olx.com.br DOM (410KB) + screenshot. Egress IP appears Brazilian (179.94.127.251 via apkcombo checkin), so CF block is bot-fingerprint, not geo.
- ⇒ Web/API hunting is viable via Chrome; curl is not.

## APK deep-dive (com.schibsted.bomnegocio.androidApp v26.26.0)
- 62MB base + splits (arm64/en/mdpi). 6 dex. jadx → 42,830 java files. apktool decoded.
- **Firebase**: project `olxapps-aa7fd`, RTDB `olxapps-aa7fd.firebaseio.com`, bucket `olxapps-aa7fd.appspot.com`, keys AIzaSyBfT0k9KF7utydjqEe-pATTDebrDmrEUyc / AIzaSyAqcJ_KrnxnNobr8ThJlj3k9Uf0ptJK9yY.
  - **Tested (read-only, non-destructive)**: RTDB = disabled (423), Firestore = 404 (none), Storage list = disallowed (rules v1). **Hardened, no misconfig.**
- No AWS/Stripe/JWT/hardcoded secrets in dex strings. AIza keys are standard Android Firebase (not secret).
- **API routing**: app → `apigw.olx.com.br/graphql` (Apollo GraphQL) + `/delivery/`. Backend hosts (wallet-api, api-transaction, payment-by-chat) reached via apigw, not direct.
- Auth: `conta.olx.com.br` OAuth/OIDC + PKCE (CodeChallengeMethod). Facebook Login SDK present (3rd-party = OOS).
- 261 Apollo operation classes. See graphql_ops.txt.

## GraphQL operations (BOLA/IDOR candidates — all need auth token)
- **Chat (prime BOLA)**: GetChat, GetChatList, GetMessagesWithAd, GetMiniChat, chatAdview, DeleteChat
- **Offers (money/logic)**: MakeOffer, ApproveOffer, RejectOffer
- **Partner/dispute**: BlockPartner, UnblockPartner, DenouncePartner, CloseDispute
- **Ads**: getAdFromId, getSellerAds
- **Delivery**: query delivery
- Favorites/notifications: FavoriteSaveMutation, DeleteFavoriteMutation, EnableNotification

## Blockers to high-value validation
1. GraphQL `/graphql` → 401 (needs session token). Chat/offer BOLA untestable unauth.
2. No OLX account (Brazilian phone/CPF needed to register; program encourages account creation).
3. Interactive OAuth/web testing needs proper browser automation (Playwright/Puppeteer), not just `--dump-dom`.

## Reachable unauthenticated avenues (Chrome-viable)
- conta.olx.com.br OAuth/OIDC flow — redirect_uri validation, response_type, PKCE downgrade → 0-click ATO (RAG-flagged).
- delivery-tracking / delivery-quote (nginx POST APIs) — possible BOLA on tracking IDs.
- payment.olx.com.br (543) — investigate.
- Public GraphQL ops (getAdFromId, getSellerAds) if any work unauth.
- Web client-side (DOM XSS, postMessage) on olx.com.br via Chrome.

## Firebase / secrets verdict
Hardened. No reportable secret or misconfig from APK static analysis.

## Unauth OAuth/web hunt (Playwright) — 2026-07-05
- Tooling: Playwright + system Chrome PASSES Cloudflare (persistent context + warmup handles managed challenge; repeated raw automated hits still get 403-challenged intermittently).
- **conta.olx.com.br auth = returnToToken mechanism**: `conta.olx.com.br/` → `/acesso?returnToToken=<JWT HS256>`, payload `{"url":"<return target>","iat":ms}`. Post-auth redirect goes to `url` claim.
- **Open-redirect analysis (CLOSED, no bug):**
  1. HS256 secret NOT crackable — rockyou.txt exhausted (14.3M, 834k/s) no match → strong/random secret. No forge.
  2. Sig-validation test: valid / bad-sig / alg:none all render "Minha conta" 200 unauth; redirect fires only post-auth (can't observe without account).
  3. Token-minting test: `?returnTo=/return_to/url/redirect/returnUrl/next=<EXT>` → minted token's `url` claim = current same-origin URL (`conta.olx.com.br/?param=EXT`), NOT external. Redirect host always same-origin. No external-target injection.
  - Verdict: JWT-signed same-origin return mechanism = deliberate anti-open-redirect control. Not exploitable unauth.

## OLX session verdict (unauth)
No confirmed vuln. CF-bypass + APK intel + Playwright infra established. High-value classes (GraphQL chat/offer BOLA, wallet/payment IDOR) remain auth-gated (401, no account). Open-redirect/JWT surface is hardened.

## Delivery APIs hunt (in-scope) — 2026-07-05
- **delivery-tracking / delivery-quote** (nginx, no CF): GET any path → 405 (method blocked); POST any path → 404 (backend has route but path unknown). POST-only microservices.
- Tried paths (POST): /, /quote(s), /v1/quote(s), /estimate, /track, /trackings, /v1/tracking + realistic quote/tracking bodies → all 404.
- Passive discovery (gau/waybackurls/urlscan): only `/` archived. NOT referenced in APK. Opaque partner/internal APIs.
- APK delivery routing: app uses `apigw.olx.com.br/delivery/` (401, needs auth) + CheckoutService `@GET /checkout/delivery?listId=&addressId=` (IDOR candidates listId/addressId — via apigw, auth-gated).
- **IDOR-rich order URLs found in APK but OUT OF SCOPE**: `comprasegura.olx.com.br/pedidos/{orderId}/pix?listId=`, `meus-pedidos.olx.com.br/minhas-compras|minhas-vendas`, `pedido.olx.com.br`, `pos-venda.olx.com.br/pedido/`, `trackingapp.olx.com.br/track`. NOT in explicit scope list → not tested.

### Delivery verdict
In-scope delivery hosts are opaque POST APIs with no discoverable routes unauth; blind path enumeration = OOS scanner behavior. Real delivery IDOR testing (listId/addressId, order IDs) requires an authenticated session to observe valid paths+IDs. Avenue exhausted unauth-within-scope.

## Log4Shell (CVE-2021-44228) hunt — R$4.000 bonus — 2026-07-05
- OOB: interactsh (oast.site). Self-test DNS+HTTP callback CONFIRMED detection works. Egress IP 179.94.127.251 (BR).
- nginx-direct hosts (delivery-tracking, delivery-quote, payment — no CF): payloads in UA/XFF/X-Api-Version/Referer/X-Client-Version/True-Client-IP/X-Forwarded-Host/Authorization (WAF-bypass + hostName exfil) REACHED origin -> No callback. Not vulnerable.
- CF-fronted hosts (apigw/wallet-api/api-transaction/goldpayments/payment-by-chat-api/conta): real Chrome nav + route header injection.
  - CONTROL (clean) apigw -> 401 (reaches origin).
  - Variants lower:j / ::-j / env / date / upper -> all 403 = Cloudflare Managed WAF blocks every Log4j payload at edge.
- No JNDI callback fired anywhere.
### Verdict: OLX NOT demonstrably Log4Shell-vulnerable. CF WAF filters all obfuscations (401 clean vs 403 payload); nginx origins show no callback. Honest negative.
