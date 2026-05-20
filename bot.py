import os
import re
import asyncio
import logging
import threading
from urllib.parse import urlparse, urlencode, urlunparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import aiohttp

# ── Configurações ────────────────────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN")
AFILIADO_ID = os.environ.get("AFILIADO_ID", "chioli")
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN:
    raise ValueError("Configure DISCORD_TOKEN nas variáveis de ambiente!")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

DISCORD_API = "https://discord.com/api/v10"

# ── Servidor HTTP (keep alive Render) ────────────────────────────────────────
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
    HTTPServer(("0.0.0.0", PORT), KeepAlive).serve_forever()

# ── Funções de link ──────────────────────────────────────────────────────────
DOMINIOS_ML = [
    "mercadolivre.com.br",
    "mercadolibre.com",
    "ml.com.br",
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

def converter_links(texto: str, afiliado_id: str):
    regex = r"https?://[^\s<>\"']+"
    links = re.findall(regex, texto)
    texto_final = texto
    convertidos = []
    for link in links:
        if eh_link_ml(link):
            novo = adicionar_afiliado(link, afiliado_id)
            texto_final = texto_final.replace(link, novo)
            convertidos.append(novo)
    return texto_final, convertidos

# ── Gateway Discord via aiohttp puro ─────────────────────────────────────────
async def enviar_mensagem(session, channel_id, conteudo):
    url = f"{DISCORD_API}/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    payload = {"content": conteudo}
    async with session.post(url, json=payload, headers=headers) as r:
        if r.status not in (200, 201):
            logging.error(f"Erro ao enviar mensagem: {r.status}")

async def conectar_gateway():
    headers = {"Authorization": f"Bot {TOKEN}"}
    async with aiohttp.ClientSession() as session:
        # Pegar URL do gateway
        async with session.get(f"{DISCORD_API}/gateway", headers=headers) as r:
            data = await r.json()
            gateway_url = data["url"] + "?v=10&encoding=json"

        logging.info(f"Conectando ao gateway: {gateway_url}")

        async with session.ws_connect(gateway_url) as ws:
            heartbeat_interval = None
            sequence = None

            async def heartbeat():
                while True:
                    await asyncio.sleep(heartbeat_interval / 1000)
                    await ws.send_json({"op": 1, "d": sequence})

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.json()
                    op = data.get("op")
                    t = data.get("t")

                    if data.get("s"):
                        sequence = data["s"]

                    # Hello — iniciar heartbeat e identificar
                    if op == 10:
                        heartbeat_interval = data["d"]["heartbeat_interval"]
                        asyncio.create_task(heartbeat())
                        await ws.send_json({
                            "op": 2,
                            "d": {
                                "token": TOKEN,
                                "intents": 33280,  # GUILDS + GUILD_MESSAGES + MESSAGE_CONTENT
                                "properties": {
                                    "os": "linux",
                                    "browser": "bot",
                                    "device": "bot"
                                }
                            }
                        })

                    # Evento de mensagem
                    elif op == 0 and t == "MESSAGE_CREATE":
                        autor = data["d"].get("author", {})
                        if autor.get("bot"):
                            continue

                        conteudo = data["d"].get("content", "")
                        channel_id = data["d"]["channel_id"]

                        texto_convertido, links = converter_links(conteudo, AFILIADO_ID)

                        if links:
                            qtd = len(links)
                            plural = "link convertido" if qtd == 1 else "links convertidos"
                            resposta = f"🛒 {qtd} {plural} com afiliado:\n\n{texto_convertido}"
                            await enviar_mensagem(session, channel_id, resposta)

                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    logging.warning("WebSocket desconectado, reconectando...")
                    break

async def main():
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    logging.info(f"Servidor HTTP iniciado na porta {PORT}")
    logging.info("Bot Discord iniciando...")

    while True:
        try:
            await conectar_gateway()
        except Exception as e:
            logging.error(f"Erro: {e}")
        logging.info("Reconectando em 5 segundos...")
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
