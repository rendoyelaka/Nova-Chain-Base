import telebot
import random
import string
import requests
import json
import os
import base64
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════

BOT_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
GITHUB_TOKEN  = os.environ["GH_PAT"]
GITHUB_REPO   = os.environ["REPO_NAME"]

bot = telebot.TeleBot(BOT_TOKEN)

BUILDS_LOG = "builds_log.json"

# ════════════════════════════════════════════════════════
# SESSION STATE — stores name + icon between steps
# ════════════════════════════════════════════════════════

session = {
    "app_name":   None,   # string entered by user
    "icon_b64":   None,   # base64 encoded icon image
    "step":       None    # current step: "waiting_name" | "waiting_icon" | None
}

# ════════════════════════════════════════════════════════
# GENERATION HELPERS
# ════════════════════════════════════════════════════════

def generate_chain():
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=10))
    part2 = ''.join(random.choices(chars, k=10))
    return part1, part2

def generate_package():
    prefixes  = ["com", "org", "net"]
    companies = ["settings", "system", "manager", "service", "helper",
                 "assistant", "optimizer", "updater", "cleaner", "support"]
    prefix  = random.choice(prefixes)
    company = random.choice(companies)
    suffix  = ''.join(random.choices(string.ascii_lowercase, k=4))
    return f"{prefix}.{company}.{suffix}"

# ════════════════════════════════════════════════════════
# GITHUB ACTIONS TRIGGER
# ════════════════════════════════════════════════════════

def trigger_workflow(inputs: dict) -> bool:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/build.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {"ref": "main", "inputs": inputs}
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 204

# ════════════════════════════════════════════════════════
# BUILD LOG
# ════════════════════════════════════════════════════════

def log_build(part1, part2, main_pkg, companion_pkg, app_name):
    builds = []
    if os.path.exists(BUILDS_LOG):
        try:
            with open(BUILDS_LOG, 'r') as f:
                builds = json.load(f)
        except Exception:
            builds = []
    builds.append({
        "timestamp":         datetime.now().isoformat(),
        "app_name":          app_name,
        "main_package":      main_pkg,
        "companion_package": companion_pkg,
        "chain":             f"{part1}-{part2}"
    })
    with open(BUILDS_LOG, 'w') as f:
        json.dump(builds, f, indent=2)

# ════════════════════════════════════════════════════════
# MENUS
# ════════════════════════════════════════════════════════

def main_menu():
    markup = InlineKeyboardMarkup()
    # Show tick if name/icon already set
    name_label = f"✏️ App Name {'✅' if session['app_name'] else ''}".strip()
    icon_label = f"📤 Upload Icon {'✅' if session['icon_b64'] else ''}".strip()
    markup.row(InlineKeyboardButton(name_label, callback_data="set_name"))
    markup.row(InlineKeyboardButton(icon_label, callback_data="set_icon"))
    markup.row(InlineKeyboardButton("🔨 Build App", callback_data="build_app"))
    markup.row(InlineKeyboardButton("📋 List Builds", callback_data="list_builds"))
    return markup

def status_text():
    name = session["app_name"] or "❌ Not set"
    icon = "✅ Uploaded" if session["icon_b64"] else "❌ Not set"
    return (
        f"🤖 *Builder Bot*\n\n"
        f"✏️ App Name: `{name}`\n"
        f"📤 Icon: {icon}\n\n"
        f"Select an action:"
    )

# ════════════════════════════════════════════════════════
# /start
# ════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ Unauthorized")
        return
    bot.send_message(
        ADMIN_CHAT_ID,
        status_text(),
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ════════════════════════════════════════════════════════
# MESSAGE HANDLER — captures name input + icon upload
# ════════════════════════════════════════════════════════

@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    # Capture app name
    if session["step"] == "waiting_name" and message.content_type == "text":
        name = message.text.strip()
        if len(name) < 1 or len(name) > 30:
            bot.send_message(ADMIN_CHAT_ID, "❌ Name must be 1–30 characters. Try again:")
            return
        session["app_name"] = name
        session["step"] = None
        bot.send_message(
            ADMIN_CHAT_ID,
            f"✅ App name set to: *{name}*",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        return

    # Capture icon upload
    if session["step"] == "waiting_icon" and message.content_type == "photo":
        # Get highest resolution photo
        photo = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded = bot.download_file(file_info.file_path)
        session["icon_b64"] = base64.b64encode(downloaded).decode("utf-8")
        session["step"] = None
        bot.send_message(
            ADMIN_CHAT_ID,
            "✅ Icon uploaded successfully.",
            reply_markup=main_menu()
        )
        return

    # Unexpected input
    if session["step"] == "waiting_name":
        bot.send_message(ADMIN_CHAT_ID, "✏️ Please type the app name as text:")
        return
    if session["step"] == "waiting_icon":
        bot.send_message(ADMIN_CHAT_ID, "📤 Please send the icon as a photo/image:")
        return

# ════════════════════════════════════════════════════════
# CALLBACK HANDLERS
# ════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return

    bot.answer_callback_query(call.id)

    if call.data == "set_name":
        session["step"] = "waiting_name"
        bot.send_message(ADMIN_CHAT_ID, "✏️ Enter the app name:")

    elif call.data == "set_icon":
        session["step"] = "waiting_icon"
        bot.send_message(ADMIN_CHAT_ID, "📤 Send the icon image:")

    elif call.data == "build_app":
        handle_build_app()

    elif call.data == "list_builds":
        handle_list_builds()

# ════════════════════════════════════════════════════════
# BUILD APP
# ════════════════════════════════════════════════════════

def handle_build_app():
    # Validate name + icon set
    if not session["app_name"]:
        bot.send_message(
            ADMIN_CHAT_ID,
            "❌ App name not set. Tap ✏️ App Name first.",
            reply_markup=main_menu()
        )
        return
    if not session["icon_b64"]:
        bot.send_message(
            ADMIN_CHAT_ID,
            "❌ Icon not uploaded. Tap 📤 Upload Icon first.",
            reply_markup=main_menu()
        )
        return

    part1, part2  = generate_chain()
    main_pkg      = generate_package()
    companion_pkg = generate_package()
    app_name      = session["app_name"]

    bot.send_message(
        ADMIN_CHAT_ID,
        f"🔨 *BUILD APP STARTED*\n\n"
        f"📱 App Name: `{app_name}`\n"
        f"📦 Main Package: `{main_pkg}`\n"
        f"📦 Companion Package: `{companion_pkg}`\n"
        f"🔐 Chain Part 1: `{part1}`\n"
        f"🔐 Chain Part 2: `{part2}`\n\n"
        f"⏳ Triggering GitHub Actions...",
        parse_mode="Markdown"
    )

    inputs = {
        "build_type":        "both",
        "main_package":      main_pkg,
        "companion_package": companion_pkg,
        "chain_part1":       part1,
        "chain_part2":       part2,
        "app_name":          app_name,
        "icon_b64":          session["icon_b64"]
    }

    if trigger_workflow(inputs):
        log_build(part1, part2, main_pkg, companion_pkg, app_name)
        # Reset session after successful trigger
        session["app_name"] = None
        session["icon_b64"] = None
        bot.send_message(
            ADMIN_CHAT_ID,
            f"✅ *Build triggered successfully*\n\n"
            f"📱 App Name: `{app_name}`\n"
            f"📦 Main: `{main_pkg}`\n"
            f"📦 Companion: `{companion_pkg}`\n"
            f"🔐 Chain: `{part1}-{part2}`\n\n"
            f"⏳ Build takes 5–8 mins. Both APKs will be sent here when ready.",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    else:
        bot.send_message(
            ADMIN_CHAT_ID,
            "❌ Failed to trigger GitHub Actions.",
            reply_markup=main_menu()
        )

# ════════════════════════════════════════════════════════
# LIST BUILDS
# ════════════════════════════════════════════════════════

def handle_list_builds():
    try:
        if not os.path.exists(BUILDS_LOG):
            bot.send_message(ADMIN_CHAT_ID, "📋 No builds yet.", reply_markup=main_menu())
            return
        with open(BUILDS_LOG, 'r') as f:
            builds = json.load(f)
        if not builds:
            bot.send_message(ADMIN_CHAT_ID, "📋 No builds yet.", reply_markup=main_menu())
            return
        text = "📋 *Last 10 Builds*\n\n"
        for i, b in enumerate(builds[-10:], 1):
            text += (
                f"*{i}.* `{b['timestamp'][:16]}`\n"
                f"   📱 Name: `{b.get('app_name', 'N/A')}`\n"
                f"   📦 Main: `{b['main_package']}`\n"
                f"   📦 Companion: `{b['companion_package']}`\n"
                f"   🔐 Chain: `{b['chain']}`\n\n"
            )
        bot.send_message(ADMIN_CHAT_ID, text, parse_mode="Markdown", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"❌ Error: {e}", reply_markup=main_menu())

# ════════════════════════════════════════════════════════
# START POLLING
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Bot running...")
    bot.infinity_polling()
