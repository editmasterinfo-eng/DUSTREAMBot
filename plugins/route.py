# Don't Remove Credit @VJ_Botz
import re, math, logging, secrets, mimetypes, time
from info import *
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from plugins.start import decode, encode 
from datetime import datetime
from plugins.database import record_visit, get_count
from TechVJ.bot import multi_clients, work_loads, TechVJBot
from TechVJ.server.exceptions import FIleNotFound, InvalidHash
from TechVJ import StartTime, __version__
from TechVJ.util.custom_dl import ByteStreamer
from TechVJ.util.time_format import get_readable_time
from TechVJ.util.render_template import render_page
from TechVJ.util.file_properties import get_file_ids

routes = web.RouteTableDef()

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to VJ Disk</title>
    <style>
        body { margin: 0; font-family: 'Arial', sans-serif; background: linear-gradient(135deg, #ff7e5f, #feb47b); color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; text-align: center; }
        h1 { font-size: 4em; text-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
        p { font-size: 1.5em; margin-top: 20px; }
        .button { margin-top: 30px; padding: 15px 30px; font-size: 1.2em; background-color: #4CAF50; border: none; border-radius: 5px; color: white; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome To VJ Disk!</h1><p>Your ultimate destination for streaming!</p>
    </div>
</body>
</html>
"""

# 1. ROOT ROUTE
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text=html_content, content_type='text/html')

# 2. CLICK COUNTER
@routes.post('/click-counter')
async def handle_click(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        today = datetime.now().strftime('%Y-%m-%d')
        user_agent = request.headers.get('User-Agent')
        if "Chrome" in user_agent or "Google Inc" in user_agent:
            if request.cookies.get('visited') == today: return
            response = web.Response(text="Hello, World!")
            response.set_cookie('visited', today, max_age=24*60*60)
            u = get_count(user_id)
            record_visit(user_id, int(u + 1) if u else 1)
            return response
    except: pass

# 3. LINK GENERATOR ROUTE
@routes.get('/link', allow_head=True)
async def visits(request: web.Request):
    user, watch, second, third = request.query.get('u'), request.query.get('w'), request.query.get('s'), request.query.get('t')
    data, user_id, sec_id, th_id = await encode(watch), await encode(user), await encode(second), await encode(third)
    base_url = STREAM_URL.rstrip('/')
    raise web.HTTPFound(f"{base_url}/{data}/{user_id}/{sec_id}/{th_id}")

# 4. 🔥 MASTER DOWNLOAD ROUTE (Fixes 404 routing conflict completely)
@routes.get(r"/dl/{path:.*}", allow_head=True)
async def stream_handler_master(request: web.Request):
    try:
        path = request.match_info["path"]
        id_match = re.search(r"(\d+)", path)
        if not id_match:
            return web.Response(status=404, text="404 Error: Invalid Link, Message ID not found in URL.")
        
        message_id = int(id_match.group(1))
        secure_hash = request.rel_url.query.get("hash", "")
        return await media_streamer(request, message_id, secure_hash)
    except FIleNotFound as e:
        return web.Response(status=404, text=f"404 Error: File not found in Telegram! Please ensure Bot is Admin in Log Channel and the video was not deleted. Details: {e.message}")
    except Exception as e:
        return web.Response(status=500, text=f"Server Error: {str(e)}")

# 5. 🔥 STREAM ROUTE
@routes.get(r"/stream/{path:.*}", allow_head=True)
async def stream_handler_rotation(request):
    try:
        path = request.match_info["path"]
        id_match = re.search(r"(\d+)", path)
        if not id_match:
            return web.Response(status=404, text="404 Error: Invalid Stream ID.")
        message_id = int(id_match.group(1))
        return await media_streamer(request, message_id, "")
    except FIleNotFound as e:
        return web.Response(status=404, text=f"404 Error: Telegram File Missing! {e.message}")
    except Exception as e:
        return web.Response(status=500, text=f"Server Error: {str(e)}")

# 6. WATCH ONLINE PAGE RENDER ROUTE
@routes.get(r"/{path}/{user_path}/{second}/{third}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        id = int(await decode(request.match_info["path"]))
        user_id = int(await decode(request.match_info["user_path"]))
        secid = int(await decode(request.match_info["second"]))
        thid = int(await decode(request.match_info["third"]))
        return web.Response(text=await render_page(id, user_id, secid, thid), content_type='text/html')
    except: return web.Response(text=html_content, content_type='text/html')

# 7. SHORT LINK ROUTE (Hamesha Last me hona chahiye taaki `/dl/` block na ho)
@routes.get('/{short_link}', allow_head=True)
async def get_original(request: web.Request):
    short_link = request.match_info["short_link"]
    original = await decode(short_link)
    if original:
        base_url = STREAM_URL.rstrip('/')
        raise web.HTTPFound(f"{base_url}/link?{original}")
    else:
        return web.Response(text=html_content, content_type='text/html')

# === MEDIA STREAMER LOGIC ===
class_cache = {}
async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
    else:
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
        
    file_id = await tg_connect.get_file_properties(id)
    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(status=416, body="416: Range not satisfiable", headers={"Content-Range": f"bytes */{file_size}"})

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)
    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1
    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    
    body = tg_connect.yield_file(file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size)
    mime_type = file_id.mime_type or mimetypes.guess_type(file_id.file_name or "")[0] or "application/octet-stream"
    file_name = file_id.file_name or f"{secrets.token_hex(2)}.unknown"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )
