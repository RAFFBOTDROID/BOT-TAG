import os
import random
import sqlite3
import asyncio
import threading
import logging
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

logging.basicConfig(level=logging.INFO)

DB_PATH = "database.db"

# ================= FRASES FALLBACK =================
FRASES_FALLBACK = [
    "💖 O amor é a poesia do coração.",
    "🌹 Amar é sentir o infinito em um instante.",
    "💞 Você é o verso mais bonito do meu dia.",
    "✨ Onde há amor, há magia.",
    "🥰 Amar é cuidar sem pedir nada em troca."
]

# ================= DATABASE =================
def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS canais (
            chat_id INTEGER PRIMARY KEY,
            canal_nome TEXT DEFAULT '',
            ativo INTEGER DEFAULT 1,
            personalidade TEXT DEFAULT 'romantico',
            memoria TEXT DEFAULT '',
            intervalo INTEGER DEFAULT 3600,
            ia_ativa INTEGER DEFAULT 1,
            love_mode INTEGER DEFAULT 1
        )
        """)

init_db()

def all_canais():
    with db() as con:
        return con.execute("SELECT chat_id, canal_nome FROM canais WHERE ativo=1").fetchall()

def get_cfg(cid):
    with db() as con:
        return con.execute("SELECT * FROM canais WHERE chat_id=?", (cid,)).fetchone()

def salvar_canal(cid, nome):
    with db() as con:
        con.execute("""
        INSERT OR IGNORE INTO canais (chat_id, canal_nome)
        VALUES (?, ?)
        """, (cid, nome))

# ================= LOVE MODE IA =================
def gerar_post_romantico(personalidade="romantico", memoria=""):
    prompt = f"""
    Você escreve posts para um canal de romance, amor, paixão e carinho.

    Personalidade do canal: {personalidade}
    Memória emocional do canal: {memoria}

    Gere um post completo com:
    - Texto romântico intenso
    - Emojis apaixonados
    - Hashtags no final
    Tom: profundo, sentimental, viral, amoroso.
    """

    if client:
        try:
            resp = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "Você é uma IA especialista em amor, romance, paixão e emoção profunda."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.95
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Erro IA: {e}")

    return random.choice(FRASES_FALLBACK)

# ================= AUTPOST LOOP =================
async def autopost_loop(app):
    await app.bot.initialize()
    logging.info("💖 Love Mode Autopost iniciado")

    while True:
        canais = all_canais()

        for cid, nome in canais:
            cfg = get_cfg(cid)
            if not cfg:
                continue

            ativo = cfg[2]
            personalidade = cfg[3]
            memoria = cfg[4]
            intervalo = cfg[5]
            ia_on = cfg[6]

            if ativo == 0:
                continue

            if ia_on:
                texto = gerar_post_romantico(personalidade, memoria)
            else:
                texto = random.choice(FRASES_FALLBACK)

            try:
                await app.bot.send_message(cid, texto)
                logging.info(f"💌 Autopost enviado → {nome}")
            except Exception as e:
                logging.error(f"Erro autopost {cid}: {e}")

        await asyncio.sleep(300)

# ================= TELEGRAM COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type == "channel":
        salvar_canal(chat.id, chat.title or "Canal sem nome")
        await update.message.reply_text("💖 Canal registrado no Love Mode!")
    else:
        await update.message.reply_text("💌 Me adicione a um CANAL para ativar Love Mode.")

# ================= FLASK DASHBOARD =================
web = Flask(__name__)

@web.route("/")
def dashboard():
    canais = all_canais()
    html = "<h1>💖 Love Mode Dashboard</h1>"
    for cid, nome in canais:
        html += f"<p>📢 {nome} — {cid}</p>"
    return html

def run_web():
    web.run(host="0.0.0.0", port=8080)

# ================= MAIN =================
def main():
    print("🚀 LOVE MODE BOT INICIANDO...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(autopost_loop(app)), daemon=True).start()

    app.run_polling()

if __name__ == "__main__":
    main()
