import asyncio
import os
import urllib.parse
import time
import re
from pyrogram import Client, filters
from pyrogram import StopPropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import pyrebase
from info import ADMINS

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
SOURCE_CHANNEL = -1003897025049  
STREAM_URL = "https://dustreambot.onrender.com"  # ✅ Fixed Domain

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
# 🛠️ 2. HELPERS & THREAD-SAFE FIREBASE LOGIC
# ==========================================
def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict): return data.get("title") or data.get("name") or "Unnamed"
    return "Unnamed"

def get_file_name_robust(message):
    if message.document and getattr(message.document, 'file_name', None): return message.document.file_name
    if message.video and getattr(message.video, 'file_name', None): return message.video.file_name
    if message.audio and getattr(message.audio, 'file_name', None): return message.audio.file_name
    if message.photo: return f"Image_{message.id}.png"
    if message.caption: return message.caption[:30] + ".mp4"
    return f"File_{message.id}.mp4"

def get_stream_url(msg):
    file_name = get_file_name_robust(msg)
    clean_name = file_name.replace("_", " ").replace("-", " ")
    safe_filename = urllib.parse.quote_plus(file_name)
    # 🔥 FIX: Removed '/dl/' to prevent 404 error in DUSTREAMBot
    direct_link = f"{STREAM_URL}/{msg.id}/{safe_filename}"
    return direct_link, clean_name

def extract_module_name(caption):
    """🔥 Extract exact subfolder name from caption"""
    if not caption: return "Main Module"
    match = re.search(r'/folder\s+([^\n]+)', caption)
    if match:
        path = match.group(1).strip()
        parts = [p.strip() for p in path.split('/') if p.strip()]
        if len(parts) > 0:
            return parts[-1]
    return "Main Module"

# 🔥 FIX: THREAD-SAFE FIREBASE FUNCTIONS (Prevents Root Dumping)
def fb_create_module(cat_id, batch_id, mod_name):
    path = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules")
    ref = path.push({"name": mod_name, "id": ""})
    mod_id = ref['name']
    path.child(mod_id).update({"id": mod_id})
    return mod_id

def fb_push_file(cat_id, batch_id, mod_id, target_node, payload):
    path = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(mod_id).child(target_node)
    file_ref = path.push(payload)
    path.child(file_ref['name']).update({"id": file_ref['name']})

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
# 🤖 4. COMMANDS & MENUS (GROUP=-1)
# ==========================================
@Client.on_message(filters.command("new") & filters.private & filters.user(ADMINS), group=-1)
async def new_cmd(client, message: Message):
    user_session[message.from_user.id] = {"state": "selecting_cat"}
    try:
        cats = db.child("categories").get().val()
        buttons = []
        if cats:
            for k, v in cats.items():
                if v and isinstance(v, dict): buttons.append([InlineKeyboardButton(f"📂 {get_name(v)}", callback_data=f"fbcat_{k}")])
        buttons.append([InlineKeyboardButton("➕ Create New Category", callback_data="fbnewcat")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")])
        await message.reply_text("🔥 **Auto-Bulk Sync Started!**\n\n**Step 1:** Select a Category or Create New:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await message.reply_text(f"Database Error: {e}")
    raise StopPropagation

@Client.on_message(filters.command("see") & filters.private & filters.user(ADMINS), group=-1)
async def see_cmd(client, message: Message):
    await new_cmd(client, message)

@Client.on_callback_query(filters.regex("^fbcancel"), group=-1)
async def cancel_cb(client, query):
    user_session[query.from_user.id] = {"state": "idle"}
    await query.message.edit_text("🚫 **Process Cancelled.**")
    raise StopPropagation

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
        await query.message.edit_text("**Step 2:** Select a Batch or Create New:", reply_markup=InlineKeyboardMarkup(buttons))
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
# ✍️ 5. TEXT CREATION HANDLERS
# ==========================================
@Client.on_message(filters.text & filters.private & state_filter, group=-1)
async def handle_names(client, message: Message):
    user_id = message.from_user.id
    state = user_session[user_id]["state"]
    text = message.text.strip()
    
    if state == "waiting_cat_name":
        def create_cat():
            ref = db.child("categories").push({"title": text, "id": ""})
            cat_id = ref['name']
            db.child("categories").child(cat_id).update({"id": cat_id})
            return cat_id
        cat_id = await asyncio.to_thread(create_cat)
        user_session[user_id].update({"cat_id": cat_id, "state": "waiting_batch_name"})
        buttons = [[InlineKeyboardButton("➕ Create New Batch", callback_data="fbnewbatch")], [InlineKeyboardButton("❌ Cancel", callback_data="fbcancel")]]
        await message.reply_text(f"✅ Category `{text}` Created!\n\n**Step 2:** Select or Create a Batch inside it:", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif state == "waiting_batch_name":
        cat_id = user_session[user_id]["cat_id"]
        def create_batch():
            ref = db.child("categories").child(cat_id).child("batches").push({"title": text, "id": ""})
            batch_id = ref['name']
            db.child("categories").child(cat_id).child("batches").child(batch_id).update({"id": batch_id})
            return batch_id
        batch_id = await asyncio.to_thread(create_batch)
        user_session[user_id].update({"batch_id": batch_id})
        buttons = [[InlineKeyboardButton("⚡ AUTOMATIC (Smart Caption)", callback_data="fbauto_mode")], [InlineKeyboardButton("➕ New Module (Manual)", callback_data="fbnewmod")]]
        await message.reply_text(f"✅ Batch `{text}` Created!\n\n🎯 **Choose Upload Mode:**", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif state == "waiting_mod_name":
        cat_id, batch_id = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
        mod_id = await asyncio.to_thread(fb_create_module, cat_id, batch_id, text)
        user_session[user_id].update({"mod_id": mod_id, "state": "waiting_first_file_manual"})
        await message.reply_text(f"✅ Module `{text}` Created!\n\n📥 **Please FORWARD the FIRST FILE of this module.**")
    
    raise StopPropagation

# ==========================================
# 📥 6. FORWARD HANDLER
# ==========================================
@Client.on_message((filters.forwarded | filters.media) & filters.private & file_filter, group=-1)
async def handle_files(client, message: Message):
    user_id = message.from_user.id
    state = user_session[user_id]["state"]
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id

    if message.forward_from_chat:
        user_session[user_id]["source_chat"] = message.forward_from_chat.id
    else:
        user_session[user_id]["source_chat"] = SOURCE_CHANNEL

    if state == "waiting_first_file_auto":
        user_session[user_id].update({"start_id": msg_id, "state": "waiting_last_file_auto"})
        await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 Now **FORWARD** the LAST FILE.")
        
    elif state == "waiting_last_file_auto":
        user_session[user_id].update({"end_id": msg_id, "state": "processing"})
        await message.reply_text("🚀 **Initializing Live Dashboard... Please wait!**")
        asyncio.create_task(process_bulk_auto(client, message, user_id))

    elif state == "waiting_first_file_manual":
        user_session[user_id].update({"start_id": msg_id, "state": "waiting_last_file_manual"})
        await message.reply_text(f"🎯 **First File Locked (ID: {msg_id})**\n\n📤 Now **FORWARD** the LAST FILE.")
        
    elif state == "waiting_last_file_manual":
        user_session[user_id].update({"end_id": msg_id, "state": "processing"})
        await message.reply_text("🚀 **Initializing Live Dashboard... Please wait!**")
        asyncio.create_task(process_bulk_manual(client, message, user_id))
        
    raise StopPropagation

# ==========================================
# ⚡ 7. THE BRAIN: LIVE DASHBOARD PROCESSOR (AUTO)
# ==========================================
async def process_bulk_auto(client, message, user_id):
    start_id = user_session[user_id]["start_id"]
    end_id = user_session[user_id]["end_id"]
    source_chat = user_session[user_id]["source_chat"]
    
    if start_id > end_id: start_id, end_id = end_id, start_id
    total_files = (end_id - start_id) + 1
        
    status_msg = await message.reply_text("🔄 **Starting Deep Live Scan...**")
    cat_id, batch_id = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
    
    module_cache = {}
    v_count = f_count = failed_count = scanned = 0
    failed_logs = []
    timestamp_base = int(time.time() * 1000)
    last_update_time = time.time()
    
    video_exts = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.wmv', '.m4v']
    all_ids = list(range(start_id, end_id + 1))
    
    try:
        for i in range(0, len(all_ids), 20):
            chunk_ids = all_ids[i:i + 20]
            try:
                messages = await client.get_messages(source_chat, chunk_ids)
            except Exception as e:
                failed_count += len(chunk_ids)
                failed_logs.append(f"Channel Error: {str(e)[:30]}")
                continue
                
            for msg in messages:
                scanned += 1
                if msg.empty or not getattr(msg, "media", None): continue
                
                try:
                    direct_link, clean_name = get_stream_url(msg)
                    mod_name = extract_module_name(msg.caption)
                    
                    if mod_name not in module_cache:
                        mod_id = await asyncio.to_thread(fb_create_module, cat_id, batch_id, mod_name)
                        module_cache[mod_name] = mod_id
                    
                    mod_id = module_cache[mod_name]
                    
                    file_name_lower = get_file_name_robust(msg).lower()
                    is_video = False
                    if getattr(msg, "video", None): is_video = True
                    elif any(file_name_lower.endswith(ext) for ext in video_exts): is_video = True
                    
                    target_node = "lectures" if is_video else "resources"
                    if is_video: v_count += 1
                    else: f_count += 1
                    
                    payload = {"name": clean_name, "link": direct_link, "order": timestamp_base + scanned, "thumbnail": ""}
                    await asyncio.to_thread(fb_push_file, cat_id, batch_id, mod_id, target_node, payload)
                    
                except Exception as ex:
                    failed_count += 1
                    failed_logs.append(f"ID {msg.id}: Sync Error")

                now = time.time()
                if now - last_update_time > 2.5:
                    ui = (
                        f"⚡ **LIVE SYNC DASHBOARD**\n━━━━━━━━━━━━━━━━━━━━\n"
                        f"📊 **Progress:** {scanned} / {total_files} Scanned\n"
                        f"📂 **Module:** `{mod_name}`\n"
                        f"📄 **File:** `{clean_name[:20]}...`\n\n"
                        f"✅ **Added:** {v_count + f_count} (🎬 {v_count} | 📑 {f_count})\n"
                        f"❌ **Failed:** {failed_count}"
                    )
                    try: await status_msg.edit_text(ui); last_update_time = now
                    except: pass
                    
        final_ui = (
            f"✅ **SMART BATCH SYNC COMPLETE!**\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 **Modules Auto-Created:** {len(module_cache)}\n"
            f"🎬 **Videos (Lectures):** {v_count}\n"
            f"📑 **Files (Resources):** {f_count}\n"
            f"❌ **Total Skipped/Failed:** {failed_count}\n\n🔥 *Strictly Organized in Firebase!*"
        )
        await status_msg.edit_text(final_ui)
        
    except Exception as e: await status_msg.edit_text(f"❌ **Fatal Error:** {e}")
    finally: user_session[user_id] = {"state": "idle"}

# ==========================================
# ⚡ 8. MANUAL PROCESSOR
# ==========================================
async def process_bulk_manual(client, message, user_id):
    start_id, end_id = user_session[user_id]["start_id"], user_session[user_id]["end_id"]
    source_chat = user_session[user_id]["source_chat"]
    if start_id > end_id: start_id, end_id = end_id, start_id
    total_files = (end_id - start_id) + 1
    
    status_msg = await message.reply_text("🔄 **Initializing Live Dashboard...**")
    cat_id, batch_id, mod_id = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["mod_id"]
    
    v_count = f_count = failed_count = scanned = 0
    timestamp_base = int(time.time() * 1000)
    last_update_time = time.time()
    
    video_exts = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.wmv', '.m4v']
    all_ids = list(range(start_id, end_id + 1))
    
    try:
        for i in range(0, len(all_ids), 20):
            chunk_ids = all_ids[i:i + 20]
            try: messages = await client.get_messages(source_chat, chunk_ids)
            except: continue
                
            for msg in messages:
                scanned += 1
                if msg.empty or not getattr(msg, "media", None): continue
                
                try:
                    direct_link, clean_name = get_stream_url(msg)
                    file_name_lower = get_file_name_robust(msg).lower()
                    is_video = False
                    if getattr(msg, "video", None): is_video = True
                    elif any(file_name_lower.endswith(ext) for ext in video_exts): is_video = True
                    
                    target_node = "lectures" if is_video else "resources"
                    if is_video: v_count += 1
                    else: f_count += 1
                    
                    payload = {"name": clean_name, "link": direct_link, "order": timestamp_base + scanned, "thumbnail": ""}
                    await asyncio.to_thread(fb_push_file, cat_id, batch_id, mod_id, target_node, payload)
                except: failed_count += 1

                now = time.time()
                if now - last_update_time > 2.5:
                    ui = f"⚡ **MANUAL SYNC ({scanned}/{total_files})**\n━━━━━━━━━━━━━━━━━━━━\n📄 `{clean_name[:25]}...`\n✅ Added: {v_count + f_count} (🎬 {v_count} | 📑 {f_count}) | ❌ Failed: {failed_count}"
                    try: await status_msg.edit_text(ui); last_update_time = now
                    except: pass
                    
        await status_msg.edit_text(f"✅ **MANUAL SYNC COMPLETE!**\n🎬 Videos: {v_count} | 📑 Files: {f_count} | ❌ Failed: {failed_count}")
    except Exception as e: await status_msg.edit_text(f"❌ Error: {e}")
    finally: user_session[user_id] = {"state": "idle"}
