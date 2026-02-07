# ================= CHANNEL BEAUTIFY PRO =================
import logging
import sqlite3
import os
import threading
import time
import shutil

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")

DB_NAME = "bot_tags.db"
INVISIVEL = "⠀"

logging.basicConfig(level=logging.INFO)

# ================= BANCO =================
def db():
    return sqlite3.connect(DB_NAME)

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS canais (
            chat_id INTEGER PRIMARY KEY,
            ativo INTEGER DEFAULT 1,
            texto_inicio TEXT DEFAULT '',
            texto_fim TEXT DEFAULT '',
            tags_inicio TEXT DEFAULT '',
            tags_fim TEXT DEFAULT '',
            botao_texto TEXT DEFAULT '',
            botao_link TEXT DEFAULT '',
            espaco INTEGER DEFAULT 2
        )
        """)

def get_cfg(chat_id):
    with db() as con:
        cur = con.execute("SELECT * FROM canais WHERE chat_id=?", (chat_id,))
        return cur.fetchone()

def set_cfg(chat_id, campo, valor):
    with db() as con:
        con.execute(f"UPDATE canais SET {campo}=? WHERE chat_id=?", (valor, chat_id))

def reset_cfg(chat_id):
    with db() as con:
        con.execute("""
        UPDATE canais SET
        texto_inicio='',
        texto_fim='',
        tags_inicio='',
        tags_fim='',
        botao_texto='',
        botao_link='',
        espaco=2
        WHERE chat_id=?
        """, (chat_id,))

def all_canais():
    with db() as con:
        return con.execute("SELECT chat_id FROM canais").fetchall()

# ================= UTIL =================
def gerar_espaco(n):
    return "\n" * n

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Meus Canais / Grupos", callback_data="canais")]
    ])
    await update.message.reply_text(
        "🤖 **Channel Beautify PRO**\n\n"
        "✨ Embeleza postagens automaticamente\n"
        "📸 🎬 🎵 Texto, imagem, vídeo e música\n"
        "🎨 Totalmente configurável pelo menu\n\n"
        "👉 Adicione o bot como **ADMIN** no canal.",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================= MENU =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "canais":
        canais = all_canais()
        if not canais:
            await q.message.reply_text("❌ Nenhum canal registrado.\nPoste algo primeiro.")
            return

        kb = [
            [InlineKeyboardButton(f"📢 {cid[0]}", callback_data=f"cfg:{cid[0]}")]
            for cid in canais
        ]
        await q.message.reply_text("📢 Selecione o canal:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("cfg:"):
        chat_id = int(data.split(":")[1])
        context.user_data["chat_id"] = chat_id

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏ Texto início", callback_data="ti"),
             InlineKeyboardButton("✏ Texto fim", callback_data="tf")],
            [InlineKeyboardButton("🏷 Tags início", callback_data="tgi"),
             InlineKeyboardButton("🏷 Tags fim", callback_data="tgf")],
            [InlineKeyboardButton("🔘 Botão texto", callback_data="bt"),
             InlineKeyboardButton("🔗 Botão link", callback_data="bl")],
            [InlineKeyboardButton("📏 Espaçamento", callback_data="espaco")],
            [InlineKeyboardButton("🔌 Ativar / Desativar", callback_data="toggle")],
            [InlineKeyboardButton("🗑 Resetar tudo", callback_data="reset")],
        ])
        await q.message.reply_text(
            f"⚙️ Configuração do canal:\n`{chat_id}`",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return

    if data in {"ti", "tf", "tgi", "tgf", "bt", "bl"}:
        context.user_data["edit"] = data
        await q.message.reply_text("✍️ Envie o texto agora:")
        return

    if data == "espaco":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▫ Compacto", callback_data="esp:1")],
            [InlineKeyboardButton("▫ Médio", callback_data="esp:2")],
            [InlineKeyboardButton("▫ Grande", callback_data="esp:3")],
        ])
        await q.message.reply_text("📏 Escolha o espaçamento:", reply_markup=kb)
        return

    if data.startswith("esp:"):
        chat_id = context.user_data["chat_id"]
        nivel = int(data.split(":")[1])
        set_cfg(chat_id, "espaco", nivel)
        await q.message.reply_text("✅ Espaçamento atualizado!")
        return

    if data == "toggle":
        chat_id = context.user_data["chat_id"]
        cfg = get_cfg(chat_id)
        novo = 0 if cfg[1] == 1 else 1
        set_cfg(chat_id, "ativo", novo)
        await q.message.reply_text("✅ Ativado" if novo else "⛔ Desativado")
        return

    if data == "reset":
        chat_id = context.user_data["chat_id"]
        reset_cfg(chat_id)
        await q.message.reply_text("♻️ Configurações resetadas!")
        return

# ================= RECEBER TEXTO =================
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "edit" not in context.user_data:
        return

    chat_id = context.user_data["chat_id"]
    campo = context.user_data.pop("edit")

    mapa = {
        "ti": "texto_inicio",
        "tf": "texto_fim",
        "tgi": "tags_inicio",
        "tgf": "tags_fim",
        "bt": "botao_texto",
        "bl": "botao_link",
    }

    set_cfg(chat_id, mapa[campo], update.message.text)
    await update.message.reply_text("✅ Salvo com sucesso!")

# ================= PROCESSAR POSTS =================
async def processar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post or update.message
    if not msg or not msg.chat:
        return

    chat_id = msg.chat.id

    with db() as con:
        con.execute("INSERT OR IGNORE INTO canais (chat_id) VALUES (?)", (chat_id,))

    cfg = get_cfg(chat_id)
    if not cfg or cfg[1] == 0:
        return

    if msg.reply_to_message:
        return

    ti = cfg[2]
    tf = cfg[3]
    tgi = cfg[4]
    tgf = cfg[5]
    bt = cfg[6]
    bl = cfg[7]
    esp = cfg[8]

    texto_base = msg.text or msg.caption or INVISIVEL
    espaco = gerar_espaco(esp)

    inicio = f"{ti}{espaco}{tgi}{espaco}" if ti or tgi else ""
    fim = f"{espaco}{tgf}{espaco}{tf}" if tf or tgf else ""
    texto_final = inicio + texto_base + fim

    teclado = None
    if bt and bl:
        teclado = InlineKeyboardMarkup([[InlineKeyboardButton(bt, url=bl)]])

    try:
        if msg.text:
            await msg.edit_text(texto_final, reply_markup=teclado)
        else:
            await msg.edit_caption(texto_final, reply_markup=teclado)
    except Exception as e:
        logging.error(f"Erro ao editar: {e}")

# ================= SAFE MODE THREADS =================
BACKUP_INTERVAL = 3600
WATCHDOG_INTERVAL = 120

def backup_db():
    while True:
        try:
            if os.path.exists(DB_NAME):
                shutil.copy(DB_NAME, DB_NAME + ".backup")
                logging.info("💾 Backup criado")
        except Exception as e:
            logging.error(f"Erro backup: {e}")
        time.sleep(BACKUP_INTERVAL)

def watchdog():
    while True:
        logging.info("💓 Bot vivo (Watchdog OK)")
        time.sleep(WATCHDOG_INTERVAL)

# ================= WEB SERVER (RENDER FREE FIX) =================
try:
    from flask import Flask

    web_app = Flask(__name__)

    @web_app.route("/")
    def home():
        return "🤖 Channel Beautify PRO ONLINE — Render OK"

    def run_web():
        port = int(os.environ.get("PORT", 10000))
        web_app.run(host="0.0.0.0", port=port)

    threading.Thread(target=run_web, daemon=True).start()

except Exception as e:
    logging.warning(f"Flask indisponível — ignorado: {e}")

# ================= MAIN =================
def main():
    if not TOKEN:
        logging.error("❌ BOT_TOKEN não definido!")
        return

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, receber_texto))
    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL
            | filters.ChatType.GROUP
            | filters.ChatType.SUPERGROUP,
            processar
        )
    )

    threading.Thread(target=backup_db, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()

    logging.info("🚀 Channel Beautify PRO ONLINE — SAFE MODE")

    app.run_polling()

if __name__ == "__main__":
    main()
