#!/usr/bin/env python3
"""Telegram bot with HTTP notification endpoint for Pico Claw job-search agent."""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("telegram_bot")

HOST = "127.0.0.1"
PORT = 5003

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_ID = os.environ.get("TELEGRAM_OWNER_ID", "")

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data")
DB_PATH = os.path.join(DB_DIR, "seen_offers.db")
os.makedirs(DB_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "config", "search_params.yaml"
)

CV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cv", "curriculum.md"
)

bot_app: Application = None
bot_loop: asyncio.AbstractEventLoop = None
bot_ready = threading.Event()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS seen_offers ("
        "  url_hash TEXT,"
        "  title_hash TEXT,"
        "  notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "  PRIMARY KEY (url_hash, title_hash)"
        ")"
    )
    conn.commit()
    conn.close()


def is_duplicate(url: str, title: str) -> bool:
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    title_hash = hashlib.sha256(title.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT 1 FROM seen_offers WHERE url_hash=? AND title_hash=?",
        (url_hash, title_hash),
    )
    exists = cursor.fetchone() is not None
    if not exists:
        conn.execute(
            "INSERT INTO seen_offers (url_hash, title_hash) VALUES (?, ?)",
            (url_hash, title_hash),
        )
        conn.commit()
    conn.close()
    return exists


def get_cv_path() -> str:
    if os.path.exists(CV_PATH):
        return CV_PATH
    alt = "/app/cv/curriculum.md"
    if os.path.exists(alt):
        return alt
    return CV_PATH


async def send_telegram_message(chat_id: str, text: str) -> bool:
    try:
        await bot_app.bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        log.error("Failed to send message to %s: %s", chat_id, e)
        return False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\U0001f44b \u00a1Hola! Soy **Pico Claw**, tu asistente de b\u00fasqueda de empleo.\n\n"
        "Trabajo para encontrar las mejores ofertas de call center y ventas en Colombia "
        "que se ajusten a tu perfil. \ud83d\udc4d\n\n"
        "Usa /help para ver los comandos disponibles."
    )


async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\u23f3 B\u00fasqueda manual activada. Espera 2-5 min mientras reviso nuevas ofertas...\n\n"
        "Funcionalidad en desarrollo \u2014 el orquestador ejecutar\u00e1 el pipeline completo."
    )


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token_status = "\u2705 Configurado" if BOT_TOKEN else "\u274c No configurado"
    owner_status = "\u2705 Configurado" if OWNER_ID else "\u274c No configurado"
    db_exists = os.path.exists(DB_PATH)

    msg = (
        f"\U0001f535 **Estado de Pico Claw**\n\n"
        f"\U0001f916 **Bot Telegram:** {token_status}\n"
        f"\U0001f464 **Owner ID:** {owner_status}\n"
        f"\U0001f4be **Base datos ofertas:** {'\u2705 Creada' if db_exists else '\u26a0\ufe0f Pendiente'}\n"
        f"\U0001f310 **Servidor HTTP:** Puerto {PORT}\n"
    )
    await update.message.reply_text(msg)


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("\u26a0\ufe0f Solo el propietario puede usar este comando.")
        return
    try:
        import yaml
        with open(CONFIG_PATH, "r") as f:
            cfg = yaml.safe_load(f)
    except ImportError:
        await update.message.reply_text("PyYAML no instalado. No se puede leer la configuraci\u00f3n.")
        return
    except Exception as e:
        await update.message.reply_text(f"Error al leer configuraci\u00f3n: {e}")
        return

    keywords = ", ".join(cfg.get("keywords", []))
    location = cfg.get("location", "No especificada")
    modality = ", ".join(cfg.get("modality", []))
    portals = ", ".join(cfg.get("portals", []))
    msg = (
        f"\U0001f6e1\ufe0f **Configuraci\u00f3n de b\u00fasqueda**\n\n"
        f"\U0001f50d **Keywords:** {keywords}\n"
        f"\U0001f4cd **Ubicaci\u00f3n:** {location}\n"
        f"\U0001f3e0 **Modalidad:** {modality}\n"
        f"\U0001f310 **Portales:** {portals}\n"
    )
    await update.message.reply_text(msg)


async def cmd_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("\u26a0\ufe0f Solo el propietario puede usar este comando.")
        return
    cv_path = get_cv_path()
    if not os.path.exists(cv_path):
        await update.message.reply_text("\u274c No se encontr\u00f3 el archivo curriculum.md")
        return
    with open(cv_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename="curriculum.md",
            caption="\U0001f4c4 Curr\u00edculum vitae de Andr\u00e9s Felipe Botache Rojas",
        )


async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT COUNT(*) FROM seen_offers WHERE notified_at >= datetime('now', '-7 days')"
    )
    total = cursor.fetchone()[0]
    conn.close()
    msg = (
        f"\U0001f4ca **Historial (\u00faltimos 7 d\u00edas)**\n\n"
        f"Ofertas notificadas: **{total}**\n\n"
        f"Funcionalidad extendida en desarrollo \u2014 "
        f"pr\u00f3ximamente incluir\u00e1 puntajes y resumen por portal."
    )
    await update.message.reply_text(msg)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "\U0001f916 **Comandos disponibles**\n\n"
        "/start \u2014 Mensaje de bienvenida\n"
        "/buscar \u2014 Activar b\u00fasqueda manual\n"
        "/estado \u2014 Estado del bot y servicios\n"
        "/config \u2014 Ver configuraci\u00f3n de b\u00fasqueda (solo owner)\n"
        "/cv \u2014 Recibir CV en PDF (solo owner)\n"
        "/historial \u2014 Resumen de ofertas \u00faltimos 7 d\u00edas\n"
        "/help \u2014 Mostrar esta ayuda"
    )
    await update.message.reply_text(msg)


class NotificationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_json({"status": "ok"})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/send-message":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self.send_json({"error": f"Invalid JSON: {e}"}, 400)
            return

        chat_id = data.get("chat_id")
        text = data.get("text", "")
        url = data.get("url", "")
        title = data.get("title", "")

        if not chat_id or not text:
            self.send_json({"error": "chat_id and text are required"}, 400)
            return

        if url and title and is_duplicate(url, title):
            log.info("Duplicate offer skipped: %s - %s", title, url)
            self.send_json({"status": "skipped", "reason": "duplicate"})
            return

        future = asyncio.run_coroutine_threadsafe(
            send_telegram_message(chat_id, text),
            bot_loop,
        )
        try:
            success = future.result(timeout=15)
            if success:
                self.send_json({"status": "sent"})
            else:
                self.send_json({"error": "Failed to send message"}, 500)
        except Exception as e:
            log.error("Error sending message: %s", e)
            self.send_json({"error": str(e)}, 500)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        log.info(fmt, *args)


def run_http_server():
    bot_ready.wait(timeout=30)
    if not bot_ready.is_set():
        log.warning("Bot not ready within 30s, starting HTTP server anyway")
    server = HTTPServer((HOST, PORT), NotificationHandler)
    log.info("HTTP notification server listening on %s:%d", HOST, PORT)
    server.serve_forever()


async def post_init(app: Application):
    global bot_loop
    bot_loop = asyncio.get_running_loop()
    bot_ready.set()
    log.info("Telegram bot started and ready. Owner ID: %s", OWNER_ID or "not set")


async def async_main():
    global bot_app

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("cv", cmd_cv))
    app.add_handler(CommandHandler("historial", cmd_historial))
    app.add_handler(CommandHandler("help", cmd_help))

    bot_app = app

    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()


def main():
    if not BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
        raise SystemExit(1)
    if not OWNER_ID:
        log.warning("TELEGRAM_OWNER_ID not set. Owner-only commands will be unavailable.")

    init_db()
    log.info("SQLite database ready at %s", DB_PATH)

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    log.info("HTTP server thread started (waiting for bot readiness)")

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
