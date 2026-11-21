import os
import math
import json
import asyncio

# Python 3.14 Event Loop Fix for Pyrogram
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import datetime
from threading import Thread
from flask import Flask
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified, FloodWait

# ================= CONFIGURATION =================
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

OWNER_ID = int(os.environ.get("OWNER_ID", "123456789"))
TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", "-1001234567890"))
TARGET_TOPIC_ID = int(os.environ.get("TARGET_TOPIC_ID", "0"))
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "-1009876543210"))

MM_TZ = datetime.timezone(datetime.timedelta(hours=6, minutes=30))
STATE_FILE = "dashboard_state.json"
HBD_BACKUP_FILE = "birthdays_backup.json"
RS_BACKUP_FILE = "relationships_backup.json"

# ================= FLASK KEEP-ALIVE =================
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Owner-Controlled Topic Billboard Bot is Running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# ================= DEFAULT STATE =================
DEFAULT_STATE = {
    "pin_msg_id": None,
    "page_index": 0,
    "current_date": "",
    "wished_date": "",     # မွေးနေ့နှင့် နှစ်ပတ်လည် ဂုဏ်ပြုစာ ပို့ပြီးသား ရက်စွဲမှတ်ရန်
    "chat_counts": {},     # {"uid": {"name": "Mg Mg", "username": "mgmg", "count": 10}}
    "birthdays": [],       # [{"uid": 123456, "name": "Mg Mg", "username": "mgmg", "day": 25, "month": "Dec"}]
    "relationships": []    # [{"uid1": 111, "name1": "MgMg", "user1": "mgmg", "uid2": 222, "name2": "SuSu", "user2": "susu", "day": 14, "month": "Feb", "year": 2025}]
}

state = DEFAULT_STATE.copy()

# ၁။ အဓိက မြို့ကြီး ၁၅ မြို့
MAIN_REGIONS = [
    ("📍 ပြည်ထောင်စုနယ်မြေ", [
        ("နေပြည်တော်", 19.7633, 96.0785),
    ]),
    ("📍 အောက်မြန်မာပြည်", [
        ("ရန်ကုန်", 16.8409, 96.1735),
        ("ပဲခူး", 17.3352, 96.4814),
        ("ပုသိမ်", 16.7792, 94.7321),
        ("မော်လမြိုင်", 16.4905, 97.6283),
        ("ဘားအံ", 16.8906, 97.6348),
    ]),
    ("📍 အထက်မြန်မာပြည်", [
        ("မန္တလေး", 21.9588, 96.0891),
        ("မကွေး", 20.1496, 94.9325),
        ("မုံရွာ", 22.1086, 95.1358),
        ("မြစ်ကြီးနား", 25.3833, 97.4000),
    ]),
    ("📍 တောင်ပေါ်နှင့် ကမ်းရိုးတန်း", [
        ("တောင်ကြီး", 20.7892, 97.0378),
        ("လွိုင်ကော်", 19.6742, 97.2094),
        ("ဟားခါး", 22.6445, 93.6108),
        ("စစ်တွေ", 20.1462, 92.8984),
        ("ထားဝယ်", 14.0823, 98.1915),
    ])
]

# ၂။ အခြားမြို့ ၃၀ စာရင်း
OTHER_REGIONS = [
    ("🏔 ရှမ်းနှင့် ကချင်ဒေသ", [
        ("ပြင်ဦးလွင်", 22.0350, 96.4568),
        ("လားရှိုး", 22.9359, 97.7498),
        ("မူဆယ်", 23.9922, 97.9022),
        ("ကျိုင်းတုံ", 21.2936, 99.6078),
        ("တာချီလိတ်", 20.4475, 99.8808),
        ("ကလော", 20.6317, 96.5567),
        ("ညောင်ရွှေ", 20.6606, 96.9317),
        ("ဗန်းမော်", 24.2526, 97.2336),
        ("ဖားကန့်", 25.6122, 96.3133),
        ("ပူတာအို", 27.3333, 97.4167),
    ]),
    ("🌾 အလယ်ပိုင်းနှင့် စစ်ကိုင်းဒေသ", [
        ("မိတ္ထီလာ", 20.8778, 95.8584),
        ("ပုဂံ/ညောင်ဦး", 21.1717, 94.8585),
        ("ကျောက်ပန်းတောင်း", 20.8400, 95.1300),
        ("ပခုက္ကူ", 21.3349, 95.0844),
        ("ရေနံချောင်း", 20.4550, 94.8730),
        ("ချောက်", 20.8961, 94.8186),
        ("ရွှေဘို", 22.5692, 95.6982),
        ("ကသာ", 24.1821, 96.3306),
        ("ကလေး", 23.1888, 94.0512),
        ("တမူး", 24.2167, 94.3167),
    ]),
    ("🌊 အောက်ပိုင်းနှင့် ကမ်းရိုးတန်းဒေသ", [
        ("ပြည်", 18.8246, 95.2222),
        ("တောင်ငူ", 18.9429, 96.4341),
        ("မြဝတီ", 16.6891, 98.5089),
        ("သထုံ", 16.9206, 97.3714),
        ("ရေး", 15.2467, 97.8556),
        ("မြိတ်", 12.4395, 98.6003),
        ("ကော့သောင်း", 9.9833, 98.5500),
        ("ကျောက်ဖြူ", 19.4264, 93.5488),
        ("သံတွဲ", 18.4608, 94.3661),
        ("မောင်တော", 20.8167, 92.3667),
    ])
]

cache_data = {
    "weather_main": "Loading main cities...",
    "weather_other": "Loading other cities...",
    "market": "• 🪙 **Gold Spot:** `-`\n• **BTC:** `-` | **BNB:** `-`\n• **SOL:** `-` | **TON:** `-`",
    "football": "လက်ရှိ အနီးစပ်ဆုံး ပွဲစဉ်များ မရှိသေးပါ ⚽"
}

app = Client("dashboard_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
owner_only = filters.user(OWNER_ID)

# ================= USER RESOLVER & CLICKABLE MENTION =================
def user_link(uid: int, name: str) -> str:
    safe_name = str(name).replace("[", "").replace("]", "")
    return f"[{safe_name}](tg://user?id={uid})"

async def resolve_user_target(target: str):
    """@username သို့မဟုတ် User ID မှတစ်ဆင့် User ID, Account Name နှင့် Username ကို ဆွဲထုတ်ပေးမည်"""
    clean_target = target.strip()
    if clean_target.startswith("@"):
        clean_target = clean_target[1:]

    # 1. Cache (Group ထဲ စကားပြောဖူးသူများ) ထဲတွင် အရင်ရှာမည်
    if clean_target.isdigit():
        uid_str = clean_target
        if uid_str in state["chat_counts"]:
            info = state["chat_counts"][uid_str]
            return int(uid_str), info["name"], info.get("username", "")
    else:
        for uid_str, info in state["chat_counts"].items():
            if info.get("username", "").lower() == clean_target.lower():
                return int(uid_str), info["name"], info.get("username", "")

    # 2. Telegram API (get_users) မှ တိုက်ရိုက်ဆွဲယူမည်
    try:
        query_val = int(clean_target) if clean_target.isdigit() else clean_target
        u = await app.get_users(query_val)
        return u.id, (u.first_name or "User"), (u.username or "")
    except Exception:
        if clean_target.isdigit():
            return int(clean_target), f"User_{clean_target[-4:]}", ""
        return None, None, None

# ================= EXACT MYANMAR CALENDAR ALGORITHM =================
def to_myanmar_digits(num: int) -> str:
    mm_digits = "၀၁၂၃၄၅၆၇၈၉"
    return "".join(mm_digits[int(d)] for d in str(num))

def get_exact_myanmar_date(dt: datetime.datetime) -> str:
    y, m, d = dt.year, dt.month, dt.day
    a = (14 - m) // 12
    y_j = y + 4800 - a
    m_j = m + 12 * a - 3
    jdn = d + (153 * m_j + 2) // 5 + 365 * y_j + y_j // 4 - y_j // 100 + y_j // 400 - 32045

    SY = 1577917828.0 / 4320000.0
    MO = 1954168.050623
    my = math.floor((jdn - 0.5 - MO) / SY)

    def chk_my(year):
        WO = -0.5 if year >= 1312 else (-1.1 if year >= 1217 else -0.85)
        watat = 0
        ed = (SY * (year + 3739)) % 29.530587946
        if ed < 13.765293973:
            ed += 29.530587946
        if year >= 1312 and ed >= (29.530587946 - 13.765293973):
            watat = 1

        exact_watat = {1380: 1, 1381: 0, 1382: 1, 1383: 0, 1384: 0, 1385: 1, 1386: 0, 1387: 0, 1388: 1, 1389: 0, 1390: 0, 1391: 1, 1392: 0, 1393: 1}
        if year in exact_watat:
            watat = exact_watat[year]

        fm = round(SY * year + MO - ed + 4.5 * watat + WO)
        wte = 0
        if watat == 1:
            exact_big = {1385: 1, 1388: 0, 1391: 1}
            wte = exact_big.get(year, 0)
        return watat, fm, wte

    watat, fm, wte = chk_my(my)
    prev_watat, prev_fm, prev_wte = chk_my(my - 1)
    tg1 = prev_fm + 354 + prev_watat * 30 + prev_wte
    if jdn < tg1:
        my -= 1
        watat, fm, wte = prev_watat, prev_fm, prev_wte
        prev_watat, prev_fm, prev_wte = chk_my(my - 1)
        tg1 = prev_fm + 354 + prev_watat * 30 + prev_wte

    dd = jdn - tg1 + 1
    b = wte
    c = 1 if watat == 1 else 0
    myl = 354 + c * 30 + b
    mmt = (dd - 1) // myl
    dd -= mmt * myl
    a = (dd + 423) // 512
    mm = int((dd - b * a + c * a * 30 + 29.26) // 29.544)
    e = (mm + 12) // 16
    f = (mm + 11) // 16
    md = int(dd - math.floor(29.544 * mm - 29.26) - b * e + c * f * 30)
    mm += f * 3 - e * 4

    month_names = [
        "", "တန်ခူး", "ကဆုန်", "နယုန်", "ဝါဆို", "ဝါခေါင်", "တော်သလင်း",
        "သီတင်းကျွတ်", "တန်ဆောင်မုန်း", "နတ်တော်", "ပြာသို", "တပို့တွဲ", "တပေါင်း",
        "နှောင်းတန်ခူး", "နှောင်းကဆုန်"
    ]
    if mm == 4 and watat == 1:
        m_str = "ဒုတိယဝါဆို"
    elif mm == 0:
        m_str = "ပထမဝါဆို"
    elif 1 <= mm <= 14:
        m_str = month_names[mm]
    else:
        m_str = "တန်ဆောင်မုန်း"

    if md == 15:
        phase_str = "လပြည့်နေ့"
    elif md >= 29:
        phase_str = "လကွယ်နေ့"
    elif md < 15:
        phase_str = f"လဆန်း {to_myanmar_digits(md)} ရက်"
    else:
        phase_str = f"လဆုတ် {to_myanmar_digits(md - 15)} ရက်"

    return f"မြန်မာသက္ကရာဇ် {to_myanmar_digits(my)} ခုနှစ်၊ {m_str}{phase_str}"

def get_calendar_line(now: datetime.datetime) -> str:
    mm_full = get_exact_myanmar_date(now)
    thingyan = datetime.datetime(now.year, 4, 13, tzinfo=MM_TZ)
    if now > thingyan:
        thingyan = datetime.datetime(now.year + 1, 4, 13, tzinfo=MM_TZ)
    days_to_thingyan = (thingyan.date() - now.date()).days
    return f"🌙 {mm_full}\n💦 သင်္ကြန်ရောက်ရန် {days_to_thingyan} ရက် လိုသေးသည်"

# ================= STATE PERSISTENCE =================
async def load_state():
    global state
    try:
        async for msg in app.get_chat_history(LOG_CHANNEL_ID, limit=10):
            if msg.document and msg.document.file_name == STATE_FILE:
                path = await app.download_media(msg)
                with open(path, "r", encoding="utf-8") as f:
                    state.update(json.load(f))
                os.remove(path)
                print("✅ State loaded from Telegram Log Channel.")
                return
    except Exception as e:
        print(f"⚠️ Load state error: {e}")

async def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        await app.send_document(
            LOG_CHANNEL_ID,
            document=STATE_FILE,
            caption=f"Auto-Backup: {datetime.datetime.now(MM_TZ).strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        print(f"⚠️ Save state error: {e}")

# ================= WEATHER, BIRTHDAY & ANNIVERSARY HELPERS =================
def get_now():
    return datetime.datetime.now(MM_TZ)

def decode_wmo_weather(code: int) -> str:
    if code == 0:
        return "☀️ နေသာ"
    elif code in [1, 2]:
        return "⛅ တိမ်အနည်းငယ်"
    elif code == 3:
        return "☁️ တိမ်ထူ/မိုးအုံ့"
    elif code in [45, 48]:
        return "🌫️ မြူဆိုင်း"
    elif code in [51, 53, 55, 56, 57]:
        return "🌦️ မိုးဖွဲကျ"
    elif code in [61, 63, 65, 66, 67, 80, 81, 82]:
        return "🌧️ မိုးရွာ"
    elif code in [95, 96, 99]:
        return "⛈️ မိုးကြိုး"
    else:
        return "🌤️ ပုံမှန်"

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

def get_today_birthdays(now: datetime.datetime):
    today_bdays = []
    for b in state["birthdays"]:
        m_num = MONTH_MAP.get(b["month"].capitalize(), 1)
        if int(b["day"]) == now.day and m_num == now.month:
            today_bdays.append(b)
    return today_bdays

def get_today_anniversaries(now: datetime.datetime):
    today_annis = []
    for r in state["relationships"]:
        m_num = MONTH_MAP.get(r["month"].capitalize(), 1)
        if int(r["day"]) == now.day and m_num == now.month:
            yrs = now.year - int(r["year"])
            today_annis.append((yrs, r))
    return today_annis

def get_birthday_line(now: datetime.datetime) -> str:
    today_bdays = get_today_birthdays(now)
    if today_bdays:
        names = ", ".join([f"**{user_link(b['uid'], b['name'])}**" for b in today_bdays])
        return f"🎂 **Today's HBD:** 🎉 {names} 🥳"
    return "🎂 ယနေ့မွေးနေ့ရှင်စာရင်း မရှိပါ"

def get_anniversary_line(now: datetime.datetime) -> str:
    today_annis = get_today_anniversaries(now)
    if not today_annis:
        return ""
    pairs = []
    for yrs, r in today_annis:
        p1 = user_link(r["uid1"], r["name1"])
        p2 = user_link(r["uid2"], r["name2"])
        yr_txt = f" ({yrs} နှစ်ပြည့်)" if yrs > 0 else ""
        pairs.append(f"**{p1}** ❤️ **{p2}**{yr_txt}")
    return f"💑 **Happy Anniversary:** 🎉 {', '.join(pairs)} 🥂"

# ================= AUTO EXTERNAL DATA FETCHERS =================
async def fetch_regions_weather(session, regions_data) -> str:
    flat_cities = [c for _, cities in regions_data for c in cities]
    lats = ",".join(str(c[1]) for c in flat_cities)
    lons = ",".join(str(c[2]) for c in flat_cities)
    w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}&current=temperature_2m,weather_code"
    async with session.get(w_url, timeout=15) as resp:
        if resp.status == 200:
            results = await resp.json()
            sections = []
            idx = 0
            for region_title, cities in regions_data:
                lines = [f"**{region_title}**"]
                for mm_name, _, _ in cities:
                    curr = results[idx].get("current", {})
                    temp = round(curr.get("temperature_2m", 0))
                    desc = decode_wmo_weather(curr.get("weather_code", 0))
                    lines.append(f"• {mm_name}: `{temp}°C` ({desc})")
                    idx += 1
                sections.append("\n".join(lines))
            return "\n\n".join(sections)
    return ""

async def update_external_data():
    async with aiohttp.ClientSession() as session:
        try:
            main_w = await fetch_regions_weather(session, MAIN_REGIONS)
            if main_w:
                cache_data["weather_main"] = main_w
            other_w = await fetch_regions_weather(session, OTHER_REGIONS)
            if other_w:
                cache_data["weather_other"] = other_w
        except Exception as e:
            print("Weather batch err:", e)

        try:
            symbols = '["PAXGUSDT","BTCUSDT","BNBUSDT","SOLUSDT","TONUSDT"]'
            c_url = f"https://api.binance.com/api/v3/ticker/price?symbols={symbols}"
            async with session.get(c_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    prices = {}
                    for item in data:
                        sym = item["symbol"].replace("USDT", "")
                        val = float(item["price"])
                        prices[sym] = f"${val:,.0f}" if val >= 1000 else f"${val:,.2f}"
                    cache_data["market"] = (
                        f"• 🪙 **Gold Spot:** `{prices.get('PAXG', '-')}/oz`\n"
                        f"• ₿ **BTC:** `{prices.get('BTC', '-')}` | **BNB:** `{prices.get('BNB', '-')}`\n"
                        f"• 💎 **SOL:** `{prices.get('SOL', '-')}` | **TON:** `{prices.get('TON', '-')}`"
                    )
        except Exception as e:
            print("Market fetch err:", e)

        leagues = [
            ("🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL", "eng.1"),
            ("🇪🇸 La Liga", "esp.1"),
            ("🏆 UCL", "uefa.champions")
        ]
        match_lines = []
        for league_name, code in leagues:
            try:
                f_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard"
                async with session.get(f_url, timeout=10) as resp:
                    if resp.status == 200:
                        f_data = await resp.json()
                        for ev in f_data.get("events", []):
                            status_type = ev["status"]["type"]["state"]
                            if status_type in ["in", "pre"]:
                                comp = ev["competitions"][0]["competitors"]
                                home = comp[0]["team"]["abbreviation"]
                                away = comp[1]["team"]["abbreviation"]
                                h_score = comp[0].get("score", "0")
                                a_score = comp[1].get("score", "0")
                                detail = ev["status"]["type"]["shortDetail"]

                                if status_type == "in":
                                    match_lines.append(f"🔴 {league_name}: **{home} {h_score} - {a_score} {away}** `[{detail}]`")
                                elif len(match_lines) < 6:
                                    match_lines.append(f"⏳ {league_name}: {home} vs {away} ({detail})")
            except Exception as e:
                print(f"ESPN err ({code}):", e)

        cache_data["football"] = "\n".join(match_lines[:8]) if match_lines else "လက်ရှိ အနီးစပ်ဆုံး ပွဲစဉ်များ မရှိသေးပါ ⚽"

# ================= DAILY WISHES & TOP 3 ANNOUNCEMENTS =================
async def send_daily_celebrations(now: datetime.datetime):
    """မွေးနေ့ရှင်နှင့် နှစ်ပတ်လည်အတွဲများ ရှိပါက Mention ဖြင့် ဂုဏ်ပြုစာ ပို့ပေးမည်"""
    today_key = now.strftime("%Y-%m-%d")
    if state.get("wished_date") == today_key:
        return

    topic_arg = {"reply_to_message_id": TARGET_TOPIC_ID} if TARGET_TOPIC_ID else {}
    today_bdays = get_today_birthdays(now)
    today_annis = get_today_anniversaries(now)

    # 1. မွေးနေ့ဂုဏ်ပြုစာ
    if today_bdays:
        mentions = ", ".join([f"**{user_link(b['uid'], b['name'])}**" for b in today_bdays])
        try:
            await app.send_message(
                TARGET_GROUP_ID,
                f"🎂🎉 **HAPPY BIRTHDAY!** 🎉🎂\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"ဒီနေ့ဟာ အဖွဲ့သား {mentions} ရဲ့ မွေးနေ့လေး ဖြစ်ပါတယ်!\n"
                f"ပျော်ရွှင်စရာ မွေးနေ့လေးဖြစ်ပြီး စိတ်ချမ်းသာ ကိုယ်ကျန်းမာစွာနဲ့ လိုအင်ဆန္ဒတွေ အားလုံး ပြည့်ဝပါစေလို့ Group တစ်ခုလုံးက ဆုတောင်းဂုဏ်ပြုပေးလိုက်ပါတယ်ဗျာ 🥂✨",
                parse_mode=ParseMode.MARKDOWN,
                **topic_arg
            )
        except Exception as e:
            print("Bday wish err:", e)

    # 2. နှစ်ပတ်လည် ဂုဏ်ပြုစာ
    if today_annis:
        for yrs, r in today_annis:
            p1 = user_link(r["uid1"], r["name1"])
            p2 = user_link(r["uid2"], r["name2"])
            yr_txt = f"**{yrs} နှစ်ပြည့်**" if yrs > 0 else "အထူး"
            try:
                await app.send_message(
                    TARGET_GROUP_ID,
                    f"💑🥂 **HAPPY ANNIVERSARY!** 🥂💑\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"ဒီနေ့ဟာ **{p1}** ❤️ **{p2}** တို့ရဲ့ {yr_txt} နှစ်ပတ်လည်နေ့လေး ဖြစ်ပါတယ်!\n"
                    f"နောင်နှစ်ပေါင်းများစွာတိုင်အောင် အခုလိုပဲ ပျော်ပျော်ရွှင်ရွှင် ချစ်ချစ်ခင်ခင်နဲ့ လက်တွဲသွားနိုင်ကြပါစေလို့ Group တစ်ခုလုံးက ဂုဏ်ပြုဆုတောင်းပေးလိုက်ပါတယ်ဗျာ 💖✨",
                    parse_mode=ParseMode.MARKDOWN,
                    **topic_arg
                )
            except Exception as e:
                print("Anni wish err:", e)

    state["wished_date"] = today_key
    await save_state()

async def check_daily_rollover(now: datetime.datetime):
    today_key = now.strftime("%Y-%m-%d")
    if state["current_date"] and state["current_date"] != today_key:
        if state["chat_counts"]:
            sorted_yest = sorted(state["chat_counts"].items(), key=lambda x: x[1]["count"], reverse=True)[:3]
            medals = ["🥇", "🥈", "🥉"]
            lines = "\n".join([f"{medals[i]} **{user_link(int(uid), u['name'])}** — `{u['count']} msgs`" for i, (uid, u) in enumerate(sorted_yest)])
            try:
                topic_arg = {"reply_to_message_id": TARGET_TOPIC_ID} if TARGET_TOPIC_ID else {}
                await app.send_message(
                    TARGET_GROUP_ID,
                    f"🌟 **မနေ့က ({state['current_date']}) စကားအများဆုံးပြောခဲ့သူများ** 🌟\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{lines}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"ဒီနေ့အတွက် စာရင်းအသစ် ပြန်စပါပြီဗျာ! 🎉",
                    parse_mode=ParseMode.MARKDOWN,
                    **topic_arg
                )
            except Exception as e:
                print("Yesterday summary err:", e)
        state["chat_counts"] = {}
        state["current_date"] = today_key
        await save_state()
    elif not state["current_date"]:
        state["current_date"] = today_key

    # နေ့သစ်အတွက် မွေးနေ့/နှစ်ပတ်လည် ဂုဏ်ပြုစာ စစ်ဆေးပေးပို့မည်
    await send_daily_celebrations(now)

# ================= AUTO-ROTATING PAGE RENDERER =================
PAGES = ["home", "weather_main", "weather_other", "market_sports"]

def render_page(page_idx: int) -> str:
    now = get_now()
    date_str = now.strftime("%d %b %Y (%a)")
    page_key = PAGES[page_idx % len(PAGES)]

    if page_key == "home":
        cal_info = get_calendar_line(now)
        bday_line = get_birthday_line(now)
        anni_line = get_anniversary_line(now)
        events_block = f"{bday_line}\n{anni_line}" if anni_line else bday_line

        sorted_chatters = sorted(state["chat_counts"].items(), key=lambda x: x[1]["count"], reverse=True)[:5]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        if sorted_chatters:
            chat_lines = "\n".join([f"{medals[i]} **{user_link(int(uid), u['name'])}** — `{u['count']} msgs`" for i, (uid, u) in enumerate(sorted_chatters)])
        else:
            chat_lines = "_ဒီနေ့ စကားပြောသူ မရှိသေးပါ_"

        return (
            f"📌 **GROUP LIVE BOARD** `[1/4 • 🏠 Home]`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **{date_str}**\n"
            f"{cal_info}\n"
            f"{events_block}\n\n"
            f"🏆 **Today's Top Chatters**\n"
            f"{chat_lines}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔄 _စာမျက်နှာ အလိုအလျောက် ပြောင်းလဲပြသနေသည်_"
        )

    elif page_key == "weather_main":
        return (
            f"🌤 **MYANMAR WEATHER** `[2/4 • အဓိက ၁၅ မြို့]`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{cache_data['weather_main']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔄 _စာမျက်နှာ အလိုအလျောက် ပြောင်းလဲပြသနေသည်_"
        )

    elif page_key == "weather_other":
        return (
            f"🏙 **MYANMAR WEATHER** `[3/4 • အခြား ၃၀ မြို့]`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{cache_data['weather_other']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔄 _စာမျက်နှာ အလိုအလျောက် ပြောင်းလဲပြသနေသည်_"
        )

    elif page_key == "market_sports":
        return (
            f"💹 **MARKET & LIVE SCORES** `[4/4 • Global]`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Global Gold & Crypto Prices**\n"
            f"{cache_data['market']}\n\n"
            f"⚽ **Football Live & Upcoming**\n"
            f"{cache_data['football']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔄 _စာမျက်နှာ အလိုအလျောက် ပြောင်းလဲပြသနေသည်_"
        )

# ================= BOARD SPAWN & ROTATION =================
async def spawn_new_board():
    old_id = state.get("pin_msg_id")
    if old_id:
        try:
            await app.delete_messages(TARGET_GROUP_ID, old_id)
        except Exception:
            pass

    await update_external_data()
    state["page_index"] = 0
    if not state["current_date"]:
        state["current_date"] = get_now().strftime("%Y-%m-%d")

    topic_arg = {"reply_to_message_id": TARGET_TOPIC_ID} if TARGET_TOPIC_ID else {}
    sent = await app.send_message(
        chat_id=TARGET_GROUP_ID,
        text=render_page(0),
        parse_mode=ParseMode.MARKDOWN,
        **topic_arg
    )
    try:
        await sent.pin(disable_notification=True)
    except Exception as e:
        print("Pin err:", e)

    state["pin_msg_id"] = sent.id
    await save_state()

async def rotate_board_page():
    msg_id = state.get("pin_msg_id")
    if not msg_id:
        return
    await check_daily_rollover(get_now())
    state["page_index"] = (state.get("page_index", 0) + 1) % len(PAGES)
    try:
        await app.edit_message_text(
            chat_id=TARGET_GROUP_ID,
            message_id=msg_id,
            text=render_page(state["page_index"]),
            parse_mode=ParseMode.MARKDOWN
        )
    except MessageNotModified:
        pass
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        if "MESSAGE_ID_INVALID" in str(e) or "Message to edit not found" in str(e):
            print("⚠️ Pinned board was deleted! Re-spawning in target topic...")
            await spawn_new_board()
        else:
            print("Rotate board err:", e)

# ================= OWNER-ONLY BIRTHDAY COMMANDS =================
@app.on_message(filters.command(["board", "initdash"]) & owner_only)
async def cmd_spawn_board(client, message):
    await spawn_new_board()
    if message.chat.id == TARGET_GROUP_ID:
        try:
            await message.delete()
        except Exception:
            pass
    else:
        await message.reply("✅ သတ်မှတ်ထားသော Topic အခန်းထဲတွင် Board အသစ် ထုတ်ပြီး Pin တင်လိုက်ပါပြီ။")

@app.on_message(filters.command("addhbd") & owner_only)
async def add_birthday(client, message):
    parts = message.text.split()
    replied = message.reply_to_message

    if replied and replied.from_user and len(parts) >= 3:
        day, month = parts[1], parts[2].capitalize()[:3]
        uid = replied.from_user.id
        name = replied.from_user.first_name or "User"
        uname = replied.from_user.username or ""
    elif len(parts) >= 4:
        day, month, target = parts[1], parts[2].capitalize()[:3], parts[3]
        uid, name, uname = await resolve_user_target(target)
        if not uid:
            return await message.reply(f"❌ `{target}` အကောင့်ကို ရှာမတွေ့ပါ။ `@username` မှန်ကန်ကြောင်း စစ်ဆေးပါ (သို့) ထိုသူ၏ စာကို Reply ပြန်ပြီး `/addhbd {day} {month}` ရိုက်ပါ။")
    else:
        return await message.reply(
            "📌 **မွေးနေ့ထည့်သွင်းနည်း:**\n"
            "• `/addhbd 25 Dec @username`\n"
            "• `/addhbd 25 Dec 123456789`\n"
            "• သို့မဟုတ် ထိုသူ၏ စာကို Reply ပြန်ပြီး `/addhbd 25 Dec`"
        )

    if month not in MONTH_MAP or not day.isdigit() or not (1 <= int(day) <= 31):
        return await message.reply("❌ ရက် (1-31) နှင့် လအတိုကောက် (`Jan` မှ `Dec`) မှန်ကန်စွာ ထည့်ပါ။")

    state["birthdays"] = [b for b in state["birthdays"] if int(b["uid"]) != uid]
    state["birthdays"].append({"uid": uid, "name": name, "username": uname, "day": int(day), "month": month})
    await save_state()
    await message.reply(f"✅ {user_link(uid, name)} ရဲ့ မွေးနေ့ (`{day} {month}`) ကို စာရင်းသွင်းပြီးပါပြီ။", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("hbdlist") & owner_only)
async def list_birthdays(client, message):
    if not state["birthdays"]:
        return await message.reply("🎂 မွေးနေ့စာရင်းထဲတွင် မည်သူမျှ မရှိသေးပါ။")
    sorted_bdays = sorted(state["birthdays"], key=lambda b: (MONTH_MAP.get(b["month"], 13), int(b["day"])))
    state["birthdays"] = sorted_bdays
    lines = ["🎂 **Group မွေးနေ့စာရင်းများ**", "━━━━━━━━━━━━━━━━━━━━━━"]
    for i, b in enumerate(sorted_bdays, 1):
        u_txt = f" (@{b['username']})" if b.get("username") else ""
        lines.append(f"{i}. {user_link(b['uid'], b['name'])}{u_txt} — `{b['day']} {b['month']}`")
    lines.append("\n_(ဖျက်လိုပါက `/delhbd နံပါတ်` သို့မဟုတ် `/delhbd @username` ရိုက်ပါ)_")
    await message.reply("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("delhbd") & owner_only)
async def delete_birthday(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("ဖျက်လိုသော နံပါတ်စဉ်၊ `@username` သို့မဟုတ် နာမည်ထည့်ပါ။ ဥပမာ- `/delhbd @mgmg`")
    query = parts[1].strip()
    clean_q = query[1:].lower() if query.startswith("@") else query.lower()

    if query.isdigit() and 1 <= int(query) <= len(state["birthdays"]):
        removed = state["birthdays"].pop(int(query) - 1)
        await save_state()
        return await message.reply(f"🗑️ **{removed['name']}** ကို မွေးနေ့စာရင်းမှ ဖျက်လိုက်ပါပြီ။")

    before_len = len(state["birthdays"])
    state["birthdays"] = [
        b for b in state["birthdays"]
        if b["name"].lower() != clean_q
        and str(b["uid"]) != clean_q
        and b.get("username", "").lower() != clean_q
    ]
    if len(state["birthdays"]) == before_len:
        return await message.reply(f"❌ `{query}` ဖြင့် မွေးနေ့စာရင်း မတွေ့ပါ။ (`/hbdlist` ဖြင့် ပြန်စစ်ပါ)")
    await save_state()
    await message.reply(f"🗑️ **{query}** ကို မွေးနေ့စာရင်းမှ ဖျက်လိုက်ပါပြီ။")

@app.on_message(filters.command("backuphbd") & owner_only)
async def backup_birthdays(client, message):
    if not state["birthdays"]:
        return await message.reply("🎂 Backup ထုတ်ရန် မွေးနေ့စာရင်း မရှိသေးပါ။")
    with open(HBD_BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(state["birthdays"], f, ensure_ascii=False, indent=2)
    await message.reply_document(
        document=HBD_BACKUP_FILE,
        caption=f"🎂 မွေးနေ့စာရင်း Backup ({len(state['birthdays'])} ဦး)\nပြန်သွင်းလိုပါက ဒီဖိုင်ကို Reply ပြန်ပြီး `/restorehbd` ရိုက်ပါ။"
    )
    os.remove(HBD_BACKUP_FILE)

@app.on_message(filters.command("restorehbd") & owner_only)
async def restore_birthdays(client, message):
    replied = message.reply_to_message
    if not replied or not replied.document or not replied.document.file_name.endswith(".json"):
        return await message.reply("⚠️ `birthdays_backup.json` ဖိုင်ကို Reply ပြန်ပြီး `/restorehbd` လို့ ရိုက်ပါ။")
    path = await app.download_media(replied)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Invalid JSON format")
        state["birthdays"] = data
        await save_state()
        await message.reply(f"✅ မွေးနေ့စာရင်း **{len(data)} ဦး** ကို အောင်မြင်စွာ Restore လုပ်ပြီးပါပြီ။")
    except Exception as e:
        await message.reply(f"❌ ဖိုင်ဖတ်ရာတွင် အမှားရှိနေပါသည်: `{e}`")
    finally:
        if os.path.exists(path):
            os.remove(path)

# ================= OWNER-ONLY RELATIONSHIP COMMANDS =================
@app.on_message(filters.command("addrs") & owner_only)
async def add_relationship(client, message):
    parts = message.text.split()
    if len(parts) < 6:
        return await message.reply(
            "📌 **အတွဲစာရင်း ထည့်သွင်းနည်း:**\n"
            "`/addrs 14 Feb 2025 @user1 @user2`\n"
            "_(စတွဲတဲ့ရက် လ ခုနှစ် + `@username` သို့မဟုတ် User ID ၂ ခု)_"
        )
    day, month, year = parts[1], parts[2].capitalize()[:3], parts[3]
    target1, target2 = parts[4], parts[5]

    if month not in MONTH_MAP or not day.isdigit() or not year.isdigit():
        return await message.reply("❌ ရက်စွဲပုံစံ မှားယွင်းနေပါသည်။ ဥပမာ- `14 Feb 2025`")

    uid1, name1, user1 = await resolve_user_target(target1)
    if not uid1:
        return await message.reply(f"❌ `{target1}` အကောင့်ကို ရှာမတွေ့ပါ။ `@username` သို့မဟုတ် User ID အမှန်ထည့်ပါ။")

    uid2, name2, user2 = await resolve_user_target(target2)
    if not uid2:
        return await message.reply(f"❌ `{target2}` အကောင့်ကို ရှာမတွေ့ပါ။ `@username` သို့မဟုတ် User ID အမှန်ထည့်ပါ။")

    state["relationships"] = [
        r for r in state["relationships"]
        if int(r["uid1"]) not in (uid1, uid2) and int(r["uid2"]) not in (uid1, uid2)
    ]
    state["relationships"].append({
        "uid1": uid1, "name1": name1, "user1": user1,
        "uid2": uid2, "name2": name2, "user2": user2,
        "day": int(day), "month": month, "year": int(year)
    })
    await save_state()
    p1 = user_link(uid1, name1)
    p2 = user_link(uid2, name2)
    await message.reply(f"💑 {p1} ❤️ {p2} အတွဲကို (`{day} {month} {year}`) မှစတင်၍ စာရင်းသွင်းပြီးပါပြီ။", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("rslist") & owner_only)
async def list_relationships(client, message):
    if not state["relationships"]:
        return await message.reply("💑 အတွဲစာရင်းထဲတွင် မည်သူမျှ မရှိသေးပါ။")
    now = get_now().date()
    lines = ["💑 **Group အတွဲစာရင်းများ**", "━━━━━━━━━━━━━━━━━━━━━━"]
    for i, r in enumerate(state["relationships"], 1):
        p1 = user_link(r["uid1"], r["name1"])
        p2 = user_link(r["uid2"], r["name2"])
        start_d = datetime.date(int(r["year"]), MONTH_MAP[r["month"]], int(r["day"]))
        days_together = max(0, (now - start_d).days)
        lines.append(f"{i}. {p1} ❤️ {p2} — `{r['day']} {r['month']} {r['year']}` ({days_together} ရက်)")
    lines.append("\n_(ဖြုတ်လိုပါက `/delrs နံပါတ်` သို့မဟုတ် `/delrs @username` ရိုက်ပါ)_")
    await message.reply("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("delrs") & owner_only)
async def delete_relationship(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("ဖြုတ်လိုသော နံပါတ်စဉ်၊ `@username` သို့မဟုတ် နာမည်ထည့်ပါ။ ဥပမာ- `/delrs @mgmg`")
    query = parts[1].strip()
    clean_q = query[1:].lower() if query.startswith("@") else query.lower()

    if query.isdigit() and 1 <= int(query) <= len(state["relationships"]):
        removed = state["relationships"].pop(int(query) - 1)
        await save_state()
        return await message.reply(f"💔 **{removed['name1']} & {removed['name2']}** အတွဲကို စာရင်းမှ ဖြုတ်လိုက်ပါပြီ။")

    kept = []
    removed_pairs = []
    for r in state["relationships"]:
        match_p1 = (
            r["name1"].lower() == clean_q
            or str(r["uid1"]) == clean_q
            or r.get("user1", "").lower() == clean_q
        )
        match_p2 = (
            r["name2"].lower() == clean_q
            or str(r["uid2"]) == clean_q
            or r.get("user2", "").lower() == clean_q
        )
        if match_p1 or match_p2:
            removed_pairs.append(f"{r['name1']} & {r['name2']}")
        else:
            kept.append(r)

    if not removed_pairs:
        return await message.reply(f"❌ `{query}` ဖြင့် အတွဲစာရင်း မတွေ့ပါ။ (`/rslist` ဖြင့် ပြန်စစ်ပါ)")

    state["relationships"] = kept
    await save_state()
    await message.reply(f"💔 **{', '.join(removed_pairs)}** အတွဲကို စာရင်းမှ ဖြုတ်လိုက်ပါပြီ။")

@app.on_message(filters.command("backuprs") & owner_only)
async def backup_relationships(client, message):
    if not state["relationships"]:
        return await message.reply("💑 Backup ထုတ်ရန် အတွဲစာရင်း မရှိသေးပါ။")
    with open(RS_BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(state["relationships"], f, ensure_ascii=False, indent=2)
    await message.reply_document(
        document=RS_BACKUP_FILE,
        caption=f"💑 အတွဲစာရင်း Backup ({len(state['relationships'])} တွဲ)\nပြန်သွင်းလိုပါက ဒီဖိုင်ကို Reply ပြန်ပြီး `/restorers` ရိုက်ပါ။"
    )
    os.remove(RS_BACKUP_FILE)

@app.on_message(filters.command("restorers") & owner_only)
async def restore_relationships(client, message):
    replied = message.reply_to_message
    if not replied or not replied.document or not replied.document.file_name.endswith(".json"):
        return await message.reply("⚠️ `relationships_backup.json` ဖိုင်ကို Reply ပြန်ပြီး `/restorers` လို့ ရိုက်ပါ။")
    path = await app.download_media(replied)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Invalid JSON format")
        state["relationships"] = data
        await save_state()
        await message.reply(f"✅ အတွဲစာရင်း **{len(data)} တွဲ** ကို အောင်မြင်စွာ Restore လုပ်ပြီးပါပြီ။")
    except Exception as e:
        await message.reply(f"❌ ဖိုင်ဖတ်ရာတွင် အမှားရှိနေပါသည်: `{e}`")
    finally:
        if os.path.exists(path):
            os.remove(path)

# ================= MESSAGE COUNTER & AUTO-PROFILE SYNC =================
@app.on_message(filters.chat(TARGET_GROUP_ID) & ~filters.service)
async def count_messages(client, message):
    if not message.from_user or message.from_user.is_bot:
        return
    uid_int = message.from_user.id
    uid = str(uid_int)
    name = message.from_user.first_name or "User"
    uname = message.from_user.username or ""

    if uid not in state["chat_counts"]:
        state["chat_counts"][uid] = {"name": name, "username": uname, "count": 0}
    state["chat_counts"][uid]["name"] = name
    state["chat_counts"][uid]["username"] = uname
    state["chat_counts"][uid]["count"] += 1

    # အဖွဲ့သား Name သို့မဟုတ် Username ပြောင်းသွားပါက အလိုအလျောက် Sync လုပ်ပေးမည်
    for b in state["birthdays"]:
        if int(b["uid"]) == uid_int:
            b["name"] = name
            b["username"] = uname
    for r in state["relationships"]:
        if int(r["uid1"]) == uid_int:
            r["name1"] = name
            r["user1"] = uname
        if int(r["uid2"]) == uid_int:
            r["name2"] = name
            r["user2"] = uname

# ================= SCHEDULER & MAIN =================
async def start_scheduler():
    scheduler = AsyncIOScheduler(timezone=MM_TZ)
    scheduler.add_job(rotate_board_page, "interval", minutes=2)
    scheduler.add_job(update_external_data, "interval", minutes=15)
    scheduler.add_job(save_state, "interval", minutes=30)
    scheduler.start()

async def main():
    Thread(target=run_flask, daemon=True).start()
    await app.start()
    await load_state()
    await update_external_data()
    await start_scheduler()
    print("🚀 Owner-Controlled Billboard with Username/ID Sync & Celebrations Started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop.run_until_complete(main())
