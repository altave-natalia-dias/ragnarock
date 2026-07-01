# Email de Submissao — Amdax Responsible Disclosure

---

## Para: rd@amdax.com
## Assunto: [Responsible Disclosure] CORS Misconfiguration + GraphQL User Data Exposure (HIGH)

---

## Corpo do Email

---

Prezado time Amdax,

Durante um teste de seguranca responsavel, identifiquei uma vulnerabilidade de configuracao critica no dominio www.amdax.com. Seguem os detalhes conforme solicitado em sua politica de Responsible Disclosure.

---

### 1. Data e Hora da Descoberta
2026-06-29 18:00 BRT (UTC-3)

### 2. Tipo de Vulnerabilidade
CORS Misconfiguration (CWE-942) + Information Disclosure via GraphQL (CWE-200)

### 3. Servico/URL Afetado
https://www.amdax.com/api (GraphQL endpoint)

### 4. IP de Origem
201.1.100.69

### 5. Informacoes para Reproduzir

#### a) CORS Misconfiguration
O endpoint retorna Access-Control-Allow-Origin: * juntamente com Access-Control-Allow-Credentials: true para QUALQUER origem. Isso permite que qualquer dominio faca requisicoes cross-origin.

Comando para verificar:
```
curl -sv "https://www.amdax.com/api" -X OPTIONS -H "Origin: https://qualquer-site.com" -H "Access-Control-Request-Method: POST" 2>&1 | grep -i access-control
```

#### b) GraphQL sem Autenticacao
A query abaixo retorna dados de usuarios do sistema sem exigir qualquer token de autenticacao:
```
curl -s "https://www.amdax.com/api" -X POST -H "Content-Type: application/json" -d '{"query":"{ users { id name email } }"}'
```

Foram extraidos dados de usuarios (nomes e emails) via paginacao. Uma amostra representativa de 5 usuarios esta incluida abaixo como evidencia. O dataset completo (92 registros) esta disponivel se necessario para verificacao.

### 6. Confirmacao de Nao-Disrupcao
Nenhuma atividade foi realizada para interromper sistemas ou servicos. Nenhum dado foi copiado (alem do minimo necessario para PoC), alterado, vazado ou deletado. Nenhuma conta foi criada ou acessada.

### 7. Hall da Fama
Gostaria de ser incluido no Wall of Fame da Amdax.
Alias: Natalia Aparecida Souza Dias

### 8. GPG Key
Caso necessario, posso fornecer as evidencias completas via GPG. Por favor, informe a chave publica para encryptacao.

---

Atenciosamente,
Natalia Aparecida Souza Dias
201.1.100.69

---

## Arquivos Anexos

1. amdax_users_sample.csv — Amostra de 5 usuarios expostos via GraphQL (dataset completo disponivel se necessario)
2. amdax_cors_exploit_poc.html — PoC HTML funcional para reproducao

---

## Checklist Pre-Envio

- [ ] Substituir Natalia Aparecida Souza Dias pelo alias desejado
- [ ] Substituir Natalia Aparecida Souza Dias pelo seu nome ou pseudonimo
- [ ] Anexar o arquivo CSV de usuarios
- [ ] Anexar o PoC HTML (opcional)
- [ ] Enviar para rd@amdax.com
- [ ] Se dados sensiveis, usar GPG key
