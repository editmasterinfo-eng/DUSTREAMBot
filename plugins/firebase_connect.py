import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram import StopPropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import pyrebase
from info import ADMINS

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
SOURCE_CHANNEL = -1003897025049  
STREAM_URL = "https://skillneaststream.onrender.com"

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

def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict): return data.get("title") or data.get("name") or "Unnamed"
    return "Unnamed"

def get_file_name_robust(message):
    if message.document and message.document.file_name: return message.document.file_name
    if message.video and message.video.file_name: return message.video.file_name
    if message.audio and message.audio.file_name: return message.audio.file_name
    if message.caption: return message.caption[:30]
    return "Unknown_File"

def get_stream_url(msg):
    file_name = get_file_name_robust(msg)
    clean_name = file_name.replace("_", " ").replace("-", " ")
    safe_filename = urllib.parse.quote_plus(file_name)
    direct_link = f"{STREAM_URL}/dl/{msg.id}/{safe_filename}"
    return direct_link, clean_name

# ==========================================
# 🛡️ 2. VIP TRACK FILTERS
# ==========================================
async def check_state(_, __, m):
    state = user_session.get(m.from_user.id, {}).get("state", "")
    return bool(state in ["waiting_cat_name", "waiting_batch_name", "waiting_mod_name"])

async def check_files(_, __, m):
    state = user_session.get(m.from_user.id, {}).get("state", "")
    return bool(state in ["waiting_first_file", "waiting_last_file"])

state_filter = filters.create(check_state)
file_filter = filters.create(check_files)

# ==========================================
# 🤖 3. THE /new UI (GROUP=-1 VIP TRACK)
# ==========================================
@Client.on_message(filters.command("new") & filters.private & filters.user(ADMINS), group=-1)
async def new_cmd(client, message: Message):
    user_session[message.from_user.id] = {"state": "selecting_cat"}
    try:
        cats = db.child("categories").get().val()
        buttons = []
        if cats:
            for k, v in cats.items():
                if v and isinstance(v, dict): 
                    buttons.append([InlineKeyboardButton(f"📂 {get_name(v)}", callback_data=f"fbcat_{k}")])
        
        # 🔥 FIX: Added "Create New Category" Button
        buttons.append([InlineKeyboardButton("➕ Create New Category", callback_data="fbnewcat")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")])
        
        await message.reply_text("🔥 **Auto-Bulk Sync Started!**\n\n**Step 1:** Select a Category or Create New:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await message.reply_text(f"Database Error: {e}")
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbcancel"), group=-1)
async def cancel_cb(client, query):
    user_session[query.from_user.id] = {"state": "idle"}
    await query.message.edit_text("🚫 **Process Cancelled.**")
    raise StopPropagation

# 🔥 ADDED: Handler for New Category Button
@Client.on_callback_query(filters.regex("^fbnewcat"), group=-1)
async def new_cat_btn(client, query):
    user_session[query.from_user.id]["state"] = "waiting_cat_name"
    await query.message.edit_text("📝 **Type the name for the NEW CATEGORY:**")
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbcat_"), group=-1)
async def sel_cat(client, query):
    cat_id = query.data.split("_")[1]
    user_session[query.from_user.id].update({"cat_id": cat_id, "state": "selecting_batch"})
    try:
        batches = db.child("categories").child(cat_id).child("batches").get().val()
        buttons = []
        if batches:
            for k, v in batches.items():
                if v and isinstance(v, dict): 
                    buttons.append([InlineKeyboardButton(f"🎬 {get_name(v)}", callback_data=f"fbbatch_{k}")])
        buttons.append([InlineKeyboardButton("➕ Create New Batch", callback_data="fbnewbatch")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")])
        await query.message.edit_text("**Step 2:** Select a Batch or Create New:", reply_markup=InlineKeyboardMarkup(buttons))
    except: pass
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbbatch_"), group=-1)
async def sel_batch(client, query):
    batch_id = query.data.split("_")[1]
    user_session[query.from_user.id].update({"batch_id": batch_id, "state": "selecting_mod"})
    cat_id = user_session[query.from_user.id]["cat_id"]
    try:
        mods = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        if mods:
            for k, v in mods.items():
                if v and isinstance(v, dict): 
                    buttons.append([InlineKeyboardButton(f"📺 {get_name(v)}", callback_data=f"fbmod_{k}")])
        buttons.append([InlineKeyboardButton("➕ Create New Module", callback_data="fbnewmod")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")])
        await query.message.edit_text("**Step 3:** Select a Module or Create New:", reply_markup=InlineKeyboardMarkup(buttons))
    except: pass
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbnewbatch"), group=-1)
async def new_batch_btn(client, query):
    user_session[query.from_user.id]["state"] = "waiting_batch_name"
    await query.message.edit_text("📝 **Type the name for the NEW BATCH:**")
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbnewmod"), group=-1)
async def new_mod_btn(client, query):
    user_session[query.from_user.id]["state"] = "waiting_mod_name"
    await query.message.edit_text("📝 **Type the name for the NEW MODULE:**")
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbmod_"), group=-1)
async def sel_mod(client, query):
    mod_id = query.data.split("_")[1]
    user_session[query.from_user.id].update({"mod_id": mod_id, "state": "waiting_first_file"})
    await query.message.edit_text("✅ **Target Locked!**\n\n📥 **Step 4:** Please **FORWARD** the FIRST FILE of this module from your Main Channel.")
    raise StopPropagation

# ==========================================
# ✍️ 4. TEXT HANDLER (CREATE CAT/BATCH/MOD IN DB)
# ==========================================
@Client.on_message(filters.text & filters.private & state_filter, group=-1)
async def handle_names(client, message: Message):
    user_id = message.from_user.id
    state = user_session[user_id]["state"]
    text = message.text.strip()
    
    # 🔥 Logic for New Category
    if state == "waiting_cat_name":
        ref = db.child("categories").push({"title": text, "id": ""})
        cat_id = ref['name']
        db.child("categories").child(cat_id).update({"id": cat_id})
        
        user_session[user_id].update({"cat_id": cat_id, "state": "selecting_batch"})
        buttons = [
            [InlineKeyboardButton("➕ Create New Batch", callback_data="fbnewbatch")],
            [InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")]
        ]
        await message.reply_text(f"✅ Category `{text}` Created!\n\n**Step 2:** Select or Create a Batch inside it:", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif state == "waiting_batch_name":
        cat_id = user_session[user_id]["cat_id"]
        ref = db.child("categories").child(cat_id).child("batches").push({"title": text, "id": ""})
        batch_id = ref['name']
        db.child("categories").child(cat_id).child("batches").child(batch_id).update({"id": batch_id})
        
        user_session[user_id].update({"batch_id": batch_id, "state": "waiting_mod_name"})
        await message.reply_text(f"✅ Batch `{text}` Created!\n\n📝 **Now type the name for the NEW MODULE inside this batch:**")
        
    elif state == "waiting_mod_name":
        cat_id = user_session[user_id]["cat_id"]
        batch_id = user_session[user_id]["batch_id"]
        ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").push({"name": text, "id": ""})
        mod_id = ref['name']
        db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(mod_id).update({"id": mod_id})
        
        user_session[user_id].update({"mod_id": mod_id, "state": "waiting_first_file"})
        await message.reply_text(f"✅ Module `{text}` Created!\n\n📥 **Step 4:** Please **FORWARD** the FIRST FILE of this module from your Main Channel.")
    
    raise StopPropagation

# ==========================================
# 📥 5. FORWARD HANDLER (FIRST & LAST FILE)
# ==========================================
@Client.on_message((filters.forwarded | filters.media) & filters.private & file_filter, group=-1)
async def handle_files(client, message: Message):
    user_id = message.from_user.id
    state = user_session[user_id]["state"]
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id
    
    if state == "waiting_first_file":
        user_session[user_id].update({"start_id": msg_id, "state": "waiting_last_file"})
        await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 **Step 5:** Now **FORWARD** the LAST FILE.")
        
    elif state == "waiting_last_file":
        user_session[user_id].update({"end_id": msg_id, "state": "processing"})
        start_id = user_session[user_id]["start_id"]
        end_id = msg_id
        
        await message.reply_text(f"🚀 **Target Locked! ({start_id} to {end_id})**\n\nScanning channel and uploading structured data to Firebase...")
        asyncio.create_task(process_bulk_data(client, message, start_id, end_id, user_id))
        
    raise StopPropagation

# ==========================================
# ⚡ 6. THE AUTO-BULK PROCESSOR
# ==========================================
async def process_bulk_data(client, message, start_id, end_id, user_id):
    if start_id > end_id: start_id, end_id = end_id, start_id
        
    status_msg = await message.reply_text("🔄 Fetching and organizing files...")
    
    cat_id = user_session[user_id]["cat_id"]
    batch_id = user_session[user_id]["batch_id"]
    mod_id = user_session[user_id]["mod_id"]
    
    db_path = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(mod_id)
    
    v_count = f_count = scanned = 0
    timestamp_base = int(time.time() * 1000)
    
    try:
        for current_id in range(start_id, end_id + 1):
            try:
                msg = await client.get_messages(SOURCE_CHANNEL, current_id)
                if msg.empty or not getattr(msg, "media", None): continue
                    
                scanned += 1
                direct_link, clean_name = get_stream_url(msg)
                
                target_node = "lectures" if msg.video else "resources"
                if msg.video: v_count += 1
                else: f_count += 1
                
                payload = {
                    "name": clean_name,
                    "link": direct_link,
                    "order": timestamp_base + scanned,
                    "thumbnail": ""
                }
                
                ref = db_path.child(target_node).push(payload)
                db_path.child(target_node).child(ref['name']).update({"id": ref['name']})
                
                if scanned % 5 == 0:
                    await status_msg.edit_text(f"⏳ **Processing...**\nScanned: {scanned}\nVideos (Lectures): {v_count}\nFiles (Resources): {f_count}")
            except Exception as e:
                pass
                
        await status_msg.edit_text(f"✅ **BATCH SUCCESSFULLY SYNCED!**\n━━━━━━━━━━━━━━━━━━━━\n🎬 **Lectures (Videos):** {v_count}\n📑 **Resources (Files):** {f_count}\n\n🔥 *All data securely saved to Firebase Realtime Database!*")
    except Exception as e:
        await status_msg.edit_text(f"❌ **Fatal Error:** {e}")
    finally:
        user_session[user_id] = {"state": "idle"}
