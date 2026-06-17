import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import Message
import pyrebase
from info import ADMINS  # 🔥 FIX: Ab ye directly aapke main bot se Admin ID lega!

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
SOURCE_CHANNEL = -1003911500529  # Jis channel se files uthani hain
STREAM_URL = "https://dustreambot.onrender.com"

# Firebase Config (Aapki keys)
firebaseConfig = {
    "apiKey": "AIzaSyBhMItJzgDtMmwLesBqs1mUzna3-0WD8Rk",
    "authDomain": "skillneast-669ba.firebaseapp.com",
    "databaseURL": "https://skillneast-669ba-default-rtdb.firebaseio.com",
    "projectId": "skillneast-669ba",
    "storageBucket": "skillneast-669ba.firebasestorage.app",
    "messagingSenderId": "774896061813",
    "appId": "1:774896061813:web:4148313e5f081f18e2973c",
    "measurementId": "G-P19YEBE3P6"
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

user_session = {}

# ==========================================
# 🛠️ 2. STREAM LINK GENERATOR
# ==========================================
def get_file_name_robust(message):
    if message.document and message.document.file_name: return message.document.file_name
    if message.video and message.video.file_name: return message.video.file_name
    if message.audio and message.audio.file_name: return message.audio.file_name
    return "Unknown_File"

def get_stream_url(msg):
    file_name = get_file_name_robust(msg)
    clean_name = file_name.replace("_", " ").replace("-", " ")
    safe_filename = urllib.parse.quote_plus(file_name)
    direct_link = f"{STREAM_URL}/dl/{msg.id}/{safe_filename}"
    return direct_link, clean_name

# ==========================================
# 🛡️ 3. SMART CUSTOM FILTERS
# ==========================================
async def check_name_state(_, __, m):
    return bool(m.from_user and user_session.get(m.from_user.id, {}).get("state") == "waiting_for_name")

async def check_first_file(_, __, m):
    return bool(m.from_user and user_session.get(m.from_user.id, {}).get("state") == "waiting_for_first_file")

async def check_last_file(_, __, m):
    return bool(m.from_user and user_session.get(m.from_user.id, {}).get("state") == "waiting_for_last_file")

name_state_filter = filters.create(check_name_state)
first_file_filter = filters.create(check_first_file)
last_file_filter = filters.create(check_last_file)

# ==========================================
# 🤖 4. THE MAGIC COMMANDS (/new)
# ==========================================
@Client.on_message(filters.command("new") & filters.private & filters.user(ADMINS))
async def new_batch_cmd(client, message: Message):
    user_session[message.from_user.id] = {"state": "waiting_for_name"}
    await message.reply_text("📝 **Step 1:** Please send the **Name of the Batch/Module** you want to create (e.g., *Editing Mastery 2.0*).")

@Client.on_message(filters.command("cancel_fb") & filters.private & filters.user(ADMINS))
async def cancel_cmd(client, message: Message):
    user_session[message.from_user.id] = {"state": "idle"}
    await message.reply_text("🚫 **Process Cancelled!** Send `/new` to start again.")

@Client.on_message(filters.text & filters.private & name_state_filter)
async def text_handler(client, message: Message):
    user_id = message.from_user.id
    batch_name = message.text.strip()
    user_session[user_id]["batch_name"] = batch_name
    user_session[user_id]["state"] = "waiting_for_first_file"
    await message.reply_text(f"✅ **Batch Name Saved:** `{batch_name}`\n\n📥 **Step 2:** Please **FORWARD** the FIRST FILE of this batch from your Main Channel.")

@Client.on_message((filters.forwarded | filters.media) & filters.private & first_file_filter)
async def first_file_handler(client, message: Message):
    user_id = message.from_user.id
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id
    user_session[user_id]["start_id"] = msg_id
    user_session[user_id]["state"] = "waiting_for_last_file"
    await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 **Step 3:** Now **FORWARD** the LAST FILE of this batch.")

@Client.on_message((filters.forwarded | filters.media) & filters.private & last_file_filter)
async def last_file_handler(client, message: Message):
    user_id = message.from_user.id
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id
    
    user_session[user_id]["end_id"] = msg_id
    user_session[user_id]["state"] = "processing"
    
    start_id = user_session[user_id]["start_id"]
    end_id = msg_id
    batch_name = user_session[user_id]["batch_name"]
    
    await message.reply_text(f"🚀 **Target Locked! (From {start_id} to {end_id})**\n\nScanning channel and uploading to Firebase... Please wait.")
    asyncio.create_task(process_bulk_data(client, message, start_id, end_id, batch_name))

# ==========================================
# ⚡ 5. THE AUTO-BULK PROCESSOR
# ==========================================
async def process_bulk_data(client, message, start_id, end_id, batch_name):
    if start_id > end_id:
        start_id, end_id = end_id, start_id
        
    status_msg = await message.reply_text("🔄 Fetching files from channel...")
    total_scanned = videos_added = files_added = 0
    db_path = db.child("Modules").child(batch_name)
    
    try:
        for current_id in range(start_id, end_id + 1):
            try:
                msg = await client.get_messages(SOURCE_CHANNEL, current_id)
                if msg.empty or not msg.media: continue
                    
                total_scanned += 1
                direct_link, clean_name = get_stream_url(msg)
                
                if msg.video: category, videos_added = "videos", videos_added + 1
                else: category, files_added = "files", files_added + 1
                
                payload = {"name": clean_name, "stream_link": direct_link, "msg_id": msg.id, "timestamp": int(time.time()), "type": category}
                ref = db_path.child(category).push(payload)
                db_path.child(category).child(ref['name']).update({"id": ref['name']})
                
                if total_scanned % 5 == 0:
                    await status_msg.edit_text(f"⏳ **Processing...**\nScanned: {total_scanned}\nVideos Added: {videos_added}\nFiles Added: {files_added}")
            except Exception as e:
                print(f"Skipping ID {current_id}: {e}")
                
        await status_msg.edit_text(f"✅ **BATCH SUCCESSFULLY SYNCED!**\n━━━━━━━━━━━━━━━━━━━━\n📂 **Batch Name:** `{batch_name}`\n🎬 **Videos Added:** {videos_added}\n📑 **Files/PDFs Added:** {files_added}\n\n🔥 *All data saved in Firebase!*")
    except Exception as e:
        await status_msg.edit_text(f"❌ **Fatal Error:** {e}")
    finally:
        user_session[message.chat.id] = {"state": "idle"}
