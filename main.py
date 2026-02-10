# ================= CHANNEL BEAUTIFY PRO + LOVE MODE =================
import logging
import sqlite3
import os
import threading
import time
import shutil
import random
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DB_NAME = "bot_tags.db"
INVISIVEL = "⠀"

logging.basicConfig(level=logging.INFO)

# ================= IA =================
try:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except:
    client = None

FRASES_FALLBACK = [
    "💖 O amor transforma tudo.",
    "✨ Cada dia é melhor ao seu lado.",
    "🔥 A paixão move o coração.",
    "💌 Amar é um ato de coragem.",
    "🌹 Você é poesia em forma de gente.",
    "💞 O carinho cura a alma.",
    "🥰 Amor verdadeiro é conexão eterna.",
    "❤️ Que nunca falte amor e ternura.",
]

def gerar_post_romantico(personalidade="romantico", memoria=""):
    prompt = f"""
    Você escreve posts para um canal de romance, amor, paixão e carinho.
    Personalidade do canal: {personalidade}
    Memória emocional do canal: {memoria}

    Gere um post completo com:
    - Texto romântico emocional
    - Emojis apaixonados
    - Hashtags no final
    Tom: profundo, carinhoso, viral, sentimental.
    """

    if client:
        try:
            resp = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "Você é uma IA especialista em romance, amor, paixão e emoção profunda."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=220,
                temperature=0.95
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Erro IA: {e}")

    return random.choice(FRASES_FALLBACK)

# ================= BANCO =================
def db():
    return sqlite3.connect(DB_NAME)

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS canais (
            chat_id INTEGER PRIMARY KEY,
            canal_nome TEXT DEFAULT '',
            ativo INTEGER DEFAULT 1,
            texto_inicio TEXT DEFAULT '',
            texto_fim TEXT DEFAULT '',
            tags_inicio TEXT DEFAULT '',
            tags_fim TEXT DEFAULT '',
            botao_texto TEXT DEFAULT '',
            botao_link TEXT DEFAULT '',
            espaco INTEGER DEFAULT 2,
            ia_ativa INTEGER DEFAULT 1,
            love_mode INTEGER DEFAULT 1,
            personalidade TEXT DEFAULT 'romantico',
            memoria TEXT DEFAULT '',
            intervalo INTEGER DEFAULT 3600
        )
        """)

def get_cfg(chat_id):
    with db() as con:
        return con.execute("SELECT * FROM canais WHERE chat_id=?", (chat_id,)).fetchone()

def set_cfg(chat_id, campo, valor):
    with db() as con:
        con.execute(f"UPDATE canais SET {campo}=? WHERE chat_id=?", (valor, chat_id))

def all_canais():
    with db() as con:
        return con.execute("SELECT chat_id, canal_nome FROM canais").fetchall()

# ================= UTIL =================
def gerar_espaco(n):
    return "\n" * n

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Meus Canais", callback_data="canais")]
    ])
    await update.message.reply_text(
        "💖 **Channel Beautify PRO + Love Mode**\n\n"
        "✨ Embeleza posts\n"
        "🧠 IA Romântica automática\n"
        "💌 Autopost sem comandos\n"
        "❤️ Memória emocional por canal\n\n"
        "👉 Adicione o bot como ADMIN no canal.",
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
            await q.message.reply_text("❌ Nenhum canal registrado.")
            return

        kb = []
        for cid, nome in canais:
            nome = nome or f"Canal {cid}"
            kb.append([InlineKeyboardButton(f"📢 {nome}", callback_data=f"cfg:{cid}")])

        await q.message.reply_text("📢 Selecione o canal:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("cfg:"):
        chat_id = int(data.split(":")[1])
        context.user_data["chat_id"] = chat_id

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧠 IA ON/OFF", callback_data="ia_toggle")],
            [InlineKeyboardButton("❤️ Love Mode ON/OFF", callback_data="love_toggle")],
            [InlineKeyboardButton("✍ Memória emocional", callback_data="memoria")],
            [InlineKeyboardButton("⏱ Intervalo Autopost", callback_data="intervalo")],
            [InlineKeyboardButton("🔌 Ativar / Desativar", callback_data="toggle")]
        ])

        await q.message.reply_text("⚙️ Configuração Love Mode:", reply_markup=kb)
        return

    if data == "ia_toggle":
        chat_id = context.user_data["chat_id"]
        cfg = get_cfg(chat_id)
        novo = 0 if cfg[10] == 1 else 1
        set_cfg(chat_id, "ia_ativa", novo)
        await q.message.reply_text("🧠 IA ON" if novo else "🚫 IA OFF")
        return

    if data == "love_toggle":
        chat_id = context.user_data["chat_id"]
        cfg = get_cfg(chat_id)
        novo = 0 if cfg[11] == 1 else 1
        set_cfg(chat_id, "love_mode", novo)
        await q.message.reply_text("❤️ Love Mode ON" if novo else "💔 Love Mode OFF")
        return

    if data == "memoria":
        context.user_data["edit"] = "memoria"
        await q.message.reply_text("✍ Envie a personalidade emocional do canal:")
        return

    if data == "intervalo":
        context.user_data["edit"] = "intervalo"
        await q.message.reply_text("⏱ Envie intervalo em segundos (ex: 3600 = 1h):")
        return

# ================= RECEBER TEXTO =================
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "edit" not in context.user_data:
        return

    chat_id = context.user_data["chat_id"]
    campo = context.user_data.pop("edit")

    if campo == "memoria":
        set_cfg(chat_id, "memoria", update.message.text)
        await update.message.reply_text("❤️ Memória salva!")

    elif campo == "intervalo":
        try:
            set_cfg(chat_id, "intervalo", int(update.message.text))
            await update.message.reply_text("⏱ Intervalo atualizado!")
        except:
            await update.message.reply_text("❌ Envie apenas números.")

# ================= PROCESSAR POSTS =================
async def processar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post or update.message
    if not msg or not msg.chat:
        return

    chat_id = msg.chat.id
    canal_nome = msg.chat.title or msg.chat.username or f"Canal {chat_id}"

    with db() as con:
        con.execute("INSERT OR IGNORE INTO canais (chat_id, canal_nome) VALUES (?, ?)", (chat_id, canal_nome))
        con.execute("UPDATE canais SET canal_nome=? WHERE chat_id=?", (canal_nome, chat_id))

# ================= AUTPOST LOOP =================
async def autopost_loop(app):
    await app.bot.initialize()

    while True:
        canais = all_canais()

        for cid, nome in canais:
            cfg = get_cfg(cid)
            if not cfg:
                continue

            ativo = cfg[2]
            ia_on = cfg[10]
            love = cfg[11]
            personalidade = cfg[12]
            memoria = cfg[13]
            intervalo = cfg[14]

            if ativo == 0 or ia_on == 0:
                continue

            texto = gerar_post_romantico(personalidade, memoria)

            try:
                await app.bot.send_message(cid, texto)
                logging.info(f"💌 Autopost enviado → {nome}")
            except Exception as e:
                logging.error(f"Erro autopost {cid}: {e}")

        await asyncio.sleep(300)

# ================= SAFE THREADS =================
def backup_db():
    while True:
        try:
            if os.path.exists(DB_NAME):
                shutil.copy(DB_NAME, DB_NAME + ".backup")
        except:
            pass
        time.sleep(3600)

def watchdog():
    while True:
        logging.info("💓 Bot vivo (Love Mode OK)")
        time.sleep(120)

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
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP, processar))

    threading.Thread(target=backup_db, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(autopost_loop(app)), daemon=True).start()

    logging.info("💖 CHANNEL BEAUTIFY LOVE MODE ONLINE")

    app.run_polling()

if __name__ == "__main__":
    main()
