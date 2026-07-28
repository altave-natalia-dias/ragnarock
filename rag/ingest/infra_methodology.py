"""
Ingest infra-asset vulnerability taxonomy (message queues, containers,
Kubernetes/orchestrators, databases) + elite-researcher recon/exploit/
post-exploit methodology + severity-tier mindset framework + the 100-rule
"see beyond the obvious paths" playbook into the RAG.

Source: user-curated Gemini conversation (28/07/2026), reorganized into
retrievable chunks following the same pattern as ingest/knowledge.py and
ingest/web3.py. Content is operational/defensive-research knowledge (attack
PATTERNS and methodology, no target-specific exploit code) intended to sharpen
recon/triage judgment during authorized bug bounty engagements.

Standalone (adds ONLY these chunks to the existing `pentest_kb` collection):
    PYTHONPATH=/home/altave/.bughunter /home/altave/venv/bin/python3 -m rag.ingest.infra_methodology
"""
from __future__ import annotations
import sys
from pathlib import Path

RAG_DIR = Path(__file__).parent.parent

INFRA_KB: list[tuple[str, dict]] = []


def _kb(text: str, tags: list[str], category: str = "infra_ops"):
    INFRA_KB.append((text.strip(), {
        "type":     "pentest_kb",
        "category": category,
        "tags":     ",".join(tags),
    }))


# ==================================================================== #
# 1. MESSAGE QUEUES — errors + recon/exploit/post-exploit               #
# ==================================================================== #
_kb("""
FILAS DE MENSAGERIA (RabbitMQ, Kafka, SQS, Redis) — Erros Recorrentes

- Falta de autenticação/autorização: instâncias expostas com credenciais
  padrão (guest/guest) ou sem senha.
- Deserialização insegura: consumidores que desserializam payloads não
  confiáveis (pickle Python, deserialização Java) → RCE.
- Falta de criptografia em trânsito: AMQP/HTTP em texto plano → MitM,
  leitura/injeção de mensagens na rede interna.
- Painéis de admin expostos: porta de management (RabbitMQ 15672) acessível
  externamente sem restrição de IP.

Padrão de exploração: varrer portas expostas (5672, 6379, 9092, 4222),
testar credenciais padrão, injetar mensagens maliciosas em tópicos públicos,
explorar falha de auth pra esvaziar/manipular filas e escalar privilégio.
""", ["messaging", "rabbitmq", "kafka", "redis", "sqs", "default-creds", "recon"], "messaging")

_kb("""
FILAS DE MENSAGERIA — Metodologia Recon/Exploit/Post-Exploit

RECON:
  - Nmap/Masscan portas padrão: 5672/15672 (RabbitMQ), 6379 (Redis),
    9092 (Kafka), 4222 (NATS).
  - Shodan/Censys + gobuster/ffuf por painéis web (/rabbitmq/, /manager/).
  - Fingerprint de banner de conexão pra achar versão vulnerável a CVE
    pública de RCE/auth-bypass.

EXPLOIT:
  - Credenciais padrão (guest:guest, admin:admin, sem auth).
  - Conexão direta via cliente legítimo (pika, kafka-python, redis-py) pra
    injetar mensagem maliciosa em tópico crítico.
  - Redis: se CONFIG SET estiver liberado, alterar working dir pra
    /var/spool/cron/ e injetar cronjob via persistência de dados → RCE.

POST-EXPLOIT:
  - Exfiltrar dados em trânsito (PII, tokens, chaves de API trafegando
    entre microsserviços).
  - Usar o broker como pivô/vetor de propagação pra outros nós que confiam
    na identidade da fila.
""", ["messaging", "recon", "exploit", "post-exploit", "rce", "redis-cronjob"], "messaging")


# ==================================================================== #
# 2. CONTAINERS (Docker) — errors + recon/exploit/post-exploit          #
# ==================================================================== #
_kb("""
CONTAINERS (Docker) — Erros Recorrentes

- Execução como root (UID 0) dentro do container: se houver escape, o
  atacante ganha root imediato no host.
- --privileged: desativa isolamento de kernel (cgroups, namespaces),
  permite acesso direto a devices do host e montagem de discos.
- Socket Docker exposto (/var/run/docker.sock) montado dentro do container
  (comum em CI/CD) → container cria novo container privilegiado no host.
- Imagens base desatualizadas com CVEs conhecidas (alpine, ubuntu antigos).

Padrão de exploração: varrer sockets Docker expostos, explorar app web
vulnerável dentro do container pra acesso inicial, depois técnica de escape
via falha de kernel ou privilégio excessivo.
""", ["containers", "docker", "escape", "privileged", "docker-socket", "recon"], "containers")

_kb("""
CONTAINERS — Metodologia Recon/Exploit/Post-Exploit

RECON:
  - Fingerprint via headers HTTP/mensagens de erro que denunciem Docker
    Engine/Docker API.
  - Varrer porta 2375/2376 (API Docker sem TLS) ou socket Unix mapeado
    indevidamente em app vulnerável a LFI/RCE.

EXPLOIT:
  - Escape via docker.sock: se montado dentro de container comprometido,
    interagir via curl/CLI pra criar container privilegiado com `/` do host
    montado → controle imediato da máquina física.
  - Escape via falha de kernel: exploit público contra namespaces/cgroups
    a partir de processo root dentro do container.
  - Abuso de --privileged: `fdisk -l`, `mount /dev/sda1 /mnt` de dentro do
    container pra ler /etc/shadow ou injetar chave SSH autorizada.
  - Auditoria de capabilities: `cat /proc/self/status`, `capsh --print` —
    se CAP_SYS_ADMIN ativo, monta filesystem do host sem exploit de kernel,
    só abusando de config nativa mal aplicada.

POST-EXPLOIT:
  - Persistência: novo container oculto iniciando com o SO do host, ou
    serviço systemd malicioso injetado.
  - Roubo de credenciais de containers vizinhos via inspeção de processo
    ou volume compartilhado.
""", ["containers", "recon", "exploit", "post-exploit", "docker-socket-escape", "capabilities"], "containers")


# ==================================================================== #
# 3. KUBERNETES / ORQUESTRADORES — errors + recon/exploit/post-exploit  #
# ==================================================================== #
_kb("""
KUBERNETES (K8s) — Erros Recorrentes

- API Server exposta sem RBAC adequado, ou porta 6443 acessível
  publicamente sem restrição.
- ServiceAccount over-privileged: ClusterRoleBinding com wildcard `*` em
  verbos/recursos — comprometer 1 pod = controle total do cluster.
- Falta de NetworkPolicies: tráfego lateral livre entre namespaces/pods
  por padrão.
- Secrets em texto plano (Base64 no etcd sem criptografia em repouso) ou
  expostos em env vars via `kubectl describe`.

Padrão de exploração: descobrir API exposta, enumerar permissão via
`kubectl auth can-i`, roubar token de ServiceAccount montado em
/var/run/secrets/kubernetes.io/serviceaccount/token, mover lateralmente
até dominar o plano de controle (cluster takeover).
""", ["kubernetes", "k8s", "rbac", "serviceaccount", "cluster-takeover", "recon"], "kubernetes")

_kb("""
KUBERNETES — Metodologia Recon/Exploit/Post-Exploit

RECON:
  - Localizar API Server (6443) ou Kubelet (10250) via varredura de rede
    ou certificado SSL autoassinado característico.
  - Enumerar permissões com token obtido: `kubectl auth can-i --list`, ou
    query manual à API pra mapear recursos legíveis/modificáveis
    (Pods, Secrets, ServiceAccounts).

EXPLOIT:
  - Roubar token de ServiceAccount ao obter execução em qualquer Pod
    (/var/run/secrets/kubernetes.io/serviceaccount/token).
  - Abusar de permissão excessiva: usar o token pra criar Pod que monta
    root filesystem do Node, ou conceder cluster-admin à própria
    ServiceAccount de baixo privilégio.
  - Kubelet anônimo: porta 10250 com `--anonymous-auth=true` permite
    execução arbitrária de comando direto nos nós.
  - Testar verbos de API menos óbvios: `impersonate`, `bind`, `escalate` —
    ver se a API concede cluster-admin indevidamente via encadeamento de
    permissões aparentemente inofensivas.

POST-EXPLOIT:
  - Cluster takeover: exportar todos os Secrets do etcd (senhas, chaves,
    credenciais de banco).
  - Cryptojacking/sprawl: usar recursos computacionais do cluster.
""", ["kubernetes", "recon", "exploit", "post-exploit", "kubelet", "token-theft", "rbac-escalation"], "kubernetes")


# ==================================================================== #
# 4. BANCOS DE DADOS — errors + recon/exploit/post-exploit              #
# ==================================================================== #
_kb("""
BANCOS DE DADOS (Relacionais e NoSQL) — Erros Recorrentes

- Exposição direta à internet: PostgreSQL (5432), MySQL (3306), MSSQL
  (1433), MongoDB (27017), Redis em IP público.
- SQLi/NoSQLi por validação inadequada de entrada.
- Privilégio excessivo: app conecta com superusuário (postgres/root) —
  comprometimento da app = comprometimento total do SGBD (leitura de
  arquivo via COPY/xp_cmdshell).
- Ausência de criptografia em repouso e de auditoria de queries anômalas.

Padrão de exploração: identificar porta aberta, testar injeção em
parâmetro de form/API, abusar de função administrativa integrada pra
escalar privilégio no SO subjacente.
""", ["database", "sql", "nosql", "sqli", "privilege-escalation", "recon"], "databases")

_kb("""
BANCOS DE DADOS — Metodologia Recon/Exploit/Post-Exploit

RECON:
  - Nmap fingerprint de porta/versão (5432/3306/1433/27017/6379).
  - sqlmap ou teste manual de validação em login/API/busca.

EXPLOIT:
  - SQLi clássica: UNION, error-based, boolean-blind, time-based.
  - Abuso de função admin: xp_cmdshell (SQL Server), `COPY ... TO PROGRAM`
    (PostgreSQL), UDF maliciosa (MySQL) — se o usuário conectado tiver
    privilégio elevado.
  - NoSQLi lógica: operadores JSON tipo `{"$ne": null}` ou `{"$gt": ""}`
    pra burlar tela de login em Mongo.

POST-EXPLOIT:
  - Dump de tabelas com dados confidenciais/hashes de senha (avaliar
    força do hash pra quebra offline com hashcat).
  - Criar novo usuário admin no banco pra persistência de longo prazo;
    usar credencial do SGBD pra pivotar pra outros sistemas integrados.
""", ["database", "recon", "exploit", "post-exploit", "sqli", "stored-procedure-abuse", "nosqli"], "databases")


# ==================================================================== #
# 5. MINDSET DE PESQUISADOR ELITE — recon/exploit/post-exploit          #
# ==================================================================== #
_kb("""
MINDSET DO PESQUISADOR SÊNIOR — Antes de rodar qualquer comando

Não pergunta só "quais portas estão abertas". Pergunta:
  - Onde há assunção de confiança? (ex.: microsserviço confia cegamente
    no payload da fila porque está na mesma VPC?)
  - Onde a complexidade esconde o caos? (ex.: como o controller do K8s
    reconcilia estado desejado vs atual, e onde há race condition nisso?)
  - Qual é o caminho não-intencional? (ex.: API de cache pensada só pra
    localhost, mas o proxy reverso encaminha X-Forwarded-For?)

Recon avançado raramente é varredura barulhenta logo de início (evita
IDS/IPS) — é cirúrgico e guiado por contexto: análise estática de código
(Dockerfiles, Helm charts, manifests K8s) buscando suposição perigosa;
fingerprint silencioso via requisição malformada e timing.
""", ["mindset", "recon", "senior-researcher", "trust-boundary"], "mindset")

_kb("""
MINDSET — Encadeamento de Falhas por Ativo (Chaining)

A genialidade sênior está em encadear falhas pequenas e inofensivas em
impacto crítico:

- Fila: "Se o broker exige auth pro consumidor, o produtor valida
  esquema? Injetar objeto que força desserialização arbitrária?"
- Container: "Roda como root mas com capabilities restritas — quais
  capabilities sobraram por preguiça operacional (CAP_SYS_ADMIN,
  CAP_SYS_PTRACE, CAP_DAC_READ_SEARCH)?"
- K8s: "RBAC bloqueia criar Pod, mas permite criar Deployment/Job que
  herda ServiceAccount privilegiada? Kubelet 10250 aceita exec sem
  mTLS configurado certo?"
- Banco: "SQLi clássica já mapeada, mas como o ORM traduz parâmetro
  complexo? Dá pra manipular JSON pra forçar operador de comparação
  implícito num NoSQL?"
""", ["mindset", "chaining", "capabilities", "orm", "senior-researcher"], "mindset")

_kb("""
MINDSET — Pós-Exploit de Elite (não é só pegar /etc/shadow)

- Persistência invisível: em vez de cronjob barulhento, usa
  comportamento nativo da arquitetura (injetar chave em Secret K8s
  gerenciado por operador legítimo, hook em evento de fila).
- Lateralização por identidade, não por rede: em cloud moderna, perímetro
  de rede importa menos que identidade — foca em roubar metadados de
  instância (AWS IMDSv1/v2, token de ServiceAccount) pra pivotar via
  API de nuvem.
- Relatório em linguagem de risco de negócio: traduz a falha técnica pra
  "vazamento de dado regulado (LGPD/GDPR)" ou "paralisação operacional",
  não só CVSS cru.
""", ["mindset", "post-exploit", "persistence", "lateral-movement", "reporting", "business-risk"], "mindset")

_kb("""
MINDSET — Framework de Severidade (Medium / High / Critical / Excepcional)

MEDIUM — domínio da lógica local e vazamento de informação: enumerar
comportamento não-intencional que não quebra o sistema mas expõe
privacidade/consistência (enumeração de usuário, erro verboso, IDOR de
leitura em dado não-sensível). Foco: controles de acesso secundários e
higiene de dado.

HIGH — quebra de limite/perímetro (BOLA, SSRF, IDOR crítico): assume
papel de usuário mal-intencionado cruzando barreira lógica vertical ou
horizontal sem autorização. Foco: comprometer conta de terceiro, dado
financeiro, manipular preço, saltar pra rede interna via servidor exposto.

CRITICAL — comprometimento do núcleo (RCE, deserialização, injection
total): pensa como invasor avançado buscando execução de código no
servidor ou controle total do plano de controle de nuvem. Foco: pontos de
entrada de dado não-confiável (upload, fila, serialização) forçando SO/
interpretador a executar comando arbitrário.

EXCEPCIONAL (0-day / arquitetural / cadeia complexa) — visão holística de
arquiteto reverso: não busca falha isolada, busca falha de DESIGN que
invalida toda a premissa de segurança do produto. Encadeia 3-4
vulnerabilidades menores (ex.: CSRF → SSRF → deserialização em
microsserviço interno isolado). Exige paciência cirúrgica, PoC
customizado, e tradução do colapso técnico em relatório irrefutável pra
diretoria executiva.
""", ["mindset", "severity", "medium", "high", "critical", "exceptional", "0day", "chaining"], "mindset")


# ==================================================================== #
# 6. "100 REGRAS" — playbook de visão além do óbvio (10 módulos)        #
# ==================================================================== #
_kb("""
MÓDULO 1 — Visão Além do Óbvio (Recon e Mapeamento Mental)

1. Código legado é cemitério de features esquecidas: /api/v1/ ou /old/
   ainda hospedado junto da v2 corrigida.
2. Parâmetros ocultos = superfície invisível: força bruta de parâmetro
   (Arjun) acha ?debug=true, ?admin=1, ?test=bypass em endpoint estático.
3. Erro de tipagem revela backend: forçar array [] onde se espera string
   "" expõe stack trace com stack tecnológico e caminho absoluto.
4. Homologação conversa com produção: stg/dev/sandbox/uat raramente tem
   hardening igual a prod, às vezes compartilha string de conexão do BD.
5. Source maps (.js.map) revelam rota interna de API, chave de serviço e
   lógica exata de auth do client.
6. .git/ exposto: baixar o repo inteiro expõe segredo removido mas ainda
   presente no histórico de commit.
7. Swagger/OpenAPI/GraphQL sem proteção (/swagger-ui.html, /api-docs,
   /graphql) entrega mapa de navegação completo.
8. Cabeçalho de proxy engana borda: X-Forwarded-For, X-Original-URL,
   X-Rewrite-URL frequentemente burlam controle de acesso.
9. M&A deixa infra esquecida apontada pra IP legado → subdomain takeover.
10. Storage externo (S3/GCS) vinculado à app frequentemente tem permissão
    de escrita incorreta ou listagem de diretório habilitada.
""", ["playbook", "recon", "parameter-mining", "source-map", "git-exposure", "swagger", "takeover"], "playbook_rules")

_kb("""
MÓDULO 2 — Lógica de Negócio e Autorização (IDOR, BOLA, Race Condition)

11. ID sequencial previsível → testar UUID parcial, hash alterado,
    substituição de tipo (string em vez de inteiro).
12. IDOR em método HTTP alternativo: se GET bloqueia, testar POST/PUT ou
    header X-HTTP-Method-Override: GET.
13. Bypass de fluxo multi-etapa: pular etapa chamando direto a API da
    última etapa (ex.: pular pagamento, chamar confirmação de pedido).
14. Race condition em cupom/crédito: requisições paralelas idênticas pra
    aplicar o mesmo cupom múltiplas vezes antes do banco atualizar saldo.
15. Preço do lado do client nunca é confiável: alterar valor unitário no
    JSON interceptado, enviar negativo ou zero.
16. BOLA vertical ≠ horizontal: testar conta parceira acessando dado de
    admin, não só usuário comum vs usuário comum.
17. Fluxo "esqueci senha": token derivado de dado previsível (timestamp,
    email em MD5 sem salt)? Expira certo após uso?
18. Sessão após logout: token continua válido em endpoint secundário
    depois do usuário clicar "Sair"?
19. Campo de privilégio oculto no cadastro: enviar "is_admin":true,
    "role":"superuser", "verified":true extra no JSON de registro.
20. Rate limit por IP vs por usuário: se login bloqueia por IP, alternar
    X-Forwarded-For a cada tentativa = força bruta infinita.
""", ["playbook", "idor", "bola", "race-condition", "mass-assignment", "business-logic"], "playbook_rules")

_kb("""
MÓDULO 3 — Injeções Modernas e Deserialização (RCE, SSRF, NoSQLi)

21. Toda função "importar por URL"/webhook é vetor de SSRF pra varrer
    rede interna (metadata AWS 169.254.169.254).
22. Bypass de filtro SSRF via DNS rebinding: domínio que alterna IP
    externo válido (passa na validação) pra IP interno (2ª consulta).
23. NoSQLi por operador JSON: {"$ne": null} ou {"$gt": ""} pra burlar
    verificação de senha no Mongo.
24. SSTI em campo de nome/perfil refletido em template (Jinja2/Twig/
    Thymeleaf): ${7*7} ou {{7*7}}.
25. Mass assignment: enviar propriedade não-intencional no payload de
    update de perfil (ex.: alterar `balance`/`credits` junto do nome).
26. Prototype pollution em Node: função de merge com __proto__.admin=true
    via JSON aninhado.
27. Deserialização em fila sem validação de esquema → injetar objeto
    serializado malicioso pra atingir o worker.
28. XXE em upload (SVG/XLSX/PDF modificado com entidade externa) pra ler
    /etc/passwd.
29. SQLi de segunda ordem: string maliciosa salva com segurança num
    campo, executada sem sanitização depois num relatório automatizado.
30. Command injection mascarado: função de processamento de mídia
    (ffmpeg, convert) recebendo nome de arquivo direto pro binário do SO.
""", ["playbook", "ssrf", "ssti", "nosqli", "prototype-pollution", "xxe", "second-order-sqli", "mass-assignment"], "playbook_rules")

_kb("""
MÓDULO 4 — Cloud, Containers e Orquestradores

31. SSRF/RCE deve sempre mirar extração de credencial IAM temporária via
    /latest/meta-data/iam/security-credentials/.
32. Varredura profunda em repo público do GitHub da empresa pra achar
    chave AWS, token Slack, segredo JWT hardcoded.
33. CORS ultra-permissivo: Access-Control-Allow-Origin: * +
    Allow-Credentials: true = roubo de sessão autenticada.
34. Bucket S3 com policy pública de escrita → upload de HTML/JS pra
    Stored XSS via domínio da própria empresa.
35. Painel de métrica exposto sem auth: Prometheus (9090), Grafana
    (3000), Kube State Metrics.
36. Container com UID 0: `id` logo após ganhar execução, pra avaliar
    risco de escape pro host.
37. Volume de host perigoso montado em pod (/, /var/run/docker.sock)
    acessível por pod de baixo privilégio.
38. Sem NetworkPolicy no K8s = tráfego lateral livre entre namespaces.
39. Lambda com role IAM excessiva (AdministratorAccess) + falha de
    injeção no evento de entrada = alvo crítico.
40. Tela de erro detalhada vazando variável de ambiente com senha de
    banco e chave privada.
""", ["playbook", "cloud", "aws", "iam", "cors", "s3", "containers", "kubernetes", "serverless"], "playbook_rules")

_kb("""
MÓDULO 5 — Criptografia, Autenticação e Gestão de Sessão

41. JWT "alg":"none" + assinatura removida — testa se servidor aceita.
42. JWT HS256 com segredo curto/comum — brute-force offline pra forjar
    token de admin.
43. Hash de senha com algoritmo obsoleto (MD5/SHA1 sem salt) — rainbow
    table.
44. Logout/troca de senha realmente revoga token ativo emitido antes?
45. Regex de validação de origem CORS fraca (.*target\\.com) — registrar
    eviltarget.com passa na validação.
46. OAuth2 redirect_uri manipulável — enviar código de auth pra servidor
    controlado pelo atacante.
47. CSRF em endpoint sensível (troca de e-mail/senha): token anti-CSRF
    robusto? Cookie SameSite configurado certo?
48. Token de reset de senha/API key trafegando em parâmetro GET fica
    salvo em histórico de navegador e log de proxy.
49. Session fixation: identificador de sessão muda depois do login com
    sucesso?
50. CBC padding oracle: app revela erro detalhado de decifragem de bloco
    criptografado.
""", ["playbook", "jwt", "crypto", "cors", "oauth", "csrf", "session", "padding-oracle"], "playbook_rules")

_kb("""
MÓDULO 6 — Sabedoria Operacional e Psicologia do Bounty Hunter

51. Foque na lógica, não só na ferramenta — ferramenta acha o óbvio,
    lógica humana acha o que o dev não imaginou.
52. Entenda o negócio do alvo pra argumentar impacto real na triagem.
53. Relatório cirúrgico: claro, direto, PoC reproduzível, impacto de
    negócio na primeira linha.
54. Velocidade + profundidade evita duplicata: enquanto todo mundo testa
    o óbvio nos primeiros 10min, mapeie fluxo secundário que ninguém olha.
55. Monitore scope creep: novo endpoint/API adicionado sem aviso = bug
    fácil pra quem testar primeiro.
56. Leia código-fonte aberto de componente open-source usado pelo alvo,
    analise estaticamente em laboratório antes de testar em prod.
57. Paciência analítica: bounty crítico vem de horas de análise silenciosa
    seguidas de insight lógico repentino.
58. Automatize o repetitivo (scan de diretório/parâmetro), reserve
    capacidade mental pra análise lógica de fluxo.
59. Respeite as regras de engajamento — nunca DoS agressivo, nunca acesse
    dado de usuário real além do estritamente necessário pra PoC.
60. Estude disclosure público (HackerOne/Bugcrowd) pra entender o
    raciocínio de quem achou falha complexa.
""", ["playbook", "mindset", "reporting", "triage", "scope-creep", "ethics"], "playbook_rules")

_kb("""
MÓDULO 7 — Técnicas Avançadas de Evasão e Exploração Fina

61. Bypass de WAF via double URL encoding (%252e%252e%252f) em path
    traversal.
62. HTTP Request Smuggling (CL.TE/TE.CL) por inconsistência entre proxy
    e backend no tratamento de Content-Length/Transfer-Encoding.
63. Cache poisoning via header não-keyado (X-Forwarded-Host) refletido e
    cacheado pela CDN pra todos os usuários seguintes.
64. Investigar dependência npm desatualizada importada no frontend.
65. Race condition em troca de e-mail simultânea com reset de senha pra
    sequestrar fluxo de token.
66. Upload com nome de arquivo contendo char de escape de shell
    (`test; id > /tmp/pwn.txt; .jpg`) pra testar processamento local.
67. GraphQL com introspecção ativa → mapear todo tipo/mutation/query
    oculto que não aparece na doc oficial.
68. Tag HTML/JS maliciosa em campo exportado pra PDF via headless
    (Puppeteer) → RCE ou SSRF interno.
69. Analisar CSP `script-src`/`connect-src` pra descobrir domínio e API
    de terceiro integrada oculta.
70. IV estático em criptografia simétrica → replay attack ou decifragem.
""", ["playbook", "waf-bypass", "request-smuggling", "cache-poisoning", "graphql", "csp", "iv-reuse"], "playbook_rules")

_kb("""
MÓDULO 8 — Engenharia de Contexto e Perspectiva Ofensiva

71. Pense como o arquiteto, ataque como o adversário — entenda por que o
    sistema foi desenhado assim pra prever onde o atalho de dev foi
    tomado.
72. Integração de terceiro (gateway de pagamento, CRM, login social)
    costuma falhar na validação de estado, mesmo com o core seguro.
73. Erro de lógica em conversão de moeda/arredondamento de fração de
    centavo em sistema financeiro → acúmulo de crédito indevido.
74. Header de geolocalização (X-Country-Code, CF-IPCountry) manipulável
    pra burlar restrição geográfica.
75. Timing attack em comparador de string de token corporativo.
76. Gateway valida JWT mas microsserviço interno confia cegamente no
    header repassado sem revalidar.
77. WebSocket confiando em mensagem binária/JSON sem a mesma validação
    rigorosa da requisição HTTP tradicional.
78. Token de sessão mobile de longa duração que não invalida mesmo após
    atualização de versão do app.
79. Enumeração de usuário via diferença de tempo/tamanho de resposta
    entre e-mail cadastrado e não-cadastrado.
80. Mass assignment avançado: campo interno de controle de estado
    (deleted_at, created_by) modificável via update em massa.
""", ["playbook", "microservices", "payment-integration", "geolocation", "timing-attack", "websocket", "mobile-token"], "playbook_rules")

_kb("""
MÓDULO 9 — Maestria, Resiliência e Ética

81. Diário de laboratório com toda hipótese testada e descartada evita
    retrabalho em alvo complexo.
82. Relatório "Not Applicable" ensina a lógica de defesa da empresa mais
    que dez relatórios aceitos.
83. Especialize-se num nicho (GraphQL, K8s, lógica de pagamento) antes de
    generalizar.
84. Conhecer LGPD/GDPR ajuda a contextualizar gravidade de vazamento pra
    o analista de triagem.
85. Confie em script próprio (Python/Bash) mais que em ferramenta pública
    que muda de comportamento sem aviso.
86. A ética é a linha entre pesquisador de elite e criminoso: escopo
    autorizado + comunicação transparente com o programa.
87. Ceticismo técnico radical: questione premissa estabelecida ("é seguro
    porque usa HTTPS?", "é imune porque usa framework moderno?").
88. Engenharia reversa de mobile (APK/iOS) revela regra de segurança de
    API escondida na lógica compilada do client.
89. Recon passivo contínuo em background pra ser o primeiro a testar
    funcionalidade nova lançada.
90. Falha crítica real geralmente vem de erro estúpido de configuração,
    não de exploit matemático complexo — simplicidade vence complexidade.
""", ["playbook", "mindset", "ethics", "lab-notebook", "specialization", "lgpd", "gdpr", "reverse-engineering"], "playbook_rules")

_kb("""
MÓDULO 10 — O Toque Final do Pesquisador de Elite

91. Deploy de sexta à tarde tem a maior densidade de erro/bypass — janela
    de fadiga do dev.
92. Nunca submeta sem validar a PoC em instância limpa/isolada primeiro.
93. Changelog de dependência popular aponta exatamente que tipo de falha
    foi corrigida — procure onde o patch falhou (bypass parcial).
94. Rastreie o dado do input do usuário até o storage final — cada ponto
    de transformação é ponto de falha potencial.
95. Cuidado com falso-positivo de scanner (ex.: "XSS" que a codificação
    de saída na verdade impede) — validação manual é obrigatória.
96. Comunicação escrita clara evita rejeição por má interpretação da
    triagem, mesmo em bug crítico real.
97. Inspecione toda requisição de rede em SPA rica (React/Vue) via
    DevTools — endpoint sensível costuma vazar no bundle do client.
98. Entenda como API Gateway (Kong, Apigee, Envoy) trata header de auth e
    contexto de roteamento.
99. Antes de reportar, tente provar a si mesmo que o achado NÃO é
    explorável — eleva taxa de aceitação pra quase 100%.
100. O exploit de verdade é a mente do pesquisador: hardware/software
     evolui, mas sistema complexo feito por humano sempre tem ponto cego
     lógico gerado por premissa não questionada.
""", ["playbook", "deployment-timing", "poc-validation", "changelog-diffing", "data-flow", "false-positive", "reporting"], "playbook_rules")


def ingest_infra_methodology(rag=None):
    from rag.store import get_rag
    r = rag or get_rag()
    print(f"  Upserting {len(INFRA_KB)} infra/mindset/playbook KB records → pentest_kb …")
    r.upsert_batch("pentest_kb", INFRA_KB)
    print("  Infra + methodology + playbook knowledge ingested.")


if __name__ == "__main__":
    sys.path.insert(0, str(RAG_DIR.parent))
    ingest_infra_methodology()
    print("Done.")
