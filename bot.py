import os
import re
import logging
import threading
import asyncio
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord

# ── Configurações ────────────────────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN")
AFILIADO_ID = os.environ.get("AFILIADO_ID", "chioli")
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN:
    raise ValueError("Configure DISCORD_TOKEN nas variáveis de ambiente!")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ── Servidor HTTP (keep alive para Render gratuito) ──────────────────────────
class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot rodando!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass

def iniciar_servidor():
    server = HTTPServer(("0.0.0.0", PORT), KeepAlive)
    server.serve_forever()

# ── Funções de link ──────────────────────────────────────────────────────────
DOMINIOS_ML = [
    "mercadolivre.com.br",
    "mercadolibre.com",
    "ml.com.br",
    "mlm.net.br",
    "produto.mercadolivre.com.br",
]

def eh_link_ml(url: str) -> bool:
    try:
        dominio = urlparse(url).netloc.lower().replace("www.", "")
        return any(dominio.endswith(d) for d in DOMINIOS_ML)
    except Exception:
        return False

def adicionar_afiliado(url: str, afiliado_id: str) -> str:
    try:
        parsed = urlparse(url)
        nova_query = urlencode({"matt_word": afiliado_id})
        return urlunparse(parsed._replace(query=nova_query, fragment=""))
    except Exception:
        return url

def extrair_e_converter_links(texto: str, afiliado_id: str):
    regex = r"https?://[^\s<>\"']+"
    links_encontrados = re.findall(regex, texto)
    texto_final = texto
    links_convertidos = []
    for link in links_encontrados:
        if eh_link_ml(link):
            novo_link = adicionar_afiliado(link, afiliado_id)
            texto_final = texto_final.replace(link, novo_link)
            links_convertidos.append((link, novo_link))
    return texto_final, links_convertidos

# ── Bot Discord ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")

@client.event
async def on_message(message):
    # Ignora mensagens do próprio bot
    if message.author == client.user:
        return

    texto = message.content
    if not texto.strip():
        return

    texto_convertido, links = extrair_e_converter_links(texto, AFILIADO_ID)

    if not links:
        return  # Ignora mensagens sem link do ML

    qtd = len(links)
    plural = "link convertido" if qtd == 1 else "links convertidos"

    await message.reply(f"🛒 {qtd} {plural} com afiliado:\n\n{texto_convertido}")

# ── Inicialização ────────────────────────────────────────────────────────────
async def main():
    t = threading.Thread(target=iniciar_servidor, daemon=True)
    t.start()
    print(f"🌐 Servidor HTTP iniciado na porta {PORT}")
    print("🤖 Bot Discord rodando...")
    await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
