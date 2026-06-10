import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import os
import json

# 🔐 TOKEN Railway
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN manquant")

# 📌 Channel Discord
CHANNEL_ID = os.getenv("channel")

if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID manquant")

# 🤖 Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 💾 fichier anti doublons
DATA_FILE = "data.json"


# ----------------------------
# 💾 STORAGE (anti doublons)
# ----------------------------
def load_last_code():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f).get("last_code")
    except:
        return None


def save_last_code(code):
    with open(DATA_FILE, "w") as f:
        json.dump({"last_code": code}, f)


# ----------------------------
# 🔎 SCRAPER
# ----------------------------
def get_all_codes():
    url = "https://www.wows-gamer-blog.com/2023/10/bonus-codes.html"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    for bonus_div in soup.select("div.bonus-code"):
        code_el = bonus_div.select_one("span.code-value")
        if not code_el:
            continue

        code = code_el.get_text(strip=True)

        # 🎁 reward safe
        reward_text = "Non spécifié"
        reward_label = bonus_div.find(string=lambda t: t and "Reward:" in t)
        if reward_label:
            reward_text = reward_label.strip()

        # 🌐 servers safe
        servers = list(dict.fromkeys([
            s.strip()
            for s in bonus_div.stripped_strings
            if "Server" in s or "NA" in s or "EU" in s or "Asia" in s
        ]))

        results.append({
            "code": code,
            "servers": servers,
            "reward": reward_text
        })

    return results


# ----------------------------
# 📦 FORMAT MESSAGE
# ----------------------------
def format_code(c):
    return (
        f"💥 **Code WoWs :** {c['code']}\n"
        f"🌐 Serveurs : {', '.join(c['servers']) if c['servers'] else 'Non spécifié'}\n"
        f"🎁 Reward : {c['reward'] or 'Non spécifié'}"
    )


# ----------------------------
# 🚀 BOT READY
# ----------------------------
@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

    channel = await bot.fetch_channel(CHANNEL_ID)

    codes = get_all_codes()
    if not codes:
        print("Aucun code trouvé")
        return

    newest = codes[0]
    last_code = load_last_code()

    # 🔥 évite doublon au démarrage
    if last_code != newest["code"]:
        await channel.send("💾 **Démarrage du bot**\n" + format_code(newest))
        save_last_code(newest["code"])

    check_codes.start()


# ----------------------------
# 🔁 LOOP 12H
# ----------------------------
@tasks.loop(hours=12)
async def check_codes():
    channel = await bot.fetch_channel(CHANNEL_ID)

    codes = get_all_codes()
    if not codes:
        return

    newest = codes[0]
    last_code = load_last_code()

    if last_code != newest["code"]:
        await channel.send(format_code(newest))
        save_last_code(newest["code"])
    else:
        print("Aucun nouveau code")


# ----------------------------
# ▶️ RUN BOT
# ----------------------------
if __name__ == "__main__":
    bot.run(TOKEN)
