import os
import discord
import requests
import asyncio
import json
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# ------------------- Zmienne środowiskowe -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

URL = "https://cyleria.pl/?subtopic=killstatistics"
DATA_FILE = "watched.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (CyleriaBot; Discord death tracker)"
}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

last_seen = set()

# ------------------- Utils -------------------
def make_char_link(name):
    encoded = quote_plus(name)
    return f"[{name}](<https://cyleria.pl/?subtopic=characters&name={encoded}>)"

def split_killers(killer_str):
    killer_str = killer_str.replace(" oraz ", ",")
    return [k.strip() for k in killer_str.split(",") if k.strip()]

# ------------------- Persistencja -------------------
def load_watched():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            print("Błąd wczytywania watched.json")

    return {
        "Agnieszka",
        "Miekka Parowka",
        "Gazowany Kompot",
        "Tapczan'ed",
        "Interested",
        "Negocjator",
        "Astma",
        "Mistrz Negocjacji",
        "Jestem Karma",
        "Pan Trezer",
        "Negocjatorka"
    }

def save_watched():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(list(WATCHED), f, ensure_ascii=False, indent=2)

WATCHED = load_watched()

# ------------------- Cyleria -------------------
def is_player(killer):
    killer = killer.lower().strip()
    return not killer.startswith(("a ", "an ", "the "))

def get_deaths():
    try:
        r = requests.get(URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        tbody = soup.find("tbody")
        if not tbody:
            return []

        deaths = []
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue

            time = tds[0].get_text(strip=True)
            text = tds[1].get_text(" ", strip=True)

            if "śmierć na poziomie" in text:
                parts = text.split("śmierć na poziomie")
                name = parts[0].strip()
                rest = parts[1].strip()
                if "przez" in rest:
                    level, killer = rest.split("przez", 1)
                else:
                    level, killer = rest, "Nieznany"
            else:
                name = text.split("przez")[0].strip()
                level = "?"
                killer = text.split("przez")[1].strip() if "przez" in text else "Nieznany"

            if name not in WATCHED:
                continue

            key = time + text
            deaths.append((key, time, name, level.strip(), killer.strip()))

        return deaths

    except Exception as e:
        print("Cyleria error:", e)
        return []

# ------------------- Loop -------------------
async def check_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    for key, *_ in get_deaths():
        last_seen.add(key)

    while True:
        try:
            for key, time, name, level, killer in reversed(get_deaths()):
                if key in last_seen:
                    continue

                victim = make_char_link(name)
                msg = f"🕒 {time}\n@everyone Zginął 🟢 **{victim}** na poziomie {level} przez "

                if is_player(killer):
                    killers = split_killers(killer)
                    killer_links = [make_char_link(k) for k in killers]
                    msg += "🔴 **" + " , ".join(killer_links) + "**"
                else:
                    msg += killer

                await channel.send(msg)
                last_seen.add(key)

            if len(last_seen) > 300:
                last_seen.clear()

        except Exception as e:
            print("Loop error:", e)

        await asyncio.sleep(30)

# ------------------- Komendy -------------------
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!dodaj"):
        try:
            nick = message.content.split('"')[1]
            WATCHED.add(nick)
            save_watched()
            await message.channel.send(f"✅ Dodano **{nick}**")
        except:
            await message.channel.send("Użycie: `!dodaj \"Nick\"`")

    elif message.content.startswith("!usun"):
        try:
            nick = message.content.split('"')[1]
            WATCHED.discard(nick)
            save_watched()
            await message.channel.send(f"✅ Usunięto **{nick}**")
        except:
            await message.channel.send("Użycie: `!usun \"Nick\"`")

    elif message.content.startswith("!lista"):
        if not WATCHED:
            await message.channel.send("Lista jest pusta ❌")
        else:
            lista = "\n".join(f"🟢 {n}" for n in sorted(WATCHED))
            await message.channel.send(f"**Śledzone postacie:**\n{lista}")

    elif message.content.startswith("!info"):
        await message.channel.send(
            "**Komendy:**\n"
            "`!dodaj \"Nick\"` – dodaje postać\n"
            "`!usun \"Nick\"` – usuwa postać\n"
            "`!lista` – lista śledzonych\n"
            "`!info` – pomoc"
        )

# ------------------- Ready -------------------
@client.event
async def on_ready():
    print("Zalogowany jako", client.user)
    channel = client.get_channel(CHANNEL_ID)
    await channel.send("**Zgony v1.0.0 by wLoDaRr** uruchomione ✅ ✅✅**Skanowanie Cylerii w toku !!**✅✅")
    client.loop.create_task(check_loop())

client.run(DISCORD_TOKEN)
