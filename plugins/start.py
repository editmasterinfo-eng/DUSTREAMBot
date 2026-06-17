import os
import urllib.parse
import base64
import binascii
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import LOG_CHANNEL, LINK_URL, ADMINS, STREAM_URL
from Script import script
from plugins.database import checkdb, db, get_count, get_withdraw, record_withdraw

# --- Helper Functions ---

def get_file_name_robust(message):
    if message.caption:
        return message.caption # Use caption as name if available
    if message.document and getattr(message.document, 'file_name', None):
        return message.document.file_name
    if message.video and getattr(message.video, 'file_name', None):
        return message.video.file_name
    if message.audio and getattr(message.audio, 'file_name', None):
        return message.audio.file_name
    return "Unknown_File"

async def get_stream_url(client, message_id, file_name_override=None):
    """Generates Direct Link with Clean Name (Spaces instead of underscores)"""
    try:
        msg = await client.get_messages(LOG_CHANNEL, message_id)
        file_name = file_name_override if file_name_override else get_file_name_robust(msg)
        
        # 1. Clean Name Logic
        clean_name = file_name.replace("_", " ")
        
        # 🔥 FIX: URL safe encoding without '+' sign
        safe_filename = urllib.parse.quote(file_name)
        
        # 🔥 FIX: Direct Link me Double slashes block
        base_url = STREAM_URL.rstrip('/')
        direct_link = f"{base_url}/dl/{message_id}/{safe_filename}"
        
        return direct_link, clean_name
            
    except Exception as e:
        print(f"Error in get_stream_url: {e}")
        return None, None

async def encode(string):
    string_bytes = str(string).encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    try:
        base64_string = base64_string.strip("=")
        base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
        string_bytes = base64.urlsafe_b64decode(base64_bytes)
        string = string_bytes.decode("ascii")
        return string
    except Exception:
        return None


# --- Start Command ---

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    # Check if user exists
    if not await checkdb.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        name = await client.ask(message.chat.id, "<b>Welcome To VJ Disk.\n\nSend Business Name:\nEx :- <code>Tech VJ</code></b>")
        if name.text:
            await db.set_name(message.from_user.id, name=name.text)
        else:
            return await message.reply("Wrong Input. /start again.")
        
        link = await client.ask(message.chat.id, "<b>Send Telegram Channel Link:\nEx :- <code>https://t.me/VJ_Bots</code></b>")
        if link.text and link.text.startswith(('http://', 'https://')):
            await db.set_link(message.from_user.id, link=link.text)
        else:
            return await message.reply("Wrong Input. /start again.")
            
        await checkdb.add_user(message.from_user.id, message.from_user.first_name)
        return await message.reply("<b>Account Created Successfully! 🎉\n\nUse /quality for quality options.\nSend any file to get direct link.</b>")
    
    else:
        # Existing User - Show Welcome & Admin Panel Button
        buttons = [[InlineKeyboardButton("✨ Update Channel", url="https://t.me/VJ_Disk")]]
        
        # Add Firebase Button ONLY for Admins
        if message.from_user.id in ADMINS:
            buttons.append([InlineKeyboardButton("🔥 Open Firebase Panel", callback_data="fb_cat_list")])
            
        await client.send_message(
            chat_id=message.from_user.id,
            text=script.START_TXT.format(message.from_user.mention),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        return


# --- Update Command ---
@Client.on_message(filters.command("update") & filters.private)
async def update(client, message):
    name = await client.ask(message.chat.id, "<b>Send New Business Name:\n/cancel to cancel</b>")
    if name.text == "/cancel": return await message.reply("Cancelled")
    if name.text: await db.set_name(message.from_user.id, name=name.text)
    
    link = await client.ask(message.chat.id, "<b>Send New Channel Link:</b>")
    if link.text and link.text.startswith(('http://', 'https://')):
        await db.set_link(message.from_user.id, link=link.text)
        await message.reply("<b>Updated Successfully.</b>")
    else:
        await message.reply("Invalid Link.")


# --- File Handler (Clean Name & Direct Link) ---
@Client.on_message(filters.private & (filters.document | filters.video | filters.photo | filters.audio))
async def universal_handler(client, message):
    if not message.media: return

    # Save to Log Channel
    try:
        log_msg = await message.copy(LOG_CHANNEL)
    except Exception as e:
        print(f"Error copying to log: {e}")
        return await message.reply("Error saving file. Check bot permissions.")

    # Get Link & Clean Name
    direct_link, clean_name = await get_stream_url(client, log_msg.id)
    
    if not direct_link:
        return await message.reply("Error generating link.")

    # Generate Website Link
    params = {'u': message.from_user.id, 'w': str(log_msg.id), 's': str(0), 't': str(0)}
    base_link_url = LINK_URL.rstrip('/')
    website_url = f"{base_link_url}?Tech_VJ={await encode(urllib.parse.urlencode(params))}"
    
    # Reply Text
    text = (
        f"**📂 Name:** `{clean_name}`\n\n"
        f"**🔗 Direct Stream URL:**\n`{direct_link}`\n\n"
        f"**🌐 Website Link:**\n`{website_url}`"
    )
    
    # Buttons
    buttons = [
        [InlineKeyboardButton("⬇️ Direct Download", url=direct_link)],
        [InlineKeyboardButton("🖥️ Watch Online", url=website_url)]
    ]
    
    # Add Firebase Button if Admin
    if message.from_user.id in ADMINS:
        buttons.append([InlineKeyboardButton("🔥 Add to Firebase", callback_data="fb_cat_list")])

    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )


# --- Quality Command ---
@Client.on_message(filters.private & filters.command("quality"))
async def quality_link(client, message):
    # Simplified Logic for Quality
    await message.reply("Quality Feature is currently simplified. Use direct file send for best links.")


# --- Link Processing (Decryption) ---
@Client.on_message(filters.private & filters.text & ~filters.command(["account", "withdraw", "notify", "quality", "start", "update", "firebase"]))
async def link_start(client, message):
    if not message.text.startswith(LINK_URL): return
    
    try:
        link_part = message.text.split("?Tech_VJ=")[1]
        decoded = await decode(link_part)
        if not decoded: return await message.reply("Invalid Link")
        
        # Parse params
        data = {x.split("=")[0]: x.split("=")[1] for x in decoded.split("&")}
        msg_id = data.get('w')
        
        if msg_id and msg_id != "0":
            link, name = await get_stream_url(client, int(msg_id))
            await message.reply(
                f"**🎬 Video:** `{name}`\n\n**🔗 Direct Link:**\n`{link}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Download", url=link)]])
            )
        else:
            await message.reply("Content not found.")
            
    except Exception as e:
        await message.reply(f"Error: {e}")


# --- Account & Withdraw ---
@Client.on_message(filters.private & filters.command("account"))
async def show_account(client, message):
    clicks = get_count(message.from_user.id) or 0
    balance = f"{clicks / 1000.0:.2f}"
    await message.reply(f"**🆔 API Key:** `{message.from_user.id}`\n**▶️ Plays:** {clicks}\n**💰 Balance:** ${balance}")


@Client.on_message(filters.private & filters.command("withdraw"))
async def show_withdraw(client, message):
    clicks = get_count(message.from_user.id) or 0
    if clicks < 1000:
        return await message.reply("Minimum withdrawal is 1000 Plays.")
    
    if get_withdraw(message.from_user.id):
        return await message.reply("Withdrawal already pending.")
        
    await client.send_message(ADMINS[0], f"Withdraw Request from {message.from_user.id}\nPlays: {clicks}")
    record_withdraw(message.from_user.id, True)
    await message.reply("Withdrawal request sent.")


@Client.on_message(filters.private & filters.command("notify") & filters.user(ADMINS))
async def show_notify(client, message):
    await message.reply("Use manual notification for now.")
