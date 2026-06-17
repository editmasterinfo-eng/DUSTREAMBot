import asyncio
import os
import urllib.parse
import base64
import time
from pyrogram import Client, filters
from pyrogram.types import Message
import pyrebase

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
API_ID = 33720317
API_HASH = "145db99951f44490f134ac7446126630"
BOT_TOKEN = "8896606844:AAGMLGlI4d1CTmr6YRL1JL30yy-2Z-61jw4"

# ⚠️ VERY IMPORTANT: Jis channel se bot files uthayega uska ID yahan daalein
SOURCE_CHANNEL = -1003897025049  
ADMINS = [8692160077]  # Aapki Admin ID

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
app = Client("AutoBulkBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_session = {}

# ==========================================
# 🛠️ 2. STREAM LINK GENERATOR (Aapke Code Se)
# ==========================================
def get_file_name_robust(message):
    if message.document and message.document.file_name: return message.document.file_name
    if message.video and message.video.file_name: return message.video.file_name
    if message.audio and message.audio.file_name: return message.audio.file_name
    return "Unknown_File"

def get_stream_url(msg):
    """Generates Direct Link using your exact formula"""
    file_name = get_file_name_robust(msg)
    clean_name = file_name.replace("_", " ").replace("-", " ")
    safe_filename = urllib.parse.quote_plus(file_name)
    direct_link = f"{STREAM_URL}/dl/{msg.id}/{safe_filename}"
    return direct_link, clean_name

# ==========================================
# 🤖 3. THE MAGIC COMMANDS (/new)
# ==========================================
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    text = (
        "🔥 **Welcome to Auto-Bulk Database Bot!**\n\n"
        "Send `/new` to create a new Module/Batch.\n"
        "Send `/cancel` to stop at any time."
    )
    await message.reply_text(text)

@app.on_message(filters.command("cancel") & filters.private & filters.user(ADMINS))
async def cancel_cmd(client, message: Message):
    user_session[message.from_user.id] = {"state": "idle"}
    await message.reply_text("🚫 **Process Cancelled!** Send `/new` to start again.")

# --- STEP 1: CREATE NEW BATCH ---
@app.on_message(filters.command("new") & filters.private & filters.user(ADMINS))
async def new_batch_cmd(client, message: Message):
    user_id = message.from_user.id
    user_session[user_id] = {"state": "waiting_for_name"}
    await message.reply_text("📝 **Step 1:** Please send the **Name of the Batch/Module** you want to create (e.g., *Editing Mastery 2.0*).")

# --- STEP 2: GET NAME & ASK FOR FIRST FILE ---
@app.on_message(filters.text & filters.private & filters.user(ADMINS) & ~filters.command(["new", "cancel", "start"]))
async def text_handler(client, message: Message):
    user_id = message.from_user.id
    state = user_session.get(user_id, {}).get("state", "idle")
    
    if state == "waiting_for_name":
        batch_name = message.text.strip()
        user_session[user_id]["batch_name"] = batch_name
        user_session[user_id]["state"] = "waiting_for_first_file"
        
        await message.reply_text(
            f"✅ **Batch Name Saved:** `{batch_name}`\n\n"
            f"📥 **Step 2:** Please **FORWARD** the FIRST FILE of this batch from your Main Channel."
        )

# --- STEP 3 & 4: GET FIRST AND LAST FILE ---
@app.on_message((filters.forwarded | filters.media) & filters.private & filters.user(ADMINS))
async def forward_handler(client, message: Message):
    user_id = message.from_user.id
    state = user_session.get(user_id, {}).get("state", "idle")
    
    # Extract Original Message ID from the forwarded message
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id

    if state == "waiting_for_first_file":
        user_session[user_id]["start_id"] = msg_id
        user_session[user_id]["state"] = "waiting_for_last_file"
        await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 **Step 3:** Now **FORWARD** the LAST FILE of this batch.")
        
    elif state == "waiting_for_last_file":
        user_session[user_id]["end_id"] = msg_id
        user_session[user_id]["state"] = "processing"
        
        start_id = user_session[user_id]["start_id"]
        end_id = msg_id
        batch_name = user_session[user_id]["batch_name"]
        
        await message.reply_text(f"🚀 **Target Locked! (From {start_id} to {end_id})**\n\nScanning channel and uploading to Firebase... Please wait.")
        
        # Start Bulk Processor
        asyncio.create_task(process_bulk_data(client, message, start_id, end_id, batch_name))

# ==========================================
# ⚡ 4. THE AUTO-BULK PROCESSOR
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
                # Fetch message from Channel
                msg = await client.get_messages(SOURCE_CHANNEL, current_id)
                
                # If message is deleted or has no media, skip it
                if msg.empty or not msg.media:
                    continue
                    
                total_scanned += 1
                
                # 1. Generate Link & Name
                direct_link, clean_name = get_stream_url(msg)
                
                # 2. Sorting Logic (Video vs Files)
                if msg.video:
                    category = "videos"
                    videos_added += 1
                else:
                    category = "files"
                    files_added += 1
                
                # 3. Create Payload Data
                payload = {
                    "name": clean_name,
                    "stream_link": direct_link,
                    "msg_id": msg.id,
                    "timestamp": int(time.time()),
                    "type": category
                }
                
                # 4. Push to Firebase under Videos or Files
                ref = db_path.child(category).push(payload)
                db_path.child(category).child(ref['name']).update({"id": ref['name']})
                
                # Update Status every 5 files to prevent telegram flood
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
        # Reset Session
        user_session[message.chat.id] = {"state": "idle"}

# ==========================================
# 🚀 SAFE RUNNER
# ==========================================
if __name__ == "__main__":
    print("🔥 Auto-Bulk Bot is LIVE!")
    app.run()
