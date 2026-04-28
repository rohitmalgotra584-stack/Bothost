import atexit
import hashlib
import html
import json
import logging
import mimetypes
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime, timedelta
from threading import Thread
import psutil
import requests
import telebot
from flask import Flask
from telebot import types

# --- Flask Keep Alive ---
app = Flask("")


@app.route("/")
def home():
    return "SkullBotHost - Online ✅"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    logger.info("Flask Keep-Alive server started.")


# --- Configuration ---
TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "8529203727:AAG3mi64ZqrLbTaLRksAeKSHl2mcaOyUlHc",
).strip()
OWNER_ID = int(os.environ.get("OWNER_ID", 8624480309))
ADMIN_ID = int(os.environ.get("ADMIN_ID", 8624480309))
YOUR_USERNAME = os.environ.get("YOUR_USERNAME", "@itsukiarai")
UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "@botsarefather")
BOT_NAME = os.environ.get("BOT_NAME", "SkullBotHost")
WELCOME_IMAGE_URL = os.environ.get(
    "WELCOME_IMAGE_URL",
    "https://kommodo.ai/i/VyGyR77XQdZZIfRcGN46",
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, "upload_bots")
IROTECH_DIR = os.path.join(BASE_DIR, "inf")
DATABASE_PATH = os.path.join(IROTECH_DIR, "bot_data.db")

FREE_USER_LIMIT = 3
SUBSCRIBED_USER_LIMIT = 20
ADMIN_LIMIT = 999
OWNER_LIMIT = float("inf")

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, threaded=True)

bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
DB_LOCK = threading.Lock()
awaiting_db_restore = set()
awaiting_forcejoin_add = set()

STATE_LOCK = threading.RLock()
CALLBACK_TOKEN_LENGTH = 12
SCRIPT_STATUS_REFRESH_DELAY = float(os.environ.get("SCRIPT_STATUS_REFRESH_DELAY", "0.6"))
RUN_ALL_START_DELAY = float(os.environ.get("RUN_ALL_START_DELAY", "0.25"))
BROADCAST_BATCH_SIZE = int(os.environ.get("BROADCAST_BATCH_SIZE", "35"))
BROADCAST_BATCH_DELAY = float(os.environ.get("BROADCAST_BATCH_DELAY", "1.0"))
ACTIVE_BOT_PANEL_LIMIT = int(os.environ.get("ACTIVE_BOT_PANEL_LIMIT", "30"))
PIP_INSTALL_CACHE = set()
NPM_INSTALL_CACHE = set()

# ForceJoin channels: list of dicts {channel_id, channel_username, channel_name, enabled}
forcejoin_channels = []

# ─────────────────────────────────────────────
# PREMIUM CUSTOM EMOJI SYSTEM
# ─────────────────────────────────────────────

CE = {
    "eyes": ("5210956306952758910", "👀"),
    "smile": ("5461117441612462242", "🙂"),
    "lightning": ("5456140674028019486", "⚡️"),
    "comet": ("5224607267797606837", "☄️"),
    "bag": ("5229064374403998351", "🛍"),
    "no_entry": ("5260293700088511294", "⛔️"),
    "no": ("5240241223632954241", "🚫"),
    "exclaim": ("5274099962655816924", "❗️"),
    "double_exclaim": ("5440660757194744323", "‼️"),
    "interrobang": ("5314504236132747481", "⁉️"),
    "question": ("5436113877181941026", "❓"),
    "warning": ("5447644880824181073", "⚠️"),
    "warning2": ("5420323339723881652", "⚠️"),
    "globe": ("5447410659077661506", "🌐"),
    "speech": ("5443038326535759644", "💬"),
    "thought": ("5467538555158943525", "💭"),
    "question2": ("5452069934089641166", "❓"),
    "chart": ("5231200819986047254", "📊"),
    "arrow_up": ("5449683594425410231", "🔼"),
    "arrow_down": ("5447183459602669338", "🔽"),
    "candle": ("5451882707875276247", "🕯"),
    "stats_up": ("5244837092042750681", "📈"),
    "stats_down": ("5246762912428603768", "📉"),
    "check": ("5206607081334906820", "✔️"),
    "cross": ("5210952531676504517", "❌"),
    "cool": ("5222079954421818267", "🆒"),
    "bell": ("5458603043203327669", "🔔"),
    "disguise": ("5391112412445288650", "🥸"),
    "clown": ("5269531045165816230", "🤡"),
    "lips": ("5395444514028529554", "🫦"),
    "pin": ("5397782960512444700", "📌"),
    "dollar": ("5409048419211682843", "💵"),
    "money_fly": ("5233326571099534068", "💸"),
    "money_fly2": ("5231449120635370684", "💸"),
    "money_fly3": ("5278751923338490157", "💸"),
    "money_fly4": ("5290017777174722330", "💸"),
    "money_fly5": ("5231005931550030290", "💸"),
    "exchange": ("5402186569006210455", "💱"),
    "play": ("5264919878082509254", "▶️"),
    "red_circle": ("5411225014148014586", "🔴"),
    "green_circle": ("5416081784641168838", "🟢"),
    "arrow_right": ("5416117059207572332", "➡️"),
    "fire": ("5424972470023104089", "🔥"),
    "boom": ("5276032951342088188", "💥"),
    "mic2": ("5294339927318739359", "🎙"),
    "mic": ("5224736245665511429", "🎤"),
    "broadcast": ("5424818078833715060", "📣"),
    "shh": ("5431609822288033666", "🤫"),
    "thumbs_down": ("5449875686837726134", "👎"),
    "speaking": ("5460795800101594035", "🗣️"),
    "search": ("5231012545799666522", "🔍"),
    "shield": ("5251203410396458957", "🛡"),
    "link": ("5271604874419647061", "🔗"),
    "monitor": ("5282843764451195532", "🖥"),
    "copyright": ("5323442290708985472", "©"),
    "info": ("5334544901428229844", "ℹ️"),
    "thumbs_up": ("5337080053119336309", "👍"),
    "play2": ("5348125953090403204", "▶️"),
    "pause": ("5359543311897998264", "⏸"),
    "hundred": ("5341498088408234504", "💯"),
    "restart": ("5375338737028841420", "🔄"),
    "top": ("5415655814079723871", "🔝"),
    "new": ("5382357040008021292", "🆕"),
    "soon": ("5440621591387980068", "🔜"),
    "location": ("5391032818111363540", "📍"),
    "plus": ("5397916757333654639", "➕"),
    "diamond": ("5427168083074628963", "💎"),
    "star": ("5438496463044752972", "⭐️"),
    "sparkle": ("5325547803936572038", "✨"),
    "crown": ("5217822164362739968", "👑"),
    "trash": ("5445267414562389170", "🗑"),
    "bookmark": ("5222444124698853913", "🔖"),
    "mail": ("5253742260054409879", "✉️"),
    "lock": ("5296369303661067030", "🔒"),
    "wow": ("5303479226882603449", "😮"),
    "paperclip": ("5305265301917549162", "📎"),
    "settings": ("5341715473882955310", "⚙️"),
    "gamepad": ("5361741454685256344", "🎮"),
    "volume": ("5388632425314140043", "🔈"),
    "hourglass": ("5386367538735104399", "⌛"),
    "down": ("5406745015365943482", "⬇️"),
    "sun": ("5402477260982731644", "☀️"),
    "rain": ("5399913388845322366", "🌧"),
    "moon": ("5449569374065152798", "🌛"),
    "snow": ("5449449325434266744", "❄️"),
    "rainbow": ("5409109841538994759", "🌈"),
    "drop": ("5393512611968995988", "💧"),
    "calendar": ("5413879192267805083", "🗓"),
    "bulb": ("5422439311196834318", "💡"),
    "gold": ("5440539497383087970", "🥇"),
    "silver": ("5447203607294265305", "🥈"),
    "bronze": ("5453902265922376865", "🥉"),
    "music": ("5463107823946717464", "🎵"),
    "free": ("5406756500108501710", "🆓"),
    "pencil": ("5395444784611480792", "✏️"),
    "alarm": ("5395695537687123235", "🚨"),
    "bag2": ("5406683434124859552", "🛍"),
    "home": ("5416041192905265756", "🏠"),
    "flag": ("5460755126761312667", "🚩"),
    "party": ("5461151367559141950", "🎉"),
    "robot": ("5258093637450866522", "🤖"),
    "admin": ("5258260149037965799", "💼"),
    "folder_open": ("5258514780469075716", "📂"),
    "folder": ("5257965810634202885", "📁"),
    "file": ("5258477770735885832", "📄"),
    "user": ("5258362837411045098", "👤"),
    "users": ("5258486128742244085", "👥"),
    "upload": ("5258043150110301407", "⬆️"),
    "back": ("5258132936401624790", "⬅️"),
    "laptop": ("5258423306255604960", "💻"),
    "time": ("5258258882022612173", "⏲️"),
    "id_num": ("5226513232549664618", "🔢"),
    "package": ("5258134813302332906", "📦"),
    "phone": ("5258020476977946656", "📞"),
    "check2": ("5260726538302660868", "✅"),
    "check3": ("5258057130228849960", "✅"),
    "cross2": ("5260342697075416641", "❌"),
    "db": ("5258254475386167466", "🖼"),
    "write": ("5258331647358540449", "✍️"),
}


def ce(key, fallback=None):
    if key in CE:
        emoji_id, fb = CE[key]
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback or fb}</tg-emoji>'
    return fallback or key


def bold(text):
    return f"<b>{text}</b>"


def code(text):
    return f"<code>{text}</code>"


EFFECT_FIRE = "5104841245755129431"
EFFECT_LIKE = "5107584321108051014"
EFFECT_CELEBRATE = "5104858069142078462"
EFFECT_HEART = "5044134455711629726"


def send_with_effect(chat_id, text, effect_id=None, reply_markup=None, reply_to=None, parse_mode="HTML"):
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if effect_id:
        kwargs["message_effect_id"] = effect_id
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    try:
        return bot.send_message(**kwargs)
    except Exception:
        kwargs.pop("message_effect_id", None)
        return bot.send_message(**kwargs)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

TEXT_LIKE_EXTENSIONS = {
    ".py",
    ".js",
    ".json",
    ".txt",
    ".md",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".toml",
    ".env",
    ".csv",
}


def safe_filename(file_name):
    return os.path.basename((file_name or "").replace("\\", "/")).strip()


def safe_join(base_dir, *paths):
    target = os.path.abspath(os.path.join(base_dir, *paths))
    base_abs = os.path.abspath(base_dir)
    if target != base_abs and not target.startswith(base_abs + os.sep):
        raise ValueError("Unsafe file path detected")
    return target


def is_text_like(file_name):
    return os.path.splitext(file_name.lower())[1] in TEXT_LIKE_EXTENSIONS


def message_is_cancel(message):
    return bool(message and message.text and message.text.strip().lower() == "/cancel")


def ensure_text_message(message, warning_text):
    if message and message.text:
        return True
    bot.reply_to(message, warning_text, parse_mode="HTML")
    return False


def get_windows_process_flags():
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return startupinfo, creationflags


def format_username(username):
    return f"@{username}" if username else "N/A"


def escape_html(value):
    return html.escape(str(value), quote=False)


def get_bot_script_items():
    return list(bot_scripts.items())


def get_running_scripts_snapshot(owner_id=None):
    running = []
    for script_key, script_info in get_bot_script_items():
        script_owner_id = script_info.get("script_owner_id")
        file_name = script_info.get("file_name")
        if owner_id is not None and script_owner_id != owner_id:
            continue
        if file_name and is_bot_running(script_owner_id, file_name):
            running.append((script_key, script_info))
    return running


def count_running_scripts(owner_id=None):
    return len(get_running_scripts_snapshot(owner_id))


def make_callback_token(value):
    return hashlib.sha1(str(value).encode("utf-8", errors="ignore")).hexdigest()[:CALLBACK_TOKEN_LENGTH]


def build_named_callback(action, owner_id, value):
    return f"{action}:{owner_id}:{make_callback_token(value)}"


def parse_named_callback(data, expected_action):
    legacy_prefix = f"{expected_action}_"
    if data.startswith(legacy_prefix):
        _, owner_id_str, raw_value = data.split("_", 2)
        return int(owner_id_str), raw_value, True

    action, owner_id_str, token = data.split(":", 2)
    if action != expected_action:
        raise ValueError(f"Expected callback action {expected_action}, got {action}")
    return int(owner_id_str), token, False


def resolve_token_from_candidates(token, candidates):
    for candidate in candidates:
        if make_callback_token(candidate) == token:
            return candidate
    return None


def resolve_user_file_from_callback(data, expected_action):
    owner_id, raw_value, legacy = parse_named_callback(data, expected_action)
    if legacy:
        return owner_id, raw_value
    file_name = resolve_token_from_candidates(raw_value, [name for name, _ in user_files.get(owner_id, [])])
    if not file_name:
        raise KeyError("File token expired or file removed.")
    return owner_id, file_name


def resolve_running_script_from_callback(data, expected_action):
    owner_id, raw_value, legacy = parse_named_callback(data, expected_action)
    if legacy:
        return owner_id, raw_value
    file_name = resolve_token_from_candidates(
        raw_value,
        [script_info["file_name"] for _, script_info in get_running_scripts_snapshot(owner_id)],
    )
    if not file_name:
        raise KeyError("Running script token expired or script stopped.")
    return owner_id, file_name


def resolve_user_log_from_callback(data, expected_action):
    owner_id, raw_value, legacy = parse_named_callback(data, expected_action)
    if legacy:
        return owner_id, raw_value
    user_folder = get_user_folder(owner_id)
    log_candidates = []
    if os.path.isdir(user_folder):
        log_candidates = [name for name in os.listdir(user_folder) if name.endswith(".log")]
    log_name = resolve_token_from_candidates(raw_value, log_candidates)
    if not log_name:
        raise KeyError("Log token expired or log removed.")
    return owner_id, log_name


def send_or_edit_context(message_or_call, text, reply_markup=None, parse_mode="HTML"):
    if isinstance(message_or_call, types.CallbackQuery):
        try:
            bot.edit_message_text(
                text,
                message_or_call.message.chat.id,
                message_or_call.message.message_id,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except telebot.apihelper.ApiTelegramException as exc:
            if "message is not modified" not in str(exc):
                bot.send_message(
                    message_or_call.message.chat.id,
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
        except Exception:
            bot.send_message(
                message_or_call.message.chat.id,
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        return

    bot.reply_to(message_or_call, text, reply_markup=reply_markup, parse_mode=parse_mode)


# ─────────────────────────────────────────────
# MALWARE DETECTION
# ─────────────────────────────────────────────

MALWARE_SIGNATURES = [b"MZ", b"\x7fELF", b"\xfe\xed\xfa", b"\xce\xfa\xed\xfe"]
ENCRYPTED_FILE_INDICATORS = [b"openssl", b"encrypted", b"cipher", b"AES", b"DES", b"RSA", b"GPG", b"PGP"]
SUSPICIOUS_KEYWORDS = [
    b"ransomware",
    b"trojan",
    b"virus",
    b"malware",
    b"backdoor",
    b"exploit",
    b"payload",
    b"botnet",
    b"keylogger",
    b"rootkit",
]


def get_file_type(file_content):
    signatures = {
        b"\x7fELF": "application/x-executable",
        b"MZ": "application/x-dosexec",
        b"\xfe\xed\xfa": "application/x-mach-binary",
        b"\xce\xfa\xed\xfe": "application/x-mach-binary",
        b"PK": "application/zip",
        b"Rar!": "application/x-rar",
    }
    for sig, mime in signatures.items():
        if file_content.startswith(sig):
            return mime
    return "application/octet-stream"


def is_suspicious_file(file_content, file_name):
    file_lower = file_name.lower()
    suspicious_extensions = [
        ".exe",
        ".dll",
        ".bat",
        ".cmd",
        ".scr",
        ".com",
        ".pif",
        ".application",
        ".gadget",
        ".msi",
        ".msp",
        ".hta",
        ".cpl",
        ".msc",
        ".jar",
        ".bin",
        ".deb",
        ".rpm",
        ".apk",
        ".app",
        ".dmg",
        ".iso",
        ".img",
    ]
    if any(file_lower.endswith(ext) for ext in suspicious_extensions):
        return True, f"Suspicious file extension: {file_name}"

    for sig in MALWARE_SIGNATURES:
        if file_content.startswith(sig):
            return True, "Executable or malware signature detected"

    sample = file_content[:4096]
    if not is_text_like(file_name):
        for indicator in ENCRYPTED_FILE_INDICATORS:
            if indicator in sample:
                return True, f"Encrypted file indicator: {indicator.decode('utf-8', errors='ignore')}"

    sample_text = sample.decode("utf-8", errors="ignore").lower()
    for keyword in SUSPICIOUS_KEYWORDS:
        kw_text = keyword.decode("utf-8").lower()
        if kw_text in sample_text and not is_text_like(file_name):
            return True, f"Suspicious keyword: {kw_text}"

    try:
        file_type = get_file_type(sample)
        if file_type in {"application/x-dosexec", "application/x-executable", "application/x-mach-binary"}:
            return True, f"Executable file type: {file_type}"
    except Exception:
        pass

    return False, "File appears safe"


def scan_file_for_malware(file_content, file_name, user_id):
    if user_id == OWNER_ID:
        return True, "Owner bypassed security check"
    is_suspicious, reason = is_suspicious_file(file_content, file_name)
    if is_suspicious:
        logger.warning("Malware detected in %s from user %s: %s", file_name, user_id, reason)
        return False, f"Security violation: {reason}"
    return True, "File passed security check"


# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

def init_db():
    logger.info("Initializing database at: %s", DATABASE_PATH)
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS subscriptions
               (user_id INTEGER PRIMARY KEY, expiry TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS user_files
               (user_id INTEGER, file_name TEXT, file_type TEXT,
                PRIMARY KEY (user_id, file_name))"""
        )
        c.execute("""CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY)""")
        c.execute("""CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)""")
        c.execute(
            """CREATE TABLE IF NOT EXISTS forcejoin_channels
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                channel_username TEXT,
                channel_name TEXT,
                enabled INTEGER DEFAULT 1)"""
        )
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("DB init error: %s", e, exc_info=True)


def load_data():
    logger.info("Loading data from database...")
    global forcejoin_channels
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()

        c.execute("SELECT user_id, expiry FROM subscriptions")
        user_subscriptions.clear()
        for user_id, expiry in c.fetchall():
            try:
                user_subscriptions[user_id] = {"expiry": datetime.fromisoformat(expiry)}
            except ValueError:
                logger.warning("Skipping malformed expiry for user %s", user_id)

        c.execute("SELECT user_id, file_name, file_type FROM user_files")
        user_files.clear()
        for user_id, file_name, file_type in c.fetchall():
            user_files.setdefault(user_id, []).append((file_name, file_type))

        c.execute("SELECT user_id FROM active_users")
        active_users.clear()
        active_users.update(uid for (uid,) in c.fetchall())

        c.execute("SELECT user_id FROM admins")
        admin_ids.clear()
        admin_ids.update(uid for (uid,) in c.fetchall())
        admin_ids.add(OWNER_ID)

        c.execute("SELECT id, channel_id, channel_username, channel_name, enabled FROM forcejoin_channels")
        forcejoin_channels = [
            {
                "id": row[0],
                "channel_id": row[1],
                "channel_username": row[2],
                "channel_name": row[3],
                "enabled": bool(row[4]),
            }
            for row in c.fetchall()
        ]
        conn.close()
        logger.info(
            "Loaded: %s users, %s subs, %s admins, %s forcejoin channels.",
            len(active_users),
            len(user_subscriptions),
            len(admin_ids),
            len(forcejoin_channels),
        )
    except Exception as e:
        logger.error("Error loading data: %s", e, exc_info=True)


init_db()
load_data()


# ─────────────────────────────────────────────
# DATABASE OPERATIONS
# ─────────────────────────────────────────────

def save_user_file(user_id, file_name, file_type="py"):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)",
                (user_id, file_name, file_type),
            )
            conn.commit()
            user_files.setdefault(user_id, [])
            user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type))
        except Exception as e:
            logger.error("Error saving file for %s: %s", user_id, e, exc_info=True)
        finally:
            conn.close()


def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM user_files WHERE user_id = ? AND file_name = ?", (user_id, file_name))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]:
                    del user_files[user_id]
        except Exception as e:
            logger.error("Error removing file for %s: %s", user_id, e, exc_info=True)
        finally:
            conn.close()


def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("INSERT OR IGNORE INTO active_users (user_id) VALUES (?)", (user_id,))
            conn.commit()
        except Exception as e:
            logger.error("Error adding active user %s: %s", user_id, e, exc_info=True)
        finally:
            conn.close()


def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)",
                (user_id, expiry.isoformat()),
            )
            conn.commit()
            user_subscriptions[user_id] = {"expiry": expiry}
        except Exception as e:
            logger.error("Error saving subscription for %s: %s", user_id, e, exc_info=True)
        finally:
            conn.close()


def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            conn.commit()
            user_subscriptions.pop(user_id, None)
        except Exception as e:
            logger.error("Error removing subscription for %s: %s", user_id, e, exc_info=True)
        finally:
            conn.close()


def add_admin_db(admin_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))
            conn.commit()
            admin_ids.add(admin_id)
        except Exception as e:
            logger.error("Error adding admin %s: %s", admin_id, e, exc_info=True)
        finally:
            conn.close()


def remove_admin_db(admin_id):
    if admin_id == OWNER_ID:
        return False
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("SELECT 1 FROM admins WHERE user_id = ?", (admin_id,))
            if c.fetchone():
                c.execute("DELETE FROM admins WHERE user_id = ?", (admin_id,))
                conn.commit()
                removed = c.rowcount > 0
                if removed:
                    admin_ids.discard(admin_id)
                return removed
            admin_ids.discard(admin_id)
            return False
        except Exception as e:
            logger.error("Error removing admin %s: %s", admin_id, e, exc_info=True)
            return False
        finally:
            conn.close()


# ─────────────────────────────────────────────
# FORCEJOIN DATABASE OPERATIONS
# ─────────────────────────────────────────────

def add_forcejoin_channel_db(channel_id, channel_username, channel_name):
    global forcejoin_channels
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute(
                """INSERT OR REPLACE INTO forcejoin_channels
                   (channel_id, channel_username, channel_name, enabled)
                   VALUES (?, ?, ?, 1)""",
                (str(channel_id), channel_username, channel_name),
            )
            conn.commit()
            load_forcejoin_channels_from_db(conn)
        except Exception as e:
            logger.error("Error adding forcejoin channel: %s", e, exc_info=True)
        finally:
            conn.close()


def remove_forcejoin_channel_db(channel_id):
    global forcejoin_channels
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM forcejoin_channels WHERE channel_id = ?", (str(channel_id),))
            conn.commit()
            load_forcejoin_channels_from_db(conn)
        except Exception as e:
            logger.error("Error removing forcejoin channel: %s", e, exc_info=True)
        finally:
            conn.close()


def toggle_forcejoin_channel_db(channel_id, enabled):
    global forcejoin_channels
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute(
                "UPDATE forcejoin_channels SET enabled = ? WHERE channel_id = ?",
                (1 if enabled else 0, str(channel_id)),
            )
            conn.commit()
            load_forcejoin_channels_from_db(conn)
        except Exception as e:
            logger.error("Error toggling forcejoin channel: %s", e, exc_info=True)
        finally:
            conn.close()


def load_forcejoin_channels_from_db(conn=None):
    global forcejoin_channels
    close_after = False
    if conn is None:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        close_after = True
    try:
        c = conn.cursor()
        c.execute("SELECT id, channel_id, channel_username, channel_name, enabled FROM forcejoin_channels")
        forcejoin_channels = [
            {
                "id": row[0],
                "channel_id": row[1],
                "channel_username": row[2],
                "channel_name": row[3],
                "enabled": bool(row[4]),
            }
            for row in c.fetchall()
        ]
    except Exception as e:
        logger.error("Error loading forcejoin channels: %s", e)
    finally:
        if close_after:
            conn.close()


# ─────────────────────────────────────────────
# FORCEJOIN CHECK
# ─────────────────────────────────────────────

def check_user_joined_channels(user_id):
    if user_id in admin_ids or user_id == OWNER_ID:
        return []
    not_joined = []
    enabled_channels = [ch for ch in forcejoin_channels if ch["enabled"]]
    valid_statuses = {"member", "administrator", "creator"}
    for ch in enabled_channels:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in valid_statuses:
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined


def send_forcejoin_message(chat_id, not_joined_channels):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in not_joined_channels:
        username = ch.get("channel_username", "")
        name = ch.get("channel_name", username or "Channel")
        if username:
            url = f"https://t.me/{username.lstrip('@')}"
            markup.add(types.InlineKeyboardButton("🔔 Join: " + str(name), url=url))

    markup.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_joined"))
    text = (
        ce("alarm")
        + " <b>Join Required!</b>\n\n"
        + "You must join all required channels to use "
        + BOT_NAME
        + ".\n\n"
        + ce("arrow_right")
        + " Click below to join, then press <b>I Joined</b>."
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")


# ─────────────────────────────────────────────
# DATABASE BACKUP & RESTORE
# ─────────────────────────────────────────────

def _logic_get_db(message_or_call):
    if isinstance(message_or_call, types.CallbackQuery):
        user_id = message_or_call.from_user.id
        chat_id = message_or_call.message.chat.id
        bot.answer_callback_query(message_or_call.id, "📦 Preparing database...")
    else:
        user_id = message_or_call.from_user.id
        chat_id = message_or_call.chat.id

    if user_id not in admin_ids:
        bot.send_message(chat_id, f"{ce('warning')} Admin access required.", parse_mode="HTML")
        return

    if not os.path.exists(DATABASE_PATH):
        bot.send_message(chat_id, f"{ce('cross')} Database file not found!", parse_mode="HTML")
        return

    try:
        db_size = os.path.getsize(DATABASE_PATH)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"skullbothost_backup_{timestamp}.db"
        with open(DATABASE_PATH, "rb") as f:
            caption = (
                f"{ce('package')} <b>Database Backup</b>\n\n"
                f"{ce('time')} <b>Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                f"{ce('stats_up')} <b>Size:</b> <code>{db_size / 1024:.1f} KB</code>\n"
                f"{ce('users')} <b>Users:</b> <code>{len(active_users)}</code>\n"
                f"{ce('folder')} <b>File records:</b> <code>{sum(len(v) for v in user_files.values())}</code>\n"
                f"{ce('star')} <b>Subscriptions:</b> <code>{len(user_subscriptions)}</code>\n"
                f"{ce('admin')} <b>Admins:</b> <code>{len(admin_ids)}</code>\n"
                f"{ce('bell')} <b>ForceJoin Channels:</b> <code>{len(forcejoin_channels)}</code>\n\n"
                f"{ce('info')} To restore, send this file back to the bot."
            )
            bot.send_document(chat_id, (backup_name, f), caption=caption, parse_mode="HTML")
    except Exception as e:
        logger.error("Error sending DB: %s", e, exc_info=True)
        bot.send_message(chat_id, f"{ce('cross')} Failed to send database: {e}", parse_mode="HTML")


def handle_db_restore(file_content, file_name, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if user_id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Only admins can restore the database.", parse_mode="HTML")
        return
    if not file_content.startswith(b"SQLite format 3"):
        bot.reply_to(message, f"{ce('cross')} <b>Invalid database file!</b>", parse_mode="HTML")
        return

    temp_path = DATABASE_PATH + ".restore_tmp"
    current_backup = DATABASE_PATH + ".pre_restore_backup"
    try:
        with open(temp_path, "wb") as f:
            f.write(file_content)

        test_conn = sqlite3.connect(temp_path)
        test_c = test_conn.cursor()
        required_tables = {"subscriptions", "user_files", "active_users", "admins", "forcejoin_channels"}
        test_c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in test_c.fetchall()}
        test_conn.close()

        missing = sorted(required_tables - existing_tables)
        if missing:
            os.remove(temp_path)
            bot.reply_to(message, f"{ce('cross')} Missing tables: <code>{', '.join(missing)}</code>", parse_mode="HTML")
            return

        bot.reply_to(message, f"{ce('time')} <b>Stopping all running scripts...</b>", parse_mode="HTML")
        for key in list(bot_scripts.keys()):
            if key in bot_scripts:
                kill_process_tree(bot_scripts[key])
                del bot_scripts[key]

        time.sleep(1)
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, current_backup)

        with DB_LOCK:
            shutil.move(temp_path, DATABASE_PATH)

        user_subscriptions.clear()
        user_files.clear()
        active_users.clear()
        admin_ids.clear()
        admin_ids.add(OWNER_ID)
        load_data()

        bot.reply_to(
            message,
            f"{ce('check')} <b>Database restored successfully!</b>\n\n"
            f"{ce('users')} <b>Users loaded:</b> <code>{len(active_users)}</code>\n"
            f"{ce('star')} <b>Subscriptions:</b> <code>{len(user_subscriptions)}</code>\n"
            f"{ce('admin')} <b>Admins:</b> <code>{len(admin_ids)}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Error restoring DB: %s", e, exc_info=True)
        if os.path.exists(current_backup):
            try:
                shutil.copy2(current_backup, DATABASE_PATH)
                bot.reply_to(
                    message,
                    f"{ce('cross')} Restore failed: <code>{e}</code>\n{ce('check2')} Previous DB recovered.",
                    parse_mode="HTML",
                )
            except Exception:
                bot.reply_to(message, f"{ce('cross')} Critical restore error: <code>{e}</code>", parse_mode="HTML")
        else:
            bot.reply_to(message, f"{ce('cross')} Restore failed: <code>{e}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def get_user_folder(user_id):
    folder = safe_join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def get_user_file_limit(user_id):
    if user_id == OWNER_ID:
        return OWNER_LIMIT
    if user_id in admin_ids:
        return ADMIN_LIMIT
    if user_id in user_subscriptions and user_subscriptions[user_id]["expiry"] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT


def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))


def get_user_status(user_id):
    expiry_info = ""
    if user_id == OWNER_ID:
        return f"{ce('crown')} Owner", expiry_info
    if user_id in admin_ids:
        return f"{ce('admin')} Admin", expiry_info
    if user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get("expiry")
        if expiry_date and expiry_date > datetime.now():
            days_left = max(0, (expiry_date - datetime.now()).days)
            expiry_info = f"\n{ce('time')} Expires in: <b>{days_left} days</b>"
            return f"{ce('diamond')} Premium", expiry_info
        remove_subscription_db(user_id)
    return f"{ce('free')} Free User", expiry_info


def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get("process"):
        try:
            proc = psutil.Process(script_info["process"].pid)
            is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not is_running:
                _cleanup_script_entry(script_key, script_info)
            return is_running
        except psutil.NoSuchProcess:
            _cleanup_script_entry(script_key, script_info)
            return False
        except Exception as e:
            logger.error("Error checking process %s: %s", script_key, e)
            return False
    return False


def _cleanup_script_entry(script_key, script_info):
    try:
        log_file = script_info.get("log_file")
        if log_file and hasattr(log_file, "close") and not log_file.closed:
            log_file.close()
    except Exception as e:
        logger.error("Error closing log for %s: %s", script_key, e)
    bot_scripts.pop(script_key, None)


def kill_process_tree(process_info):
    pid = None
    script_key = process_info.get("script_key", "N/A")
    try:
        log_file = process_info.get("log_file")
        process = process_info.get("process")
        if process and hasattr(process, "pid"):
            pid = process.pid
            if pid:
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except Exception:
                            try:
                                child.kill()
                            except Exception:
                                pass
                    _, alive = psutil.wait_procs(children, timeout=2)
                    for proc in alive:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    try:
                        parent.terminate()
                        try:
                            parent.wait(timeout=2)
                        except psutil.TimeoutExpired:
                            parent.kill()
                    except psutil.NoSuchProcess:
                        pass
                except psutil.NoSuchProcess:
                    pass
        if log_file and hasattr(log_file, "close") and not log_file.closed:
            try:
                log_file.close()
            except Exception:
                pass
    except Exception as e:
        logger.error("Error killing process tree PID %s (%s): %s", pid, script_key, e, exc_info=True)


# ─────────────────────────────────────────────
# PACKAGE MAP & AUTO-INSTALL
# ─────────────────────────────────────────────

TELEGRAM_MODULES = {
    "telebot": "pyTelegramBotAPI",
    "telegram": "python-telegram-bot",
    "aiogram": "aiogram",
    "pyrogram": "pyrogram",
    "telethon": "telethon",
    "bs4": "beautifulsoup4",
    "requests": "requests",
    "pillow": "Pillow",
    "cv2": "opencv-python",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "pandas": "pandas",
    "numpy": "numpy",
    "flask": "Flask",
    "django": "Django",
    "sqlalchemy": "SQLAlchemy",
    "psutil": "psutil",
    "asyncio": None,
    "json": None,
    "datetime": None,
    "os": None,
    "sys": None,
    "re": None,
    "time": None,
    "math": None,
    "random": None,
    "logging": None,
    "threading": None,
    "subprocess": None,
    "zipfile": None,
    "tempfile": None,
    "shutil": None,
    "sqlite3": None,
    "atexit": None,
    "struct": None,
    "hashlib": None,
    "mimetypes": None,
}


def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    if package_name is None:
        return False
    if package_name in PIP_INSTALL_CACHE:
        return True
    try:
        bot.reply_to(
            message,
            f"{ce('package')} Installing <code>{escape_html(package_name)}</code>...",
            parse_mode="HTML",
        )
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", package_name],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="ignore",
        )
        if result.returncode == 0:
            PIP_INSTALL_CACHE.add(package_name)
            bot.reply_to(
                message,
                f"{ce('check')} <code>{escape_html(package_name)}</code> installed!",
                parse_mode="HTML",
            )
            return True
        bot.reply_to(
            message,
            f"{ce('cross')} Failed to install <code>{escape_html(package_name)}</code>:\n"
            f"<code>{escape_html((result.stderr or result.stdout)[:2000])}</code>",
            parse_mode="HTML",
        )
        return False
    except Exception as e:
        bot.reply_to(
            message,
            f"{ce('cross')} Install error: <code>{escape_html(e)}</code>",
            parse_mode="HTML",
        )
        return False


def attempt_install_npm(module_name, user_folder, message):
    if module_name in NPM_INSTALL_CACHE:
        return True
    try:
        bot.reply_to(message, f"{ce('package')} Installing Node package <code>{escape_html(module_name)}</code>...", parse_mode="HTML")
        result = subprocess.run(
            ["npm", "install", module_name, "--no-audit", "--no-fund"],
            capture_output=True,
            text=True,
            check=False,
            cwd=user_folder,
            encoding="utf-8",
            errors="ignore",
        )
        if result.returncode == 0:
            NPM_INSTALL_CACHE.add(module_name)
            bot.reply_to(
                message,
                f"{ce('check')} Node package <code>{escape_html(module_name)}</code> installed!",
                parse_mode="HTML",
            )
            return True
        bot.reply_to(
            message,
            f"{ce('cross')} Failed: <code>{escape_html((result.stderr or result.stdout)[:2000])}</code>",
            parse_mode="HTML",
        )
        return False
    except FileNotFoundError:
        bot.reply_to(message, f"{ce('cross')} npm not found. Ensure Node.js is installed.", parse_mode="HTML")
        return False
    except Exception as e:
        bot.reply_to(message, f"{ce('cross')} npm error: <code>{escape_html(e)}</code>", parse_mode="HTML")
        return False


# ─────────────────────────────────────────────
# SCRIPT RUNNING
# ─────────────────────────────────────────────

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(
            message_obj_for_reply,
            f"{ce('cross')} Failed to run <code>{file_name}</code> after {max_attempts} attempts.",
            parse_mode="HTML",
        )
        return

    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"{ce('cross')} Script <code>{file_name}</code> not found! Re-upload.", parse_mode="HTML")
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_proc = None
            try:
                check_proc = subprocess.Popen(
                    [sys.executable, script_path],
                    cwd=user_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                if return_code not in (None, 0):
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr or "")
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        if attempt_install_pip(module_name, message_obj_for_reply):
                            bot.reply_to(message_obj_for_reply, f"{ce('restart')} Retrying <code>{file_name}</code>...", parse_mode="HTML")
                            time.sleep(2)
                            threading.Thread(
                                target=run_script,
                                args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1),
                                daemon=True,
                            ).start()
                            return
                        bot.reply_to(message_obj_for_reply, f"{ce('cross')} Cannot run — install failed.", parse_mode="HTML")
                        return
                    error_output = (stderr or stdout or "Script exited with a non-zero status.")[:800]
                    bot.reply_to(
                        message_obj_for_reply,
                        f"{ce('cross')} Script error in <code>{file_name}</code>:\n<code>{error_output}</code>",
                        parse_mode="HTML",
                    )
                    return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, f"{ce('cross')} Python interpreter not found.", parse_mode="HTML")
                return
            except Exception as e:
                logger.error("Pre-check error %s: %s", script_key, e, exc_info=True)
                bot.reply_to(message_obj_for_reply, f"{ce('cross')} Pre-check error: {e}", parse_mode="HTML")
                return
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()

        log_file_path = safe_join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        try:
            log_file = open(log_file_path, "w", encoding="utf-8", errors="ignore")
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"{ce('cross')} Failed to open log file: {e}", parse_mode="HTML")
            return

        try:
            startupinfo, creationflags = get_windows_process_flags()
            process = subprocess.Popen(
                [sys.executable, script_path],
                cwd=user_folder,
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=creationflags,
                encoding="utf-8",
                errors="ignore",
            )
            bot_scripts[script_key] = {
                "process": process,
                "log_file": log_file,
                "file_name": file_name,
                "chat_id": message_obj_for_reply.chat.id,
                "script_owner_id": script_owner_id,
                "start_time": datetime.now(),
                "user_folder": user_folder,
                "type": "py",
                "script_key": script_key,
            }
            bot.reply_to(
                message_obj_for_reply,
                f"{ce('green_circle')} <b>{file_name}</b> is now running!\n{ce('id_num')} <code>PID: {process.pid}</code>",
                parse_mode="HTML",
            )
        except Exception as e:
            if log_file and not log_file.closed:
                log_file.close()
            bot.reply_to(message_obj_for_reply, f"{ce('cross')} Error starting <code>{file_name}</code>: {e}", parse_mode="HTML")
            if process and process.poll() is None:
                kill_process_tree({"process": process, "log_file": log_file, "script_key": script_key})
            bot_scripts.pop(script_key, None)
    except Exception as e:
        logger.error("Unexpected error running %s: %s", file_name, e, exc_info=True)
        bot.reply_to(message_obj_for_reply, f"{ce('cross')} Unexpected error: {e}", parse_mode="HTML")
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]


def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(
            message_obj_for_reply,
            f"{ce('cross')} Failed to run <code>{file_name}</code> after {max_attempts} attempts.",
            parse_mode="HTML",
        )
        return

    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(
                message_obj_for_reply,
                f"{ce('cross')} JS script <code>{file_name}</code> not found! Re-upload.",
                parse_mode="HTML",
            )
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_proc = None
            try:
                check_proc = subprocess.Popen(
                    ["node", script_path],
                    cwd=user_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                if return_code not in (None, 0):
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr or "")
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith(".") and not module_name.startswith("/"):
                            if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                                bot.reply_to(message_obj_for_reply, f"{ce('restart')} Retrying <code>{file_name}</code>...", parse_mode="HTML")
                                time.sleep(2)
                                threading.Thread(
                                    target=run_js_script,
                                    args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1),
                                    daemon=True,
                                ).start()
                                return
                            bot.reply_to(message_obj_for_reply, f"{ce('cross')} Cannot run — npm install failed.", parse_mode="HTML")
                            return
                    error_output = (stderr or stdout or "Script exited with a non-zero status.")[:800]
                    bot.reply_to(message_obj_for_reply, f"{ce('cross')} JS error:\n<code>{error_output}</code>", parse_mode="HTML")
                    return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, f"{ce('cross')} Node.js not found.", parse_mode="HTML")
                return
            except Exception as e:
                bot.reply_to(message_obj_for_reply, f"{ce('cross')} JS pre-check error: {e}", parse_mode="HTML")
                return
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()

        log_file_path = safe_join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        try:
            log_file = open(log_file_path, "w", encoding="utf-8", errors="ignore")
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"{ce('cross')} Failed to open log: {e}", parse_mode="HTML")
            return

        try:
            startupinfo, creationflags = get_windows_process_flags()
            process = subprocess.Popen(
                ["node", script_path],
                cwd=user_folder,
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=creationflags,
                encoding="utf-8",
                errors="ignore",
            )
            bot_scripts[script_key] = {
                "process": process,
                "log_file": log_file,
                "file_name": file_name,
                "chat_id": message_obj_for_reply.chat.id,
                "script_owner_id": script_owner_id,
                "start_time": datetime.now(),
                "user_folder": user_folder,
                "type": "js",
                "script_key": script_key,
            }
            bot.reply_to(
                message_obj_for_reply,
                f"{ce('green_circle')} <b>{file_name}</b> is now running!\n{ce('id_num')} <code>PID: {process.pid}</code>",
                parse_mode="HTML",
            )
        except FileNotFoundError:
            if log_file and not log_file.closed:
                log_file.close()
            bot.reply_to(message_obj_for_reply, f"{ce('cross')} node not found.", parse_mode="HTML")
            bot_scripts.pop(script_key, None)
        except Exception as e:
            if log_file and not log_file.closed:
                log_file.close()
            bot.reply_to(message_obj_for_reply, f"{ce('cross')} Error starting: {e}", parse_mode="HTML")
            if process and process.poll() is None:
                kill_process_tree({"process": process, "log_file": log_file, "script_key": script_key})
            bot_scripts.pop(script_key, None)
    except Exception as e:
        logger.error("Unexpected JS error %s: %s", file_name, e, exc_info=True)
        bot.reply_to(message_obj_for_reply, f"{ce('cross')} Unexpected error: {e}", parse_mode="HTML")
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]


# ─────────────────────────────────────────────
# BOT BROADCAST TO ALL HOSTED BOTS
# ─────────────────────────────────────────────

def broadcast_to_hosted_bots(message_text, admin_chat_id):
    results = []
    running_scripts = get_running_scripts_snapshot()
    if not running_scripts:
        bot.send_message(
            admin_chat_id,
            f"{ce('warning')} No running scripts found to broadcast to.",
            parse_mode="HTML",
        )
        return

    sent = 0
    failed = 0
    for _, script_info in running_scripts:
        try:
            process = script_info.get("process")
            if process and process.poll() is None and process.stdin:
                process.stdin.write(message_text + "\n")
                process.stdin.flush()
                sent += 1
                results.append(
                    f"{ce('check')} <code>{escape_html(script_info['file_name'])}</code> "
                    f"(User: <code>{script_info['script_owner_id']}</code>)"
                )
            else:
                failed += 1
        except Exception as e:
            failed += 1
            results.append(
                f"{ce('cross')} <code>{escape_html(script_info['file_name'])}</code> "
                f"— <code>{escape_html(e)}</code>"
            )

    summary = (
        f"{ce('broadcast')} <b>Hosted Bots Broadcast Complete</b>\n\n"
        f"{ce('green_circle')} <b>Sent to:</b> <code>{sent}</code> processes\n"
        f"{ce('red_circle')} <b>Failed:</b> <code>{failed}</code>\n\n"
        f"{ce('file')} <b>Details:</b>\n" + "\n".join(results[:20])
    )
    if len(results) > 20:
        summary += f"\n...and {len(results) - 20} more"
    bot.send_message(admin_chat_id, summary, parse_mode="HTML")

# ─────────────────────────────────────────────
# UI: KEYBOARD LAYOUTS
# ─────────────────────────────────────────────

COMMAND_BUTTONS_LAYOUT_USER = [
    ["📤 Upload File", "📂 My Files"],
    ["📤 Send Command", "📊 Statistics"],
    ["⚡ Speed Test", "📘 User Manual"],
    ["📞 Contact Owner"],
]

COMMAND_BUTTONS_LAYOUT_ADMIN = [
    ["📤 Upload File", "📂 My Files"],
    ["📤 Send Command", "📊 Statistics"],
    ["⚡ Speed Test", "📘 User Manual"],
    ["📞 Contact Owner", "👑 Admin Panel"],
]


def create_reply_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = COMMAND_BUTTONS_LAYOUT_ADMIN if user_id in admin_ids else COMMAND_BUTTONS_LAYOUT_USER
    for row in layout:
        markup.add(*[types.KeyboardButton(text) for text in row])
    return markup


def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 Upload File", callback_data="upload"),
        types.InlineKeyboardButton("📂 My Files", callback_data="check_files"),
    )
    markup.add(
        types.InlineKeyboardButton("📤 Send Command", callback_data="send_command"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="stats"),
    )
    markup.add(
        types.InlineKeyboardButton("⚡ Speed Test", callback_data="speed"),
        types.InlineKeyboardButton("📘 User Manual", callback_data="user_manual"),
    )
    markup.add(types.InlineKeyboardButton("📞 Contact Owner", url=f"https://t.me/{YOUR_USERNAME.replace('@', '')}"))
    if user_id in admin_ids:
        markup.add(types.InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel"))
    return markup


def create_admin_panel_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("👥 Total Users", callback_data="total_users"),
        types.InlineKeyboardButton("🟢 Active Bots", callback_data="active_bots"),
    )
    markup.row(
        types.InlineKeyboardButton("📊 Hosted Bots", callback_data="hosted_bots_overview"),
        types.InlineKeyboardButton("🚀 Mega Broadcast", callback_data="mega_broadcast"),
    )
    markup.row(
        types.InlineKeyboardButton("📢 Broadcast Users", callback_data="broadcast"),
        types.InlineKeyboardButton("🤖 Broadcast Bots", callback_data="broadcast_bots"),
    )
    markup.row(
        types.InlineKeyboardButton("💳 Subscriptions", callback_data="subscription"),
        types.InlineKeyboardButton("⏰ Expiring Subs", callback_data="expiring_subscriptions"),
    )
    markup.row(
        types.InlineKeyboardButton("👥 User List", callback_data="user_list"),
        types.InlineKeyboardButton("📊 System Stats", callback_data="system_stats"),
    )
    markup.row(
        types.InlineKeyboardButton("🔗 ForceJoin", callback_data="forcejoin_panel"),
        types.InlineKeyboardButton("🗑 Clean Files", callback_data="clean_orphan_files"),
    )
    markup.row(
        types.InlineKeyboardButton("📦 Backup DB", callback_data="get_db"),
        types.InlineKeyboardButton("♻️ Restore DB", callback_data="restore_db_info"),
    )
    markup.row(
        types.InlineKeyboardButton(
            "🔒 Lock Bot" if not bot_locked else "🔓 Unlock Bot",
            callback_data="lock_bot" if not bot_locked else "unlock_bot",
        ),
        types.InlineKeyboardButton("🟢 Run All Scripts", callback_data="run_all_scripts"),
    )
    markup.row(
        types.InlineKeyboardButton("🛑 Stop All Scripts", callback_data="stop_all_scripts"),
        types.InlineKeyboardButton("📋 List Subs", callback_data="list_subscribers"),
    )
    if user_id == OWNER_ID:
        markup.row(
            types.InlineKeyboardButton("➕ Add Admin", callback_data="add_admin"),
            types.InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin"),
        )
    markup.row(
        types.InlineKeyboardButton("📋 List Admins", callback_data="list_admins"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_panel"),
    )
    markup.row(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main"))
    return markup


def create_forcejoin_panel_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="fj_add"))
    markup.add(types.InlineKeyboardButton("📋 List Channels", callback_data="fj_list"))
    markup.add(types.InlineKeyboardButton("➖ Remove Channel", callback_data="fj_remove"))
    markup.add(types.InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
    return markup


def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 Stop", callback_data=build_named_callback("stop", script_owner_id, file_name)),
            types.InlineKeyboardButton("🔄 Restart", callback_data=build_named_callback("restart", script_owner_id, file_name)),
        )
        markup.row(
            types.InlineKeyboardButton("🗑️ Delete", callback_data=build_named_callback("delete", script_owner_id, file_name)),
            types.InlineKeyboardButton("📜 Logs", callback_data=build_named_callback("logs", script_owner_id, file_name)),
        )
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 Start", callback_data=build_named_callback("start", script_owner_id, file_name)),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=build_named_callback("delete", script_owner_id, file_name)),
        )
        markup.row(
            types.InlineKeyboardButton("📜 View Logs", callback_data=build_named_callback("logs", script_owner_id, file_name))
        )
    markup.add(types.InlineKeyboardButton("🔙 Back to Files", callback_data="check_files"))
    return markup


def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("➕ Add Subscription", callback_data="add_subscription"),
        types.InlineKeyboardButton("➖ Remove Subscription", callback_data="remove_subscription"),
    )
    markup.row(types.InlineKeyboardButton("🔍 Check Subscription", callback_data="check_subscription"))
    markup.row(types.InlineKeyboardButton("📋 List Subscribers", callback_data="list_subscribers"))
    markup.row(types.InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel"))
    return markup


def create_send_command_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("📝 Send to Process", callback_data="send_to_process"),
        types.InlineKeyboardButton("🗂️ View Logs", callback_data="view_all_logs"),
    )
    markup.row(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"))
    return markup

def handle_zip_file(downloaded_file_content, file_name_zip, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    temp_dir = None

    if user_id != OWNER_ID:
        is_safe, reason = scan_file_for_malware(downloaded_file_content, file_name_zip, user_id)
        if not is_safe:
            bot.reply_to(message, f"{ce('cross')} <b>Security Alert:</b> {reason}", parse_mode="HTML")
            return

    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        zip_name = safe_filename(file_name_zip) or "archive.zip"
        zip_path = safe_join(temp_dir, zip_name)
        with open(zip_path, "wb") as f:
            f.write(downloaded_file_content)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            if user_id != OWNER_ID:
                for member in zip_ref.infolist():
                    mname = member.filename.lower()
                    bad_exts = [".exe", ".dll", ".bat", ".cmd", ".scr", ".com"]
                    if any(mname.endswith(ext) for ext in bad_exts):
                        bot.reply_to(
                            message,
                            f"{ce('cross')} <b>Security Alert:</b> ZIP contains suspicious file: <code>{member.filename}</code>",
                            parse_mode="HTML",
                        )
                        return
                    member_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                    if member_path != os.path.abspath(temp_dir) and not member_path.startswith(os.path.abspath(temp_dir) + os.sep):
                        raise zipfile.BadZipFile(f"Unsafe path: {member.filename}")
            zip_ref.extractall(temp_dir)

        target_dir = temp_dir
        root_files = os.listdir(target_dir)
        if not any(f.endswith((".py", ".js")) for f in root_files):
            for root, dirs, files in os.walk(temp_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith("__")]
                if any(f.endswith((".py", ".js")) for f in files):
                    target_dir = root
                    break

        if target_dir != temp_dir:
            for item in os.listdir(target_dir):
                src = os.path.join(target_dir, item)
                dst = os.path.join(temp_dir, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)

        extracted_items = [item for item in os.listdir(temp_dir) if item != zip_name]
        py_files = [f for f in extracted_items if f.endswith(".py")]
        js_files = [f for f in extracted_items if f.endswith(".js")]
        req_file = "requirements.txt" if "requirements.txt" in extracted_items else None
        pkg_json = "package.json" if "package.json" in extracted_items else None

        if req_file:
            req_path = safe_join(temp_dir, req_file)
            bot.reply_to(message, f"{ce('package')} Installing Python dependencies...", parse_mode="HTML")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_path],
                    capture_output=True,
                    text=True,
                    check=False,
                    encoding="utf-8",
                    errors="ignore",
                )
                if result.returncode != 0:
                    bot.reply_to(
                        message,
                        f"{ce('cross')} Failed to install deps:\n<code>{(result.stderr or result.stdout)[:2000]}</code>",
                        parse_mode="HTML",
                    )
                    return
                bot.reply_to(message, f"{ce('check')} Python dependencies installed.", parse_mode="HTML")
            except Exception as e:
                bot.reply_to(message, f"{ce('cross')} Failed to install deps: <code>{e}</code>", parse_mode="HTML")
                return

        if pkg_json:
            bot.reply_to(message, f"{ce('package')} Installing Node dependencies...", parse_mode="HTML")
            try:
                result = subprocess.run(
                    ["npm", "install"],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=temp_dir,
                    encoding="utf-8",
                    errors="ignore",
                )
                if result.returncode != 0:
                    bot.reply_to(message, f"{ce('cross')} npm error: <code>{(result.stderr or result.stdout)[:2000]}</code>", parse_mode="HTML")
                    return
                bot.reply_to(message, f"{ce('check')} Node dependencies installed.", parse_mode="HTML")
            except Exception as e:
                bot.reply_to(message, f"{ce('cross')} npm error: {e}", parse_mode="HTML")
                return

        main_script_name = None
        file_type = None
        preferred_py = ["main.py", "bot.py", "app.py"]
        preferred_js = ["index.js", "main.js", "bot.js", "app.js"]
        for preferred in preferred_py:
            if preferred in py_files:
                main_script_name = preferred
                file_type = "py"
                break
        if not main_script_name:
            for preferred in preferred_js:
                if preferred in js_files:
                    main_script_name = preferred
                    file_type = "js"
                    break
        if not main_script_name:
            if py_files:
                main_script_name = py_files[0]
                file_type = "py"
            elif js_files:
                main_script_name = js_files[0]
                file_type = "js"
        if not main_script_name:
            bot.reply_to(message, f"{ce('cross')} No .py or .js script found in archive!", parse_mode="HTML")
            return

        for item_name in extracted_items:
            src = safe_join(temp_dir, item_name)
            dst = safe_join(user_folder, item_name)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            elif os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)

        save_user_file(user_id, main_script_name, file_type)
        main_script_path = safe_join(user_folder, main_script_name)
        bot.reply_to(message, f"{ce('check')} Archive extracted! Starting <code>{main_script_name}</code>...", parse_mode="HTML")

        if file_type == "py":
            threading.Thread(target=run_script, args=(main_script_path, user_id, user_folder, main_script_name, message), daemon=True).start()
        elif file_type == "js":
            threading.Thread(target=run_js_script, args=(main_script_path, user_id, user_folder, main_script_name, message), daemon=True).start()
    except zipfile.BadZipFile as e:
        bot.reply_to(message, f"{ce('cross')} Invalid or corrupted ZIP: {e}", parse_mode="HTML")
    except Exception as e:
        logger.error("Error processing zip for %s: %s", user_id, e, exc_info=True)
        bot.reply_to(message, f"{ce('cross')} Error processing zip: {e}", parse_mode="HTML")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error("Failed to clean temp dir: %s", e)


def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, "js")
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message), daemon=True).start()
    except Exception as e:
        bot.reply_to(message, f"{ce('cross')} Error processing JS: {e}", parse_mode="HTML")


def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, "py")
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message), daemon=True).start()
    except Exception as e:
        bot.reply_to(message, f"{ce('cross')} Error processing Python file: {e}", parse_mode="HTML")


# ─────────────────────────────────────────────
# SEND COMMAND & LOG FUNCTIONS
# ─────────────────────────────────────────────

def _logic_send_command(message):
    user_id = message.from_user.id
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Bot is currently locked by admin.", parse_mode="HTML")
        return
    bot.reply_to(message, f"{ce('laptop')} <b>Send Command Options:</b>", reply_markup=create_send_command_menu(), parse_mode="HTML")


def send_to_process_init(message):
    user_id = message.from_user.id
    user_running = [
        (sk, si)
        for sk, si in get_running_scripts_snapshot()
        if user_id == si["script_owner_id"] or user_id in admin_ids
    ]
    if not user_running:
        bot.reply_to(message, f"{ce('cross')} No running scripts found.", parse_mode="HTML")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for _, script_info in user_running:
        btn_text = f"🟢 {script_info['file_name']} (User: {script_info['script_owner_id']})"
        markup.add(
            types.InlineKeyboardButton(
                btn_text,
                callback_data=build_named_callback(
                    "sendcmd_select",
                    script_info["script_owner_id"],
                    script_info["file_name"],
                ),
            )
        )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="send_command"))
    bot.reply_to(message, "📝 Select a running script:", reply_markup=markup)


def process_send_command(message, script_key):
    if script_key not in bot_scripts:
        bot.reply_to(message, f"{ce('cross')} Script is no longer running.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Please send a text command only."):
        return
    script_info = bot_scripts[script_key]
    command_text = message.text
    try:
        process = script_info["process"]
        if process and process.poll() is None and process.stdin:
            process.stdin.write(command_text + "\n")
            process.stdin.flush()
            bot.reply_to(
                message,
                f"{ce('check')} Command sent to <code>{script_info['file_name']}</code>:\n<code>{command_text}</code>",
                parse_mode="HTML",
            )
        else:
            bot.reply_to(message, f"{ce('cross')} Script <code>{script_info['file_name']}</code> is not running.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"{ce('cross')} Error sending command: {e}", parse_mode="HTML")


def view_all_logs(message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    user_logs = []
    if os.path.exists(user_folder):
        for file_name in os.listdir(user_folder):
            if file_name.endswith(".log"):
                log_path = safe_join(user_folder, file_name)
                user_logs.append((file_name, os.path.getsize(log_path), log_path))
    if not user_logs:
        bot.reply_to(message, f"{ce('info')} No log files found.", parse_mode="HTML")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for log_file, size, _ in sorted(user_logs):
        size_kb = size / 1024
        markup.add(
            types.InlineKeyboardButton(
                f"📄 {log_file} ({size_kb:.1f} KB)",
                callback_data=build_named_callback("viewlog", user_id, log_file),
            )
        )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="send_command"))
    bot.reply_to(message, f"{ce('file')} <b>Your Log Files:</b>", reply_markup=markup, parse_mode="HTML")


def send_log_file(message, log_path, log_filename):
    try:
        file_size = os.path.getsize(log_path)
        if file_size > 50 * 1024 * 1024:
            bot.reply_to(message, f"{ce('cross')} Log too large ({file_size / 1024 / 1024:.1f} MB).", parse_mode="HTML")
            return
        with open(log_path, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"📜 {log_filename}")
    except Exception as e:
        bot.reply_to(message, f"{ce('cross')} Error sending log: {e}", parse_mode="HTML")


# ─────────────────────────────────────────────
# LOGIC FUNCTIONS
# ─────────────────────────────────────────────

def _logic_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name or "User"
    user_username = message.from_user.username

    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, f"{ce('lock')} Bot is currently locked by admin. Try later.", parse_mode="HTML")
        return

    not_joined = check_user_joined_channels(user_id)
    if not_joined:
        send_forcejoin_message(chat_id, not_joined)
        return

    if user_id not in active_users:
        add_active_user(user_id)
        try:
            owner_notif = (
                f"{ce('party')} <b>New User Joined!</b>\n\n"
                f"{ce('user')} <b>Name:</b> {user_name}\n"
                f"{ce('id_num')} <b>Username:</b> {format_username(user_username)}\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>"
            )
            bot.send_message(OWNER_ID, owner_notif, parse_mode="HTML")
        except Exception as e:
            logger.error("Failed to notify owner: %s", e)

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float("inf") else "∞ Unlimited"
    user_status, expiry_info = get_user_status(user_id)

    welcome_msg = (
        f"{ce('crown')} <b>{BOT_NAME}</b> <i>Hosting Control Hub</i>\n\n"
        f"{ce('sparkle')} Hey, <b>{user_name}!</b> Welcome to your bot hosting dashboard.\n\n"
        f"{ce('id_num')} <b>ID:</b> <code>{user_id}</code>\n"
        f"{ce('user')} <b>Username:</b> <code>{format_username(user_username)}</code>\n"
        f"{ce('star')} <b>Status:</b> {user_status}{expiry_info}\n"
        f"{ce('folder_open')} <b>Files:</b> <code>{current_files} / {limit_str}</code>\n\n"
        f"{ce('fire')} <b>What you can do here:</b>\n"
        f"{ce('arrow_right')} Host <code>.py</code>, <code>.js</code>, and <code>.zip</code> projects\n"
        f"{ce('arrow_right')} Auto-install many Python and Node dependencies\n"
        f"{ce('arrow_right')} Control logs, restart flows, and live process commands\n"
        f"{ce('arrow_right')} Open <b>User Manual</b> anytime for setup help\n\n"
        f"{ce('play')} Choose an option below to continue."
    )

    reply_markup = create_reply_keyboard(user_id)
    try:
        bot.send_photo(chat_id, WELCOME_IMAGE_URL, caption=welcome_msg, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try:
            bot.send_message(chat_id, welcome_msg, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.error("Fallback welcome failed: %s", e)


def _logic_upload_file(message):
    user_id = message.from_user.id
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, f"{ce('lock')} Bot is locked. Cannot accept files.", parse_mode="HTML")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float("inf") else "Unlimited"
        bot.reply_to(
            message,
            f"{ce('warning')} File limit reached: <code>{current_files}/{limit_str}</code>\nDelete some files first.",
            parse_mode="HTML",
        )
        return
    bot.reply_to(
        message,
        f"{ce('upload')} <b>Upload Your Script</b>\n\n"
        "Supported formats:\n"
        f"{ce('arrow_right')} Python <code>.py</code>\n"
        f"{ce('arrow_right')} JavaScript <code>.js</code>\n"
        f"{ce('arrow_right')} Archive <code>.zip</code>\n\n"
        "Just send the file now!",
        parse_mode="HTML",
    )


def _logic_check_files(message):
    user_id = message.from_user.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 Upload File", callback_data="upload"))
        bot.reply_to(
            message,
            f"{ce('folder_open')} <b>Your Files</b>\n\nNo files uploaded yet.\nUpload a script to get started!",
            reply_markup=markup,
            parse_mode="HTML",
        )
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    running_count = 0
    for file_name, file_type in sorted(user_files_list):
        running = is_bot_running(user_id, file_name)
        if running:
            running_count += 1
        status_icon = "🟢" if running else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_icon} {file_name} [{file_type.upper()}]", callback_data=build_named_callback("file", user_id, file_name)))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"))
    bot.reply_to(
        message,
        f"{ce('folder_open')} <b>Your Files</b> — <code>{running_count}/{len(user_files_list)}</code> running\n\nTap a file to manage it:",
        reply_markup=markup,
        parse_mode="HTML",
    )


def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    start_time = time.time()
    wait_msg = bot.reply_to(message, f"{ce('lightning')} Testing speed...", parse_mode="HTML")
    try:
        response_time = round((time.time() - start_time) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID:
            user_level = f"{ce('crown')} Owner"
        elif user_id in admin_ids:
            user_level = f"{ce('admin')} Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get("expiry", datetime.min) > datetime.now():
            user_level = f"{ce('diamond')} Premium"
        else:
            user_level = f"{ce('free')} Free User"
        quality = "🟢 Excellent" if response_time < 300 else ("🟡 Good" if response_time < 800 else "🔴 Slow")
        speed_msg = (
            f"{ce('lightning')} <b>Speed Test Results</b>\n\n"
            f"{ce('time')} <b>Response:</b> <code>{response_time} ms</code>\n"
            f"{ce('chart')} <b>Quality:</b> {quality}\n"
            f"{ce('lock')} <b>Bot Status:</b> {status}\n"
            f"{ce('user')} <b>Your Level:</b> {user_level}\n"
            f"{ce('sparkle')} <b>Threads Ready:</b> <code>{len(get_running_scripts_snapshot())}</code> active hosted bots checked"
        )
        bot.edit_message_text(speed_msg, chat_id, wait_msg.message_id, parse_mode="HTML")
    except Exception as e:
        logger.error("Speed test error: %s", e)


def _logic_contact_owner(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📞 Contact Owner", url=f"https://t.me/{YOUR_USERNAME.replace('@', '')}"))
    bot.reply_to(message, f"{ce('phone')} Contact the bot owner:", reply_markup=markup, parse_mode="HTML")


def _logic_user_manual(message_or_call):
    manual_text = (
        f"{ce('bookmark')} <b>{BOT_NAME} User Manual</b>\n\n"
        f"{ce('upload')} <b>1. Upload:</b> Send <code>.py</code>, <code>.js</code>, or <code>.zip</code> files.\n"
        f"{ce('folder_open')} <b>2. Manage:</b> Open <b>My Files</b> to start, stop, restart, delete, or view logs.\n"
        f"{ce('package')} <b>3. ZIP Support:</b> The host auto-detects the main file and installs dependencies when possible.\n"
        f"{ce('shield')} <b>4. Safety:</b> Suspicious uploads are blocked for protection.\n"
        f"{ce('laptop')} <b>5. Commands:</b> Use <b>Send Command</b> to write to running bot processes.\n"
        f"{ce('warning')} <b>6. Limits:</b> Free, premium, admin, and owner accounts have different file limits.\n"
        f"{ce('lightning')} <b>7. Speed Tip:</b> Keep ZIPs clean and avoid unnecessary files for faster startup.\n\n"
        f"{ce('sparkle')} <b>Quick Tip:</b> If you upload a ZIP, prefer files like <code>main.py</code>, <code>bot.py</code>, or <code>index.js</code>."
    )
    send_or_edit_context(
        message_or_call,
        manual_text,
        reply_markup=create_main_menu_inline(message_or_call.from_user.id),
        parse_mode="HTML",
    )


def _logic_subscriptions_panel(message_or_call):
    if isinstance(message_or_call, types.CallbackQuery):
        user_id = message_or_call.from_user.id
        chat_id = message_or_call.message.chat.id
        send = lambda text, **kw: bot.send_message(chat_id, text, **kw)
    else:
        user_id = message_or_call.from_user.id
        send = lambda text, **kw: bot.reply_to(message_or_call, text, **kw)
    if user_id not in admin_ids:
        send(f"{ce('warning')} Admin permissions required.", parse_mode="HTML")
        return
    send(f"{ce('star')} <b>Subscription Management</b>", reply_markup=create_subscription_menu(), parse_mode="HTML")


def _logic_statistics(message):
    user_id = message.from_user.id
    now = datetime.now()
    total_users = len(active_users)
    user_files_snapshot = {uid: list(files) for uid, files in list(user_files.items())}
    total_files_records = sum(len(files) for files in user_files_snapshot.values())
    running_bots_count = count_running_scripts()
    user_running_bots = count_running_scripts(user_id)
    premium_users = sum(1 for info in user_subscriptions.values() if info.get("expiry", datetime.min) > now)

    stats_msg = (
        f"{ce('chart')} <b>Bot Statistics</b>\n\n"
        f"{ce('users')} <b>Total Users:</b> <code>{total_users}</code>\n"
        f"{ce('folder_open')} <b>File Records:</b> <code>{total_files_records}</code>\n"
        f"{ce('green_circle')} <b>Active Scripts:</b> <code>{running_bots_count}</code>\n"
        f"{ce('robot')} <b>Your Scripts:</b> <code>{user_running_bots}</code>\n"
        f"{ce('diamond')} <b>Premium Users:</b> <code>{premium_users}</code>\n"
    )
    if user_id in admin_ids:
        stats_msg += (
            f"{ce('lock')} <b>Bot Status:</b> <code>{'Locked' if bot_locked else 'Unlocked'}</code>\n"
            f"{ce('admin')} <b>Total Admins:</b> <code>{len(admin_ids)}</code>\n"
            f"{ce('globe')} <b>ForceJoin Channels:</b> <code>{len([c for c in forcejoin_channels if c['enabled']])}</code>\n"
            f"{ce('robot')} <b>Active Bot Owners:</b> <code>{len({si['script_owner_id'] for _, si in get_running_scripts_snapshot()})}</code>"
        )
    bot.reply_to(message, stats_msg, parse_mode="HTML")


def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin permissions required.", parse_mode="HTML")
        return
    msg = bot.reply_to(
        message,
        f"{ce('broadcast')} Send the message to broadcast to all users.\nType /cancel to abort.",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, process_broadcast_message)


def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin permissions required.", parse_mode="HTML")
        return
    global bot_locked
    bot_locked = not bot_locked
    status = "🔒 Locked" if bot_locked else "🔓 Unlocked"
    bot.reply_to(message, f"{ce('lock')} Bot is now <b>{status}</b>", parse_mode="HTML")


def _logic_admin_panel(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin permissions required.", parse_mode="HTML")
        return
    bot.reply_to(
        message,
        f"{ce('admin')} <b>Advanced Admin Panel</b>\n\n"
        f"{ce('sparkle')} Control users, broadcasts, hosted bots, backups, and safety tools from one place.",
        reply_markup=create_admin_panel_markup(user_id),
        parse_mode="HTML",
    )


def _logic_run_all_scripts(message_or_call):
    if isinstance(message_or_call, types.Message):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.chat.id
        reply_func = lambda text, **kw: bot.reply_to(message_or_call, text, **kw)
        admin_message_obj = message_or_call
    elif isinstance(message_or_call, types.CallbackQuery):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.message.chat.id
        bot.answer_callback_query(message_or_call.id)
        reply_func = lambda text, **kw: bot.send_message(admin_chat_id, text, **kw)
        admin_message_obj = message_or_call.message
    else:
        return

    if admin_user_id not in admin_ids:
        reply_func(f"{ce('warning')} Admin permissions required.", parse_mode="HTML")
        return

    reply_func(f"{ce('time')} Starting all user scripts...", parse_mode="HTML")
    started_count = 0
    skipped_files = 0
    error_files_details = []

    for target_user_id, files_for_user in dict(user_files).items():
        if not files_for_user:
            continue
        user_folder = get_user_folder(target_user_id)
        for file_name, file_type in files_for_user:
            if is_bot_running(target_user_id, file_name):
                continue
            file_path = safe_join(user_folder, file_name)
            if os.path.exists(file_path):
                try:
                    if file_type == "py":
                        threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj), daemon=True).start()
                    elif file_type == "js":
                        threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj), daemon=True).start()
                    else:
                        error_files_details.append(f"<code>{file_name}</code> - Unknown type")
                        skipped_files += 1
                        continue
                    started_count += 1
                    time.sleep(RUN_ALL_START_DELAY)
                except Exception:
                    error_files_details.append(f"<code>{file_name}</code> - Error")
                    skipped_files += 1
            else:
                error_files_details.append(f"<code>{file_name}</code> - Not found")
                skipped_files += 1

    summary = (
        f"{ce('check')} <b>Run All Scripts Complete</b>\n\n"
        f"{ce('play')} <b>Started:</b> <code>{started_count}</code>\n"
        f"{ce('warning')} <b>Skipped:</b> <code>{skipped_files}</code>\n"
    )
    if error_files_details:
        summary += "\nDetails:\n" + "\n".join(f"  • {err}" for err in error_files_details[:5])
    reply_func(summary, parse_mode="HTML")


def _logic_stop_all_scripts(admin_user_id, admin_chat_id):
    if admin_user_id not in admin_ids:
        bot.send_message(admin_chat_id, f"{ce('warning')} Admin permissions required.", parse_mode="HTML")
        return
    stopped = 0
    for key in list(bot_scripts.keys()):
        if key in bot_scripts:
            kill_process_tree(bot_scripts[key])
            del bot_scripts[key]
            stopped += 1
    bot.send_message(
        admin_chat_id,
        f"{ce('red_circle')} <b>Stopped All Scripts</b>\n\n{ce('check')} <b>Scripts stopped:</b> <code>{stopped}</code>",
        parse_mode="HTML",
    )


def _logic_system_stats(chat_id):
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk_root = os.path.splitdrive(BASE_DIR)[0] + os.sep if os.name == "nt" else "/"
        disk = psutil.disk_usage(disk_root)
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        running_scripts = count_running_scripts()
        stats = (
            f"{ce('monitor')} <b>System Statistics</b>\n\n"
            f"{ce('lightning')} <b>CPU Usage:</b> <code>{cpu}%</code>\n"
            f"{ce('chart')} <b>RAM:</b> <code>{ram.used // 1024 // 1024} MB / {ram.total // 1024 // 1024} MB ({ram.percent}%)</code>\n"
            f"{ce('folder')} <b>Disk:</b> <code>{disk.used // 1024 // 1024 // 1024} GB / {disk.total // 1024 // 1024 // 1024} GB ({disk.percent}%)</code>\n"
            f"{ce('time')} <b>Uptime:</b> <code>{uptime_str}</code>\n"
            f"{ce('robot')} <b>Running Scripts:</b> <code>{running_scripts}</code>\n"
            f"{ce('users')} <b>Total Users:</b> <code>{len(active_users)}</code>\n"
            f"{ce('diamond')} <b>Subscribers:</b> <code>{len(user_subscriptions)}</code>"
        )
        bot.send_message(chat_id, stats, parse_mode="HTML")
    except Exception as e:
        bot.send_message(chat_id, f"{ce('cross')} Error getting system stats: {e}", parse_mode="HTML")


def _logic_user_list(chat_id, admin_user_id):
    if admin_user_id not in admin_ids:
        bot.send_message(chat_id, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    user_list_parts = []
    for uid in list(active_users)[:50]:
        if uid == OWNER_ID:
            status = ce("crown")
        elif uid in admin_ids:
            status = ce("admin")
        elif uid in user_subscriptions and user_subscriptions[uid].get("expiry", datetime.min) > datetime.now():
            status = ce("diamond")
        else:
            status = ""
        file_count = get_user_file_count(uid)
        running = sum(1 for fn, _ in user_files.get(uid, []) if is_bot_running(uid, fn))
        user_list_parts.append(f"{status} <code>{uid}</code> — {file_count} files, {running} running")
    msg = f"{ce('users')} <b>User List</b> ({len(active_users)} total)\n\n" + "\n".join(user_list_parts)
    if len(active_users) > 50:
        msg += f"\n\n...and {len(active_users) - 50} more users"
    bot.send_message(chat_id, msg, parse_mode="HTML")


def _logic_clean_orphan_files(chat_id, admin_user_id):
    if admin_user_id not in admin_ids:
        bot.send_message(chat_id, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    removed = 0
    for uid, files in list(user_files.items()):
        user_folder = get_user_folder(uid)
        for fn, _ in list(files):
            file_path = safe_join(user_folder, fn)
            if not os.path.exists(file_path):
                remove_user_file_db(uid, fn)
                removed += 1
    bot.send_message(chat_id, f"{ce('trash')} <b>Cleanup Complete</b>\n\nRemoved <code>{removed}</code> orphan file records.", parse_mode="HTML")


# ─────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def command_send_welcome(message):
    _logic_send_welcome(message)


@bot.message_handler(commands=["status"])
def command_show_status(message):
    _logic_statistics(message)


@bot.message_handler(commands=["ping"])
def ping(message):
    start_ping = time.time()
    msg = bot.reply_to(message, f"{ce('lightning')} Pong!")
    latency = round((time.time() - start_ping) * 1000, 2)
    bot.edit_message_text(f"{ce('lightning')} Pong! <code>{latency} ms</code>", message.chat.id, msg.message_id, parse_mode="HTML")


@bot.message_handler(commands=["getdb"])
def command_get_db(message):
    _logic_get_db(message)


@bot.message_handler(commands=["restoredb"])
def command_restore_db(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin access required.", parse_mode="HTML")
        return
    awaiting_db_restore.add(user_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_db_restore"))
    bot.reply_to(
        message,
        f"{ce('package')} <b>Database Restore</b>\n\n"
        "Please send the <code>.db</code> backup file now.\n\n"
        f"{ce('warning')} <b>Warning:</b> This will replace the current database!\n"
        "All running scripts will be stopped during the restore.",
        reply_markup=markup,
        parse_mode="HTML",
    )


@bot.message_handler(commands=["addchannel"])
def cmd_add_forcejoin_channel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    msg = bot.reply_to(
        message,
        f"{ce('globe')} <b>Add ForceJoin Channel</b>\n\n"
        "Send the channel username (e.g., <code>@mychannel</code>)\n"
        "or forward a message from the channel.\n\nType /cancel to abort.",
        parse_mode="HTML",
    )
    awaiting_forcejoin_add.add(message.from_user.id)
    bot.register_next_step_handler(msg, process_add_forcejoin_channel)


@bot.message_handler(commands=["removechannel"])
def cmd_remove_forcejoin_channel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    _show_remove_forcejoin(message.chat.id)


@bot.message_handler(commands=["channels"])
def cmd_list_channels(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    _show_forcejoin_list(message.chat.id)


@bot.message_handler(commands=["broadcastbots"])
def cmd_broadcast_bots(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    msg = bot.reply_to(
        message,
        f"{ce('broadcast')} <b>Broadcast to Hosted Bots</b>\n\n"
        "Send a command/message to send to all running hosted bot processes via stdin.\nType /cancel to abort.",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, process_broadcast_bots_message)


def process_broadcast_bots_message(message):
    if message.from_user.id not in admin_ids:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Cancelled.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Please send text only."):
        return
    threading.Thread(target=broadcast_to_hosted_bots, args=(message.text, message.chat.id), daemon=True).start()


BUTTON_TEXT_TO_LOGIC = {
    "📤 Upload File": _logic_upload_file,
    "📂 My Files": _logic_check_files,
    "⚡ Speed Test": _logic_bot_speed,
    "📘 User Manual": _logic_user_manual,
    "📤 Send Command": _logic_send_command,
    "📞 Contact Owner": _logic_contact_owner,
    "📊 Statistics": _logic_statistics,
    "💳 Subscriptions": _logic_subscriptions_panel,
    "📢 Broadcast": _logic_broadcast_init,
    "🔒 Lock Bot": _logic_toggle_lock_bot,
    "🟢 Run All Scripts": _logic_run_all_scripts,
    "👑 Admin Panel": _logic_admin_panel,
}


@bot.message_handler(func=lambda message: bool(message.text) and message.text in BUTTON_TEXT_TO_LOGIC)
def handle_button_text(message):
    logic_func = BUTTON_TEXT_TO_LOGIC.get(message.text)
    if logic_func:
        logic_func(message)


@bot.message_handler(commands=["uploadfile"])
def cmd_upload(message):
    _logic_upload_file(message)


@bot.message_handler(commands=["checkfiles", "myfiles"])
def cmd_checkfiles(message):
    _logic_check_files(message)


@bot.message_handler(commands=["botspeed", "speed"])
def cmd_speed(message):
    _logic_bot_speed(message)


@bot.message_handler(commands=["sendcommand"])
def cmd_sendcommand(message):
    _logic_send_command(message)


@bot.message_handler(commands=["contactowner"])
def cmd_contact(message):
    _logic_contact_owner(message)


@bot.message_handler(commands=["manual", "helpguide"])
def cmd_manual(message):
    _logic_user_manual(message)


@bot.message_handler(commands=["subscriptions"])
def cmd_subscriptions(message):
    _logic_subscriptions_panel(message)


@bot.message_handler(commands=["statistics", "stats"])
def cmd_statistics(message):
    _logic_statistics(message)


@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    _logic_broadcast_init(message)


@bot.message_handler(commands=["megabroadcast"])
def cmd_megabroadcast(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    prompt = bot.reply_to(
        message,
        f"{ce('broadcast')} <b>Mega Broadcast</b>\n\n"
        f"{ce('users')} Sends to all registered users.\n"
        f"{ce('robot')} Also pushes the same text to all running hosted bots.\n\n"
        f"{ce('warning')} Text only. Type /cancel to abort.",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(prompt, process_mega_broadcast_message)


@bot.message_handler(commands=["lockbot"])
def cmd_lock(message):
    _logic_toggle_lock_bot(message)


@bot.message_handler(commands=["adminpanel"])
def cmd_admin(message):
    _logic_admin_panel(message)


@bot.message_handler(commands=["runallscripts", "runningallcode"])
def cmd_runall(message):
    _logic_run_all_scripts(message)


@bot.message_handler(commands=["stopall"])
def cmd_stopall(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    _logic_stop_all_scripts(message.from_user.id, message.chat.id)


def _logic_total_users(message_or_call):
    now = datetime.now()
    total_users = len(active_users)
    premium_users = sum(1 for info in user_subscriptions.values() if info.get("expiry", datetime.min) > now)
    active_bot_owners = len({si["script_owner_id"] for _, si in get_running_scripts_snapshot()})
    text = (
        f"{ce('users')} <b>Total Users Dashboard</b>\n\n"
        f"{ce('users')} <b>Total Users:</b> <code>{total_users}</code>\n"
        f"{ce('diamond')} <b>Premium Users:</b> <code>{premium_users}</code>\n"
        f"{ce('admin')} <b>Total Admins:</b> <code>{len(admin_ids)}</code>\n"
        f"{ce('robot')} <b>Running Hosted Bots:</b> <code>{count_running_scripts()}</code>\n"
        f"{ce('user')} <b>Owners With Active Bots:</b> <code>{active_bot_owners}</code>"
    )
    send_or_edit_context(
        message_or_call,
        text,
        reply_markup=create_admin_panel_markup(message_or_call.from_user.id),
        parse_mode="HTML",
    )


def _logic_hosted_bots_overview(message_or_call):
    entries = []
    total_files = 0
    for uid, files in sorted(list(user_files.items()), key=lambda item: item[0]):
        if not files:
            continue
        total = len(files)
        running = sum(1 for file_name, _ in files if is_bot_running(uid, file_name))
        total_files += total
        entries.append((running, total, uid))

    entries.sort(key=lambda item: (-item[0], -item[1], item[2]))
    lines = [
        f"{ce('chart')} <b>Hosted Bot Overview</b>",
        "",
        f"{ce('folder_open')} <b>Total Uploaded Bots:</b> <code>{total_files}</code>",
        f"{ce('green_circle')} <b>Running Bots:</b> <code>{count_running_scripts()}</code>",
        f"{ce('users')} <b>Users With Files:</b> <code>{len(entries)}</code>",
        f"{ce('users')} <b>Total Registered Users:</b> <code>{len(active_users)}</code>",
        "",
    ]
    if entries:
        for running, total, uid in entries[:20]:
            lines.append(f"{ce('user')} <code>{uid}</code> — <b>{running}</b>/<b>{total}</b> running")
        if len(entries) > 20:
            lines.append("")
            lines.append(f"...and {len(entries) - 20} more users")
    else:
        lines.append(f"{ce('info')} No hosted bots uploaded yet.")

    send_or_edit_context(
        message_or_call,
        "\n".join(lines),
        reply_markup=create_admin_panel_markup(message_or_call.from_user.id),
        parse_mode="HTML",
    )


def _logic_expiring_subscriptions(message_or_call, days=7):
    now = datetime.now()
    cutoff = now + timedelta(days=days)
    expiring = []
    for uid, sub_info in list(user_subscriptions.items()):
        expiry = sub_info.get("expiry")
        if expiry and now < expiry <= cutoff:
            expiring.append((expiry, uid))

    expiring.sort()
    if not expiring:
        text = (
            f"{ce('calendar')} <b>Expiring Subscriptions</b>\n\n"
            f"{ce('check')} No subscriptions expiring in the next <b>{days} days</b>."
        )
    else:
        lines = [
            f"{ce('calendar')} <b>Expiring Subscriptions</b>\n",
            f"{ce('time')} Next <b>{days} days</b>:\n",
        ]
        for expiry, uid in expiring[:30]:
            remaining = max(0, (expiry - now).days)
            lines.append(
                f"{ce('diamond')} <code>{uid}</code> — <code>{expiry:%Y-%m-%d %H:%M}</code> ({remaining} days left)"
            )
        if len(expiring) > 30:
            lines.append(f"\n...and {len(expiring) - 30} more users")
        text = "\n".join(lines)

    send_or_edit_context(
        message_or_call,
        text,
        reply_markup=create_admin_panel_markup(message_or_call.from_user.id),
        parse_mode="HTML",
    )


def _logic_active_bots_panel(message_or_call):
    running_scripts = get_running_scripts_snapshot()
    active_owners = sorted({script_info["script_owner_id"] for _, script_info in running_scripts})
    lines = [
        f"{ce('green_circle')} <b>Active Bots Monitor</b>",
        "",
        f"{ce('robot')} <b>Total Running Bots:</b> <code>{len(running_scripts)}</code>",
        f"{ce('users')} <b>Owners With Active Bots:</b> <code>{len(active_owners)}</code>",
        f"{ce('users')} <b>Total Registered Users:</b> <code>{len(active_users)}</code>",
        "",
    ]
    if running_scripts:
        for _, script_info in running_scripts[:ACTIVE_BOT_PANEL_LIMIT]:
            start_time = script_info.get("start_time")
            uptime = "unknown"
            if start_time:
                uptime = str(datetime.now() - start_time).split(".")[0]
            lines.append(
                f"{ce('play')} <code>{escape_html(script_info['file_name'])}</code> "
                f"• user <code>{script_info['script_owner_id']}</code> "
                f"• uptime <code>{uptime}</code>"
            )
        if len(running_scripts) > ACTIVE_BOT_PANEL_LIMIT:
            lines.append("")
            lines.append(f"...and {len(running_scripts) - ACTIVE_BOT_PANEL_LIMIT} more active bots")
    else:
        lines.append(f"{ce('info')} No hosted bots are running right now.")

    send_or_edit_context(
        message_or_call,
        "\n".join(lines),
        reply_markup=create_admin_panel_markup(message_or_call.from_user.id),
        parse_mode="HTML",
    )


def _execute_mega_broadcast(message_text, admin_chat_id):
    users_sent = 0
    users_failed = 0
    users_blocked = 0
    bot_sent = 0
    bot_failed = 0
    start_exec = time.time()

    running_scripts = get_running_scripts_snapshot()
    for _, script_info in running_scripts:
        try:
            process = script_info.get("process")
            if process and process.poll() is None and process.stdin:
                process.stdin.write(message_text + "\n")
                process.stdin.flush()
                bot_sent += 1
            else:
                bot_failed += 1
        except Exception:
            bot_failed += 1

    users_to_broadcast = list(active_users)
    for index, user_id_bc in enumerate(users_to_broadcast):
        try:
            bot.send_message(user_id_bc, message_text, parse_mode="HTML")
            users_sent += 1
        except telebot.apihelper.ApiTelegramException as e:
            err_desc = str(e).lower()
            if any(token in err_desc for token in ["bot was blocked", "user is deactivated", "chat not found", "kicked", "restricted"]):
                users_blocked += 1
            else:
                users_failed += 1
        except Exception:
            users_failed += 1

        if (index + 1) % BROADCAST_BATCH_SIZE == 0 and index < len(users_to_broadcast) - 1:
            time.sleep(BROADCAST_BATCH_DELAY)

    duration = round(time.time() - start_exec, 2)
    result_msg = (
        f"{ce('broadcast')} <b>Mega Broadcast Complete</b>\n\n"
        f"{ce('users')} <b>User Messages Sent:</b> <code>{users_sent}</code>\n"
        f"{ce('cross')} <b>User Failures:</b> <code>{users_failed}</code>\n"
        f"{ce('no')} <b>User Blocked/Inactive:</b> <code>{users_blocked}</code>\n"
        f"{ce('robot')} <b>Hosted Bots Reached:</b> <code>{bot_sent}</code>\n"
        f"{ce('warning')} <b>Hosted Bot Failures:</b> <code>{bot_failed}</code>\n"
        f"{ce('time')} <b>Duration:</b> <code>{duration}s</code>"
    )
    bot.send_message(admin_chat_id, result_msg, parse_mode="HTML")


@bot.message_handler(commands=["totalusers"])
def cmd_totalusers(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    _logic_total_users(message)


@bot.message_handler(commands=["hostedbots"])
def cmd_hostedbots(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    _logic_hosted_bots_overview(message)


@bot.message_handler(commands=["activebots"])
def cmd_activebots(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    _logic_active_bots_panel(message)


@bot.message_handler(commands=["expiringsubs"])
def cmd_expiringsubs(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, f"{ce('warning')} Admin required.", parse_mode="HTML")
        return
    _logic_expiring_subscriptions(message)


# ─────────────────────────────────────────────
# FORCEJOIN HELPERS
# ─────────────────────────────────────────────

def process_add_forcejoin_channel(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        return

    awaiting_forcejoin_add.discard(user_id)
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Cancelled.", parse_mode="HTML")
        return

    channel_input = ""
    if getattr(message, "forward_from_chat", None):
        forward_chat = message.forward_from_chat
        channel_input = str(forward_chat.id)
    elif message.text:
        channel_input = message.text.strip()

    if not channel_input:
        bot.reply_to(message, f"{ce('cross')} Please send a channel username or forward from the channel.", parse_mode="HTML")
        return

    try:
        if not channel_input.startswith("@") and not channel_input.startswith("-"):
            channel_input = "@" + channel_input
        chat_info = bot.get_chat(channel_input)
        channel_id = str(chat_info.id)
        channel_username = f"@{chat_info.username}" if getattr(chat_info, "username", None) else ""
        channel_name = chat_info.title or channel_username or channel_id
        add_forcejoin_channel_db(channel_id, channel_username, channel_name)
        bot.reply_to(
            message,
            f"{ce('check')} <b>ForceJoin Channel Added!</b>\n\n"
            f"{ce('globe')} <b>Name:</b> {channel_name}\n"
            f"{ce('link')} <b>Username:</b> {channel_username or 'Private / no username'}\n"
            f"{ce('id_num')} <b>ID:</b> <code>{channel_id}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        bot.reply_to(
            message,
            f"{ce('cross')} Failed to add channel: <code>{e}</code>\n\n"
            "Make sure:\n"
            "• The bot is an admin in that channel\n"
            "• The username is correct",
            parse_mode="HTML",
        )


def _show_forcejoin_list(chat_id):
    if not forcejoin_channels:
        bot.send_message(chat_id, f"{ce('info')} No ForceJoin channels configured.", parse_mode="HTML")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    msg_text = f"{ce('globe')} <b>ForceJoin Channels</b>\n\n"
    for ch in forcejoin_channels:
        status = f"{ce('green_circle')}" if ch["enabled"] else f"{ce('red_circle')}"
        msg_text += f"{status} <b>{ch['channel_name']}</b> ({ch['channel_username'] or 'private'})\n"
        toggle_cb = f"fj_disable_{ch['channel_id']}" if ch["enabled"] else f"fj_enable_{ch['channel_id']}"
        toggle_label = "🔴 Disable" if ch["enabled"] else "🟢 Enable"
        markup.add(types.InlineKeyboardButton(f"{toggle_label} — {ch['channel_name']}", callback_data=toggle_cb))
    markup.add(types.InlineKeyboardButton("🔙 ForceJoin Panel", callback_data="forcejoin_panel"))
    bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode="HTML")


def _show_remove_forcejoin(chat_id):
    if not forcejoin_channels:
        bot.send_message(chat_id, f"{ce('info')} No ForceJoin channels to remove.", parse_mode="HTML")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in forcejoin_channels:
        markup.add(
            types.InlineKeyboardButton(
                f"❌ {ch['channel_name']} ({ch['channel_username'] or 'private'})",
                callback_data=f"fj_del_{ch['channel_id']}",
            )
        )
    markup.add(types.InlineKeyboardButton("🔙 ForceJoin Panel", callback_data="forcejoin_panel"))
    bot.send_message(chat_id, f"{ce('trash')} <b>Select Channel to Remove:</b>", reply_markup=markup, parse_mode="HTML")


# ─────────────────────────────────────────────
# DOCUMENT HANDLER
# ─────────────────────────────────────────────

@bot.message_handler(content_types=["document"])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document

    if user_id in awaiting_db_restore:
        awaiting_db_restore.discard(user_id)
        file_name = safe_filename(doc.file_name) or "restore.db"
        if not file_name.endswith(".db"):
            bot.reply_to(message, f"{ce('cross')} Please send a <code>.db</code> file.", parse_mode="HTML")
            return
        try:
            file_info_tg = bot.get_file(doc.file_id)
            file_content = bot.download_file(file_info_tg.file_path)
            handle_db_restore(file_content, file_name, message)
        except Exception as e:
            bot.reply_to(message, f"{ce('cross')} Error downloading DB file: {e}", parse_mode="HTML")
        return

    not_joined = check_user_joined_channels(user_id)
    if not_joined:
        send_forcejoin_message(chat_id, not_joined)
        return

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, f"{ce('lock')} Bot is locked. Cannot accept files.", parse_mode="HTML")
        return

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float("inf") else "Unlimited"
        bot.reply_to(message, f"{ce('warning')} File limit reached: <code>{current_files}/{limit_str}</code>", parse_mode="HTML")
        return

    file_name = safe_filename(doc.file_name)
    if not file_name:
        bot.reply_to(message, f"{ce('warning')} File has no valid name.", parse_mode="HTML")
        return

    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext == ".db":
        if user_id in admin_ids:
            bot.reply_to(message, f"{ce('info')} To restore a database, use /restoredb first, then send the file.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"{ce('warning')} Unsupported file type!", parse_mode="HTML")
        return

    if file_ext not in [".py", ".js", ".zip"]:
        bot.reply_to(
            message,
            f"{ce('warning')} Unsupported file type!\nOnly <code>.py</code>, <code>.js</code>, and <code>.zip</code> allowed.",
            parse_mode="HTML",
        )
        return

    max_file_size = 20 * 1024 * 1024
    if doc.file_size > max_file_size:
        bot.reply_to(message, f"{ce('warning')} File too large! Max size is <code>20 MB</code>.", parse_mode="HTML")
        return

    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
        except Exception as e:
            logger.error("Failed to forward file to owner: %s", e)

        download_wait_msg = bot.reply_to(message, f"{ce('time')} Downloading <code>{file_name}</code>...", parse_mode="HTML")
        file_info_tg = bot.get_file(doc.file_id)
        downloaded_file_content = bot.download_file(file_info_tg.file_path)

        if user_id != OWNER_ID:
            is_safe, reason = scan_file_for_malware(downloaded_file_content, file_name, user_id)
            if not is_safe:
                bot.edit_message_text(f"{ce('cross')} <b>Security Alert:</b> {reason}", chat_id, download_wait_msg.message_id, parse_mode="HTML")
                return

        bot.edit_message_text(f"{ce('check')} Downloaded <code>{file_name}</code>. Processing...", chat_id, download_wait_msg.message_id, parse_mode="HTML")
        user_folder = get_user_folder(user_id)

        if file_ext == ".zip":
            handle_zip_file(downloaded_file_content, file_name, message)
            return

        file_path = safe_join(user_folder, file_name)
        with open(file_path, "wb") as f:
            f.write(downloaded_file_content)

        if file_ext == ".js":
            handle_js_file(file_path, user_id, user_folder, file_name, message)
        elif file_ext == ".py":
            handle_py_file(file_path, user_id, user_folder, file_name, message)
    except telebot.apihelper.ApiTelegramException as e:
        logger.error("Telegram API Error for %s: %s", user_id, e, exc_info=True)
        if "file is too big" in str(e).lower():
            bot.reply_to(message, f"{ce('cross')} File too large to download via Telegram (~20MB limit).", parse_mode="HTML")
        else:
            bot.reply_to(message, f"{ce('cross')} Telegram API Error: {e}", parse_mode="HTML")
    except Exception as e:
        logger.error("General error handling file for %s: %s", user_id, e, exc_info=True)
        bot.reply_to(message, f"{ce('cross')} Unexpected error: {e}", parse_mode="HTML")

# CALLBACK QUERY HANDLER
# ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data
    logger.info("Callback: User=%s, Data='%s'", user_id, data)

    unlocked_actions = {"back_to_main", "speed", "stats", "check_joined", "user_manual"}
    if bot_locked and user_id not in admin_ids and data not in unlocked_actions:
        bot.answer_callback_query(call.id, "⚠️ Bot is locked by admin.", show_alert=True)
        return

    try:
        if data == "check_joined":
            not_joined = check_user_joined_channels(user_id)
            if not_joined:
                bot.answer_callback_query(call.id, "⚠️ You haven't joined all channels yet!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "✅ All channels joined! Welcome!")
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                _logic_send_welcome(call.message)
        elif data == "upload":
            upload_callback(call)
        elif data == "check_files":
            check_files_callback(call)
        elif data.startswith("file_") or data.startswith("file:"):
            file_control_callback(call)
        elif data.startswith("start_") or data.startswith("start:"):
            start_bot_callback(call)
        elif data.startswith("stop_") or data.startswith("stop:"):
            stop_bot_callback(call)
        elif data.startswith("restart_") or data.startswith("restart:"):
            restart_bot_callback(call)
        elif data.startswith("delete_") or data.startswith("delete:"):
            delete_bot_callback(call)
        elif data.startswith("logs_") or data.startswith("logs:"):
            logs_bot_callback(call)
        elif data == "speed":
            speed_callback(call)
        elif data == "user_manual":
            user_manual_callback(call)
        elif data == "back_to_main":
            back_to_main_callback(call)
        elif data.startswith("confirm_broadcast_"):
            handle_confirm_broadcast(call)
        elif data == "cancel_broadcast":
            handle_cancel_broadcast(call)
        elif data == "send_command":
            send_command_callback(call)
        elif data == "send_to_process":
            send_to_process_callback(call)
        elif data.startswith("sendcmd_select_") or data.startswith("sendcmd_select:"):
            sendcmd_select_callback(call)
        elif data == "view_all_logs":
            view_all_logs_callback(call)
        elif data.startswith("viewlog_") or data.startswith("viewlog:"):
            viewlog_callback(call)
        elif data == "subscription":
            admin_required_callback(call, subscription_management_callback)
        elif data == "stats":
            stats_callback(call)
        elif data == "lock_bot":
            admin_required_callback(call, lock_bot_callback)
        elif data == "unlock_bot":
            admin_required_callback(call, unlock_bot_callback)
        elif data == "run_all_scripts":
            admin_required_callback(call, run_all_scripts_callback)
        elif data == "stop_all_scripts":
            admin_required_callback(call, stop_all_scripts_callback)
        elif data == "system_stats":
            admin_required_callback(call, system_stats_callback)
        elif data == "user_list":
            admin_required_callback(call, user_list_callback)
        elif data == "clean_orphan_files":
            admin_required_callback(call, clean_orphan_callback)
        elif data == "broadcast":
            admin_required_callback(call, broadcast_init_callback)
        elif data == "broadcast_bots":
            admin_required_callback(call, broadcast_bots_callback)
        elif data == "mega_broadcast":
            admin_required_callback(call, mega_broadcast_callback)
        elif data == "total_users":
            admin_required_callback(call, total_users_callback)
        elif data == "active_bots":
            admin_required_callback(call, active_bots_callback)
        elif data == "hosted_bots_overview":
            admin_required_callback(call, hosted_bots_overview_callback)
        elif data == "expiring_subscriptions":
            admin_required_callback(call, expiring_subscriptions_callback)
        elif data == "admin_panel":
            admin_required_callback(call, admin_panel_callback)
        elif data == "add_admin":
            owner_required_callback(call, add_admin_init_callback)
        elif data == "remove_admin":
            owner_required_callback(call, remove_admin_init_callback)
        elif data == "list_admins":
            admin_required_callback(call, list_admins_callback)
        elif data == "add_subscription":
            admin_required_callback(call, add_subscription_init_callback)
        elif data == "remove_subscription":
            admin_required_callback(call, remove_subscription_init_callback)
        elif data == "check_subscription":
            admin_required_callback(call, check_subscription_init_callback)
        elif data == "list_subscribers":
            admin_required_callback(call, list_subscribers_callback)
        elif data == "get_db":
            admin_required_callback(call, lambda c: _logic_get_db(c))
        elif data == "restore_db_info":
            admin_required_callback(call, restore_db_info_callback)
        elif data == "cancel_db_restore":
            cancel_db_restore_callback(call)
        elif data == "forcejoin_panel":
            admin_required_callback(call, forcejoin_panel_callback)
        elif data == "fj_add":
            admin_required_callback(call, fj_add_callback)
        elif data == "fj_list":
            admin_required_callback(call, fj_list_callback)
        elif data == "fj_remove":
            admin_required_callback(call, fj_remove_callback)
        elif data.startswith("fj_del_"):
            admin_required_callback(call, lambda c: fj_del_callback(c))
        elif data.startswith("fj_enable_"):
            admin_required_callback(call, lambda c: fj_toggle_callback(c, True))
        elif data.startswith("fj_disable_"):
            admin_required_callback(call, lambda c: fj_toggle_callback(c, False))
        else:
            bot.answer_callback_query(call.id, "Unknown action.")
    except Exception as e:
        logger.error("Error handling callback '%s' for %s: %s", data, user_id, e, exc_info=True)
        try:
            bot.answer_callback_query(call.id, "Error processing request.", show_alert=True)
        except Exception:
            pass


def admin_required_callback(call, func_to_run):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin permissions required.", show_alert=True)
        return
    func_to_run(call)


def owner_required_callback(call, func_to_run):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ Owner permissions required.", show_alert=True)
        return
    func_to_run(call)


# ─────────────────────────────────────────────
# FORCEJOIN CALLBACKS
# ─────────────────────────────────────────────

def forcejoin_panel_callback(call):
    bot.answer_callback_query(call.id)
    enabled_count = len([c for c in forcejoin_channels if c["enabled"]])
    try:
        bot.edit_message_text(
            f"{ce('globe')} <b>ForceJoin Management</b>\n\n"
            f"{ce('green_circle')} <b>Active Channels:</b> <code>{enabled_count}</code>\n"
            f"{ce('chart')} <b>Total Channels:</b> <code>{len(forcejoin_channels)}</code>\n\n"
            "Users must join all enabled channels to use the bot.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_forcejoin_panel_markup(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Error showing forcejoin panel: %s", e)


def fj_add_callback(call):
    bot.answer_callback_query(call.id)
    awaiting_forcejoin_add.add(call.from_user.id)
    msg = bot.send_message(
        call.message.chat.id,
        f"{ce('plus')} <b>Add ForceJoin Channel</b>\n\n"
        "Send the channel username (e.g. <code>@mychannel</code>)\n"
        "or forward a message from the channel.\n\n"
        f"{ce('warning')} Make sure the bot is admin in that channel!\n\nType /cancel to abort.",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, process_add_forcejoin_channel)


def fj_list_callback(call):
    bot.answer_callback_query(call.id)
    _show_forcejoin_list(call.message.chat.id)


def fj_remove_callback(call):
    bot.answer_callback_query(call.id)
    _show_remove_forcejoin(call.message.chat.id)


def fj_del_callback(call):
    channel_id = call.data.replace("fj_del_", "")
    ch = next((c for c in forcejoin_channels if c["channel_id"] == channel_id), None)
    if not ch:
        bot.answer_callback_query(call.id, "Channel not found.", show_alert=True)
        return
    remove_forcejoin_channel_db(channel_id)
    bot.answer_callback_query(call.id, f"✅ Removed {ch['channel_name']}")
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 ForceJoin Panel", callback_data="forcejoin_panel"))
        bot.edit_message_text(
            f"{ce('check')} Channel <b>{ch['channel_name']}</b> removed from ForceJoin.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML",
        )
    except Exception:
        pass


def fj_toggle_callback(call, enable):
    prefix = "fj_enable_" if enable else "fj_disable_"
    channel_id = call.data.replace(prefix, "")
    ch = next((c for c in forcejoin_channels if c["channel_id"] == channel_id), None)
    if not ch:
        bot.answer_callback_query(call.id, "Channel not found.", show_alert=True)
        return
    toggle_forcejoin_channel_db(channel_id, enable)
    status = "enabled" if enable else "disabled"
    bot.answer_callback_query(call.id, f"✅ Channel {status}")
    fj_list_callback(call)


# ─────────────────────────────────────────────
# CALLBACK IMPLEMENTATIONS
# ─────────────────────────────────────────────

def restore_db_info_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    awaiting_db_restore.add(user_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_db_restore"))
    try:
        bot.edit_message_text(
            f"{ce('package')} <b>Database Restore</b>\n\n"
            "Send the <code>.db</code> backup file now.\n\n"
            f"{ce('warning')} This will replace the current database!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Error in restore_db_info_callback: %s", e)


def cancel_db_restore_callback(call):
    user_id = call.from_user.id
    awaiting_db_restore.discard(user_id)
    bot.answer_callback_query(call.id, "✅ Restore cancelled.")
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
        bot.edit_message_text(
            f"{ce('check')} DB restore cancelled.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML",
        )
    except Exception:
        pass


def send_command_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            f"{ce('laptop')} <b>Send Command Options:</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_send_command_menu(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Error showing send command menu: %s", e)


def send_to_process_callback(call):
    bot.answer_callback_query(call.id)
    send_to_process_init(call.message)


def sendcmd_select_callback(call):
    try:
        script_owner_id, file_name = resolve_running_script_from_callback(call.data, "sendcmd_select")
        script_key = f"{script_owner_id}_{file_name}"
        if script_key not in bot_scripts:
            bot.answer_callback_query(call.id, "Script is no longer running.", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            call.message.chat.id,
            f"📝 Enter command to send to <code>{escape_html(script_key)}</code>:",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, lambda m: process_send_command(m, script_key))
    except Exception:
        bot.answer_callback_query(call.id, "Error selecting script.")


def view_all_logs_callback(call):
    bot.answer_callback_query(call.id)
    view_all_logs(call.message)


def viewlog_callback(call):
    try:
        user_id, log_filename = resolve_user_log_from_callback(call.data, "viewlog")
        requesting = call.from_user.id
        if not (requesting == user_id or requesting in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ You can only view your own logs.", show_alert=True)
            return
        user_folder = get_user_folder(user_id)
        log_path = safe_join(user_folder, log_filename)
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, "❌ Log file not found.", show_alert=True)
            return
        bot.answer_callback_query(call.id, "📜 Sending log file...")
        send_log_file(call.message, log_path, log_filename)
    except Exception as e:
        logger.error("Error in viewlog_callback: %s", e)
        bot.answer_callback_query(call.id, "Error viewing log.")


def upload_callback(call):
    user_id = call.from_user.id
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float("inf") else "Unlimited"
        bot.answer_callback_query(call.id, f"⚠️ File limit reached ({current_files}/{limit_str}).", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"{ce('upload')} <b>Upload Your Script</b>\n\nSupported: <code>.py</code>, <code>.js</code>, <code>.zip</code>\n\nSend the file now!",
        parse_mode="HTML",
    )


def check_files_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 Upload File", callback_data="upload"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"))
        try:
            bot.edit_message_text(
                f"{ce('folder_open')} <b>Your Files</b>\n\nNo files uploaded yet!",
                chat_id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Error editing msg for empty file list: %s", e)
        return

    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    running_count = 0
    for file_name, file_type in sorted(user_files_list):
        running = is_bot_running(user_id, file_name)
        if running:
            running_count += 1
        status_icon = "🟢" if running else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_icon} {file_name} [{file_type.upper()}]", callback_data=build_named_callback("file", user_id, file_name)))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"))
    try:
        bot.edit_message_text(
            f"{ce('folder_open')} <b>Your Files</b> — <code>{running_count}/{len(user_files_list)}</code> running\n\nTap a file to manage it:",
            chat_id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML",
        )
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e):
            logger.error("Error editing file list: %s", e)


def file_control_callback(call):
    try:
        script_owner_id, file_name = resolve_user_file_from_callback(call.data, "file")
        requesting = call.from_user.id
        if not (requesting == script_owner_id or requesting in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ You can only manage your own files.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return

        bot.answer_callback_query(call.id)
        running = is_bot_running(script_owner_id, file_name)
        status_text = f'{ce("green_circle")} Running' if running else f'{ce("red_circle")} Stopped'
        file_type = next((f[1] for f in user_files_list if f[0] == file_name), "?")
        script_key = f"{script_owner_id}_{file_name}"
        uptime_str = ""
        if running and script_key in bot_scripts:
            start_time = bot_scripts[script_key].get("start_time")
            if start_time:
                elapsed = datetime.now() - start_time
                uptime_str = f"\n{ce('time')} <b>Uptime:</b> <code>{str(elapsed).split('.')[0]}</code>"
        try:
            bot.edit_message_text(
                f"{ce('laptop')} <b>File Manager</b>\n\n"
                f"{ce('file')} <b>File:</b> <code>{escape_html(file_name)}</code>\n"
                f"🔧 <b>Type:</b> <code>{file_type.upper()}</code>\n"
                f"{ce('user')} <b>User:</b> <code>{script_owner_id}</code>\n"
                f"🔘 <b>Status:</b> {status_text}{uptime_str}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, running),
                parse_mode="HTML",
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                raise
    except (ValueError, IndexError, KeyError) as e:
        logger.error("Error parsing file control: %s", e)
        bot.answer_callback_query(call.id, "Error: Invalid action data.", show_alert=True)


def start_bot_callback(call):
    try:
        script_owner_id, file_name = resolve_user_file_from_callback(call.data, "start")
        requesting = call.from_user.id
        chat_id = call.message.chat.id

        if not (requesting == script_owner_id or requesting in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            return

        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = safe_join(user_folder, file_name)

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, "⚠️ File missing! Re-upload.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            return

        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, "⚠️ Already running!", show_alert=True)
            return

        bot.answer_callback_query(call.id, f"⏳ Starting {file_name}...")
        if file_type == "py":
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()
        elif file_type == "js":
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()

        time.sleep(SCRIPT_STATUS_REFRESH_DELAY)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = f'{ce("green_circle")} Running' if is_now_running else "🟡 Starting..."
        try:
            bot.edit_message_text(
                f"{ce('laptop')} <b>File Manager</b>\n\n"
                f"{ce('file')} <b>File:</b> <code>{escape_html(file_name)}</code>\n"
                f"🔧 <b>Type:</b> <code>{file_type.upper()}</code>\n"
                f"🔘 <b>Status:</b> {status_text}",
                chat_id,
                call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running),
                parse_mode="HTML",
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                raise
    except (ValueError, IndexError, KeyError):
        bot.answer_callback_query(call.id, "Error: Invalid command.", show_alert=True)
    except Exception as e:
        logger.error("Error in start_bot_callback: %s", e, exc_info=True)
        bot.answer_callback_query(call.id, "Error starting script.", show_alert=True)


def stop_bot_callback(call):
    try:
        script_owner_id, file_name = resolve_user_file_from_callback(call.data, "stop")
        requesting = call.from_user.id
        chat_id = call.message.chat.id

        if not (requesting == script_owner_id or requesting in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            return

        file_type = file_info[1]
        script_key = f"{script_owner_id}_{file_name}"
        if not is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, "⚠️ Already stopped.", show_alert=True)
            return

        bot.answer_callback_query(call.id, f"⏳ Stopping {file_name}...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            bot_scripts.pop(script_key, None)

        try:
            bot.edit_message_text(
                f"{ce('laptop')} <b>File Manager</b>\n\n"
                f"{ce('file')} <b>File:</b> <code>{escape_html(file_name)}</code>\n"
                f"🔧 <b>Type:</b> <code>{file_type.upper()}</code>\n"
                f"🔘 <b>Status:</b> {ce('red_circle')} Stopped",
                chat_id,
                call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, False),
                parse_mode="HTML",
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                raise
    except (ValueError, IndexError, KeyError):
        bot.answer_callback_query(call.id, "Error: Invalid command.", show_alert=True)
    except Exception as e:
        logger.error("Error in stop_bot_callback: %s", e, exc_info=True)
        bot.answer_callback_query(call.id, "Error stopping script.", show_alert=True)


def restart_bot_callback(call):
    try:
        script_owner_id, file_name = resolve_user_file_from_callback(call.data, "restart")
        requesting = call.from_user.id
        chat_id = call.message.chat.id

        if not (requesting == script_owner_id or requesting in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            return

        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = safe_join(user_folder, file_name)
        script_key = f"{script_owner_id}_{file_name}"

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, "⚠️ File missing! Re-upload.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            bot_scripts.pop(script_key, None)
            return

        bot.answer_callback_query(call.id, f"🔄 Restarting {file_name}...")
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            bot_scripts.pop(script_key, None)
            time.sleep(SCRIPT_STATUS_REFRESH_DELAY)

        if file_type == "py":
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()
        elif file_type == "js":
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()

        time.sleep(SCRIPT_STATUS_REFRESH_DELAY)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = f'{ce("green_circle")} Running' if is_now_running else "🟡 Starting..."
        try:
            bot.edit_message_text(
                f"{ce('laptop')} <b>File Manager</b>\n\n"
                f"{ce('file')} <b>File:</b> <code>{escape_html(file_name)}</code>\n"
                f"🔧 <b>Type:</b> <code>{file_type.upper()}</code>\n"
                f"🔘 <b>Status:</b> {status_text}",
                chat_id,
                call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running),
                parse_mode="HTML",
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                raise
    except (ValueError, IndexError, KeyError):
        bot.answer_callback_query(call.id, "Error: Invalid command.", show_alert=True)
    except Exception as e:
        logger.error("Error in restart_bot_callback: %s", e, exc_info=True)
        bot.answer_callback_query(call.id, "Error restarting.", show_alert=True)


def delete_bot_callback(call):
    try:
        script_owner_id, file_name = resolve_user_file_from_callback(call.data, "delete")
        requesting = call.from_user.id
        chat_id = call.message.chat.id

        if not (requesting == script_owner_id or requesting in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        bot.answer_callback_query(call.id, f"🗑️ Deleting {file_name}...")
        script_key = f"{script_owner_id}_{file_name}"
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            bot_scripts.pop(script_key, None)
            time.sleep(0.3)

        user_folder = get_user_folder(script_owner_id)
        file_path = safe_join(user_folder, file_name)
        log_path = safe_join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        for path in [file_path, log_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError as e:
                    logger.error("Error deleting %s: %s", path, e)

        remove_user_file_db(script_owner_id, file_name)
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Files", callback_data="check_files"))
            bot.edit_message_text(
                f"{ce('trash')} <b>Deleted!</b>\n\n<code>{escape_html(file_name)}</code> has been removed.",
                chat_id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Error editing msg after delete: %s", e)
    except (ValueError, IndexError, KeyError):
        bot.answer_callback_query(call.id, "Error: Invalid command.", show_alert=True)
    except Exception as e:
        logger.error("Error in delete_bot_callback: %s", e, exc_info=True)
        bot.answer_callback_query(call.id, "Error deleting.", show_alert=True)


def logs_bot_callback(call):
    try:
        script_owner_id, file_name = resolve_user_file_from_callback(call.data, "logs")
        requesting = call.from_user.id
        chat_id = call.message.chat.id

        if not (requesting == script_owner_id or requesting in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_folder = get_user_folder(script_owner_id)
        log_path = safe_join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, f"⚠️ No logs for '{file_name}' yet.", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        try:
            file_size = os.path.getsize(log_path)
            max_log_kb = 100
            max_tg_msg = 4000
            if file_size == 0:
                log_content = "(Log is empty)"
            elif file_size > max_log_kb * 1024:
                with open(log_path, "rb") as f:
                    f.seek(-max_log_kb * 1024, os.SEEK_END)
                    log_bytes = f.read()
                log_content = f"(Last {max_log_kb} KB)\n...\n" + log_bytes.decode("utf-8", errors="ignore")
            else:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    log_content = f.read()

            if len(log_content) > max_tg_msg:
                log_content = "...\n" + log_content[-max_tg_msg:]
            if not log_content.strip():
                log_content = "(No content)"

            bot.send_message(
                chat_id,
                f"📜 <b>Logs:</b> <code>{escape_html(file_name)}</code>\n<pre>{escape_html(log_content)}</pre>",
                parse_mode="HTML",
            )
        except Exception:
            bot.send_message(chat_id, f"{ce('cross')} Error reading log for <code>{escape_html(file_name)}</code>.", parse_mode="HTML")
    except (ValueError, IndexError, KeyError):
        bot.answer_callback_query(call.id, "Error: Invalid command.", show_alert=True)
    except Exception as e:
        logger.error("Error in logs_bot_callback: %s", e, exc_info=True)
        bot.answer_callback_query(call.id, "Error fetching logs.", show_alert=True)


def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    start_cb = time.time()
    try:
        bot.edit_message_text(f"{ce('lightning')} Testing speed...", chat_id, call.message.message_id, parse_mode="HTML")
        response_time = round((time.time() - start_cb) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID:
            user_level = f"{ce('crown')} Owner"
        elif user_id in admin_ids:
            user_level = f"{ce('admin')} Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get("expiry", datetime.min) > datetime.now():
            user_level = f"{ce('diamond')} Premium"
        else:
            user_level = f"{ce('free')} Free User"
        quality = "🟢 Excellent" if response_time < 300 else ("🟡 Good" if response_time < 800 else "🔴 Slow")
        speed_msg = (
            f"{ce('lightning')} <b>Speed Test Results</b>\n\n"
            f"⏱️ <b>Response:</b> <code>{response_time} ms</code>\n"
            f"📶 <b>Quality:</b> {quality}\n"
            f"🚦 <b>Status:</b> {status}\n"
            f"{ce('user')} <b>Level:</b> {user_level}"
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text(speed_msg, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id), parse_mode="HTML")
    except Exception as e:
        logger.error("Speed test error: %s", e)
        bot.answer_callback_query(call.id, "Error in speed test.", show_alert=True)


def user_manual_callback(call):
    bot.answer_callback_query(call.id)
    _logic_user_manual(call)


def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float("inf") else "∞"
    user_status, expiry_info = get_user_status(user_id)
    running_count = sum(1 for fn, _ in user_files.get(user_id, []) if is_bot_running(user_id, fn))

    main_menu_text = (
        f"{ce('home')} <b>{BOT_NAME}</b> — Main Menu\n\n"
        f"{ce('user')} <b>ID:</b> <code>{user_id}</code>\n"
        f"{ce('star')} <b>Status:</b> {user_status}{expiry_info}\n"
        f"{ce('folder_open')} <b>Files:</b> <code>{current_files} / {limit_str}</code>\n"
        f"{ce('green_circle')} <b>Running:</b> <code>{running_count}</code>\n\n"
        f"{ce('bookmark')} <b>Tip:</b> Open <b>User Manual</b> if you want the upload/start guide.\n\n"
        f"{ce('play')} Choose an option:"
    )
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(main_menu_text, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id), parse_mode="HTML")
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e):
            logger.error("API error on back_to_main: %s", e)


def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            f"{ce('star')} <b>Subscription Management</b>\n\nSelect an action:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_subscription_menu(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Error showing sub menu: %s", e)


def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message)


def lock_bot_callback(call):
    global bot_locked
    bot_locked = True
    bot.answer_callback_query(call.id, "🔒 Bot locked.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel_markup(call.from_user.id))
    except Exception:
        pass


def unlock_bot_callback(call):
    global bot_locked
    bot_locked = False
    bot.answer_callback_query(call.id, "🔓 Bot unlocked.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel_markup(call.from_user.id))
    except Exception:
        pass


def run_all_scripts_callback(call):
    _logic_run_all_scripts(call)


def stop_all_scripts_callback(call):
    bot.answer_callback_query(call.id, "🛑 Stopping all scripts...")
    _logic_stop_all_scripts(call.from_user.id, call.message.chat.id)


def system_stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_system_stats(call.message.chat.id)


def user_list_callback(call):
    bot.answer_callback_query(call.id)
    _logic_user_list(call.message.chat.id, call.from_user.id)


def clean_orphan_callback(call):
    bot.answer_callback_query(call.id, "🗑 Cleaning orphan files...")
    _logic_clean_orphan_files(call.message.chat.id, call.from_user.id)


def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"{ce('broadcast')} Send the message to broadcast to all users.\nType /cancel to abort.", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_broadcast_message)


def broadcast_bots_callback(call):
    bot.answer_callback_query(call.id)
    running_count = count_running_scripts()
    msg = bot.send_message(
        call.message.chat.id,
        f"{ce('broadcast')} <b>Broadcast to Hosted Bots</b>\n\n"
        f"{ce('green_circle')} <b>Currently running:</b> <code>{running_count}</code> bots\n\n"
        "Send a stdin command/message to broadcast to all running hosted bot processes.\n\nType /cancel to abort.",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, process_broadcast_bots_message)


def mega_broadcast_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        f"{ce('broadcast')} <b>Mega Broadcast</b>\n\n"
        f"{ce('users')} Sends to all registered users.\n"
        f"{ce('robot')} Also pushes the same text into all running hosted bots via stdin.\n\n"
        f"{ce('warning')} Text only. Type /cancel to abort.",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, process_mega_broadcast_message)


def process_broadcast_message(message):
    if message.from_user.id not in admin_ids:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Broadcast cancelled.", parse_mode="HTML")
        return

    allowed_types = {"text", "photo", "video", "document", "animation", "audio", "voice", "sticker"}
    content_type = getattr(message, "content_type", "text")
    if content_type not in allowed_types:
        bot.reply_to(message, f"{ce('warning')} Unsupported broadcast content type: <code>{escape_html(content_type)}</code>", parse_mode="HTML")
        return

    target_count = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Confirm & Send", callback_data=f"confirm_broadcast_{message.message_id}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast"),
    )
    preview_text = (message.text or message.caption or f"({content_type.title()} message)")[:1000].strip() or "(Media message)"
    bot.reply_to(
        message,
        f"{ce('warning')} <b>Confirm Broadcast</b>\n\n"
        f"Preview:\n<pre>{escape_html(preview_text)}</pre>\n\n"
        f"Targeting <b>{target_count}</b> users. Confirm?",
        reply_markup=markup,
        parse_mode="HTML",
    )


def process_mega_broadcast_message(message):
    if message.from_user.id not in admin_ids:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Mega broadcast cancelled.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Please send text only for mega broadcast."):
        return

    bot.reply_to(
        message,
        f"{ce('time')} <b>Launching mega broadcast...</b>\n"
        f"{ce('users')} Users: <code>{len(active_users)}</code>\n"
        f"{ce('robot')} Active bots: <code>{count_running_scripts()}</code>",
        parse_mode="HTML",
    )
    threading.Thread(target=_execute_mega_broadcast, args=(message.text, message.chat.id), daemon=True).start()


def handle_confirm_broadcast(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True)
        return
    try:
        original_message = call.message.reply_to_message
        if not original_message:
            raise ValueError("Could not retrieve original message.")

        bot.answer_callback_query(call.id, "🚀 Starting broadcast...")
        bot.edit_message_text(
            f"{ce('broadcast')} Broadcasting to <b>{len(active_users)}</b> users...",
            chat_id,
            call.message.message_id,
            reply_markup=None,
            parse_mode="HTML",
        )
        threading.Thread(
            target=execute_broadcast,
            args=(original_message.chat.id, original_message.message_id, chat_id),
            daemon=True,
        ).start()
    except ValueError as e:
        bot.edit_message_text(f"{ce('cross')} Error: <code>{escape_html(e)}</code>", chat_id, call.message.message_id, reply_markup=None, parse_mode="HTML")
    except Exception as e:
        logger.error("Error in handle_confirm_broadcast: %s", e, exc_info=True)


def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "✅ Broadcast cancelled.")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


def execute_broadcast(source_chat_id, source_message_id, admin_chat_id):
    sent_count = 0
    failed_count = 0
    blocked_count = 0
    start_exec = time.time()
    users_to_broadcast = list(active_users)
    total_users = len(users_to_broadcast)

    for i, user_id_bc in enumerate(users_to_broadcast):
        try:
            bot.copy_message(user_id_bc, source_chat_id, source_message_id)
            sent_count += 1
        except telebot.apihelper.ApiTelegramException as e:
            err_desc = str(e).lower()
            if any(token in err_desc for token in ["bot was blocked", "user is deactivated", "chat not found", "kicked", "restricted"]):
                blocked_count += 1
            elif "flood control" in err_desc or "too many requests" in err_desc:
                retry_after = 5
                match = re.search(r"retry after (\d+)", err_desc)
                if match:
                    retry_after = int(match.group(1)) + 1
                time.sleep(retry_after)
                try:
                    bot.copy_message(user_id_bc, source_chat_id, source_message_id)
                    sent_count += 1
                except Exception:
                    failed_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1

        if (i + 1) % BROADCAST_BATCH_SIZE == 0 and i < total_users - 1:
            time.sleep(BROADCAST_BATCH_DELAY)
        elif i % 5 == 0:
            time.sleep(0.12)

    duration = round(time.time() - start_exec, 2)
    result_msg = (
        f"{ce('party')} <b>Broadcast Complete!</b>\n\n"
        f"{ce('check')} <b>Sent:</b> <code>{sent_count}</code>\n"
        f"{ce('cross')} <b>Failed:</b> <code>{failed_count}</code>\n"
        f"🚫 <b>Blocked/Inactive:</b> <code>{blocked_count}</code>\n"
        f"{ce('users')} <b>Total Targets:</b> <code>{total_users}</code>\n"
        f"{ce('time')} <b>Duration:</b> <code>{duration}s</code>"
    )
    try:
        bot.send_message(admin_chat_id, result_msg, parse_mode="HTML")
    except Exception as e:
        logger.error("Failed to send broadcast result: %s", e)


def admin_panel_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    running_bots_count = count_running_scripts()
    active_bot_owners = len({si["script_owner_id"] for _, si in get_running_scripts_snapshot()})
    enabled_fj = len([c for c in forcejoin_channels if c["enabled"]])
    premium_users = sum(1 for info in user_subscriptions.values() if info.get("expiry", datetime.min) > datetime.now())
    total_uploaded = sum(len(files) for files in user_files.values())
    try:
        bot.edit_message_text(
            f"{ce('crown')} <b>Admin Control Center</b>\n\n"
            f"{ce('users')} <b>Total Users:</b> <code>{len(active_users)}</code>\n"
            f"{ce('diamond')} <b>Premium Users:</b> <code>{premium_users}</code>\n"
            f"{ce('folder_open')} <b>Uploaded Bots:</b> <code>{total_uploaded}</code>\n"
            f"{ce('green_circle')} <b>Running Scripts:</b> <code>{running_bots_count}</code>\n"
            f"{ce('user')} <b>Active Bot Owners:</b> <code>{active_bot_owners}</code>\n"
            f"{ce('globe')} <b>ForceJoin Active:</b> <code>{enabled_fj}</code>\n"
            f"{ce('lock')} <b>Bot Lock:</b> <code>{'Locked 🔒' if bot_locked else 'Unlocked 🔓'}</code>\n\n"
            f"{ce('sparkle')} Broadcast, control hosted bots, manage subscriptions, and maintain the system from here.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_admin_panel_markup(user_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Error showing admin panel: %s", e)


def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"{ce('plus')} Enter the User ID to promote to Admin.\nType /cancel to abort.", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_add_admin_id)


def process_add_admin_id(message):
    if message.from_user.id != OWNER_ID:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Cancelled.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Invalid ID. Send a numerical User ID."):
        return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id <= 0:
            raise ValueError()
        if new_admin_id == OWNER_ID:
            bot.reply_to(message, f"{ce('warning')} Owner is already the highest rank.", parse_mode="HTML")
            return
        if new_admin_id in admin_ids:
            bot.reply_to(message, f"{ce('warning')} User <code>{new_admin_id}</code> is already an Admin.", parse_mode="HTML")
            return
        add_admin_db(new_admin_id)
        bot.reply_to(message, f"{ce('check')} User <code>{new_admin_id}</code> promoted to Admin.", parse_mode="HTML")
        try:
            bot.send_message(new_admin_id, f"{ce('crown')} You've been promoted to Admin on <b>{BOT_NAME}</b>!", parse_mode="HTML")
        except Exception:
            pass
    except ValueError:
        bot.reply_to(message, f"{ce('warning')} Invalid ID. Send a numerical User ID.", parse_mode="HTML")
        msg = bot.send_message(message.chat.id, "Enter User ID or /cancel.")
        bot.register_next_step_handler(msg, process_add_admin_id)


def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"{ce('trash')} Enter the User ID of the Admin to remove.\nType /cancel to abort.", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_remove_admin_id)


def process_remove_admin_id(message):
    if message.from_user.id != OWNER_ID:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Cancelled.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Invalid ID."):
        return
    try:
        admin_id_remove = int(message.text.strip())
        if admin_id_remove == OWNER_ID:
            bot.reply_to(message, f"{ce('warning')} Cannot remove Owner.", parse_mode="HTML")
            return
        if admin_id_remove not in admin_ids:
            bot.reply_to(message, f"{ce('warning')} User <code>{admin_id_remove}</code> is not an Admin.", parse_mode="HTML")
            return
        if remove_admin_db(admin_id_remove):
            bot.reply_to(message, f"{ce('check')} Admin <code>{admin_id_remove}</code> removed.", parse_mode="HTML")
            try:
                bot.send_message(admin_id_remove, f"{ce('info')} Your Admin access on <b>{BOT_NAME}</b> has been revoked.", parse_mode="HTML")
            except Exception:
                pass
        else:
            bot.reply_to(message, f"{ce('cross')} Failed to remove admin.", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, f"{ce('warning')} Invalid ID.", parse_mode="HTML")
        msg = bot.send_message(message.chat.id, "Enter Admin ID or /cancel.")
        bot.register_next_step_handler(msg, process_remove_admin_id)


def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        admin_list_str = "\n".join(
            f"  {'👑' if aid == OWNER_ID else '🛡️'} <code>{aid}</code>{' (Owner)' if aid == OWNER_ID else ''}"
            for aid in sorted(list(admin_ids))
        )
        if not admin_list_str:
            admin_list_str = "(None configured)"
        bot.edit_message_text(
            f"{ce('admin')} <b>Admin List</b>\n\n{admin_list_str}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_admin_panel_markup(call.from_user.id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Error listing admins: %s", e)


def list_subscribers_callback(call):
    bot.answer_callback_query(call.id)
    if not user_subscriptions:
        bot.send_message(call.message.chat.id, f"{ce('info')} No active subscribers.", parse_mode="HTML")
        return
    lines = []
    for uid, sub_info in user_subscriptions.items():
        expiry = sub_info.get("expiry")
        if expiry and expiry > datetime.now():
            days_left = max(0, (expiry - datetime.now()).days)
            lines.append(f"{ce('diamond')} <code>{uid}</code> — {days_left} days left ({expiry.strftime('%Y-%m-%d')})")
        else:
            lines.append(f"{ce('cross')} <code>{uid}</code> — expired")
    msg = f"{ce('diamond')} <b>Subscribers ({len(user_subscriptions)})</b>\n\n" + "\n".join(lines[:30])
    if len(lines) > 30:
        msg += f"\n...and {len(lines) - 30} more"
    bot.send_message(call.message.chat.id, msg, parse_mode="HTML")


def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        f"{ce('star')} Enter User ID and days (space separated).\nExample: <code>12345678 30</code>\nType /cancel to abort.",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, process_add_subscription_details)


def process_add_subscription_details(message):
    if message.from_user.id not in admin_ids:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Cancelled.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Invalid. Format: <code>UserID Days</code>"):
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Format: UserID Days")
        sub_user_id = int(parts[0].strip())
        days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0:
            raise ValueError()
        current_expiry = user_subscriptions.get(sub_user_id, {}).get("expiry")
        start_date = datetime.now()
        if current_expiry and current_expiry > start_date:
            start_date = current_expiry
        new_expiry = start_date + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)
        bot.reply_to(
            message,
            f"{ce('check')} Subscription for <code>{sub_user_id}</code> extended by <b>{days} days</b>.\nExpiry: <code>{new_expiry:%Y-%m-%d}</code>",
            parse_mode="HTML",
        )
        try:
            bot.send_message(
                sub_user_id,
                f"{ce('diamond')} Your subscription on <b>{BOT_NAME}</b> activated/extended by <b>{days} days</b>!\n{ce('time')} Expires: <code>{new_expiry:%Y-%m-%d}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
    except ValueError:
        bot.reply_to(message, f"{ce('warning')} Invalid. Format: <code>UserID Days</code>", parse_mode="HTML")
        msg = bot.send_message(message.chat.id, "Enter UserID Days or /cancel.")
        bot.register_next_step_handler(msg, process_add_subscription_details)


def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"{ce('trash')} Enter User ID to remove subscription.\nType /cancel to abort.", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_remove_subscription_id)


def process_remove_subscription_id(message):
    if message.from_user.id not in admin_ids:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Cancelled.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Invalid ID."):
        return
    try:
        sub_user_id_remove = int(message.text.strip())
        if sub_user_id_remove not in user_subscriptions:
            bot.reply_to(message, f"{ce('warning')} User has no active subscription.", parse_mode="HTML")
            return
        remove_subscription_db(sub_user_id_remove)
        bot.reply_to(message, f"{ce('check')} Subscription for <code>{sub_user_id_remove}</code> removed.", parse_mode="HTML")
        try:
            bot.send_message(sub_user_id_remove, f"{ce('info')} Your subscription on <b>{BOT_NAME}</b> has been removed.", parse_mode="HTML")
        except Exception:
            pass
    except ValueError:
        bot.reply_to(message, f"{ce('warning')} Invalid ID.", parse_mode="HTML")


def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"{ce('eyes')} Enter User ID to check subscription.\nType /cancel to abort.", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_check_subscription_id)


def process_check_subscription_id(message):
    if message.from_user.id not in admin_ids:
        return
    if message_is_cancel(message):
        bot.reply_to(message, f"{ce('check')} Cancelled.", parse_mode="HTML")
        return
    if not ensure_text_message(message, f"{ce('warning')} Invalid ID."):
        return
    try:
        sub_user_id_check = int(message.text.strip())
        if sub_user_id_check in user_subscriptions:
            expiry_dt = user_subscriptions[sub_user_id_check].get("expiry")
            if expiry_dt and expiry_dt > datetime.now():
                days_left = max(0, (expiry_dt - datetime.now()).days)
                bot.reply_to(
                    message,
                    f"{ce('check')} User <code>{sub_user_id_check}</code> has an <b>active</b> subscription.\n"
                    f"{ce('time')} Expires: <code>{expiry_dt:%Y-%m-%d %H:%M}</code> ({days_left} days left)",
                    parse_mode="HTML",
                )
            else:
                bot.reply_to(message, f"{ce('warning')} Subscription expired.", parse_mode="HTML")
                remove_subscription_db(sub_user_id_check)
        else:
            bot.reply_to(message, f"{ce('info')} User <code>{sub_user_id_check}</code> has <b>no</b> active subscription.", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, f"{ce('warning')} Invalid ID.", parse_mode="HTML")
def total_users_callback(call):
    bot.answer_callback_query(call.id)
    _logic_total_users(call)


def active_bots_callback(call):
    bot.answer_callback_query(call.id)
    _logic_active_bots_panel(call)


def hosted_bots_overview_callback(call):
    bot.answer_callback_query(call.id)
    _logic_hosted_bots_overview(call)


def expiring_subscriptions_callback(call):
    bot.answer_callback_query(call.id)
    _logic_expiring_subscriptions(call)

def cleanup():
    logger.warning("Shutting down. Cleaning up processes...")
    for key in list(bot_scripts.keys()):
        if key in bot_scripts:
            logger.info("Stopping: %s", key)
            kill_process_tree(bot_scripts[key])
    logger.warning("Cleanup finished.")


atexit.register(cleanup)


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("?? %s Starting Up...", BOT_NAME)
    logger.info("?? Python: %s", sys.version.split()[0])
    logger.info("?? Upload Dir: %s", UPLOAD_BOTS_DIR)
    logger.info("?? Data Dir: %s", IROTECH_DIR)
    logger.info("?? Owner ID: %s", OWNER_ID)
    logger.info("??? Admins: %s", admin_ids)
    logger.info("?? ForceJoin Channels: %s", len(forcejoin_channels))
    logger.info("=" * 50)

    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

    keep_alive()
    logger.info("?? Starting polling...")

    while True:
        try:
            bot.infinity_polling(
                logger_level=logging.WARNING,
                timeout=60,
                long_polling_timeout=30,
                skip_pending=True,
            )
        except requests.exceptions.ReadTimeout:
            logger.warning("Polling ReadTimeout. Restarting in 5s...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as err:
            logger.error("Polling ConnectionError: %s. Retrying in 15s...", err)
            time.sleep(15)
        except Exception as e:
            logger.critical("Critical polling error: %s", e, exc_info=True)
            logger.info("Restarting in 30s...")
            time.sleep(30)
        finally:
            time.sleep(1)
