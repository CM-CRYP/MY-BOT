import os
import random
import datetime
import asyncio
import threading
import time
import requests
import json

from dotenv import load_dotenv
from flask import Flask

import discord
from discord.ext import commands

# === Load environment variables ===
load_dotenv()

# === Persistence file ===
PARTICIPANTS_FILE = "signup.json"

# === Quiz data ===
quiz_questions = [
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
    {"question": "Does MYİKKİ operate as a government-certified renovation agency? (Yes/No)", "answer": "No"},
    {"question": "Can MYİKKİ replace all interactions with contractors entirely? (Yes/No)", "answer": "No"},
    {"question": "Is the MYİKKİ token already listed on major crypto exchanges? (Yes/No)", "answer": "No"},
    {"question": "Does MYİKKİ use a centralized database to store project data? (Yes/No)", "answer": "No"},
]

# === Quests & Battle Data ===
quests = [
    "Inspect a window",
    "Certify a roof",
    "Upgrade the insulation",
    "Scan for mold"
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

# === Globals & Persistence ===
credits = {}
last_quiz_time = {}
last_quest_time = {}
last_battle_time = {}
battle_participants = []
signup_message_id = None

def load_signup():
    global signup_message_id, battle_participants
    if os.path.isfile(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, "r") as f:
            data = json.load(f)
            signup_message_id = data.get("message_id")
            battle_participants = data.get("participants", [])
    else:
        signup_message_id = None
        battle_participants = []

def save_signup():
    with open(PARTICIPANTS_FILE, "w") as f:
        json.dump({
            "message_id": signup_message_id,
            "participants": battle_participants
        }, f)

load_signup()

# === Keep-alive internal ===
def keep_awake():
    url = f"http://localhost:{os.getenv('PORT',8080)}/"
    while True:
        try:
            requests.get(url, timeout=5)
        except:
            pass
        time.sleep(60)

threading.Thread(target=keep_awake, daemon=True).start()

# === Credit helpers ===
def add_credits(user_id, amount):
    credits[user_id] = credits.get(user_id, 0) + amount

def get_credits(user_id):
    return credits.get(user_id, 0)

async def remove_role_later(member: discord.Member, role: discord.Role, delay: int):
    await asyncio.sleep(delay)
    await member.remove_roles(role)

# === Admin check by ID or role ===
def is_admin(user):
    return user.id in [865185894197887018] or any(
        r.name in ("Administrator", "Chief Discord Officer") for r in user.roles
    )

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
    if payload.user_id == bot.user.id:
        return
    if payload.message_id == signup_message_id and str(payload.emoji) == "🔨":
        if payload.user_id not in battle_participants:
            battle_participants.append(payload.user_id)
            save_signup()
            channel = bot.get_channel(payload.channel_id)
            user = await bot.fetch_user(payload.user_id)
            await channel.send(f"🧱 {user.display_name} joined the first battle!")

@bot.event
async def on_raw_reaction_remove(payload):
    global signup_message_id
    if payload.message_id == signup_message_id and str(payload.emoji) == "🔨":
        if payload.user_id in battle_participants:
            battle_participants.remove(payload.user_id)
            save_signup()

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
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.content.lower().strip() in ("yes", "no")
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
    reward = random.randint(3, 7)
    add_credits(interaction.user.id, reward)
    last_quest_time[interaction.user.id] = now
    await interaction.response.send_message(f"🛠️ Quest: **{task}**\n✅ +{reward} XP (Total: {get_credits(interaction.user.id)} XP)")

# --- /creditscore ---
@bot.tree.command(name="creditscore", description="Check your current XP")
async def slash_creditscore(interaction: discord.Interaction):
    await interaction.response.send_message(f"💰 You have {get_credits(interaction.user.id)} XP.")

# --- Battle runner ---
async def run_battle(ctx):
    if len(battle_participants) < 2:
        return await ctx.send("❌ Not enough participants.")
    now = datetime.datetime.utcnow()
    last_battle_time.setdefault(ctx.guild.id, []).append(now)
    site = random.choice(building_types)
    count = len(battle_participants)
    mentions = [(await ctx.guild.fetch_member(uid)).mention for uid in battle_participants]
    await ctx.send(f"🏗️ Battle at **{site}** with {count} players!\n🎯 Participants: {', '.join(mentions)}")
    survivors = battle_participants.copy()
    rnd = 0
    while len(survivors) > 1:
        rnd += 1
        await asyncio.sleep(4)
        if random.random() < 0.4:
            await ctx.send(random.choice(event_messages))
            await asyncio.sleep(2)
        roll = random.random()
        if roll < 0.3:
            target = random.choice(survivors)
            add_credits(target, 3)
            member = await ctx.guild.fetch_member(target)
            await ctx.send(random.choice(bonus_messages).format(name=member.display_name))
            await asyncio.sleep(2)
        elif roll < 0.5:
            target = random.choice(survivors)
            rem = min(credits.get(target, 0), 2)
            credits[target] -= rem
            member = await ctx.guild.fetch_member(target)
            await ctx.send(random.choice(malus_messages).format(name=member.display_name))
            await asyncio.sleep(2)
        elim = random.choice(survivors)
        survivors.remove(elim)
        member = await ctx.guild.fetch_member(elim)
        await ctx.send(f"❌ Round {rnd}: {random.choice(elimination_messages).format(name=member.display_name)}")
        await asyncio.sleep(2)
        left = [(await ctx.guild.fetch_member(uid)).display_name for uid in survivors]
        await ctx.send("🧱 Remaining: " + ", ".join(left))
    winner_id = survivors[0]
    add_credits(winner_id, 15)
    winner = await ctx.guild.fetch_member(winner_id)
    role = discord.utils.get(ctx.guild.roles, name="Lead Renovator") or await ctx.guild.create_role(name="Lead Renovator")
    await winner.add_roles(role)
    await ctx.send(f"🏅 {winner.display_name} is now Lead Renovator (24h)! (+15 XP)")
    asyncio.create_task(remove_role_later(winner, role, 86400))
    await ctx.send(f"🏁 Battle Complete!\n🏗️ Site: {site}\n🎖️ Winner: {winner.display_name}\n🎁 Reward: 15 XP\n🧱 Renovation done.")

# --- /startfirstbattle (5m signup, admin only) ---
@bot.tree.command(name="startfirstbattle", description="Admin: open 5m signup any time")
async def slash_startfirst(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    battle_participants.clear()
    msg = await interaction.response.send_message(
        "🚨 FIRST MYİKKİ BATTLE in #battle-renovation!\nClick 🔨 to join within 5 minutes."
    )
    msg = await interaction.original_response()
    global signup_message_id
    signup_message_id = msg.id
    save_signup()
    await msg.add_reaction("🔨")
    async def finish():
        await asyncio.sleep(300)
        channel = interaction.channel
        for uid in battle_participants:
            member = await interaction.guild.fetch_member(uid)
            await channel.send(f"🧱 {member.display_name} joined the first battle!")
        class C: guild=interaction.guild; send=channel.send
        await run_battle(C)
    asyncio.create_task(finish())

# --- /startbattle (11h signup, max 2 per 12h) ---
@bot.tree.command(name="startbattle", description="Admin: open 11h signup rumble")
async def slash_startbattle(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    now = datetime.datetime.utcnow()
    window = [t for t in last_battle_time.get(interaction.guild.id, []) if (now - t).total_seconds() < 43200]
    if len(window) >= 2:
        return await interaction.response.send_message("⏳ Max 2 per 12h.", ephemeral=True)
    battle_participants.clear()
    msg = await interaction.response.send_message("🚨 RUMBLE: React 🔨 to join within 11 hours.")
    msg = await interaction.original_response()
    signup_message_id = msg.id
    save_signup()
    await msg.add_reaction("🔨")
    async def finish():  
        await asyncio.sleep(11 * 3600)
        class C: guild=interaction.guild; send=interaction.channel.send
        await run_battle(C)
    asyncio.create_task(finish())

# === Keep-alive endpoint for external monitoring ===
app = Flask("")
@app.route("/")
def home():
    return "I'm alive!"

threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080))),
    daemon=True
).start()

# === Run the bot ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set in environment")
    bot.run(token)
