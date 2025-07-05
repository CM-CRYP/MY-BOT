import os
import random
import datetime
import asyncio
import threading
import traceback
from dotenv import load_dotenv
from flask import Flask
import discord
from discord import ui, ButtonStyle, app_commands
from discord.ext import commands

# === ENV ===
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
GUILD_OBJ = discord.Object(id=GUILD_ID)

# === Globals ===
credits, last_quiz_time, last_quest_time, last_battle_time = {}, {}, {}, {}
battle_participants, signup_message_id, battle_in_progress = [], None, False
ADVENTURE_CHANNEL_ID = None
adventure_states, last_adventure = {}, {}

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

quests = ["Inspect a window", "Certify a roof", "Upgrade the insulation", "Scan for mold"]
building_types = [
    "an old Parisian apartment building", "an abandoned rural school", "a crumbling medieval castle", "a derelict industrial warehouse",
    "a seaside lighthouse in disrepair", "a solar-powered eco-village complex", "a futuristic smart home prototype",
    "a high-rise glass office tower", "an underground subway tunnel station", "a vintage Art Deco theater",
    "a collapsing water treatment plant", "an offshore oil rig platform", "an abandoned amusement park pavilion",
    "a restored Victorian row house", "a geodesic dome greenhouse", "a windmill farm control station",
    "a derelict mountain chalet", "a modern floating skyscraper model", "a jungle treehouse research station", "a heritage Gothic cathedral"
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

def add_credits(user_id, amount):
    credits[user_id] = credits.get(user_id, 0) + amount
def get_credits(user_id):
    return credits.get(user_id, 0)
def is_admin(user):
    return user.id == 865185894197887018 or any(r.name in ("Administrator", "Chief Discord Officer") for r in getattr(user, "roles", []))

app = Flask(__name__)
@app.route("/")
def home():
    return "I'm alive!"
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080))), daemon=True).start()

# === Text-Adventure definitions ===

scenes: list[dict] = [
    # SCÈNE 1
    {
        "text": "**Scene 1 – The Manor Hall**\nYou step into the Art Deco hall: cracks spiderweb across the marble floor, and a door sensor is blinking red. What do you do?",
        "choices": [
            {"label": "1️⃣ Check the blockchain sensor", "next": 1, "xp": 1},
            {"label": "2️⃣ Inspect the cracks in the floor", "next": 2, "xp": 1},
            {"label": "3️⃣ Call a colleague for help", "next": 3, "xp": 0},
            {"label": "4️⃣ Ignore the hazard and proceed", "eliminate": True},
            {"label": "5️⃣ Explore a strange alcove you spot", "next": 36},  # Mini-Scene A
        ]
    },
    # SCÈNE 2
    {
        "text": "**Scene 2 – Sabotaged Sensor**\nThe sensor’s logs show unauthorized access last night. What’s your action?",
        "choices": [
            {"label": "1️⃣ Reset the smart contract", "next": 4, "xp": 1},
            {"label": "2️⃣ Return to the hall to find the culprit", "next": 5},
            {"label": "3️⃣ Attempt a risky rollback", "eliminate": True},
            {"label": "4️⃣ Deep-scan the blockchain logs", "next": 6, "xp": 2},
        ]
    },
    # SCÈNE 3
    {
        "text": "**Scene 3 – Deep Cracks**\nUnder the cracks you spot a faint graffito “MYI-001”. What now?",
        "choices": [
            {"label": "1️⃣ Scan it in 3D", "next": 6, "xp": 2},
            {"label": "2️⃣ Photograph for analysis", "next": 7, "xp": 1},
            {"label": "3️⃣ Patch it up quickly", "eliminate": True},
            {"label": "4️⃣ Question the owner about it", "next": 5},
            {"label": "5️⃣ Use tongs to check a glowing waste bin nearby", "next": 44},  # Mini-Scene I
        ]
    },
    # SCÈNE 4
    {
        "text": "**Scene 4 – Call for Backup**\nYour colleague is stuck at the entrance, alarmed. What order do you give?",
        "choices": [
            {"label": "1️⃣ Secure the area with ropes", "next": 2, "xp": 1},
            {"label": "2️⃣ Launch a drone inspection", "next": 6, "xp": 1},
            {"label": "3️⃣ Retreat immediately", "eliminate": True},
            {"label": "4️⃣ Erect a temporary barrier", "next": 4, "xp": 1},
        ]
    },
    # SCÈNE 5
    {
        "text": "**Scene 5 – Rollback Attempt**\nYour reset fails and corrupts the admin key. You lose 1 XP. What now?",
        "choices": [
            {"label": "1️⃣ Re-inspect the floor", "next": 2},
            {"label": "2️⃣ Search for a local backup", "next": 8, "xp": 1},
            {"label": "3️⃣ Force a manual patch", "eliminate": True},
            {"label": "4️⃣ Temporarily pause and draft an estimate", "next": 7},
        ]
    },
    # SCÈNE 6
    {
        "text": "**Scene 6 – Owner Interview**\nThe owner shows you an old archive file. Which action?",
        "choices": [
            {"label": "1️⃣ Read the entire archive", "next": 9, "xp": 2},
            {"label": "2️⃣ Photocopy sensitive pages", "next": 7, "xp": 1},
            {"label": "3️⃣ Ignore and return to the hall", "next": 0},
            {"label": "4️⃣ Destroy what you find suspicious", "eliminate": True},
            {"label": "5️⃣ Drag a fallen locker you spot into the open", "next": 42},  # Mini-Scene G
        ]
    },
    # SCÈNE 7
    {
        "text": "**Scene 7 – Drone Analysis**\nThe drone reveals a hidden tunnel beneath the manor. Decision?",
        "choices": [
            {"label": "1️⃣ Explore the tunnel", "next": 10, "xp": 2},
            {"label": "2️⃣ Alert the rescue team", "next": 9},
            {"label": "3️⃣ Abandon the drone and go alone", "eliminate": True},
            {"label": "4️⃣ Check structural stability first", "next": 8, "xp": 1},
            {"label": "5️⃣ Search for an old workbench in the shadows", "next": 41},  # Mini-Scene F
        ]
    },
    # SCÈNE 8
    {
        "text": "**Scene 8 – Image Analysis**\nYour photos show an ancient symbol. Which lead do you follow?",
        "choices": [
            {"label": "1️⃣ Compare with archeology database", "next": 9, "xp": 2},
            {"label": "2️⃣ Ignore and start digging", "eliminate": True},
            {"label": "3️⃣ Study thermal scans", "next": 10, "xp": 1},
            {"label": "4️⃣ Reprogram the sensor for more data", "next": 8, "xp": 1},
        ]
    },
    # SCÈNE 9
    {
        "text": "**Scene 9 – Backup Retrieval**\nYou find a server backup but it’s password-protected. What do you do?",
        "choices": [
            {"label": "1️⃣ Try a brute-force attack", "eliminate": True},
            {"label": "2️⃣ Use the official MYIKKI tool", "next": 11, "xp": 2},
            {"label": "3️⃣ Search paper archives", "next": 9, "xp": 1},
            {"label": "4️⃣ Bypass the security", "next": 10},
        ]
    },
    # SCÈNE 10
    {
        "text": "**Scene 10 – Decoded Archives**\nThe files reveal a secret protocol to disable the sabotage. Next step?",
        "choices": [
            {"label": "1️⃣ Apply the protocol immediately", "next": 11, "xp": 2},
            {"label": "2️⃣ Verify code integrity", "next": 10, "xp": 1},
            {"label": "3️⃣ Send an incomplete report", "eliminate": True},
            {"label": "4️⃣ Backup before executing", "next": 11, "xp": 1},
        ]
    },
    # SCÈNE 11
    {
        "text": "**Scene 11 – Secret Tunnel**\nInside the tunnel you find a sealed chest. What do you do?",
        "choices": [
            {"label": "1️⃣ Open with the laser tool", "next": 12, "xp": 2},
            {"label": "2️⃣ Place an explosive charge", "eliminate": True},
            {"label": "3️⃣ Bypass the chest mechanism", "next": 13},
            {"label": "4️⃣ Call for reinforcements", "next": 14, "xp": 1},
        ]
    },
    # SCÈNE 12
    {
        "text": "**Scene 12 – Treasure Found**\nInside the chest, you find an encrypted map and a Smart Vest!",
        "choices": [
            {"label": "1️⃣ Take the Smart Vest and study the map", "next": 15, "xp": 2, "item": "Smart Vest"},
            {"label": "2️⃣ Ignore the map", "next": 16},
            {"label": "3️⃣ Share discovery with team", "next": 17, "xp": 1},
            {"label": "4️⃣ Leave chest closed", "next": 18},
            {"label": "5️⃣ Inspect a painting on the wall", "next": 43},  # Mini-Scene H
        ]
    },
    # SCÈNE 13
    {
        "text": "**Scene 13 – Chest Trap**\nThe chest was booby-trapped! You barely escape, but lose 1 XP.",
        "choices": [
            {"label": "1️⃣ Bandage yourself and continue", "next": 19},
            {"label": "2️⃣ Rest and regain energy", "next": 20},
            {"label": "3️⃣ Ignore injuries", "eliminate": True},
            {"label": "4️⃣ Use Nano Patch Kit", "next": 21, "item": "Nano Patch Kit"},
        ]
    },
    # SCÈNE 14
    {
        "text": "**Scene 14 – Call for Help**\nYour team guides you to a hidden maintenance tunnel.",
        "choices": [
            {"label": "1️⃣ Enter the maintenance tunnel", "next": 22, "xp": 1},
            {"label": "2️⃣ Ignore the tunnel", "next": 23},
            {"label": "3️⃣ Set up sensors at entrance", "next": 24},
            {"label": "4️⃣ Thank your team and rest", "next": 25},
        ]
    },
    # SCÈNE 15
    {
        "text": "**Scene 15 – Secret Corridor**\nYou discover a ventilation shaft with a hidden switch.",
        "choices": [
            {"label": "1️⃣ Flip the switch", "next": 26, "xp": 1},
            {"label": "2️⃣ Ignore and move on", "next": 27},
            {"label": "3️⃣ Search for hidden panels", "next": 28},
            {"label": "4️⃣ Take a break", "next": 29},
            {"label": "5️⃣ Search for old tool crates", "next": 39},  # Mini-Scene D
        ]
    },
    # SCÈNE 16
    {
        "text": "**Scene 16 – Archive Room**\nYou stumble into a dusty archive. Ancient blueprints everywhere.",
        "choices": [
            {"label": "1️⃣ Examine the blueprints", "next": 30, "xp": 2},
            {"label": "2️⃣ Ignore them", "next": 31},
            {"label": "3️⃣ Take some for analysis", "next": 32, "xp": 1},
            {"label": "4️⃣ Burn the blueprints", "eliminate": True},
            {"label": "5️⃣ Investigate a blinking control tablet", "next": 38},  # Mini-Scene C
        ]
    },
    # SCÈNE 17
    {
        "text": "**Scene 17 – Puzzle Wall**\nA locked panel blocks your way. There’s a puzzle etched into the metal.",
        "choices": [
            {"label": "1️⃣ Solve the puzzle", "next": 33, "xp": 2},
            {"label": "2️⃣ Force the panel open", "eliminate": True},
            {"label": "3️⃣ Search for clues nearby", "next": 34},
            {"label": "4️⃣ Ask for help", "next": 35},
        ]
    },
    # SCÈNE 18
    {
        "text": "**Scene 18 – Rooftop Access**\nYou climb up a rickety ladder to the rooftop. Storm clouds are gathering.",
        "choices": [
            {"label": "1️⃣ Check weather sensors", "next": 20, "xp": 1},
            {"label": "2️⃣ Take shelter", "next": 21},
            {"label": "3️⃣ Continue repairs", "eliminate": True},
            {"label": "4️⃣ Use Smart Vest", "next": 22, "item": "Smart Vest"},
            {"label": "5️⃣ Check a suspicious box near the antenna", "next": 37},  # Mini-Scene B
        ]
    },
    # SCÈNE 19
    {
        "text": "**Scene 19 – Drone Malfunction**\nYour drone's camera is glitching. You see something in the dark.",
        "choices": [
            {"label": "1️⃣ Attempt manual override", "next": 23, "xp": 1},
            {"label": "2️⃣ Send it into the tunnel anyway", "eliminate": True},
            {"label": "3️⃣ Land it safely", "next": 24},
            {"label": "4️⃣ Reboot system", "next": 25},
            {"label": "5️⃣ Investigate a fallen locker in the hallway", "next": 42},  # Mini-Scene G
        ]
    },
    # SCÈNE 20
    {
        "text": "**Scene 20 – Lightning Strike**\nA lightning bolt hits the building. Emergency protocol engaged!",
        "choices": [
            {"label": "1️⃣ Activate AI backup", "next": 26, "item": "AI Memory Chip"},
            {"label": "2️⃣ Evacuate now", "next": 27},
            {"label": "3️⃣ Ignore alarm", "eliminate": True},
            {"label": "4️⃣ Secure your gear", "next": 28, "xp": 1},
        ]
    },
    # SCÈNE 21
    {
        "text": "**Scene 21 – The Laboratory**\nYou enter a lab filled with experimental gadgets.",
        "choices": [
            {"label": "1️⃣ Test new device", "next": 29, "item": "Encrypted Sensor Key"},
            {"label": "2️⃣ Leave lab", "next": 30},
            {"label": "3️⃣ Take samples", "next": 31, "xp": 1},
            {"label": "4️⃣ Accidentally trigger alarm", "eliminate": True},
        ]
    },
    # SCÈNE 22
    {
        "text": "**Scene 22 – Barricaded Door**\nYou find a door with reinforced steel bars and a keypad.",
        "choices": [
            {"label": "1️⃣ Hack the keypad", "next": 32, "xp": 2},
            {"label": "2️⃣ Search for the code", "next": 33},
            {"label": "3️⃣ Break the bars", "eliminate": True},
            {"label": "4️⃣ Wait for someone to arrive", "next": 34},
            {"label": "5️⃣ Use Lead Renovator key you found", "next": 45},  # Mini-Scene J
        ]
    },
    # SCÈNE 23
    {
        "text": "**Scene 23 – Generator Room**\nYou hear a humming noise. The generator is sparking.",
        "choices": [
            {"label": "1️⃣ Turn off power", "next": 35},
            {"label": "2️⃣ Ignore sparks", "eliminate": True},
            {"label": "3️⃣ Repair the cables", "next": 0, "xp": 2},
            {"label": "4️⃣ Use Nano Patch Kit", "next": 1, "item": "Nano Patch Kit"},
            {"label": "5️⃣ Look into a glowing waste bin in the corner", "next": 44},  # Mini-Scene I
        ]
    },
    # SCÈNE 24
    {
        "text": "**Scene 24 – Tunnel Collapse**\nThe ground shakes! Debris blocks your path.",
        "choices": [
            {"label": "1️⃣ Dig through rubble", "next": 2, "xp": 1},
            {"label": "2️⃣ Search for alternate route", "next": 3},
            {"label": "3️⃣ Wait for rescue", "next": 4},
            {"label": "4️⃣ Panic and give up", "eliminate": True},
            {"label": "5️⃣ Check a safe that survived the collapse", "next": 40},  # Mini-Scene E
        ]
    },
    # SCÈNE 25
    {
        "text": "**Scene 25 – The Hidden Office**\nYou uncover an office with old computers still running.",
        "choices": [
            {"label": "1️⃣ Search computers for clues", "next": 5, "xp": 1},
            {"label": "2️⃣ Take a break", "next": 6},
            {"label": "3️⃣ Steal some files", "eliminate": True},
            {"label": "4️⃣ Leave the office", "next": 7},
            {"label": "5️⃣ Check maintenance closet", "next": 45},  # Mini-Scene J
        ]
    },

    # SCENES 26-35 (pas de mini-scène branchée ici, mais possible à ajouter si besoin)
    {
        "text": "**Scene 26 – Secret Control Room**\nYou find a locked chamber with flickering screens and a biometric pad. A dusty manual is nearby.",
        "choices": [
            {"label": "1️⃣ Scan the manual", "next": 27, "xp": 1},
            {"label": "2️⃣ Try your fingerprint", "eliminate": True},
            {"label": "3️⃣ Use Encrypted Sensor Key", "next": 28, "xp": 2},
            {"label": "4️⃣ Retreat for now", "next": 29},
        ]
    },
    {
        "text": "**Scene 27 – The Forgotten Wing**\nYou discover a corridor filled with old blueprints and rotten panels. You hear a noise ahead.",
        "choices": [
            {"label": "1️⃣ Investigate the noise", "next": 30, "xp": 2},
            {"label": "2️⃣ Search the blueprints", "next": 31, "xp": 1},
            {"label": "3️⃣ Patch the panels", "eliminate": True},
            {"label": "4️⃣ Call in reinforcements", "next": 32},
        ]
    },
    {
        "text": "**Scene 28 – Biometric Override**\nThe Encrypted Sensor Key grants you admin access. You enter the core of the sabotage network.",
        "choices": [
            {"label": "1️⃣ Disable rogue scripts", "next": 33, "xp": 2},
            {"label": "2️⃣ Upload AI shield", "next": 34, "xp": 1},
            {"label": "3️⃣ Tamper with logs", "eliminate": True},
            {"label": "4️⃣ Reboot everything", "next": 35},
        ]
    },
    {
        "text": "**Scene 29 – Emergency Response**\nYour team detects a second sabotage attempt on the roof sensor grid.",
        "choices": [
            {"label": "1️⃣ Deploy smart drones", "next": 30, "xp": 2},
            {"label": "2️⃣ Manually climb and inspect", "next": 31},
            {"label": "3️⃣ Wait for weather clearance", "eliminate": True},
            {"label": "4️⃣ Remotely reboot via secure node", "next": 32, "xp": 1},
        ]
    },
    {
        "text": "**Scene 30 – Rooftop Discovery**\nA burnt-out sensor casing hides a memory chip. What’s your call?",
        "choices": [
            {"label": "1️⃣ Recover chip with gloves", "next": 33, "xp": 2},
            {"label": "2️⃣ Inspect damage visually", "next": 34},
            {"label": "3️⃣ Kick it aside", "eliminate": True},
            {"label": "4️⃣ Use Holo-Recorder", "next": 35, "xp": 1},
        ]
    },
    {
        "text": "**Scene 31 – Manual Inspection**\nClimbing the scaffolding, you hear metal groan. You must act fast.",
        "choices": [
            {"label": "1️⃣ Anchor your harness properly", "next": 32, "xp": 2},
            {"label": "2️⃣ Ignore and continue", "eliminate": True},
            {"label": "3️⃣ Call for help", "next": 33},
            {"label": "4️⃣ Use Smart Vest for safety", "next": 34, "xp": 1},
        ]
    },
    {
        "text": "**Scene 32 – AI Override**\nThe AI in the control system offers a mysterious command: ‘Clean Sweep’.",
        "choices": [
            {"label": "1️⃣ Execute ‘Clean Sweep’", "eliminate": True},
            {"label": "2️⃣ Ask for log review", "next": 35, "xp": 2},
            {"label": "3️⃣ Use Memory Chip", "next": 33, "xp": 1},
            {"label": "4️⃣ Pause system and investigate", "next": 34},
        ]
    },
    {
        "text": "**Scene 33 – Memory Log Access**\nRecovered logs show unauthorized admin entries from months ago.",
        "choices": [
            {"label": "1️⃣ Cross-check with renovation history", "next": 34, "xp": 2},
            {"label": "2️⃣ Notify authorities", "next": 35},
            {"label": "3️⃣ Wipe logs permanently", "eliminate": True},
            {"label": "4️⃣ Broadcast to the community DAO", "next": 35, "xp": 1},
        ]
    },
    {
        "text": "**Scene 34 – Final Backup**\nYou reach the legacy server containing all building schematics.",
        "choices": [
            {"label": "1️⃣ Create decentralized backup", "next": 35, "xp": 2},
            {"label": "2️⃣ Encrypt and hide data", "next": 35},
            {"label": "3️⃣ Send everything to media", "eliminate": True},
            {"label": "4️⃣ Issue a builder NFT for the crew", "next": 35, "xp": 1},
        ]
    },
    {
        "text": "**Scene 35 – The End of the Journey**\nYour decisions shaped the outcome of the renovation. Time to report.",
        "choices": [
            {"label": "1️⃣ Publish report to MYİKKİ ledger", "next": None, "xp": 2},
            {"label": "2️⃣ Share success on Discord", "next": None},
            {"label": "3️⃣ Archive for internal use only", "next": None},
            {"label": "4️⃣ Restart adventure", "next": 0},
        ]
    },

    # MINI-SCENES
    {
        "text": "**Mini-Scene A – Secret Alcove**\nYou find a hidden alcove in the wall with a glowing device inside.",
        "choices": [
            {"label": "1️⃣ Take the device (get Energy Shield)", "next": 15, "item": "Energy Shield"},
            {"label": "2️⃣ Ignore it", "next": 9},
            {"label": "3️⃣ Scan for danger", "next": 18, "xp": 1},
            {"label": "4️⃣ Leave a sensor beacon", "next": 14},
        ]
    },
    {
        "text": "**Mini-Scene B – Rooftop Box**\nOn the rooftop, you spot a small box tied to an antenna.",
        "choices": [
            {"label": "1️⃣ Open the box (find Weather Drone)", "next": 20, "item": "Weather Drone"},
            {"label": "2️⃣ Leave it alone", "next": 23},
            {"label": "3️⃣ Check for traps", "next": 24, "xp": 1},
            {"label": "4️⃣ Mark location for later", "next": 19},
        ]
    },
    {
        "text": "**Mini-Scene C – Abandoned Control Tablet**\nA control tablet blinks with a low battery warning.",
        "choices": [
            {"label": "1️⃣ Try to power on (get Data Chip)", "next": 17, "item": "Data Chip"},
            {"label": "2️⃣ Search for charger", "next": 10},
            {"label": "3️⃣ Take tablet anyway", "next": 12, "xp": 1},
            {"label": "4️⃣ Ignore", "next": 21},
        ]
    },
    {
        "text": "**Mini-Scene D – Crate of Tools**\nYou discover a crate filled with old but sturdy tools.",
        "choices": [
            {"label": "1️⃣ Take the best tool (get Super Wrench)", "next": 25, "item": "Super Wrench"},
            {"label": "2️⃣ Examine all tools", "next": 28, "xp": 1},
            {"label": "3️⃣ Leave tools", "next": 32},
            {"label": "4️⃣ Hide crate for later", "next": 13},
        ]
    },
    {
        "text": "**Mini-Scene E – Sub-Basement Safe**\nA safe stands in the corner, combination scratched off.",
        "choices": [
            {"label": "1️⃣ Try default codes", "next": 30, "xp": 1},
            {"label": "2️⃣ Force open (get Nano Patch Kit)", "next": 21, "item": "Nano Patch Kit"},
            {"label": "3️⃣ Ignore the safe", "next": 26},
            {"label": "4️⃣ Call in a specialist", "next": 29},
        ]
    },
    {
        "text": "**Mini-Scene F – Old Workbench**\nAn old workbench has drawers full of forgotten gadgets.",
        "choices": [
            {"label": "1️⃣ Open all drawers (get Ancient Key)", "next": 32, "item": "Ancient Key"},
            {"label": "2️⃣ Search for blueprints", "next": 8, "xp": 1},
            {"label": "3️⃣ Leave workbench", "next": 17},
            {"label": "4️⃣ Take only the top drawer", "next": 13},
        ]
    },
    {
        "text": "**Mini-Scene G – Fallen Locker**\nA locker lies toppled in the hallway. Something rattles inside.",
        "choices": [
            {"label": "1️⃣ Open locker carefully (get Access Card)", "next": 24, "item": "Access Card"},
            {"label": "2️⃣ Kick locker", "eliminate": True},
            {"label": "3️⃣ Leave locker", "next": 18},
            {"label": "4️⃣ Drag locker to corner", "next": 6},
        ]
    },
    {
        "text": "**Mini-Scene H – Panel Behind the Painting**\nA painting is crooked, revealing a hidden panel.",
        "choices": [
            {"label": "1️⃣ Open panel (get Secret Drive)", "next": 30, "item": "Secret Drive"},
            {"label": "2️⃣ Straighten painting", "next": 27},
            {"label": "3️⃣ Ignore and continue", "next": 2},
            {"label": "4️⃣ Photograph panel", "next": 12, "xp": 1},
        ]
    },
    {
        "text": "**Mini-Scene I – Hazardous Waste Bin**\nA waste bin is glowing faintly. Something’s inside.",
        "choices": [
            {"label": "1️⃣ Use tongs to retrieve object (get Protection Badge)", "next": 3, "item": "Protection Badge"},
            {"label": "2️⃣ Reach in by hand", "eliminate": True},
            {"label": "3️⃣ Call for backup", "next": 5},
            {"label": "4️⃣ Ignore", "next": 14},
        ]
    },
    {
        "text": "**Mini-Scene J – Maintenance Closet**\nYou find a locker labeled 'Lead Renovator'. The key is on a hook.",
        "choices": [
            {"label": "1️⃣ Take the key (risk minor alarm)", "next": 22, "item": "Lead Renovator Key"},
            {"label": "2️⃣ Leave it", "next": 20},
            {"label": "3️⃣ Use Smart Vest for safety", "next": 23, "xp": 1},
            {"label": "4️⃣ Search the closet for more", "next": 19}
        ]
    },  
    {
        "text": "**🏁 Adventure Summary**\nYour renovation quest is over! Here is your result:",
        "choices": [
            {"label": "1️⃣ See my XP & items", "next": None},
            {"label": "2️⃣ Restart adventure", "next": 0}
        ]
    }
]

class AdventureView(ui.View):
    def __init__(self, user_id, choices):
        super().__init__(timeout=120)
        self.user_id = user_id
        for i, c in enumerate(choices):
            btn = ui.Button(label=c["label"].split(" ",1)[1], style=ButtonStyle.primary, custom_id=str(i))
            async def on_click(inter, idx=i):
                await handle_choice(inter, idx)
            btn.callback = on_click
            self.add_item(btn)
    async def interaction_check(self, inter):
        if inter.user.id != self.user_id:
            await inter.response.send_message("⛔ This isn’t your adventure.", ephemeral=True)
            return False
        return True

async def send_scene(interaction, user_id):
    st = adventure_states[user_id]
    sc = scenes[st["step"]]
    content = sc["text"] + "\n\n" + "\n".join(c["label"] for c in sc["choices"])
    await interaction.response.send_message(content, view=AdventureView(user_id, sc["choices"]))

async def handle_choice(interaction, idx):
    user_id = interaction.user.id
    st = adventure_states.get(user_id)
    if not st:
        return await interaction.response.send_message("❌ No adventure in progress.", ephemeral=True)
    sc = scenes[st["step"]]
    choice = sc["choices"][idx]
    if choice.get("eliminate"):
        await interaction.response.edit_message(content=f"{choice['label']}\n\n💥 **Eliminated!**", view=None)
        del adventure_states[user_id]
        return
    st["xp"] += choice.get("xp", 0)
    nxt = choice.get("next")
    if nxt is None:
        summary = (
            f"{sc['text']}\n\n✅ **Adventure complete!**\n"
            f"Total XP: {st['xp']}\n"
            f"Inventory: {', '.join(st['inventory']) or 'none'}"
        )
        await interaction.response.edit_message(content=summary, view=None)
        del adventure_states[user_id]
        return
    st["step"] = nxt
    next_sc = scenes[nxt]
    content = next_sc["text"] + "\n\n" + "\n".join(c["label"] for c in next_sc["choices"])
    await interaction.response.edit_message(content=content, view=AdventureView(user_id, next_sc["choices"]))

adventure_group = app_commands.Group(name="adventure", description="MYIKKI text adventure")

@adventure_group.command(name="start", description="Start your adventure (once per day)")
async def adventure_start(interaction):
    uid = interaction.user.id
    today = (datetime.datetime.utcnow()+datetime.timedelta(hours=1)).date()
    if ADVENTURE_CHANNEL_ID and interaction.channel.id != ADVENTURE_CHANNEL_ID:
        return await interaction.response.send_message(f"❌ Use in <#{ADVENTURE_CHANNEL_ID}>", ephemeral=True)
    if last_adventure.get(uid) == today and not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Already played today!", ephemeral=True)
    adventure_states[uid] = {"step": 0, "xp": 0, "inventory": []}
    last_adventure[uid] = today
    await send_scene(interaction, uid)

@adventure_group.command(name="status", description="Show your adventure progress")
async def adventure_status(interaction):
    st = adventure_states.get(interaction.user.id)
    if not st:
        return await interaction.response.send_message("❌ No adventure.", ephemeral=True)
    await interaction.response.send_message(f"🗺️ Scene {st['step']+1}/{len(scenes)} — XP: {st['xp']}", ephemeral=True)

@adventure_group.command(name="end", description="Abandon your adventure")
async def adventure_end(interaction):
    if interaction.user.id in adventure_states:
        del adventure_states[interaction.user.id]
        return await interaction.response.send_message("❌ Adventure abandoned.", ephemeral=True)
    return await interaction.response.send_message("❌ No adventure to abandon.", ephemeral=True)

# === Bot setup ===
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        self.tree.add_command(adventure_group, guild=GUILD_OBJ)
        await self.tree.sync(guild=GUILD_OBJ)

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

@bot.event
async def on_raw_reaction_add(payload):
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
async def on_raw_reaction_remove(payload):
    global signup_message_id
    if payload.user_id == bot.user.id: return
    if not battle_in_progress or payload.message_id != signup_message_id: return
    if str(payload.emoji) == "🔨" and payload.user_id in battle_participants:
        battle_participants.remove(payload.user_id)

# === /quiz ===
@bot.tree.command(name="quiz", description="Take your daily yes/no MYIKKI quiz")
@discord.app_commands.guilds(GUILD_ID)
async def slash_quiz(interaction):
    now = datetime.datetime.utcnow()
    last = last_quiz_time.get(interaction.user.id)
    if last and (now - last).total_seconds() < 86400:
        return await interaction.response.send_message("⏳ Only once per 24h.", ephemeral=True)
    q = random.choice(quiz_questions)
    await interaction.response.send_message(f"🧠 Quiz: **{q['question']}**")
    def check(m):
        return (
            m.author.id == interaction.user.id and
            m.channel.id == interaction.channel.id and
            m.content.lower().strip() in ("yes","no")
        )
    try:
        m = await bot.wait_for("message", timeout=30, check=check)
        if m.content.lower().strip() == q["answer"].lower():
            add_credits(interaction.user.id, 5)
            last_quiz_time[interaction.user.id] = now
            await interaction.followup.send("✅ Correct! +5 XP")
        else:
            await interaction.followup.send("❌ Incorrect. Try again tomorrow!")
    except asyncio.TimeoutError:
        await interaction.followup.send("⌛ Time’s up! (30s)")

# === /quest ===
@bot.tree.command(name="quest", description="Get your daily renovation quest")
@discord.app_commands.guilds(GUILD_ID)
async def slash_quest(interaction):
    now = datetime.datetime.utcnow()
    last = last_quest_time.get(interaction.user.id)
    if last and (now - last).total_seconds() < 86400:
        return await interaction.response.send_message("⏳ Only once per 24h.", ephemeral=True)
    task = random.choice(quests)
    reward = random.randint(3,7)
    add_credits(interaction.user.id, reward)
    last_quest_time[interaction.user.id] = now
    await interaction.response.send_message(f"🛠️ Quest: **{task}**\n✅ +{reward} XP")

# === Battle system and commands ===
async def run_battle(ctx):
    global battle_in_progress, signup_message_id
    try:
        survivors = list(dict.fromkeys(battle_participants))
        if len(survivors) < 2:
            return await ctx.send("❌ Not enough participants.")
        signup_message_id = None
        now = datetime.datetime.utcnow()
        last_battle_time.setdefault(ctx.guild.id, []).append(now)
        site = random.choice(building_types)

        await ctx.send(f"🏗️ Battle at **{site}** with {len(survivors)} players!")
        await asyncio.sleep(3)
        mentions = [(await ctx.guild.fetch_member(uid)).mention for uid in survivors]
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
            left = [(await ctx.guild.fetch_member(uid)).display_name for uid in survivors]
            await ctx.send("🧱 Remaining: " + ", ".join(left))
            await asyncio.sleep(3)

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

@bot.tree.command(name="startfirstbattle", description="Admin: open 5m signup")
@discord.app_commands.guilds(GUILD_ID)
async def slash_startfirst(interaction):
    global battle_in_progress, signup_message_id
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    if battle_in_progress:
        return await interaction.response.send_message("❌ A battle is already in progress.", ephemeral=True)
    battle_in_progress = True
    battle_participants.clear()
    msg = await interaction.response.send_message("🚨 FIRST MYIKKI BATTLE! React 🔨 to join in 5 min.")
    msg = await interaction.original_response()
    signup_message_id = msg.id
    await msg.add_reaction("🔨")
    async def finish():
        await asyncio.sleep(300)
        class Ctx: guild = interaction.guild; send = interaction.channel.send
        await run_battle(Ctx())
    asyncio.create_task(finish())

@bot.tree.command(name="startbattle", description="Admin: open 11h signup rumble")
@discord.app_commands.guilds(GUILD_ID)
async def slash_startbattle(interaction):
    global battle_in_progress, signup_message_id
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    if battle_in_progress:
        return await interaction.response.send_message("❌ A battle is already in progress.", ephemeral=True)
    now = datetime.datetime.utcnow()
    window = [
        t for t in last_battle_time.get(interaction.guild.id, [])
        if (now - t).total_seconds() < 11*3600
    ]
    if len(window) >= 2:
        return await interaction.response.send_message("⏳ Max 2 per 11h.", ephemeral=True)
    battle_in_progress = True
    battle_participants.clear()
    msg = await interaction.response.send_message("🚨 RUMBLE: React 🔨 to join in 11h.")
    msg = await interaction.original_response()
    signup_message_id = msg.id
    await msg.add_reaction("🔨")
    async def finish():
        await asyncio.sleep(11*3600)
        class Ctx: guild = interaction.guild; send = interaction.channel.send
        await run_battle(Ctx())
    asyncio.create_task(finish())

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
