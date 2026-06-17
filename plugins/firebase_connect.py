import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import Message
import pyrebase

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
# ⚠️ Yahan app=Client() ya Bot Token nahi aayega kyunki aapka main bot wo already kar raha hai.

SOURCE_CHANNEL = -1003897025049  # Jis channel se files uthani hain
ADMINS = [8692160077]            # Aapki Admin ID
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

# Session memory
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
# 🛡️ 3. SMART CUSTOM FILTERS (To prevent conflicts)
# ==========================================
# Ye filters check karte hain ki kya user "/new" wale process me hai ya nahi
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

# --- STEP 2: GET NAME & ASK FOR FIRST FILE ---
@Client.on_message(filters.text & filters.private & name_state_filter)
async def text_handler(client, message: Message):
    user_id = message.from_user.id
    batch_name = message.text.strip()
    user_session[user_id]["batch_name"] = batch_name
    user_session[user_id]["state"] = "waiting_for_first_file"
    
    await message.reply_text(
        f"✅ **Batch Name Saved:** `{batch_name}`\n\n"
        f"📥 **Step 2:** Please **FORWARD** the FIRST FILE of this batch from your Main Channel."
    )

# --- STEP 3: GET FIRST FILE ---
@Client.on_message((filters.forwarded | filters.media) & filters.private & first_file_filter)
async def first_file_handler(client, message: Message):
    user_id = message.from_user.id
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id
    
    user_session[user_id]["start_id"] = msg_id
    user_session[user_id]["state"] = "waiting_for_last_file"
    
    await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 **Step 3:** Now **FORWARD** the LAST FILE of this batch.")

# --- STEP 4: GET LAST FILE & START PROCESSING ---
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
    
    # Start Bulk Processor
    asyncio.create_task(process_bulk_data(client, message, start_id, end_id, batch_name))

# ==========================================
# ⚡ 5. THE AUTO-BULK PROCESSOR
# ==========================================
async def process_bulk_data(client, message, start_id, end_id, batch_name):
    # Ensure start is smaller than end
    if start_id > end_id:
        start_id, end_id = end_id, start_id
        
    status_msg = await message.reply_text("🔄 Fetching files from channel...")
    
    total_scanned = 0
    videos_added = 0
    files_added = 0
    
    # Database path
    db_path = db.child("Modules").child(batch_name)
    
    try:
        # Loop through all Message IDs in range
        for current_id in range(start_id, end_id + 1):
            try:
                msg = await client.get_messages(SOURCE_CHANNEL, current_id)
                
                if msg.empty or not msg.media:
                    continue
                    
                total_scanned += 1
                
                # Generate Link & Name
                direct_link, clean_name = get_stream_url(msg)
                
                # Sorting Logic (Video vs Files)
                if msg.video:
                    category = "videos"
                    videos_added += 1
                else:
                    category = "files"
                    files_added += 1
                
                # Create Payload Data
                payload = {
                    "name": clean_name,
                    "stream_link": direct_link,
                    "msg_id": msg.id,
                    "timestamp": int(time.time()),
                    "type": category
                }
                
                # Push to Firebase
                ref = db_path.child(category).push(payload)
                db_path.child(category).child(ref['name']).update({"id": ref['name']})
                
                if total_scanned % 5 == 0:
                    await status_msg.edit_text(f"⏳ **Processing...**\nScanned: {total_scanned}\nVideos Added: {videos_added}\nFiles Added: {files_added}")
                    
            except Exception as e:
                print(f"Skipping ID {current_id} due to error: {e}")
                
        # Final Summary
        final_text = (
            f"✅ **BATCH SUCCESSFULLY SYNCED!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 **Batch Name:** `{batch_name}`\n"
            f"🎬 **Videos Added:** {videos_added}\n"
            f"📑 **Files/PDFs Added:** {files_added}\n\n"
            f"🔥 *All data has been successfully categorized and saved in Firebase!*"
        )
        await status_msg.edit_text(final_text)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Fatal Error:** {e}")
        
    finally:
        user_session[message.chat.id] = {"state": "idle"}
