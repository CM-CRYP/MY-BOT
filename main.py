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
from discord import ui, ButtonStyle, app_commands
from discord.ext import commands

# === Load env ===
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# === Globals ===
credits: dict[int,int] = {}
last_quiz_time: dict[int,datetime.datetime] = {}
last_quest_time: dict[int,datetime.datetime] = {}
last_battle_time: dict[int,list[datetime.datetime]] = {}
battle_participants: list[int] = []
signup_message_id: int | None = None
battle_in_progress = False

# === Adventure state ===
ADVENTURE_CHANNEL_ID = 1390419715393978388  # Mets ici le canal si tu veux restreindre, sinon ignore
adventure_states: dict[int,dict] = {}
last_adventure: dict[int,datetime.date] = {}

# === Quiz questions (20 Yes / 20 No) ===
quiz_questions = [
    {"question": "Can you create a digital twin of a building with MYIKKI? (Yes/No)", "answer": "Yes"},
    {"question": "Is MYIKKI’s digital twin visualized in 3D in real time? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYIKKI offer an interactive photorealistic rendering engine? (Yes/No)", "answer": "Yes"},
    {"question": "Can you estimate renovation budgets automatically with MYIKKI? (Yes/No)", "answer": "Yes"},
    {"question": "Are MYIKKI’s project data secured by blockchain technology? (Yes/No)", "answer": "Yes"},
    {"question": "Can users share renovation projects with contractors through NFTs? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYIKKI support thermal imaging to assess energy performance? (Yes/No)", "answer": "Yes"},
    {"question": "Is MYIKKI designed for both professionals and private owners? (Yes/No)", "answer": "Yes"},
    {"question": "Can users update the digital twin during the renovation process? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYIKKI help solve coordination and budget issues on site? (Yes/No)", "answer": "Yes"},
    {"question": "Can digital twins in MYIKKI help detect issues before construction starts? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYIKKI enable real-time monitoring of renovation progress? (Yes/No)", "answer": "Yes"},
    {"question": "Is MYIKKI presented as a Web3 global solution? (Yes/No)", "answer": "Yes"},
    {"question": "Does the MYIKKI platform reward users with XP or badges? (Yes/No)", "answer": "Yes"},
    {"question": "Is the digital twin used to validate final work delivery? (Yes/No)", "answer": "Yes"},
    {"question": "Are MYIKKI’s interactions timestamped and verifiable? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYIKKI help reduce errors and extra costs during renovation? (Yes/No)", "answer": "Yes"},
    {"question": "Can you invite artisans and architects directly into your digital twin? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYIKKI’s ecosystem include both on-chain and off-chain features? (Yes/No)", "answer": "Yes"},
    {"question": "Can a non-developer easily use MYIKKI to plan renovations? (Yes/No)", "answer": "Yes"},
    {"question": "Does MYIKKI only work for new construction projects? (Yes/No)", "answer": "No"},
    {"question": "Is MYIKKI limited to users in France only? (Yes/No)", "answer": "No"},
    {"question": "Can you use MYIKKI without creating a digital twin? (Yes/No)", "answer": "No"},
    {"question": "Is MYIKKI a traditional real estate agency? (Yes/No)", "answer": "No"},
    {"question": "Does MYIKKI sell building materials directly? (Yes/No)", "answer": "No"},
    {"question": "Can MYIKKI function entirely offline without internet? (Yes/No)", "answer": "No"},
    {"question": "Is MYIKKI a DeFi lending platform? (Yes/No)", "answer": "No"},
    {"question": "Does MYIKKI replace the need for real architects? (Yes/No)", "answer": "No"},
    {"question": "Is MYIKKI only accessible via mobile app? (Yes/No)", "answer": "No"},
    {"question": "Can you claim financial property ownership with MYIKKI NFTs? (Yes/No)", "answer": "No"},
    {"question": "Can MYIKKI be used to decorate interiors with virtual furniture only? (Yes/No)", "answer": "No"},
    {"question": "Does MYIKKI require owning cryptocurrency to use the platform? (Yes/No)", "answer": "No"},
    {"question": "Is MYIKKI exclusively focused on luxury real estate? (Yes/No)", "answer": "No"},
    {"question": "Can MYIKKI be used to rent vacation homes? (Yes/No)", "answer": "No"},
    {"question": "Does MYIKKI offer virtual reality headset support as of today? (Yes/No)", "answer": "No"},
    {"question": "Is MYIKKI a social media platform for homeowners? (Yes/No)", "answer": "No"},
    {"question": "Does MYIKKI operate as a government-certified renovation agency? (Yes/No)", "answer": "No"},
    {"question": "Can MYIKKI replace all interactions with contractors entirely? (Yes/No)", "answer": "No"},
    {"question": "Is the MYIKKI token already listed on major crypto exchanges? (Yes/No)", "answer": "No"},
    {"question": "Does MYIKKI use a centralized database to store project data? (Yes/No)", "answer": "No"},
]

# === Quests & Battle data ===
quests = ["Inspect a window", "Certify a roof", "Upgrade the insulation", "Scan for mold"]
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
    "{name} mis-tightened the platform bolts — -2 XP et stumbles off the scaffold!",
    "{name} flew their drone into a wall — device crashes, -3 XP and grounded for a round!",
    "{name} knocked over the paint mixer — sprayed in the face, -2 XP and blinded next event!",
    "{name} forgot to secure the ladder — falls, -4 XP and sits out one round!",
    "{name} overloaded the power circuit — sparks fly, -3 XP and electrical hazard next turn!",
    "{name} slipped on grease — -1 XP and loses their next action!"
]

# === Helper functions ===
def add_credits(user_id: int, amount: int):
    credits[user_id] = credits.get(user_id, 0) + amount

def get_credits(user_id: int) -> int:
    return credits.get(user_id, 0)

async def remove_role_later(member: discord.Member, role: discord.Role, delay: int):
    await asyncio.sleep(delay)
    await member.remove_roles(role)

def is_admin(user: discord.User | discord.Member) -> bool:
    return (
        user.id == 865185894197887018
        or any(r.name in ("Administrator", "Chief Discord Officer") for r in getattr(user, "roles", []))
    )

# === Keep-alive (Flask) ===
def keep_awake():
    url = f"http://localhost:{os.getenv('PORT',8080)}/"
    while True:
        try:
            requests.get(url, timeout=5)
        except:
            pass
        time.sleep(60)

threading.Thread(target=keep_awake, daemon=True).start()

# === Bot setup ===
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        # Enregistre le groupe aventure
        self.tree.add_command(adventure_group)
        # Sync des slash-commands
        if GUILD_ID:
            await self.tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"🔄 Slash-commands synchronisées sur le serveur {GUILD_ID}")
        else:
            await self.tree.sync()
            print("🔄 Slash-commands synchronisées globalement (peut prendre 1h)")

bot = MyBot()

# === on_ready pour debug ===
@bot.event
async def on_ready():
    print(f"🔑 Connecté en tant que {bot.user} ({bot.user.id})")

# === Réactions pour battles ===
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    global signup_message_id
    if payload.user_id == bot.user.id: return
    if not battle_in_progress or payload.message_id != signup_message_id: return
    if str(payload.emoji) == "🔨":
        credits.setdefault(payload.user_id, 0)
        if payload.user_id not in battle_participants:
            battle_participants.append(payload.user_id)
            chan = bot.get_channel(payload.channel_id)
            usr = await bot.fetch_user(payload.user_id)
            await chan.send(f"🧱 {usr.display_name} joined the battle!")

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    global signup_message_id
    if payload.user_id == bot.user.id: return
    if not battle_in_progress or payload.message_id != signup_message_id: return
    if str(payload.emoji) == "🔨" and payload.user_id in battle_participants:
        battle_participants.remove(payload.user_id)

# --- /quiz ---
@bot.tree.command(name="quiz", description="Take your daily yes/no MYIKKI quiz")
async def slash_quiz(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    last = last_quiz_time.get(interaction.user.id)
    if last and (now-last).total_seconds()<86400:
        return await interaction.response.send_message("⏳ Only once per 24h.", ephemeral=True)
    q = random.choice(quiz_questions)
    await interaction.response.send_message(f"🧠 Quiz: **{q['question']}**")
    def check(m: discord.Message):
        return (
            m.author.id==interaction.user.id
            and m.channel.id==interaction.channel.id
            and m.content.lower().strip() in ("yes","no")
        )
    try:
        m = await bot.wait_for("message", timeout=30, check=check)
        if m.content.lower().strip()==q["answer"].lower():
            add_credits(interaction.user.id,5)
            last_quiz_time[interaction.user.id]=now
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
    if last and (now-last).total_seconds()<86400:
        return await interaction.response.send_message("⏳ Only one quest per 24h.", ephemeral=True)
    task = random.choice(quests)
    reward = random.randint(3,7)
    add_credits(interaction.user.id, reward)
    last_quest_time[interaction.user.id] = now
    await interaction.response.send_message(
        f"🛠️ Quest: **{task}**\n✅ +{reward} XP (Total: {get_credits(interaction.user.id)} XP)"
    )

# --- /creditscore ---
@bot.tree.command(name="creditscore", description="Check your current XP")
async def slash_creditscore(interaction: discord.Interaction):
    await interaction.response.send_message(f"💰 You have {get_credits(interaction.user.id)} XP.")

# --- run_battle (logic + error capture) ---
async def run_battle(ctx):
    global battle_in_progress, signup_message_id
    try:
        survivors = list(dict.fromkeys(battle_participants))
        if len(survivors) < 2:
            return await ctx.send("❌ Not enough participants.")
        signup_message_id=None
        now = datetime.datetime.utcnow()
        last_battle_time.setdefault(ctx.guild.id,[]).append(now)
        site = random.choice(building_types)

        await ctx.send(f"🏗️ Battle at **{site}** with {len(survivors)} players!")
        await asyncio.sleep(3)
        mentions = [(await ctx.guild.fetch_member(uid)).mention for uid in survivors]
        await ctx.send(f"🎯 Participants: {', '.join(mentions)}")
        await asyncio.sleep(3)

        rnd=0
        while len(survivors)>1:
            rnd+=1
            if random.random()<0.4:
                await ctx.send(random.choice(event_messages))
                await asyncio.sleep(3)
            roll=random.random()
            if roll<0.3:
                t=random.choice(survivors)
                add_credits(t,3)
                mem=await ctx.guild.fetch_member(t)
                await ctx.send(random.choice(bonus_messages).format(name=mem.display_name))
                await asyncio.sleep(3)
            elif roll<0.5:
                t=random.choice(survivors)
                rem=min(get_credits(t),2)
                credits[t]=get_credits(t)-rem
                mem=await ctx.guild.fetch_member(t)
                await ctx.send(random.choice(malus_messages).format(name=mem.display_name))
                await asyncio.sleep(3)
            elim=random.choice(survivors)
            survivors.remove(elim)
            mem=await ctx.guild.fetch_member(elim)
            await ctx.send(f"❌ Round {rnd}: {random.choice(elimination_messages).format(name=mem.display_name)}")
            await asyncio.sleep(3)
            left=[(await ctx.guild.fetch_member(uid)).display_name for uid in survivors]
            await ctx.send("🧱 Remaining: "+", ".join(left))
            await asyncio.sleep(3)

        winner_id=survivors[0]
        add_credits(winner_id,15)
        winner=await ctx.guild.fetch_member(winner_id)
        role=discord.utils.get(ctx.guild.roles,name="Lead Renovator") or await ctx.guild.create_role(name="Lead Renovator")
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
        tb=traceback.format_exc()
        await ctx.send(f"```py\n{tb}\n```")
    finally:
        battle_in_progress=False
        signup_message_id=None
        battle_participants.clear()

# --- /startfirstbattle ---
@bot.tree.command(name="startfirstbattle", description="Admin: open 5m signup at will")
async def slash_startfirst(interaction: discord.Interaction):
    global battle_in_progress, signup_message_id
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    if battle_in_progress:
        return await interaction.response.send_message("❌ A battle is already in progress.", ephemeral=True)

    battle_in_progress=True
    battle_participants.clear()
    msg=await interaction.response.send_message(
        "🚨 FIRST MYIKKI BATTLE in #battle-renovation!\nClick 🔨 to join within 5 minutes."
    )
    msg=await interaction.original_response()
    signup_message_id=msg.id
    await msg.add_reaction("🔨")

    async def finish():
        await asyncio.sleep(300)
        class Ctx: guild=interaction.guild; send=interaction.channel.send
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

    now=datetime.datetime.utcnow()
    window=[t for t in last_battle_time.get(interaction.guild.id,[]) if (now-t).total_seconds()<11*3600]
    if len(window)>=2:
        return await interaction.response.send_message("⏳ Max 2 per 11h.", ephemeral=True)

    battle_in_progress=True
    battle_participants.clear()
    msg=await interaction.response.send_message("🚨 RUMBLE: React 🔨 to join within 11 hours.")
    msg=await interaction.original_response()
    signup_message_id=msg.id
    await msg.add_reaction("🔨")

    async def finish():
        await asyncio.sleep(11*3600)
        class Ctx: guild=interaction.guild; send=interaction.channel.send
        await run_battle(Ctx())
    asyncio.create_task(finish())

# === Text-Adventure scenes ===
scenes: list[dict] = [
    {
        "text": (
            "**Scene 1 – The Manor Hall**\n"
            "You step into the Art Deco hall: cracks spiderweb across the marble floor, "
            "and a door sensor is blinking red. What do you do?"
        ),
        "choices": [
            {"label":"1️⃣ Check the blockchain sensor","next":1,"xp":1},
            {"label":"2️⃣ Inspect the cracks in the floor","next":2,"xp":1},
            {"label":"3️⃣ Call a colleague for help","next":3,"xp":0},
            {"label":"4️⃣ Ignore the hazard and proceed","eliminate":True}
        ]
    },
    {
        "text": (
            "**Scene 2 – Sabotaged Sensor**\n"
            "The sensor’s logs show unauthorized access last night. What’s your action?"
        ),
        "choices":[
            {"label":"1️⃣ Reset the smart contract","next":4,"xp":1},
            {"label":"2️⃣ Return to the hall to find the culprit","next":5},
            {"label":"3️⃣ Attempt a risky rollback","eliminate":True},
            {"label":"4️⃣ Deep-scan the blockchain logs","next":6,"xp":2}
        ]
    },
    {
        "text": (
            "**Scene 3 – Deep Cracks**\n"
            "Under the cracks you spot a faint graffito “MYI-001”. What now?"
        ),
        "choices":[
            {"label":"1️⃣ Scan it in 3D","next":6,"xp":2},
            {"label":"2️⃣ Photograph for analysis","next":7,"xp":1},
            {"label":"3️⃣ Patch it up quickly","eliminate":True},
            {"label":"4️⃣ Question the owner about it","next":5}
        ]
    },
    {
        "text": (
            "**Scene 4 – Call for Backup**\n"
            "Your colleague is stuck at the entrance, alarmed. What order do you give?"
        ),
        "choices":[
            {"label":"1️⃣ Secure the area with ropes","next":2,"xp":1},
            {"label":"2️⃣ Launch a drone inspection","next":6,"xp":1},
            {"label":"3️⃣ Retreat immediately","eliminate":True},
            {"label":"4️⃣ Erect a temporary barrier","next":4,"xp":1}
        ]
    },
    {
        "text": (
            "**Scene 5 – Rollback Attempt**\n"
            "Your reset fails and corrupts the admin key. You lose 1 XP. What now?"
        ),
        "choices":[
            {"label":"1️⃣ Re-inspect the floor","next":2},
            {"label":"2️⃣ Search for a local backup","next":8,"xp":1},
            {"label":"3️⃣ Force a manual patch","eliminate":True},
            {"label":"4️⃣ Temporarily pause and draft an estimate","next":7}
        ]
    },
    {
        "text": (
            "**Scene 6 – Owner Interview**\n"
            "The owner shows you an old archive file. Which action?"
        ),
        "choices":[
            {"label":"1️⃣ Read the entire archive","next":9,"xp":2},
            {"label":"2️⃣ Photocopy sensitive pages","next":7,"xp":1},
            {"label":"3️⃣ Ignore and return to the hall","next":0},
            {"label":"4️⃣ Destroy what you find suspicious","eliminate":True}
        ]
    },
    {
        "text": (
            "**Scene 7 – Drone Analysis**\n"
            "The drone reveals a hidden tunnel beneath the manor. Decision?"
        ),
        "choices":[
            {"label":"1️⃣ Explore the tunnel","next":10,"xp":2},
            {"label":"2️⃣ Alert the rescue team","next":9},
            {"label":"3️⃣ Abandon the drone and go alone","eliminate":True},
            {"label":"4️⃣ Check structural stability first","next":8,"xp":1}
        ]
    },
    {
        "text": (
            "**Scene 8 – Image Analysis**\n"
            "Your photos show an ancient symbol. Which lead do you follow?"
        ),
        "choices":[
            {"label":"1️⃣ Compare with archeology database","next":9,"xp":2},
            {"label":"2️⃣ Ignore and start digging","eliminate":True},
            {"label":"3️⃣ Study thermal scans","next":10,"xp":1},
            {"label":"4️⃣ Reprogram the sensor for more data","next":8,"xp":1}
        ]
    },
    {
        "text": (
            "**Scene 9 – Backup Retrieval**\n"
            "You find a server backup mais it’s password-protected. What do you do?"
        ),
        "choices":[
            {"label":"1️⃣ Try a brute-force attack","eliminate":True},
            {"label":"2️⃣ Use the official MYIKKI tool","next":11,"xp":2},
            {"label":"3️⃣ Search paper archives","next":9,"xp":1},
            {"label":"4️⃣ Bypass the security","next":10}
        ]
    },
    {
        "text": (
            "**Scene 10 – Decoded Archives**\n"
            "The files reveal a secret protocol to disable the sabotage. Next step?"
        ),
        "choices":[
            {"label":"1️⃣ Apply the protocol immediately","next":11,"xp":2},
            {"label":"2️⃣ Verify code integrity","next":10,"xp":1},
            {"label":"3️⃣ Send an incomplete report","eliminate":True},
            {"label":"4️⃣ Backup before executing","next":11,"xp":1}
        ]
    },
    {
        "text": (
            "**Scene 11 – Secret Tunnel**\n"
            "Inside the tunnel you find a sealed chest. What do you do?"
        ),
        "choices":[
            {"label":"1️⃣ Open with the laser tool","next":11,"xp":2},
            {"label":"2️⃣ Place an explosive charge","eliminate":True},
            {"label":"3️⃣ Bypass the chest mechanism","next":11},
            {"label":"4️⃣ Call for reinforcements","next":11,"xp":1}
        ]
    },
    {
        "text": (
            "**Scene 12 – Success or Failure**\n"
            "You’ve neutralized the sabotage et secured the manor!\n\n"
            "🎉 **Your adventure summary:**"
        ),
        "choices":[
            {"label":"See my report","next":None}
        ]
    },
]

# --- Adventure group & handlers ---
adventure_group = app_commands.Group(name="adventure", description="MYIKKI text adventure")

@adventure_group.command(name="start", description="Start your adventure (once per day)")
async def adventure_start(interaction: discord.Interaction):
    user_id = interaction.user.id
    # Optionnel : restreindre à un channel
    if ADVENTURE_CHANNEL_ID and interaction.channel.id!=ADVENTURE_CHANNEL_ID:
        return await interaction.response.send_message(
            f"❌ Use this in <#{ADVENTURE_CHANNEL_ID}>", ephemeral=True
        )
    today = (datetime.datetime.utcnow()+datetime.timedelta(hours=1)).date()
    if last_adventure.get(user_id)==today:
        return await interaction.response.send_message(
            "❌ Déjà joué aujourd'hui. Reviens demain!", ephemeral=True
        )
    adventure_states[user_id]={"step":0,"xp":0,"inventory":[]}
    last_adventure[user_id]=today
    await send_scene(interaction, user_id)

@adventure_group.command(name="status", description="Show your current adventure progress")
async def adventure_status(interaction: discord.Interaction):
    st=adventure_states.get(interaction.user.id)
    if not st:
        return await interaction.response.send_message(
            "❌ Aucune aventure en cours. `/adventure start`", ephemeral=True
        )
    await interaction.response.send_message(
        f"🗺️ Scene {st['step']+1}/{len(scenes)} — XP: {st['xp']}", ephemeral=True
    )

@adventure_group.command(name="end", description="Abandon your current adventure")
async def adventure_end(interaction: discord.Interaction):
    if interaction.user.id in adventure_states:
        del adventure_states[interaction.user.id]
        return await interaction.response.send_message(
            "❌ Aventure abandonnée.", ephemeral=True
        )
    return await interaction.response.send_message(
        "❌ Pas d’aventure en cours.", ephemeral=True
    )

async def send_scene(interaction: discord.Interaction, user_id: int):
    st=adventure_states[user_id]
    sc=scenes[st["step"]]
    content=sc["text"]+"\n\n"+ "\n".join(c["label"] for c in sc["choices"])
    view=AdventureView(user_id, sc["choices"])
    await interaction.response.send_message(content, view=view)

async def handle_choice(interaction: discord.Interaction, idx: int):
    user_id=interaction.user.id
    st=adventure_states.get(user_id)
    if not st:
        return await interaction.response.send_message("❌ No adventure.", ephemeral=True)
    sc=scenes[st["step"]]
    choice=sc["choices"][idx]
    if choice.get("eliminate"):
        await interaction.response.edit_message(
            content=f"{choice['label']}\n\n💥 Eliminé!", view=None
        )
        del adventure_states[user_id]
        return
    st["xp"]+=choice.get("xp",0)
    nxt=choice.get("next")
    if nxt is None:
        summ=(
            f"{sc['text']}\n\n✅ **Terminé!**\n"
            f"Total XP: {st['xp']}\n"
            f"Inventaire: {', '.join(st['inventory']) or 'none'}"
        )
        await interaction.response.edit_message(content=summ, view=None)
        del adventure_states[user_id]
        return
    st["step"]=nxt
    await interaction.response.edit_message(
        content=scenes[nxt]["text"]+"\n\n"+ "\n".join(c["label"] for c in scenes[nxt]["choices"]),
        view=AdventureView(user_id, scenes[nxt]["choices"])
    )

class AdventureView(ui.View):
    def __init__(self, user_id:int, choices:list[dict]):
        super().__init__(timeout=120)
        self.user_id=user_id
        for i,c in enumerate(choices):
            btn=ui.Button(label=c["label"].split(" ",1)[1], style=ButtonStyle.primary, custom_id=str(i))
            async def on_click(inter:discord.Interaction, idx=i):
                await handle_choice(inter, idx)
            btn.callback=on_click
            self.add_item(btn)
    async def interaction_check(self, inter:discord.Interaction)->bool:
        if inter.user.id!=self.user_id:
            await inter.response.send_message("⛔ Pas ta partie.", ephemeral=True)
            return False
        return True

# === Flask endpoint (keep-alive) ===
app = Flask("")
@app.route("/")
def home(): return "Alive"

threading.Thread(target=lambda: app.run(host="0.0.0.0",port=int(os.getenv("PORT",8080))),daemon=True).start()

# === Run ===
if __name__=="__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set.")
    bot.run(DISCORD_TOKEN)
