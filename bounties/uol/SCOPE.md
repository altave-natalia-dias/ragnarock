# UOL Conteúdo e Serviços (UOLCS) — Bug Bounty (BugHunt) — público

Recompensas: Baixo R$300 | Médio R$1.000 | Alto R$3.000 | Crítico R$5.000
🔥 IMPULSIONAMENTO (período especial):
- 0-click ATO em conta.uol.com.br ............ R$20.000
- 0-click leitura arbitrária de e-mails ...... R$20.000
- 0-click XSS no corpo do e-mail (webmail) ... R$10.000
  (XSS deve executar no mesmo contexto do Webmail; vítima abre o email e XSS executa, SEM clicar)

## CONTA DE TESTE GRÁTIS (autenticado permitido!)
https://checkout.uol.com.br/#/bol/0?promotion=WEBEMAILBOL  (webmail BOL grátis)
- Só interagir com contas próprias / permissão do titular.
- Se achar dados sensíveis de usuários: reportar imediatamente, não vazar/manipular/destruir.
- Após testes: remover comentários/ações visíveis a usuários legítimos (senão ban).

## ESCOPO (lista explícita)
WEBMAIL:
- https://mail.uol.com.br            (webmail UOL)
- https://bmail.uol.com.br
- https://webmailpro.uol.com.br
- https://email.bol.com.br           (webmail BOL — conta grátis)
- https://webmail.uolhost.com.br
- https://email.uol.com.br
CALENDÁRIO:
- https://cal.webmailmailpro.uol.com.br
- https://cal.bmail.uol.com.br
- https://cal.mail.uol.com.br
CONTA/SSO (alvo 0-click ATO R$20k):
- https://conta.uol.com.br
HOST/PAINEL:
- https://meupainelhost.uol.com.br
- https://meupainelhost-api.uol.com.br  (API)
CONTEÚDO:
- https://ne10.uol.com.br
- https://caras.uol.com.br
- https://noticiasdatv.uol.com.br
- https://brasilescola.uol.com.br
OUTROS:
- *.service.uol.com.br   (subdomínio wildcard)
- checkout.uol.com.br
- helper.uol.com.br

## FORA DE ESCOPO / PROIBIDO
- ❌ download.uol.com.br, *.download.uol.com.br (NÃO testar — explícito)
- CNAME p/ amazonas/santi/pandeiro/salsa/samba.uol.com.br não-listados = não elegível
- Endpoints/domínios diferentes → mesma app/componente = DUPLICADO (não paga)
- Não-crítico não será analisado (LGPD → l-lgpd@uolinc.com)
- Exclusões padrão: clickjacking s/ info, self-XSS, user enum, CSRF não-auth/logout, brute-force,
  stack traces s/ PoC, OPTIONS, DoS, content spoofing s/ vetor, terceiros, eng social, SPF/DKIM,
  banner grab, rate limiting (falta), cookie flags, security headers, SRI, HSTS ausente,
  bugs públicos <7 dias, ferramentas automáticas com tráfego significativo.
- Regras: exploit NÃO pode exigir desabilitar proteções nativas (SameSite/mixed-content/sandbox/TLS).
  Ataque que pressupõe comprometimento prévio (creds/cookies) = Informativo.
- CORS só aceito com impacto no usuário final demonstrado.

## PRIORIDADES (foco medium/high/critical)
1. Webmail XSS no corpo do e-mail (stored, sanitização de HTML) → R$10k
2. IDOR/BOLA leitura de e-mails de terceiros → R$20k
3. conta.uol.com.br SSO/OAuth → 0-click ATO → R$20k
4. meupainelhost-api (API) → IDOR/BOLA
5. *.service.uol.com.br → superfície de API
6. CORS com impacto, SSRF, auth bypass
