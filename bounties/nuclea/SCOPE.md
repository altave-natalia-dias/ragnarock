# Núclea / CIP-BANCOS — Bug Bounty (BugHunt)

Plataforma: BugHunt | Público | Publicado há 2 anos
Recompensas: Baixo R$0 | Médio R$250 | Alto R$1.000 | Crítico R$2.500
Bônus: Vulns em LLMs na infra = bounty EM DOBRO

## REGRAS OPERACIONAIS CRÍTICAS
- **Rate limit: MÁXIMO 12 req/min** (1 req a cada 5s)
- **PROIBIDO scanners automáticos**
- Sem brute-force, sem DoS, sem exaustão de recursos, sem comprometimento de contas
- Sem transações financeiras indevidas
- Sem criar contas falsas / dados falsos. NÃO há contas de teste.
- Se achar PII: PARAR, apagar dados, contatar security@nuclea.com.br
- Cuidado com redirects para fora do escopo
- Sigilo: NÃO divulgar findings publicamente sem consentimento

## ESCOPO (somente estes wildcards)
*.nuclea.com.br
*.detectaflow.com.br
*.apiimf.org.br
*.chequelegal.com.br
*.cip-bancos.org.br
*.crcp.org.br
*.crt4.com.br
*.nucleaassociacao.org.br
*.nucleachain.com.br
*.nucleaconecta.com.br
*.portaldaportabilidade.org.br
*.nuclea-cotas.com.br
*.nucleaportabilidade.com.br
*.saopauloconsig.com.br
*.pds-ext.org.br
*.portaldoparticipante.org.br
*.portaldoconsignado.com.br

## FORA DE ESCOPO / NÃO ELEGÍVEL (resumo)
- Qualquer domínio Núclea NÃO listado acima + todos subdomínios não listados
- Físico, eng. social, phishing, DoS/exaustão
- Stack traces 401/403/500 sem PoC, banner disclosure, robots.txt
- Clickjacking sem info sensível, CSRF em forms anônimos, logout CSRF
- Autocomplete/save-password, speedbump, captcha bypass/weak/missing, rate limit
- User enumeration (login/forgot), brute-force login, account lockout
- OPTIONS/TRACE, ataques SSL (BEAST/BREACH/reneg), forward secrecy, MFA ausente, email confirm, password complexity
- Headers de segurança ausentes (CSP/HSTS/X-Frame/X-Content-Type), flags de cookie (HttpOnly/SameSite/Secure)
- Content spoofing/text injection sem vetor, libs vulneráveis sem PoC, serviços de terceiros
- SPF/DKIM/DMARC, XMLRPC, tabnabbing
- CVEs/exploits publicados há < 45 dias

## Prioridades (correlação RAG bb_writeups p/ alvo financeiro)
1. GraphQL broken auth / BOLA (writeup score 0.63)
2. Authorization bypass via cache misconfig (0.60)
3. IDOR / BOLA em APIs financeiras
4. Mass assignment (role/is_admin)
5. JWT alg-confusion / none
6. SSRF (bônus se LLM na infra)
