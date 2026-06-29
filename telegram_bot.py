import telebot
import random
import string
import subprocess
import os
import re
import json
import requests
from datetime import datetime

# ════════════════════════════════════════════════════════
# CONFIGURATION — UPDATE THESE BEFORE RUNNING
# ════════════════════════════════════════════════════════

BOT_TOKEN      = "YOUR_TELEGRAM_BOT_TOKEN"   # From @BotFather
bot            = telebot.TeleBot(BOT_TOKEN)
ADMIN_CHAT_ID  = YOUR_CHAT_ID                 # From @userinfobot

# Path to Nova Launcher project on your machine
NOVA_PROJECT   = "/path/to/Nova-Updated"

# Output folder for built APKs
OUTPUT_DIR     = "/home/builds"
BUILDS_LOG     = "/home/builds/builds_log.json"

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
    prefixes   = ["com", "org", "net"]
    companies  = ["settings", "system", "manager", "service", "helper",
                  "assistant", "optimizer", "updater", "cleaner", "support"]
    prefix  = random.choice(prefixes)
    company = random.choice(companies)
    suffix  = ''.join(random.choices(string.ascii_lowercase, k=4))
    return f"{prefix}.{company}.{suffix}"

# ════════════════════════════════════════════════════════
# PROJECT UPDATE FUNCTIONS
# ════════════════════════════════════════════════════════

def update_gradle(nova_pkg, companion_pkg, project_path):
    """Update app/build.gradle with new Nova + companion package names."""
    gradle_path = f"{project_path}/app/build.gradle"
    try:
        with open(gradle_path, 'r') as f:
            content = f.read()

        # Replace namespace — matches any current value
        content = re.sub(
            r"namespace\s+'[^']*'",
            f"namespace '{nova_pkg}'",
            content
        )
        # Replace applicationId
        content = re.sub(
            r'applicationId\s+"[^"]*"',
            f'applicationId "{nova_pkg}"',
            content
        )
        # Replace COMPANION_PACKAGE BuildConfig field
        content = re.sub(
            r'buildConfigField\s+"String",\s+"COMPANION_PACKAGE",\s+"[^"]*"',
            f'buildConfigField "String", "COMPANION_PACKAGE", "\\"{companion_pkg}\\""',
            content
        )

        with open(gradle_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[gradle] Error: {e}")
        return False

def update_manifest_chain(chain_part1, project_path):
    """Embed chain_part1 into AndroidManifest.xml — replaces any existing value."""
    manifest_path = f"{project_path}/app/src/main/AndroidManifest.xml"
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace chain_part1 value regardless of what's currently there
        content = re.sub(
            r'(<meta-data\s+android:name="chain_part1"\s+android:value=")[^"]*(")',
            rf'\g<1>{chain_part1}\g<2>',
            content
        )

        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[manifest] Error: {e}")
        return False

def build_release(project_path):
    """Build release APK using Gradle."""
    try:
        result = subprocess.run(
            ["./gradlew", "assembleRelease", "--no-daemon"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode != 0:
            print(f"[build] Gradle error:\n{result.stderr[-2000:]}")
        return result.returncode == 0
    except Exception as e:
        print(f"[build] Exception: {e}")
        return False

def find_apk(project_path):
    """Find the built release APK."""
    release_path = f"{project_path}/app/build/outputs/apk/release/app-release.apk"
    debug_path   = f"{project_path}/app/build/outputs/apk/debug/app-debug.apk"
    if os.path.exists(release_path):
        return release_path
    if os.path.exists(debug_path):
        return debug_path
    return None

def copy_apk(apk_path, nova_pkg):
    """Copy built APK to output dir with named file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dest = f"{OUTPUT_DIR}/Nova_{nova_pkg}.apk"
    try:
        import shutil
        shutil.copy2(apk_path, dest)
        return dest
    except Exception as e:
        print(f"[copy] Error: {e}")
        return apk_path

def log_build(part1, part2, nova_pkg, companion_pkg):
    """Append build record to builds_log.json."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        builds = []
        if os.path.exists(BUILDS_LOG):
            with open(BUILDS_LOG, 'r') as f:
                builds = json.load(f)
        builds.append({
            "timestamp":        datetime.now().isoformat(),
            "part1":            part1,
            "part2":            part2,
            "nova_package":     nova_pkg,
            "companion_package": companion_pkg
        })
        with open(BUILDS_LOG, 'w') as f:
            json.dump(builds, f, indent=2)
    except Exception as e:
        print(f"[log] Error: {e}")

# ════════════════════════════════════════════════════════
# BOT COMMANDS
# ════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ Unauthorized")
        return
    bot.send_message(ADMIN_CHAT_ID,
        "🤖 *Nova Builder Bot*\n\n"
        "Commands:\n"
        "/build\\_nova — Build Nova APK only\n"
        "/build\\_chain — Build both Nova + Companion APKs\n"
        "/list\\_builds — Show last 10 builds\n"
        "/start — Show this help",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['build_nova'])
def cmd_build_nova(message):
    """Build Nova Launcher only with random package + chain part1."""
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ Unauthorized")
        return

    part1, part2   = generate_chain()
    nova_pkg       = generate_package()
    companion_pkg  = generate_package()  # generated but companion APK not rebuilt here

    bot.send_message(ADMIN_CHAT_ID,
        f"🔗 *NOVA BUILD STARTED*\n\n"
        f"🔐 Chain Part 1: `{part1}`\n"
        f"📦 Nova Package: `{nova_pkg}`\n"
        f"📦 Companion Package: `{companion_pkg}`",
        parse_mode="Markdown"
    )

    bot.send_message(ADMIN_CHAT_ID, "📝 Updating build.gradle...")
    if not update_gradle(nova_pkg, companion_pkg, NOVA_PROJECT):
        bot.send_message(ADMIN_CHAT_ID, "❌ Failed to update build.gradle")
        return

    bot.send_message(ADMIN_CHAT_ID, "📝 Embedding chain in AndroidManifest...")
    if not update_manifest_chain(part1, NOVA_PROJECT):
        bot.send_message(ADMIN_CHAT_ID, "❌ Failed to embed chain in manifest")
        return

    bot.send_message(ADMIN_CHAT_ID, "🔨 Building Nova APK (2–5 mins)...")
    if not build_release(NOVA_PROJECT):
        bot.send_message(ADMIN_CHAT_ID, "❌ Build failed — check gradlew logs")
        return

    apk = find_apk(NOVA_PROJECT)
    if not apk:
        bot.send_message(ADMIN_CHAT_ID, "❌ APK not found after build")
        return

    named_apk = copy_apk(apk, nova_pkg)
    log_build(part1, part2, nova_pkg, companion_pkg)

    with open(named_apk, 'rb') as f:
        bot.send_document(ADMIN_CHAT_ID, f,
            caption=(
                f"✅ *Nova Launcher Ready*\n\n"
                f"📦 Package: `{nova_pkg}`\n"
                f"🔐 Chain Part 1: `{part1}`\n"
                f"🔐 Chain Part 2: `{part2}` ← embed in Companion"
            ),
            parse_mode="Markdown"
        )

    bot.send_message(ADMIN_CHAT_ID,
        f"✅ *BUILD SUCCESSFUL*\n\n"
        f"Full Chain: `{part1}-{part2}`\n"
        f"Nova ready — install on device and test.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['build_chain'])
def cmd_build_chain(message):
    """Build both Nova + Companion APKs with matching chain."""
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ Unauthorized")
        return

    part1, part2  = generate_chain()
    nova_pkg      = generate_package()
    companion_pkg = generate_package()

    bot.send_message(ADMIN_CHAT_ID,
        f"🔗 *FULL CHAIN BUILD STARTED*\n\n"
        f"🔐 Chain Part 1: `{part1}` → Nova manifest\n"
        f"🔐 Chain Part 2: `{part2}` → Companion source\n"
        f"📦 Nova Package: `{nova_pkg}`\n"
        f"📦 Companion Package: `{companion_pkg}`",
        parse_mode="Markdown"
    )

    bot.send_message(ADMIN_CHAT_ID, "📝 Updating Nova build.gradle + manifest...")
    if not update_gradle(nova_pkg, companion_pkg, NOVA_PROJECT):
        bot.send_message(ADMIN_CHAT_ID, "❌ Failed to update Nova build.gradle")
        return
    if not update_manifest_chain(part1, NOVA_PROJECT):
        bot.send_message(ADMIN_CHAT_ID, "❌ Failed to embed chain in Nova manifest")
        return

    bot.send_message(ADMIN_CHAT_ID, "🔨 Building Nova APK...")
    if not build_release(NOVA_PROJECT):
        bot.send_message(ADMIN_CHAT_ID, "❌ Nova build failed")
        return

    apk = find_apk(NOVA_PROJECT)
    if not apk:
        bot.send_message(ADMIN_CHAT_ID, "❌ Nova APK not found after build")
        return

    named_apk = copy_apk(apk, nova_pkg)
    log_build(part1, part2, nova_pkg, companion_pkg)

    with open(named_apk, 'rb') as f:
        bot.send_document(ADMIN_CHAT_ID, f,
            caption=(
                f"✅ *Nova Launcher APK*\n\n"
                f"📦 Package: `{nova_pkg}`\n"
                f"🔐 Chain Part 1 embedded: `{part1}`"
            ),
            parse_mode="Markdown"
        )

    bot.send_message(ADMIN_CHAT_ID,
        f"✅ *NOVA DONE*\n\n"
        f"⚠️ Companion APK build requires companion source.\n"
        f"Embed Part 2 `{part2}` in companion source and build separately.\n\n"
        f"Full Chain: `{part1}-{part2}`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['list_builds'])
def cmd_list_builds(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ Unauthorized")
        return
    try:
        if not os.path.exists(BUILDS_LOG):
            bot.send_message(ADMIN_CHAT_ID, "📋 No builds yet.")
            return
        with open(BUILDS_LOG, 'r') as f:
            builds = json.load(f)
        if not builds:
            bot.send_message(ADMIN_CHAT_ID, "📋 No builds yet.")
            return
        text = "📋 *Last 10 Builds*\n\n"
        for i, b in enumerate(builds[-10:], 1):
            text += (
                f"*{i}.* `{b['timestamp'][:16]}`\n"
                f"   Nova: `{b['nova_package']}`\n"
                f"   Companion: `{b['companion_package']}`\n"
                f"   Chain: `{b['part1']}-{b['part2']}`\n\n"
            )
        bot.send_message(ADMIN_CHAT_ID, text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"❌ Error: {e}")

# ════════════════════════════════════════════════════════
# START
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Bot running...")
    print(f"Token  : {BOT_TOKEN[:20]}...")
    print(f"Chat ID: {ADMIN_CHAT_ID}")
    print(f"Project: {NOVA_PROJECT}")
    bot.infinity_polling()
