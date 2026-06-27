# Finding R3 — Swagger UI (SpringFox 2.9.2) Exposto em Produção

**Título:** Swagger UI / SpringFox 2.9.2 acessível em API de produção sem autenticação  
**Severidade:** LOW (CVSS 5.3 — AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)  
**CWE:** CWE-548 (Exposure of Information Through Directory Listing) / CWE-200  
**Status:** Confirmado — `/swagger-ui.html` retorna 200 com SpringFox UI completo  
**Escopo originário:** `api.realizesolucoesfinanceiras.com.br` (em escopo explícito do programa)  
**Programa:** Realize Financeira — produção apenas

---

## Discovery Chain

```
httpx fingerprint: api.realizesolucoesfinanceiras.com.br
  → tech-detect: Spring Boot, Azion CDN (xufzemrit5.map.azionedge.com)
    → probe: GET /swagger-ui.html → HTTP 200
      → HTML contém "SpringFox 2.9.2" no JavaScript
        → Swagger UI completamente funcional sem autenticação
          → /v2/api-docs → 404 (spec não exposta nos caminhos padrão)
          → /swagger-resources → 404
          → /api/v2/api-docs → 404
```

---

## Evidências

### 1. HTTP 200 em /swagger-ui.html

```bash
$ curl -sk "https://api.realizesolucoesfinanceiras.com.br/swagger-ui.html" \
  -H "User-Agent: Mozilla/5.0..." -o /dev/null -w "%{http_code}"

200

$ curl -sk "https://api.realizesolucoesfinanceiras.com.br/swagger-ui.html" | grep -i "springfox\|swagger"

<title>Swagger UI</title>
<!-- springfox-swagger-ui.2.9.2 -->
<script src="springfox.js"></script>
```

### 2. Fingerprint completo

```bash
$ curl -sk "https://api.realizesolucoesfinanceiras.com.br/" -D - | grep -i "server\|x-powered\|via"

server: azion-nginx
via: 1.1 aZion (Media Gateway)
# Sem x-powered-by (Spring Boot não expõe)
```

### 3. Spec não encontrada (caminhos padrão — 404)

```bash
$ for path in /v2/api-docs /swagger-resources /api/v2/api-docs /openapi.json; do
    code=$(curl -sk "https://api.realizesolucoesfinanceiras.com.br$path" \
      -o /dev/null -w "%{http_code}")
    echo "$code  $path"
  done

404  /v2/api-docs
404  /swagger-resources
404  /api/v2/api-docs
404  /openapi.json
```

> A spec não está acessível nos caminhos padrão do SpringFox. Pode estar em path não-padrão, atrás de autenticação, ou desabilitada mas o UI não foi removido.

### 4. Actuator — access-controlled (403 em todos endpoints)

```bash
$ curl -sk "https://api.realizesolucoesfinanceiras.com.br/actuator" -o /dev/null -w "%{http_code}"
403
$ curl -sk "https://api.realizesolucoesfinanceiras.com.br/actuator/health" -o /dev/null -w "%{http_code}"
403
```

> Actuator está corretamente protegido — positivo. Apenas o Swagger UI escapou da proteção.

---

## Análise de Impacto

### Exposição atual

O Swagger UI sem spec exposta tem impacto limitado: 
- Revela que o backend é Spring Boot + SpringFox 2.9.2
- Versão SpringFox 2.9.2 é de 2018, sem manutenção ativa (EOL)
- CVE-2020-5421 (SpringFox 2.x) e CVE-2021-22044 (Spring Cloud) afetam versões antigas

### CVEs relevantes no SpringFox 2.9.2

| CVE | CVSS | Impacto |
|-----|------|---------|
| CVE-2022-22965 (Spring4Shell) | 9.8 | RCE via DataBinder — afeta Spring MVC sem servlet container update |
| CVE-2021-22112 | 8.8 | Privilege escalation Spring Security |
| SpringFox 2.9.2 last release | — | 2018 — sem patches de segurança desde então |

> **Nota:** Spring4Shell afeta Spring Framework 5.3.x < 5.3.18 / 5.2.x < 5.2.20. Requer JDK 9+. Confirmar versão real via `X-Application-Context` ou Actuator (atualmente 403).

### Escalada potencial

```
Swagger UI acessível
  → Spec descoberta (path não-padrão via dirbust: /realize/v2/api-docs?)
    → Todos os endpoints e parâmetros mapeados
      → Fuzzing direcionado de parâmetros financeiros
        → Potencial para IDOR, mass assignment, SQLi em endpoints não testados
```

---

## Remediação

### Opção A — Remover Swagger UI de produção (recomendada)

```yaml
# application-prod.yml
springfox:
  documentation:
    swagger-ui:
      enabled: false
```

### Opção B — Proteger com autenticação

```java
// SecurityConfig.java
http.authorizeRequests()
    .antMatchers("/swagger-ui.html", "/swagger-resources/**", "/v2/api-docs")
    .hasRole("INTERNAL")
    ...
```

### Atualizar SpringFox ou migrar para SpringDoc

SpringFox 2.9.2 está EOL. Migrar para:
- **SpringDoc OpenAPI 2.x** (substituto mantido) + OpenAPI 3.0
- Permite controle fino de visibilidade por ambiente

### Atualizar Spring Framework

Garantir Spring Framework >= 5.3.18 (Spring4Shell patch) e Spring Boot >= 2.6.6.
