# OLX Brasil — Bug Bounty (BugHunt) — público

Recompensas: Baixo R$0 | Médio R$300 | Alto R$1.000 | Crítico R$2.000
BÔNUS: **Log4j PoC = R$4.000** (fornecer screenshots, payloads, endpoints)

## DICA OFICIAL
- **Criar conta na OLX antes de testar** (autenticado é permitido/encorajado).
- Persistência de sessão no cookie campo **`loginIdentifier`**.

## ESCOPO (lista explícita de hosts — NÃO é wildcard)
- Android app: com.schibsted.bomnegocio.androidApp
- https://apigw.olx.com.br            (API + Web)
- https://conta.olx.com.br            (conta/auth)
- https://wallet.olx.com.br           (Web)
- https://wallet-api.olx.com.br       (API)  ★ dinheiro
- https://payment.olx.com.br          (Web)  ★
- https://goldpayments.olx.com.br     (Web)  ★
- https://payment-by-chat-api.olx.com.br (API) ★
- https://api-transaction.olx.com.br  (API)  ★
- https://delivery-tracking.olx.com.br (API)
- https://delivery-quote.olx.com.br   (API)
- https://olx.com.br                  (Web)

## REGRAS-CHAVE
- Só interagir com contas próprias ou com permissão explícita do titular.
- Evitar violação de privacidade, destruição de dados, DoS.
- Toda vuln SÓ é aceita **explorada + evidências anexadas** (PoC obrigatória).

## OUT OF SCOPE (resumo)
- Clickjacking sem info sensível, Self-XSS, ACAO em qualquer página
- Email/access confirmation, API que não retorna dados sensíveis / já expostos no frontend
- User/email enumeration (login/forgot), CSRF não-auth login/logout, CSRF em ações não-críticas
- Security headers ausentes, cookie flags, rate limiting (falta de), brute-force em auth
- Flash, MITM/físico, libs vulneráveis sem PoC, CSV injection sem PoC, SSL/TLS best-practice
- Stack traces sem PoC, OPTIONS habilitado, DoS, content/text spoofing sem vetor
- Integrações de terceiros não-oficiais, eng. social/phishing, SPF/DKIM
- Info disclosure insensível (versão de software), banner grabbing
- Scanner não-validado (falso positivo), WordPress low/med, SSL pinning mobile, tabnabbing

## Prioridades (RAG bb_writeups)
1. IDOR/BOLA em wallet-api / api-transaction / payment-by-chat-api / delivery-*
2. Chain improper-authz → race condition (payment/wallet) → financial impact
3. OAuth/OIDC misconfig → 0-click ATO (conta.olx.com.br)
4. Log4j (R$4.000) em qualquer endpoint que reflita/logue input
5. Business logic em payment/goldpayments (valores, moeda, negativo)
