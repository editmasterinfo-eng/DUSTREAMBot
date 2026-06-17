import asyncio
import os
import urllib.parse
import time
import re
from pyrogram import Client, filters
from pyrogram import StopPropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import pyrebase

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
SOURCE_CHANNEL = -1003897025049  
STREAM_URL = "https://dustreambot.onrender.com"  # 🔥 Aapka Naya URL
ADMINS = [8692160077]  # Aapki Admin ID

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
# 🛠️ 2. HELPERS & GENERATORS
# ==========================================
def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict): return data.get("title") or data.get("name") or "Unnamed"
    return "Unnamed"

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

def extract_module_name(caption):
    """🔥 Extract Module Name from Caption (e.g., /folder Main/Subfolder -> Subfolder)"""
    if not caption: return "Main Files"
    match = re.search(r'/folder\s+([^\n<]+)', caption)
    if match:
        path = match.group(1).strip()
        parts = [p.strip() for p in path.split('/') if p.strip()]
        if len(parts) > 0:
            return parts[-1]  # Returns the last folder name as Module Name
    return "Main Files"

# ==========================================
# 🛡️ 3. VIP TRACK FILTERS
# ==========================================
async def check_state(_, __, m):
    state = user_session.get(m.from_user.id, {}).get("state", "")
    return bool(state in ["waiting_cat_name", "waiting_batch_name", "waiting_mod_name"])

async def check_files(_, __, m):
    state = user_session.get(m.from_user.id, {}).get("state", "")
    return bool(state in ["waiting_first_file_manual", "waiting_last_file_manual", "waiting_first_file_auto", "waiting_last_file_auto"])

state_filter = filters.create(check_state)
file_filter = filters.create(check_files)

# ==========================================
# 🤖 4. NEW & SEE COMMANDS
# ==========================================
@Client.on_message(filters.command("new") & filters.private & filters.user(ADMINS), group=-1)
async def new_cmd(client, message: Message):
    user_session[message.from_user.id] = {"state": "waiting_cat_name"}
    await message.reply_text("🔥 **Auto-Bulk Creation Started!**\n\n📝 **Step 1:** Type the name for the **NEW CATEGORY**:")
    raise StopPropagation

@Client.on_message(filters.command("see") & filters.private & filters.user(ADMINS), group=-1)
async def see_cmd(client, message: Message):
    user_session[message.from_user.id] = {"state": "selecting_cat"}
    try:
        cats = db.child("categories").get().val()
        buttons = []
        if cats:
            for k, v in cats.items():
                if v and isinstance(v, dict): 
                    buttons.append([InlineKeyboardButton(f"📂 {get_name(v)}", callback_data=f"fbcat_{k}")])
        buttons.append([InlineKeyboardButton("➕ Create New Category", callback_data="fbnewcat")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")])
        await message.reply_text("👁 **Database Viewer:**\nSelect a Category:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await message.reply_text(f"Database Error: {e}")
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbcancel"), group=-1)
async def cancel_cb(client, query):
    user_session[query.from_user.id] = {"state": "idle"}
    await query.message.edit_text("🚫 **Process Cancelled.**")
    raise StopPropagation

# ==========================================
# 🗂️ 5. NAVIGATION MENUS
# ==========================================
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
                if v and isinstance(v, dict): buttons.append([InlineKeyboardButton(f"🎬 {get_name(v)}", callback_data=f"fbbatch_{k}")])
        buttons.append([InlineKeyboardButton("➕ Create New Batch", callback_data="fbnewbatch")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")])
        await query.message.edit_text("**Select a Batch or Create New:**", reply_markup=InlineKeyboardMarkup(buttons))
    except: pass
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbnewbatch"), group=-1)
async def new_batch_btn(client, query):
    user_session[query.from_user.id]["state"] = "waiting_batch_name"
    await query.message.edit_text("📝 **Type the name for the NEW BATCH:**")
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbbatch_"), group=-1)
async def sel_batch(client, query):
    batch_id = query.data.split("_")[1]
    user_session[query.from_user.id].update({"batch_id": batch_id})
    
    # 🔥 THE MAGIC MENU: Automatic vs Manual
    buttons = [
        [InlineKeyboardButton("⚡ AUTOMATIC (Smart Caption)", callback_data="fbauto_mode")],
        [InlineKeyboardButton("➕ New Module (Manual)", callback_data="fbnewmod")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")]
    ]
    await query.message.edit_text("🎯 **Batch Locked! Choose Upload Mode:**\n\n⚡ **AUTOMATIC:** Bot will read captions and auto-create modules for you.\n➕ **MANUAL:** Create 1 module and put all files inside it.", reply_markup=InlineKeyboardMarkup(buttons))
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbnewmod"), group=-1)
async def new_mod_btn(client, query):
    user_session[query.from_user.id]["state"] = "waiting_mod_name"
    await query.message.edit_text("📝 **Type the name for the NEW MODULE:**")
    raise StopPropagation

@Client.on_callback_query(filters.regex("^fbauto_mode"), group=-1)
async def auto_mode_btn(client, query):
    user_session[query.from_user.id]["state"] = "waiting_first_file_auto"
    await query.message.edit_text("⚡ **AUTOMATIC MODE ACTIVATED!**\n\n📥 Please **FORWARD** the FIRST FILE from your Channel.")
    raise StopPropagation

# ==========================================
# ✍️ 6. TEXT CREATION HANDLERS
# ==========================================
@Client.on_message(filters.text & filters.private & state_filter, group=-1)
async def handle_names(client, message: Message):
    user_id = message.from_user.id
    state = user_session[user_id]["state"]
    text = message.text.strip()
    
    if state == "waiting_cat_name":
        ref = db.child("categories").push({"title": text, "id": ""})
        cat_id = ref['name']
        db.child("categories").child(cat_id).update({"id": cat_id})
        user_session[user_id].update({"cat_id": cat_id, "state": "waiting_batch_name"})
        await message.reply_text(f"✅ Category `{text}` Created!\n\n📝 **Now type the name for the NEW BATCH inside it:**")
        
    elif state == "waiting_batch_name":
        cat_id = user_session[user_id]["cat_id"]
        ref = db.child("categories").child(cat_id).child("batches").push({"title": text, "id": ""})
        batch_id = ref['name']
        db.child("categories").child(cat_id).child("batches").child(batch_id).update({"id": batch_id})
        user_session[user_id].update({"batch_id": batch_id})
        
        buttons = [
            [InlineKeyboardButton("⚡ AUTOMATIC (Smart Caption)", callback_data="fbauto_mode")],
            [InlineKeyboardButton("➕ New Module (Manual)", callback_data="fbnewmod")]
        ]
        await message.reply_text(f"✅ Batch `{text}` Created!\n\n🎯 **Choose Upload Mode:**", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif state == "waiting_mod_name":
        cat_id, batch_id = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
        ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").push({"name": text, "id": ""})
        mod_id = ref['name']
        db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(mod_id).update({"id": mod_id})
        user_session[user_id].update({"mod_id": mod_id, "state": "waiting_first_file_manual"})
        await message.reply_text(f"✅ Module `{text}` Created!\n\n📥 **Please FORWARD the FIRST FILE of this module.**")
    
    raise StopPropagation

# ==========================================
# 📥 7. FORWARD HANDLER
# ==========================================
@Client.on_message((filters.forwarded | filters.media) & filters.private & file_filter, group=-1)
async def handle_files(client, message: Message):
    user_id = message.from_user.id
    state = user_session[user_id]["state"]
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id
    
    if state == "waiting_first_file_auto":
        user_session[user_id].update({"start_id": msg_id, "state": "waiting_last_file_auto"})
        await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 Now **FORWARD** the LAST FILE.")
        
    elif state == "waiting_last_file_auto":
        user_session[user_id].update({"end_id": msg_id, "state": "processing"})
        await message.reply_text("🚀 **Scanning & Auto-Creating Modules... Please wait!**")
        asyncio.create_task(process_bulk_auto(client, message, user_id))

    elif state == "waiting_first_file_manual":
        user_session[user_id].update({"start_id": msg_id, "state": "waiting_last_file_manual"})
        await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 Now **FORWARD** the LAST FILE.")
        
    elif state == "waiting_last_file_manual":
        user_session[user_id].update({"end_id": msg_id, "state": "processing"})
        await message.reply_text("🚀 **Scanning & Uploading to Manual Module... Please wait!**")
        asyncio.create_task(process_bulk_manual(client, message, user_id))
        
    raise StopPropagation

# ==========================================
# ⚡ 8. THE BRAIN: AUTO-MODULE PROCESSOR
# ==========================================
async def process_bulk_auto(client, message, user_id):
    start_id, end_id = user_session[user_id]["start_id"], user_session[user_id]["end_id"]
    if start_id > end_id: start_id, end_id = end_id, start_id
        
    status_msg = await message.reply_text("🔄 **AI Analyzing Captions...**")
    cat_id, batch_id = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
    base_db_path = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules")
    
    module_cache = {} # Keeps track of created modules
    v_count = f_count = scanned = 0
    timestamp_base = int(time.time() * 1000)
    
    try:
        for current_id in range(start_id, end_id + 1):
            try:
                msg = await client.get_messages(SOURCE_CHANNEL, current_id)
                if msg.empty or not getattr(msg, "media", None): continue
                    
                scanned += 1
                direct_link, clean_name = get_stream_url(msg)
                
                # 🔥 Extract Module Name from Caption
                mod_name = extract_module_name(msg.caption)
                
                # Automatically Create Module in Firebase if it doesn't exist
                if mod_name not in module_cache:
                    ref = base_db_path.push({"name": mod_name, "id": ""})
                    mod_id = ref['name']
                    base_db_path.child(mod_id).update({"id": mod_id})
                    module_cache[mod_name] = mod_id
                
                mod_id = module_cache[mod_name]
                
                target_node = "lectures" if msg.video else "resources"
                if msg.video: v_count += 1
                else: f_count += 1
                
                payload = {
                    "name": clean_name,
                    "link": direct_link,
                    "order": timestamp_base + scanned,
                    "thumbnail": ""
                }
                
                file_ref = base_db_path.child(mod_id).child(target_node).push(payload)
                base_db_path.child(mod_id).child(target_node).child(file_ref['name']).update({"id": file_ref['name']})
                
                if scanned % 5 == 0:
                    await status_msg.edit_text(f"⚡ **Auto-Sorting...**\n📂 Modules Auto-Created: {len(module_cache)}\n🎬 Videos: {v_count} | 📑 Files: {f_count}")
            except Exception as e: pass
                
        await status_msg.edit_text(f"✅ **SMART BATCH SYNC COMPLETE!**\n━━━━━━━━━━━━━━━━━━━━\n📂 **Modules Auto-Created:** {len(module_cache)}\n🎬 **Videos:** {v_count}\n📑 **Files:** {f_count}\n\n🔥 *All dynamically structured!*")
    except Exception as e:
        await status_msg.edit_text(f"❌ **Fatal Error:** {e}")
    finally:
        user_session[user_id] = {"state": "idle"}

# ==========================================
# ⚡ 9. MANUAL PROCESSOR (Old Style)
# ==========================================
async def process_bulk_manual(client, message, user_id):
    # Old logic for manual module selection (keeps it safe in one module)
    start_id, end_id = user_session[user_id]["start_id"], user_session[user_id]["end_id"]
    if start_id > end_id: start_id, end_id = end_id, start_id
    status_msg = await message.reply_text("🔄 Processing manual module...")
    
    cat_id, batch_id, mod_id = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["mod_id"]
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
                
                payload = {"name": clean_name, "link": direct_link, "order": timestamp_base + scanned, "thumbnail": ""}
                ref = db_path.child(target_node).push(payload)
                db_path.child(target_node).child(ref['name']).update({"id": ref['name']})
                if scanned % 5 == 0: await status_msg.edit_text(f"⏳ Processing... {scanned}")
            except: pass
        await status_msg.edit_text(f"✅ **MANUAL SYNC COMPLETE!**\n🎬 Videos: {v_count} | 📑 Files: {f_count}")
    except Exception as e: await status_msg.edit_text(f"❌ Error: {e}")
    finally: user_session[user_id] = {"state": "idle"}
