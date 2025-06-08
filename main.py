# main.py

import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import random
import datetime
import asyncio
from flask import Flask
from threading import Thread

# === Load environment variables from .env (local) ===
load_dotenv()

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

# === Data Structures ===
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

# === Helper Functions ===
def add_credits(user_id, amount):
    credits[user_id] = credits.get(user_id, 0) + amount

def get_credits(user_id):
    return credits.get(user_id, 0)

async def remove_role_later(member, role, delay_seconds):
    await asyncio.sleep(delay_seconds)
    await member.remove_roles(role)

# === Quiz Command ===
@bot.command()
async def quiz(ctx):
    now = datetime.datetime.utcnow()
    last = last_quiz_time.get(ctx.author.id)
    if last and (now - last).total_seconds() < 86400:
        return await ctx.send("⏳ You can only do the quiz once every 24 hours.")
    q = random.choice(quiz_questions)
    await ctx.send(f"🧠 Quiz Time!\n{q['question']}")
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        m = await bot.wait_for("message", check=check, timeout=60)
        if m.content.lower().strip() == q["answer"].lower().strip():
            add_credits(ctx.author.id, 5)
            last_quiz_time[ctx.author.id] = now
            await ctx.send(f"✅ Correct! +5 XP (Total: {get_credits(ctx.author.id)} XP)")
        else:
            await ctx.send("❌ Incorrect. Try again tomorrow!")
    except asyncio.TimeoutError:
        await ctx.send("⌛ Time’s up! You had 60 seconds to answer.")

# === Quest Command (once per day) ===
@bot.command()
async def quest(ctx):
    now = datetime.datetime.utcnow()
    last = last_quest_time.get(ctx.author.id)
    if last and (now - last).total_seconds() < 86400:
        return await ctx.send("⏳ Only one daily quest allowed per 24 h.")
    task = random.choice(quests)
    reward = random.randint(3, 7)
    add_credits(ctx.author.id, reward)
    last_quest_time[ctx.author.id] = now
    await ctx.send(f"🛠️ Quest: **{task}**\n✅ You earned {reward} XP (Total: {get_credits(ctx.author.id)} XP)")

# === Credit Score ===
@bot.command()
async def creditscore(ctx):
    await ctx.send(f"💰 You have {get_credits(ctx.author.id)} XP.")

# === First Battle: 2-minute signup ===
@bot.command()
@commands.has_any_role("Administrator", "Chief Discord Officer")
async def startfirstbattle(ctx):
    if ctx.guild.id in last_battle_time:
        return await ctx.send("⚠️ First battle already run.")
    battle_participants.clear()
    msg = await ctx.send(
        "🚨 **FIRST MYİKKİ BATTLE** in #battle-renovation!\n"
        "Click 🔨 to join within 2 minutes."
    )
    await msg.add_reaction("🔨")
    def check(r, u): return r.message.id == msg.id and str(r.emoji) == "🔨" and not u.bot
    try:
        while True:
            r, u = await bot.wait_for("reaction_add", timeout=120, check=check)
            if u.id not in battle_participants:
                battle_participants.append(u.id)
                await ctx.send(f"🧱 {u.display_name} joined the first battle!")
    except asyncio.TimeoutError:
        pass
    await run_battle(ctx)

# === Regular Battle: 11-hour signup, max 2 per 12 h ===
@bot.command()
@commands.has_any_role("Administrator", "Chief Discord Officer")
async def startbattle(ctx):
    now = datetime.datetime.utcnow()
    window = last_battle_time.get(ctx.guild.id, [])
    window = [t for t in window if (now - t).total_seconds() < 43200]
    if len(window) >= 2:
        return await ctx.send("⏳ Only 2 battles allowed per 12 h.")
    battle_participants.clear()
    msg = await ctx.send(
        "🚨 **MYİKKİ RUMBLE RENOVATION** in #battle-renovation!\n"
        "Click 🔨 to join within 11 hours."
    )
    await msg.add_reaction("🔨")
    def check(r, u): return r.message.id == msg.id and str(r.emoji) == "🔨" and not u.bot
    end = now + datetime.timedelta(hours=11)
    while datetime.datetime.utcnow() < end:
        try:
            r, u = await bot.wait_for("reaction_add", timeout=60, check=check)
            if u.id not in battle_participants:
                battle_participants.append(u.id)
                await ctx.send(f"🧱 {u.display_name} joined the Rumble!")
        except asyncio.TimeoutError:
            continue
    await run_battle(ctx)

# === Core Battle Logic ===
async def run_battle(ctx):
    if len(battle_participants) < 2:
        return await ctx.send("❌ Not enough participants. Cancelled.")
    now = datetime.datetime.utcnow()
    last_battle_time.setdefault(ctx.guild.id, []).append(now)

    site = random.choice(building_types)
    await ctx.send(f"🏗️ Battle at **{site}** with {len(battle_participants)} players!")
    mentions = [(await ctx.guild.fetch_member(uid)).mention for uid in battle_participants]
    await ctx.send("🎯 Participants: " + ", ".join(mentions))

    survivors = battle_participants.copy()
    rnd = 0
    while len(survivors) > 1:
        rnd += 1
        await asyncio.sleep(4)

        # random event
        if random.random() < 0.4:
            await ctx.send(random.choice(event_messages))
            await asyncio.sleep(3)

        # bonus or malus
        roll = random.random()
        if roll < 0.3:
            target = random.choice(survivors)
            add_credits(target, 3)
            member = await ctx.guild.fetch_member(target)
            await ctx.send(random.choice(bonus_messages).format(name=member.display_name))
            await asyncio.sleep(2)
        elif roll < 0.5:
            target = random.choice(survivors)
            remove_amount = min(credits.get(target, 0), 2)
            credits[target] = credits.get(target, 0) - remove_amount
            member = await ctx.guild.fetch_member(target)
            await ctx.send(random.choice(malus_messages).format(name=member.display_name))
            await asyncio.sleep(2)

        # elimination
        elim = random.choice(survivors)
        survivors.remove(elim)
        mem = await ctx.guild.fetch_member(elim)
        await ctx.send(f"❌ Round {rnd}: {random.choice(elimination_messages).format(name=mem.display_name)}")
        await asyncio.sleep(3)

        # survivors update
        left = [(await ctx.guild.fetch_member(uid)).display_name for uid in survivors]
        await ctx.send("🧱 Remaining: " + ", ".join(left))

    # winner
    winner_id = survivors[0]
    winner = await ctx.guild.fetch_member(winner_id)
    add_credits(winner_id, 15)

    role = discord.utils.get(ctx.guild.roles, name="Lead Renovator")
    if not role:
        role = await ctx.guild.create_role(name="Lead Renovator")
    await winner.add_roles(role)
    await ctx.send(f"🏅 {winner.display_name} is now Lead Renovator (24 h role)!")
    asyncio.create_task(remove_role_later(winner, role, 86400))

    await ctx.send(f"""
🏁 **Battle Complete**
🏗️ Site: {site}
🎖️ Winner: {winner.display_name}
🎁 Reward: 15 XP
🧱 Renovation done.
""")

# === Flask Keep-Alive for Render ===
app = Flask('')
@app.route('/')
def home():
    return "I'm alive"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run).start()

# === Run the Bot ===
bot.run(os.environ["DISCORD_TOKEN"])
