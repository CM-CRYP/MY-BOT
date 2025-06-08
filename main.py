# main.py

import os
import random
import datetime
import asyncio
import threading
import time
import requests
from threading import Thread

from dotenv import load_dotenv
from flask import Flask

import discord
from discord import app_commands
from discord.ext import commands

# === Charge les variables de .env pour le dev local ===
load_dotenv()

# === Keep-alive interne : ping sur "/" toutes les 60s ===
def keep_awake():
    url = f"http://localhost:{os.environ.get('PORT', 8080)}/"
    while True:
        try:
            requests.get(url, timeout=5)
        except:
            pass
        time.sleep(60)

threading.Thread(target=keep_awake, daemon=True).start()

# === Toutes les questions Oui/Non pour le quiz ===
quiz_questions = [
    # 20 questions "Yes"
    {"question": "Can you create a digital twin of a building with MYİKKİ? (Yes/No)", "answer": "Yes"},
    {"question": "Is MYİKKİ’s digital twin visualized in 3D in real time? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYİKKİ offer an interactive photorealistic rendering engine? (Yes/No)", "answer": "Yes"},
    {"question": "Can you estimate renovation budgets automatically with MYİKKİ? (Yes/No)", "answer": "Yes"},
    {"question": "Are MYİKKİ’s project data secured by blockchain technology? (Yes/No)", "answer": "Yes"},
    {"question": "Can users share renovation projects with contractors through NFTs? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYİKKİ support thermal imaging to assess energy performance? (Yes/No)", "answer": "Yes"},
    {"question": "Is MYİKKİ designed for both professionals and private owners? (Yes/No)", "answer": "Yes"},
    {"question": "Can users update the digital twin during the renovation process? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYİKKİ help solve coordination and budget issues on site? (Yes/No)", "answer": "Yes"},
    {"question": "Can digital twins in MYİKKİ help detect issues before construction starts? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYİKKİ enable real-time monitoring of renovation progress? (Yes/No)", "answer": "Yes"},
    {"question": "Is MYİKKİ presented as a Web3 global solution? (Yes/No)", "answer": "Yes"},
    {"question": "Does the MYİKKİ platform reward users with XP or badges? (Yes/No)", "answer": "Yes"},
    {"question": "Is the digital twin used to validate final work delivery? (Yes/No)", "answer": "Yes"},
    {"question": "Are MYİKKİ’s interactions timestamped and verifiable? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYİKKİ help reduce errors and extra costs during renovation? (Yes/No)", "answer": "Yes"},
    {"question": "Can you invite artisans and architects directly into your digital twin? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYİKKİ’s ecosystem include both on-chain and off-chain features? (Yes/No)", "answer": "Yes"},
    {"question": "Can a non-developer easily use MYİKKİ to plan renovations? (Yes/No)", "answer": "Yes"},

    # 20 questions "No"
    {"question": "Does MYİKKİ only work for new construction projects? (Yes/No)", "answer": "No"},
    {"question": "Is MYİKKİ limited to users in France only? (Yes/No)", "answer": "No"},
    {"question": "Can you use MYİKKİ without creating a digital twin? (Yes/No)", "answer": "No"},
    {"question": "Is MYİKKİ a traditional real estate agency? (Yes/No)", "answer": "No"},
    {"question": "Does MYİKKİ sell building materials directly? (Yes/No)", "answer": "No"},
    {"question": "Can MYİKKİ function entirely offline without internet? (Yes/No)", "answer": "No"},
    {"question": "Is MYİKKİ a DeFi lending platform? (Yes/No)", "answer": "No"},
    {"question": "Does MYİKKİ replace the need for real architects? (Yes/No)", "answer": "No"},
    {"question": "Is MYİKKİ only accessible via mobile app? (Yes/No)", "answer": "No"},
    {"question": "Can you claim financial property ownership with MYİKKİ NFTs? (Yes/No)", "answer": "No"},
    {"question": "Can MYİKKİ be used to decorate interiors with virtual furniture only? (Yes/No)", "answer": "No"},
    {"question": "Does MYİKKİ require owning cryptocurrency to use the platform? (Yes/No)", "answer": "No"},
    {"question": "Is MYİKKİ exclusively focused on luxury real estate? (Yes/No)", "answer": "No"},
    {"question": "Can MYİKKİ be used to rent vacation homes? (Yes/No)", "answer": "No"},
    {"question": "Does MYİKKİ offer virtual reality headset support as of today? (Yes/No)", "answer": "No"},
    {"question": "Is MYİKKİ a social media platform for homeowners? (Yes/No)", "answer": "No"},
    {"question": "Does MYİKKİ operates in China? (Yes/No)", "answer": "No"},
    {"question": "Can MYİKKİ replace all interactions with contractors entirely? (Yes/No)", "answer": "No"},
    {"question": "Is the MYİKKİ token already listed on major crypto exchanges? (Yes/No)", "answer": "No"},
    {"question": "Does MYİKKİ use a centralized database to store project data? (Yes/No)", "answer": "No"},
]

# === Structures globales pour XP, temps et batailles ===
credits = {}
last_quiz_time = {}
last_quest_time = {}
last_battle_time = {}
battle_participants = []

# (les autres listes building_types, event_messages, etc. restent inchangées)

# === Helpers pour gérer XP et rôles ===
def add_credits(user_id: int, amount: int):
    credits[user_id] = credits.get(user_id, 0) + amount

def get_credits(user_id: int) -> int:
    return credits.get(user_id, 0)

async def remove_role_later(member: discord.Member, role: discord.Role, delay: int):
    await asyncio.sleep(delay)
    await member.remove_roles(role)

# === Bot Custom avec sync auto des slash commands ===
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🔄 Slash commands synced")

bot = MyBot()

# === Slash command: /quiz ===
@bot.tree.command(name="quiz", description="Take your daily yes/no MYİKKİ quiz")
async def slash_quiz(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    last = last_quiz_time.get(interaction.user.id)
    if last and (now - last).total_seconds() < 86400:
        await interaction.response.send_message(
            "⏳ You can only do the quiz once every 24 hours.", ephemeral=True
        )
        return

    q = random.choice(quiz_questions)
    await interaction.response.send_message(f"🧠 Quiz: **{q['question']}**")

    def check(m: discord.Message):
        return (
            m.author.id == interaction.user.id
            and m.channel.id == interaction.channel.id
            and m.content.lower().strip() in ("yes", "no")
        )

    try:
        m = await bot.wait_for("message", timeout=30, check=check)
        réponse = m.content.lower().strip()
        correct = (réponse == q["answer"].lower())
        if correct:
            add_credits(interaction.user.id, 5)
            last_quiz_time[interaction.user.id] = now
            await interaction.followup.send(
                f"✅ Correct! +5 XP (Total: {get_credits(interaction.user.id)} XP)"
            )
        else:
            await interaction.followup.send("❌ Incorrect. Try again tomorrow!")
    except asyncio.TimeoutError:
        await interaction.followup.send("⌛ Time’s up! (30s)")

# (reste du code : /quest, battle, Flask server, etc. inchangé)

# === Flask keep-alive endpoint ===
app = Flask("")
@app.route("/")
def home():
    return "I'm alive"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask).start()

# === Démarrage ===
if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
