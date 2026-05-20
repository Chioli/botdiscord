# 🤖 Bot de Afiliado ML — Discord

Converte automaticamente links do Mercado Livre postados no Discord para links de afiliado.

---

## Como criar o bot no Discord

1. Acesse https://discord.com/developers/applications
2. Clique em **New Application** e dê um nome
3. Vá em **Bot** no menu lateral → clique em **Add Bot**
4. Em **Privileged Gateway Intents**, ative **Message Content Intent**
5. Copie o **Token** do bot
6. Vá em **OAuth2 → URL Generator**:
   - Marque **bot** em Scopes
   - Marque **Read Messages** e **Send Messages** em Bot Permissions
7. Acesse a URL gerada e adicione o bot ao seu servidor

## Deploy no Render

1. Suba os arquivos no GitHub
2. Crie um Web Service no render.com
3. Adicione as variáveis:
   - `DISCORD_TOKEN` = token do bot
   - `AFILIADO_ID` = chioli
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python bot.py`
