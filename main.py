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

# === Structures globales pour XP, temps et batailles ===
credits = {}
last_quiz_time = {}
last_quest_time = {}
last_battle_time = {}
battle_participants = []

quiz_questions = [
    {"question": "What is a Digital Twin used for in MYİKKİ?", "answer": "To certify and store building improvements"},
    {"question": "What kind of properties can benefit from MYİKKİ's system?", "answer": "Old and renovated buildings"},
    {"question": "How are renovations tracked in MYİKKİ?", "answer": "On-chain through NFTs"},
    {"question": "Can a user interact with their building in MYİKKİ?", "answer": "Yes, through a digital twin"},
    {"question": "What does MYİKKİ aim to bring to real estate?", "answer": "Transparency and certified value"},
    {"question": "Who benefits from MYİKKİ’s renovation memory system?", "answer": "Owners, professionals, and future buyers"}
]

quests = [
    "Inspect a window", "Certify a roof", "Upgrade the insulation", "Scan for mold"
]

building_types = [
    "an old Parisian apartment building",
    "an abandoned rural school",
    "a crumbling medieval castle",
    "a derelict industrial warehouse",
    "a seaside lighthouse in disrepair",
    "a solar-powered eco-village complex",
    "a futuristic smart home prototype",
    "a high-rise glass office tower",
    "an underground subway tunnel station",
    "a vintage Art Deco theater",
    "a collapsing water treatment plant",
    "an offshore oil rig platform",
    "an abandoned amusement park pavilion",
    "a restored Victorian row house",
    "a geodesic dome greenhouse",
    "a windmill farm control station",
    "a derelict mountain chalet",
    "a modern floating skyscraper model",
    "a jungle treehouse research station",
    "a heritage Gothic cathedral"
]

event_messages = [
    "⚠️ A sudden downpour drenches the site—tools start slipping everywhere!",
    "🧯 Fire alarms blare: a welding spark ignited debris—teams must evacuate momentarily.",
    "⚡ Power surge fries the lighting—construction pauses in darkness.",
    "🌀 Gusting winds yank at scaffolding—workers cling on for dear life.",
    "🚨 Surprise safety inspection—any code violations will send someone home!",
    "🌩️ Thunder cracks close by—electrical equipment is now taboo for a round.",
    "🌡️ Extreme heat chases everyone to the shade—pace slows down next turn.",
    "❄️ A sudden freeze covers surfaces in ice—movement is treacherous.",
    "🌪️ A mini-tornado of dust and debris sweeps the site—visibility drops.",
    "🏗️ Crane malfunction: the load swings wildly—stay clear or get eliminated!"
]

elimination_messages = [
    "{name} was caught under falling debris—eliminated!",
    "{name} stepped into wet cement—sank and is out!",
    "{name} got struck by a swinging beam—knocked out!",
    "{name} lost balance on a plank—took a tumble!",
    "{name} misread the blueprint—built the wrong wall and got disqualified!",
    "{name}’s drone malfunctioned and toppled a rafter—down for the count!",
    "{name} tumbled through an unsecured hatch—gone!",
    "{name} cut the wrong wire—tripped the alarm and was removed!",
    "{name} got tangled in electrical cables—out!",
    "{name} used the wrong tool and collapsed the scaffolding—eliminated!"
]

bonus_messages = [
    "{name} activated their safety harness — immune to the next elimination!",
    "{name} deployed a temporary shield wall — skips the next event unscathed!",
    "{name} discovered a hidden crawlspace — advances directly to the next round!",
    "{name} found a rapid-repair kit — +4 XP and fully patched for what’s next!",
    "{name} reinforced the floor with steel beams — avoids any collapse this round!",
    "{name} calibrated their drone camera — perfect vision for the next elimination (safe)!",
    "{name} stumbled upon extra scaffolding — +3 XP and climbs ahead of the pack!",
    "{name} donned magnetic boots — won’t slip on any spilled materials next round!",
    "{name} grabbed the contractor’s coffee — +2 XP and jitter-free performance!",
    "{name} used the emergency exit plan — leaps past one elimination attempt!"
]

malus_messages = [
    "{name} dropped a heavy beam — loses 2 XP and misses the next round!",
    "{name} got sprayed with wet cement — slips and is unable to act this turn!",
    "{name} triggered a floor collapse — -3 XP and stuck for one round!",
    "{name} jammed their tool in the rubble — loses 1 XP and can’t compete this round!",
    "{name} mis-tightened the platform bolts — -2 XP and stumbles off the scaffold!",
    "{name} flew their drone into a wall — device crashes, -3 XP and grounded for a round!",
    "{name} knocked over the paint mixer — sprayed in the face, -2 XP and blinded next event!",
    "{name} forgot to secure the ladder — falls, -4 XP and sits out one round!",
    "{name} overloaded the power circuit — sparks fly, -3 XP and electrical hazard next turn!",
    "{name} slipped on grease — -1 XP and loses their next action!"
]

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

# === Slash commands ===
@bot.tree.command(name="start", description="Check if bot is online")
async def slash_start(interaction: discord.Interaction):
    await interaction.response.send_message("✅ MYİKKİ Bot is active!")

@bot.tree.command(name="quiz", description="Take your daily MYİKKİ quiz")
async def slash_quiz(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    last = last_quiz_time.get(interaction.user.id)
    if last and (now - last).total_seconds() < 86400:
        await interaction.response.send_message("⏳ Only one quiz per 24h", ephemeral=True)
        return
    q = random.choice(quiz_questions)
    await interaction.response.send_message(f"🧠 Quiz: **{q['question']}**")
    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
    try:
        m = await bot.wait_for("message", timeout=60, check=check)
        if m.content.lower().strip() == q["answer"].lower().strip():
            add_credits(interaction.user.id, 5)
            last_quiz_time[interaction.user.id] = now
            await interaction.followup.send(f"✅ Correct! +5 XP (Total: {get_credits(interaction.user.id)})")
        else:
            await interaction.followup.send("❌ Incorrect. Try again tomorrow!")
    except asyncio.TimeoutError:
        await interaction.followup.send("⌛ Time’s up!")

@bot.tree.command(name="quest", description="Get your daily renovation quest")
async def slash_quest(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    last = last_quest_time.get(interaction.user.id)
    if last and (now - last).total_seconds() < 86400:
        await interaction.response.send_message("⏳ Only one quest per 24h", ephemeral=True)
        return
    task = random.choice(quests)
    reward = random.randint(3, 7)
    add_credits(interaction.user.id, reward)
    last_quest_time[interaction.user.id] = now
    await interaction.response.send_message(
        f"🛠️ Quest: **{task}**\n✅ You earned {reward} XP (Total: {get_credits(interaction.user.id)})"
    )

@bot.tree.command(name="creditscore", description="Check your current XP")
async def slash_credits(interaction: discord.Interaction):
    await interaction.response.send_message(f"💰 You have {get_credits(interaction.user.id)} XP.")

# === Battle logic (signup + run) ===
async def run_battle(interaction: discord.Interaction):
    if len(battle_participants) < 2:
        await interaction.channel.send("❌ Not enough participants.")
        return
    now = datetime.datetime.utcnow()
    last_battle_time.setdefault(interaction.guild.id, []).append(now)
    site = random.choice(building_types)
    mentions = []
    for uid in battle_participants:
        member = await interaction.guild.fetch_member(uid)
        mentions.append(member.mention)
    await interaction.channel.send(f"🏗️ Battle at **{site}** with {len(mentions)} players!\n🎯 Participants: {', '.join(mentions)}")
    survivors = battle_participants.copy()
    rnd = 0
    while len(survivors) > 1:
        rnd += 1
        await asyncio.sleep(4)
        if random.random() < 0.4:
            await interaction.channel.send(random.choice(event_messages))
            await asyncio.sleep(2)
        roll = random.random()
        if roll < 0.3:
            target = random.choice(survivors)
            add_credits(target, 3)
            member = await interaction.guild.fetch_member(target)
            await interaction.channel.send(random.choice(bonus_messages).format(name=member.display_name))
            await asyncio.sleep(2)
        elif roll < 0.5:
            target = random.choice(survivors)
            remove_amt = min(credits.get(target, 0), 2)
            credits[target] = credits.get(target, 0) - remove_amt
            member = await interaction.guild.fetch_member(target)
            await interaction.channel.send(random.choice(malus_messages).format(name=member.display_name))
            await asyncio.sleep(2)
        elim = random.choice(survivors)
        survivors.remove(elim)
        mem = await interaction.guild.fetch_member(elim)
        await interaction.channel.send(f"❌ Round {rnd}: {random.choice(elimination_messages).format(name=mem.display_name)}")
        await asyncio.sleep(2)
        left = [ (await interaction.guild.fetch_member(uid)).display_name for uid in survivors ]
        await interaction.channel.send("🧱 Remaining: " + ", ".join(left))
    winner_id = survivors[0]
    add_credits(winner_id, 15)
    winner = await interaction.guild.fetch_member(winner_id)
    role = discord.utils.get(interaction.guild.roles, name="Lead Renovator")
    if not role:
        role = await interaction.guild.create_role(name="Lead Renovator")
    await winner.add_roles(role)
    await interaction.channel.send(f"🏅 {winner.display_name} is now Lead Renovator (24h)!")
    asyncio.create_task(remove_role_later(winner, role, 86400))
    await interaction.channel.send(f"🏁 Battle complete! Winner: {winner.display_name} (+15 XP)")

@bot.tree.command(name="startfirstbattle", description="Admin: launch the first 2-min signup battle")
async def slash_startfirst(interaction: discord.Interaction):
    if not any(r.name in ("Administrator","Chief Discord Officer") for r in interaction.user.roles):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return
    if interaction.guild.id in last_battle_time:
        await interaction.response.send_message("⚠️ Already run.", ephemeral=True)
        return
    battle_participants.clear()
    await interaction.response.send_message("🚨 FIRST BATTLE: click 🔨 to join (2 min)")
    msg = await interaction.original_response()
    await msg.add_reaction("🔨")
    def check(r,u): return r.message.id==msg.id and str(r.emoji)=="🔨" and not u.bot
    try:
        while True:
            r,u = await bot.wait_for("reaction_add", timeout=120, check=check)
            if u.id not in battle_participants:
                battle_participants.append(u.id)
                await interaction.channel.send(f"🧱 {u.display_name} joined!")
    except asyncio.TimeoutError:
        pass
    await run_battle(interaction)

@bot.tree.command(name="startbattle", description="Admin: launch an 11h signup rumble")
async def slash_startbattle(interaction: discord.Interaction):
    if not any(r.name in ("Administrator","Chief Discord Officer") for r in interaction.user.roles):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return
    now = datetime.datetime.utcnow()
    window = [t for t in last_battle_time.get(interaction.guild.id, []) if (now - t).total_seconds() < 43200]
    if len(window) >= 2:
        await interaction.response.send_message("⏳ Max 2 per 12h.", ephemeral=True)
        return
    battle_participants.clear()
    await interaction.response.send_message("🚨 RUMBLE: click 🔨 to join (11h)")
    msg = await interaction.original_response()
    await msg.add_reaction("🔨")
    end = now + datetime.timedelta(hours=11)
    def check(r,u): return r.message.id==msg.id and str(r.emoji)=="🔨" and not u.bot
    while datetime.datetime.utcnow() < end:
        try:
            r,u = await bot.wait_for("reaction_add", timeout=60, check=check)
            if u.id not in battle_participants:
                battle_participants.append(u.id)
                await interaction.channel.send(f"🧱 {u.display_name} joined!")
        except asyncio.TimeoutError:
            continue
    await run_battle(interaction)

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
