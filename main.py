import os
import random
import datetime
import asyncio
import threading
import time
import requests
import traceback

from dotenv import load_dotenv
from flask import Flask

import discord
from discord.ext import commands

# === Load environment ===
load_dotenv()

# === Globals ===
credits = {}
last_quiz_time = {}
last_quest_time = {}
last_battle_time = {}
battle_participants = []
signup_message_id = None
battle_in_progress = False

# === Quiz data ===
quiz_questions = [
    {"question": "Can you create a digital twin of a building with MYİKKİ? (Yes/No)", "answer": "Yes"},
    # ... autres questions ...
    {"question": "Does MYİKKİ use a centralized database to store project data? (Yes/No)", "answer": "No"},
]

# === Quests & Battle Data ===
quests = ["Inspect a window", "Certify a roof", "Upgrade the insulation", "Scan for mold"]
building_types = [
    "an old Parisian apartment building",
    # ... autres sites ...
    "a heritage Gothic cathedral"
]
event_messages = [
    "⚠️ A sudden downpour drenches the site—tools start slipping everywhere!",
    # ... autres événements ...
    "🏗️ Crane malfunction: the load swings wildly—stay clear or get eliminated!"
]
elimination_messages = [
    "{name} was caught under falling debris—eliminated!",
    # ... autres éliminations ...
    "{name} used the wrong tool and collapsed the scaffolding—eliminated!"
]
bonus_messages = [
    "{name} activated their safety harness — immune to the next elimination!",
    # ... autres bonus ...
    "{name} used the emergency exit plan — leaps past one elimination attempt!"
]
malus_messages = [
    "{name} dropped a heavy beam — loses 2 XP and misses the next round!",
    # ... autres malus ...
    "{name} slipped on grease — -1 XP and loses their next action!"
]

# === Helpers ===
def add_credits(user_id, amount):
    credits[user_id] = credits.get(user_id, 0) + amount

def get_credits(user_id):
    return credits.get(user_id, 0)

async def remove_role_later(member: discord.Member, role: discord.Role, delay: int):
    await asyncio.sleep(delay)
    await member.remove_roles(role)

def is_admin(user):
    return user.id == 865185894197887018 or any(
        r.name in ("Administrator", "Chief Discord Officer") for r in user.roles
    )

# === Keep-alive thread ===
def keep_awake():
    url = f"http://localhost:{os.getenv('PORT',8080)}/"
    while True:
        try: requests.get(url, timeout=5)
        except: pass
        time.sleep(60)

threading.Thread(target=keep_awake, daemon=True).start()

# === Bot setup ===
GUILD_ID = int(os.getenv("GUILD_ID", 0))
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        if GUILD_ID:
            await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        else:
            await self.tree.sync()

bot = MyBot()

# === Reaction handlers ===
@bot.event
async def on_raw_reaction_add(payload):
    global signup_message_id
    if payload.user_id == bot.user.id: return
    if not battle_in_progress or payload.message_id != signup_message_id: return
    if str(payload.emoji) == "🔨":
        # init XP à 0 pour éviter KeyError
        credits.setdefault(payload.user_id, 0)
        if payload.user_id not in battle_participants:
            battle_participants.append(payload.user_id)
            channel = bot.get_channel(payload.channel_id)
            user = await bot.fetch_user(payload.user_id)
            await channel.send(f"🧱 {user.display_name} joined the battle!")

@bot.event
async def on_raw_reaction_remove(payload):
    global signup_message_id
    if payload.user_id == bot.user.id: return
    if not battle_in_progress or payload.message_id != signup_message_id: return
    if str(payload.emoji) == "🔨" and payload.user_id in battle_participants:
        battle_participants.remove(payload.user_id)

# --- /quiz ---
@bot.tree.command(name="quiz", description="Take your daily yes/no MYİKKİ quiz")
async def slash_quiz(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    last = last_quiz_time.get(interaction.user.id)
    if last and (now - last).total_seconds() < 86400:
        return await interaction.response.send_message("⏳ Only once per 24h.", ephemeral=True)
    q = random.choice(quiz_questions)
    await interaction.response.send_message(f"🧠 Quiz: **{q['question']}**")
    def check(m):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.content.lower().strip() in ("yes","no")
    try:
        m = await bot.wait_for("message", timeout=30, check=check)
        if m.content.lower().strip() == q["answer"].lower():
            add_credits(interaction.user.id, 5)
            last_quiz_time[interaction.user.id] = now
            await interaction.followup.send(f"✅ Correct! +5 XP (Total: {get_credits(interaction.user.id)} XP)")
        else:
            await interaction.followup.send("❌ Incorrect. Try again tomorrow!")
    except asyncio.TimeoutError:
        await interaction.followup.send("⌛ Time’s up! (30s)")

# --- /quest ---
@bot.tree.command(name="quest", description="Get your daily renovation quest")
async def slash_quest(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    last = last_quest_time.get(interaction.user.id)
    if last and (now - last).total_seconds() < 86400:
        return await interaction.response.send_message("⏳ Only one quest per 24h.", ephemeral=True)
    task = random.choice(quests)
    reward = random.randint(3,7)
    add_credits(interaction.user.id, reward)
    last_quest_time[interaction.user.id] = now
    await interaction.response.send_message(f"🛠️ Quest: **{task}**\n✅ +{reward} XP (Total: {get_credits(interaction.user.id)} XP)")

# --- /creditscore ---
@bot.tree.command(name="creditscore", description="Check your current XP")
async def slash_creditscore(interaction: discord.Interaction):
    await interaction.response.send_message(f"💰 You have {get_credits(interaction.user.id)} XP.")

# --- Battle runner with error capture ---
async def run_battle(ctx):
    global battle_in_progress, signup_message_id
    try:
        survivors = battle_participants.copy()
        if len(survivors) < 2:
            return await ctx.send("❌ Not enough participants.")
        # on désactive toute nouvelle inscription
        signup_message_id = None

        now = datetime.datetime.utcnow()
        last_battle_time.setdefault(ctx.guild.id, []).append(now)
        site = random.choice(building_types)

        # début
        await ctx.send(f"🏗️ Battle at **{site}** with {len(survivors)} players!")
        await asyncio.sleep(3)

        # participants
        mentions = []
        for uid in survivors:
            member = await ctx.guild.fetch_member(uid)
            mentions.append(member.mention)
        await ctx.send(f"🎯 Participants: {', '.join(mentions)}")
        await asyncio.sleep(3)

        rnd = 0
        while len(survivors) > 1:
            rnd += 1

            if random.random() < 0.4:
                await ctx.send(random.choice(event_messages))
                await asyncio.sleep(3)

            roll = random.random()
            if roll < 0.3:
                t = random.choice(survivors)
                add_credits(t, 3)
                mem = await ctx.guild.fetch_member(t)
                await ctx.send(random.choice(bonus_messages).format(name=mem.display_name))
                await asyncio.sleep(3)
            elif roll < 0.5:
                t = random.choice(survivors)
                rem = min(get_credits(t), 2)
                credits[t] = get_credits(t) - rem
                mem = await ctx.guild.fetch_member(t)
                await ctx.send(random.choice(malus_messages).format(name=mem.display_name))
                await asyncio.sleep(3)

            elim = random.choice(survivors)
            survivors.remove(elim)
            mem = await ctx.guild.fetch_member(elim)
            await ctx.send(f"❌ Round {rnd}: {random.choice(elimination_messages).format(name=mem.display_name)}")
            await asyncio.sleep(3)

            left = []
            for uid in survivors:
                m = await ctx.guild.fetch_member(uid)
                left.append(m.display_name)
            await ctx.send("🧱 Remaining: " + ", ".join(left))
            await asyncio.sleep(3)

        # gagnant
        winner_id = survivors[0]
        add_credits(winner_id, 15)
        winner = await ctx.guild.fetch_member(winner_id)
        role = discord.utils.get(ctx.guild.roles, name="Lead Renovator") or await ctx.guild.create_role(name="Lead Renovator")
        await winner.add_roles(role)
        await ctx.send(f"🏅 {winner.display_name} is now Lead Renovator (24h)! (+15 XP)")
        await asyncio.sleep(3)
        await ctx.send(
            f"🏁 Battle Complete!\n"
            f"🏗️ Site: {site}\n"
            f"🎖️ Winner: {winner.display_name}\n"
            f"🎁 Reward: 15 XP\n"
            f"🧱 Renovation done."
        )

    except Exception as e:
        await ctx.send(f"❌ **Error in battle:** {e}")
        tb = traceback.format_exc()
        await ctx.send(f"```py\n{tb}\n```")
    finally:
        battle_in_progress = False
        signup_message_id = None
        battle_participants.clear()

# --- /startfirstbattle ---
@bot.tree.command(name="startfirstbattle", description="Admin: open 5m signup at will")
async def slash_startfirst(interaction: discord.Interaction):
    global battle_in_progress, signup_message_id
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    if battle_in_progress:
        return await interaction.response.send_message("❌ A battle is already in progress.", ephemeral=True)

    battle_in_progress = True
    battle_participants.clear()
    msg = await interaction.response.send_message(
        "🚨 FIRST MYİKKİ BATTLE in #battle-renovation!\nClick 🔨 to join within 5 minutes."
    )
    msg = await interaction.original_response()
    signup_message_id = msg.id
    await msg.add_reaction("🔨")

    async def finish():
        await asyncio.sleep(300)  # 5 min
        class Ctx:
            guild = interaction.guild
            send = interaction.channel.send
        await run_battle(Ctx())

    asyncio.create_task(finish())

# --- /startbattle ---
@bot.tree.command(name="startbattle", description="Admin: open 11h signup rumble")
async def slash_startbattle(interaction: discord.Interaction):
    global battle_in_progress, signup_message_id
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    if battle_in_progress:
        return await interaction.response.send_message("❌ A battle is already in progress.", ephemeral=True)

    now = datetime.datetime.utcnow()
    window = [
        t for t in last_battle_time.get(interaction.guild.id, [])
        if (now - t).total_seconds() < 11 * 3600
    ]
    if len(window) >= 2:
        return await interaction.response.send_message("⏳ Max 2 per 11h.", ephemeral=True)

    battle_in_progress = True
    battle_participants.clear()
    msg = await interaction.response.send_message("🚨 RUMBLE: React 🔨 to join within 11 hours.")
    msg = await interaction.original_response()
    signup_message_id = msg.id
    await msg.add_reaction("🔨")

    async def finish():
        await asyncio.sleep(11 * 3600)  # 11 h
        class Ctx:
            guild = interaction.guild
            send = interaction.channel.send
        await run_battle(Ctx())

    asyncio.create_task(finish())

# === Keep-alive endpoint ===
app = Flask("")
@app.route("/")
def home():
    return "I'm alive!"

threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080))),
    daemon=True
).start()

# === Run ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set.")
    bot.run(token)
