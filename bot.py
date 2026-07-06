import re
import asyncio
import logging
import time
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from config import BOT_TOKEN, OWNER_IDS, DEVELOPER_USERNAME, CHANNEL_INVITE,
MAX_WARNINGS
from database import (
    init_db, add_warning, reset_warnings,
    is_whitelisted, whitelist_user, unwhitelist_user, get_whitelist,
    register_chat, get_all_chats
)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
START_IMAGE = "https://files.catbox.moe/7w33t6.jpg"
AUTO_DELETE_SECONDS = 15
# ── Small caps font ────────────────────────────────────────────────────────────
WELCOME_TEXT = """👋 ᴡᴇʟᴄᴏᴍᴇ, {first_name}!
ʙɪᴏ ʟɪɴᴋ ᴘʀᴏᴛᴇᴄᴛᴏʀ ᴋᴇᴇᴘꜱ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴄᴏᴍᴍᴜɴɪᴛʏ ꜱᴀꜰᴇ ʙʏ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇᴛᴇᴄᴛɪɴɢ ᴀɴᴅ ʙʟᴏᴄᴋɪɴɢ ᴜɴᴡᴀɴᴛᴇᴅ ʙɪᴏ ʟɪɴᴋꜱ.
🔒 ɪɴꜱᴛᴀɴᴛ ʙɪᴏ ʟɪɴᴋ ᴅᴇᴛᴇᴄᴛɪᴏɴ
⚡  ʀᴇᴀʟ-ᴛɪᴍᴇ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ
🛡️ ᴘᴏᴡᴇʀꜰᴜʟ ᴀᴅᴍɪɴ ᴛᴏᴏʟꜱ
✨  ꜰᴀꜱᴛ, ʀᴇʟɪᴀʙʟᴇ, ᴀɴᴅ ᴇᴀꜱʏ ᴛᴏ ᴜꜱᴇ
ᴛᴀᴘ ʜᴇʟᴘ ᴛᴏ ᴠɪᴇᴡ ᴛʜᴇ ꜱᴇᴛᴜᴘ ɢᴜɪᴅᴇ, ꜰᴇᴀᴛᴜʀᴇꜱ, ᴀɴᴅ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅꜱ.
ᴘʀᴏᴛᴇᴄᴛ ʏᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ᴡɪᴛʜ ᴄᴏɴꜰɪᴅᴇɴᴄᴇ."""
HELP_TEXT = """📖 ʜᴇʟᴘ & ᴄᴏᴍᴍᴀɴᴅꜱ
👮 ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅꜱ:
/whitelist @user — ᴀᴅᴅ ᴜꜱᴇʀ ᴛᴏ ᴡʜɪᴛᴇʟɪꜱᴛ
/unwhitelist @user — ʀᴇᴍᴏᴠᴇ ꜰʀᴏᴍ ᴡʜɪᴛᴇʟɪꜱᴛ
/whitelistinfo — ꜱʜᴏᴡ ᴀʟʟ ᴡʜɪᴛᴇʟɪꜱᴛᴇᴅ ᴜꜱᴇʀꜱ
/ping — ᴄʜᴇᴄᴋ ʙᴏᴛ ꜱᴘᴇᴇᴅ
⚙️ ʜᴏᴡ ɪᴛ ᴡᴏʀᴋꜱ:
ʙᴏᴛ ᴅᴇᴛᴇᴄᴛꜱ ᴀʟʟ ʟɪɴᴋ ᴛʏᴘᴇꜱ ɪɴ ᴜꜱᴇʀ ʙɪᴏ
ᴜꜱᴇʀ ɢᴇᴛꜱ 3 ᴡᴀʀɴɪɴɢꜱ — 4ᴛʜ = 🔇 ᴘᴇʀᴍᴀɴᴇɴᴛ ᴍᴜᴛᴇ
ᴀᴅᴍɪɴꜱ ᴀɴᴅ ᴡʜɪᴛᴇʟɪꜱᴛᴇᴅ ᴜꜱᴇʀꜱ ᴀʀᴇ ᴇxᴇᴍᴘᴛ"""
def has_link(text: str) -> bool:
    """
    Detects ANY type of link in text:
    - URLs: http://, https://, www.
    - Telegram: t.me/, me.t/, @username
    - Domains: .com, .in, .shop, .org, etc
    - Hidden links mixed with text
    """
    if not text:
        return False
    text_lower = text.lower()
    # 1. Check for http/https/www
    if 'http://' in text_lower or 'https://' in text_lower or 'www.' in text_lower:
        return True
    # 2. Check for Telegram links
    if 't.me/' in text_lower or 'me.t/' in text_lower:
        return True
    # 3. Check for @username
    if re.search(r'@[a-zA-Z0-9_]{3,}', text):
        return True
    # 4. Check for domain extensions
    if re.search(r'\.(com|in|shop|org|net|io|co|xyz|me|info|site|web|app|store|link|tv|pro|club|tech|dev|ai|bot|ru|uk|us|de|fr|it|es|nl|br|jp|cn|pk|bd|ng|za|mx)\b', text_lower):
        return True
    # 5. Check for // (double slash like me.t//)
    if '//' in text and 'http' not in text_lower:
        return True
    # 6. Check for email-like patterns
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
        return True
    return False
# ── Auto-delete ────────────────────────────────────────────────────────────────
async def auto_delete(message, delay: int = AUTO_DELETE_SECONDS):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass
def schedule_delete(message):
    asyncio.ensure_future(auto_delete(message))
# ── Helper: Check admin ────────────────────────────────────────────────────────
async def is_admin(context, chat_id: int, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False
# ── Helper: Send and auto-delete ───────────────────────────────────────────────
async def send_and_autodelete(context, chat_id: int, text: str):
    try:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown"
        )
        schedule_delete(msg)
        return msg
    except Exception as e:
        logger.error(f"Error: {e}")
# ── /start command ────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != "private":
        try:
            await update.message.delete()
        except Exception:
            pass
        return
    keyboard = [
        [InlineKeyboardButton("➕    ᴀᴅᴅ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ  ➕ ",
                            url="https://t.me/BioLinkProtectorBot?startgroup=true")],
        [InlineKeyboardButton("📋  ʜᴇʟᴘ & ᴄᴏᴍᴍᴀɴᴅꜱ", callback_data="help")],
        [
            InlineKeyboardButton("👨‍💻  ᴅᴇᴠᴇʟᴏᴘᴇʀ  ↗", url=f"https://t.me/{DEVELOPER_USERNAME}"),
            InlineKeyboardButton("📢  ᴄʜᴀɴɴᴇʟ  ↗", url=CHANNEL_INVITE)
        ]
    ]
    await update.message.reply_photo(
        photo=START_IMAGE,
        caption=WELCOME_TEXT.format(first_name=user.first_name or "ᴜꜱᴇʀ"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
# ── Help callback ──────────────────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.message.chat.type == "private" and query.data == "help":
        await query.message.reply_text(HELP_TEXT)
# ── /ping command ──────────────────────────────────────────────────────────────
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    t = time.monotonic()
    msg = await update.message.reply_text("🏓 ᴘɪɴɢɪɴɢ...")
    ms = int((time.monotonic() - t) * 1000)
    await msg.edit_text(f"🏓 ᴘᴏɴɢ!\n⚡  ʀᴇꜱᴘᴏɴꜱᴇ: {ms}ms\n✅  ʙᴏᴛ ɪꜱ ᴀʟɪᴠᴇ ᴀɴᴅ
ʀᴜɴɴɪɴɢ!")
    if chat.type != "private":
        schedule_delete(msg)
        try:
            await update.message.delete()
        except Exception:
            pass
# ── /whitelist command ─────────────────────────────────────────────────────────
async def cmd_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        await update.message.reply_text("❌  ɢʀᴏᴜᴘꜱ ᴏɴʟʏ.")
        return
    if not await is_admin(context, chat.id, user.id):
        msg = await update.message.reply_text("❌  ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ.")        schedule_delete(msg)
        try:
            await update.message.delete()
        except Exception:
            pass
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            m = await context.bot.get_chat_member(chat.id, context.args[0].lstrip("@"))
            target = m.user
        except Exception:
            pass
    if not target:
        msg = await update.message.reply_text("❌  ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ ᴏʀ ᴘʀᴏᴠɪᴅᴇ
@ᴜꜱᴇʀɴᴀᴍᴇ.")
        schedule_delete(msg)
        try:
            await update.message.delete()
        except Exception:
            pass
        return
    await whitelist_user(target.id, chat.id, user.id)
    await reset_warnings(target.id, chat.id)
    msg = await update.message.reply_text(
        f"✅  {target.full_name} ᴀᴅᴅᴇᴅ ᴛᴏ ᴡʜɪᴛᴇʟɪꜱᴛ. ᴛʜᴇʏ ᴄᴀɴ ɴᴏᴡ ᴘᴏꜱᴛ ʟɪɴᴋꜱ ꜰʀᴇᴇʟʏ."
    )
    schedule_delete(msg)
    try:
        await update.message.delete()
    except Exception:
        pass
# ── /unwhitelist command ───────────────────────────────────────────────────────
async def cmd_unwhitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        await update.message.reply_text("❌  ɢʀᴏᴜᴘꜱ ᴏɴʟʏ.")
        return
    if not await is_admin(context, chat.id, user.id):
        msg = await update.message.reply_text("❌  ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ.")        schedule_delete(msg)
        try:
            await update.message.delete()
        except Exception:
            pass
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            m = await context.bot.get_chat_member(chat.id, context.args[0].lstrip("@"))
            target = m.user
        except Exception:
            pass
    if not target:
        msg = await update.message.reply_text("❌  ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ ᴏʀ ᴘʀᴏᴠɪᴅᴇ
@ᴜꜱᴇʀɴᴀᴍᴇ.")
        schedule_delete(msg)
        try:
            await update.message.delete()
        except Exception:
            pass
        return
    await unwhitelist_user(target.id, chat.id)
    msg = await update.message.reply_text(
        f"⚠️ {target.full_name} ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴡʜɪᴛᴇʟɪꜱᴛ."
    )
    schedule_delete(msg)
    try:
        await update.message.delete()
    except Exception:
        pass
# ── /whitelistinfo command ─────────────────────────────────────────────────────
async def cmd_whitelistinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        await update.message.reply_text("❌  ɢʀᴏᴜᴘꜱ ᴏɴʟʏ.")
        return
    if not await is_admin(context, chat.id, user.id):
        msg = await update.message.reply_text("❌  ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ.")        schedule_delete(msg)
        try:
            await update.message.delete()
        except Exception:
            pass
        return
    wl_ids = await get_whitelist(chat.id)
    if not wl_ids:
        msg = await update.message.reply_text("📋 ɴᴏ ᴜꜱᴇʀꜱ ᴡʜɪᴛᴇʟɪꜱᴛᴇᴅ.")
        schedule_delete(msg)
        try:
            await update.message.delete()
        except Exception:
            pass
        return
    lines = ["📋 ᴡʜɪᴛᴇʟɪꜱᴛᴇᴅ ᴜꜱᴇʀꜱ:\n"]
    for uid in wl_ids:
        try:
            m = await context.bot.get_chat_member(chat.id, uid)
            lines.append(f"• {m.user.full_name}")
        except Exception:
            lines.append(f"• ɪᴅ: {uid}")
    msg = await update.message.reply_text("\n".join(lines))
    schedule_delete(msg)
    try:
        await update.message.delete()
    except Exception:
        pass
# ── /broadcast command ─────────────────────────────────────────────────────────
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in OWNER_IDS:
        await update.message.reply_text("❌  ᴏᴡɴᴇʀꜱ ᴏɴʟʏ.")
        return
    if not context.args:
        await update.message.reply_text("📢 ᴜꜱᴀɢᴇ: /broadcast ʏᴏᴜʀ ᴍᴇꜱꜱᴀɢᴇ")
        return
    text = " ".join(context.args)
    chat_ids = await get_all_chats()
    if not chat_ids:
        await update.message.reply_text("❌  ɴᴏ ɢʀᴏᴜᴘꜱ ʀᴇɢɪꜱᴛᴇʀᴇᴅ ʏᴇᴛ.")
        return
    status = await update.message.reply_text(f"📡 ʙʀᴏᴀᴅᴄᴀꜱᴛɪɴɢ ᴛᴏ {len(chat_ids)} ɢʀᴏᴜᴘꜱ...")
    success = 0
    failed = 0
    for cid in chat_ids:
        try:
            await context.bot.send_message(chat_id=cid, text=f"📢 ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴍᴇꜱꜱᴀɢᴇ\n\n{text}")
            success += 1
        except Exception as e:
            logger.warning(f"Broadcast failed {cid}: {e}")
            failed += 1
    await status.edit_text(
        f"✅  ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇ\n📨 ꜱᴇɴᴛ: {success}\n❌  ꜰᴀɪʟᴇᴅ: {failed}"
    )
# ── Message Handler - CHECK BIO FOR LINKS ──────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not user or not chat:
        return
    if chat.type == "private":
        return
    # Register group
    await register_chat(chat.id, chat.title or "Unknown")
    if user.is_bot:
        return
    if user.id in OWNER_IDS:
        return
    if await is_admin(context, chat.id, user.id):
        return
    if await is_whitelisted(user.id, chat.id):
        return
    # ── CHECK BIO ──
    try:
        user_bio = await context.bot.get_chat(user.id)
        bio_text = user_bio.bio or ""
        if has_link(bio_text):
            # Delete user message
            try:
                await message.delete()
            except Exception:
                pass
            # Add warning
            warn_count = await add_warning(user.id, chat.id)
            if warn_count > MAX_WARNINGS:
                # Mute
                try:
                    await context.bot.restrict_chat_member(
                        chat_id=chat.id,
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False)
                    )
                except Exception:
                    pass
                await send_and_autodelete(
                    context, chat.id,
                    f"🔇 [{user.full_name}](tg://user?id={user.id}) ʜᴀꜱ ʙᴇᴇɴ
ᴍᴜᴛᴇᴅ!\n\n"
                    f"ʀᴇᴀꜱᴏɴ: ʙɪᴏ ʟɪɴᴋ ᴅᴇᴛᴇᴄᴛᴇᴅ {warn_count} ᴛɪᴍᴇꜱ.\n"
                    "ᴄᴏɴᴛᴀᴄᴛ ᴀɴ ᴀᴅᴍɪɴ ᴛᴏ ɢᴇᴛ ᴜɴᴍᴜᴛᴇᴅ."
                )
            else:
                icons = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣"}
                icon = icons.get(warn_count, "⚠️")
                remaining = MAX_WARNINGS - warn_count
                next_action = (
                    "⛔  ɴᴇxᴛ ᴀᴄᴛɪᴏɴ = 🔇 ᴘᴇʀᴍᴀɴᴇɴᴛ ᴍᴜᴛᴇ"
                    if remaining == 0
                    else f"🔔 {remaining} ᴡᴀʀɴɪɴɢ(ꜱ) ʀᴇᴍᴀɪɴɪɴɢ"
                )
                await send_and_autodelete(
                    context, chat.id,
                    f"⚠️ ᴡᴀʀɴɪɴɢ {icon} — [{user.full_name}](tg://user?id={user.id})\n\n"
                    f"🔗 ʙɪᴏ ʟɪɴᴋ ᴅᴇᴛᴇᴄᴛᴇᴅ!\n\n"
                    f"📊 ᴡᴀʀɴɪɴɢꜱ: {warn_count}/{MAX_WARNINGS}\n"
                    f"{next_action}"
                )
    except Exception as e:
        logger.warning(f"Bio check error: {e}")
        pass
# ── Initialize & Start ────────────────────────────────────────────────────────
async def post_init(application: Application):
    await init_db()
    logger.info("Database initialized successfully.")
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("whitelist", cmd_whitelist))
    app.add_handler(CommandHandler("unwhitelist", cmd_unwhitelist))
    app.add_handler(CommandHandler("whitelistinfo", cmd_whitelistinfo))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION | filters.Sticker.ALL | filters.PHOTO | filters.VIDEO, handle_message))
    logger.info("Bio Link Protector Bot is RUNNING...")
    app.run_polling(drop_pending_updates=True)
if __name__ == "__main__":
    main()
