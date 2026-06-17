# Don't Remove Credit @VJ_Botz
import re, math, logging, secrets, mimetypes, time
from aiohttp import web

# 🔥 FIX: Routes Top par define kiya hai taaki Import Error kabhi na aaye
routes = web.RouteTableDef()

from info import *
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome To VJ Disk!</h1><p>Your ultimate destination for streaming!</p>
    </div>
</body>
</html>
"""

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text=html_content, content_type='text/html')

@routes.post('/click-counter')
async def handle_click(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        today = datetime.now().strftime('%Y-%m-%d')
        if request.cookies.get('visited') == today: return
        response = web.Response(text="Counted")
        response.set_cookie('visited', today, max_age=24*60*60)
        u = get_count(user_id)
        record_visit(user_id, int(u + 1) if u else 1)
        return response
    except: pass

@routes.get('/link', allow_head=True)
async def visits(request: web.Request):
    user, watch, second, third = request.query.get('u'), request.query.get('w'), request.query.get('s'), request.query.get('t')
    data, user_id, sec_id, th_id = await encode(watch), await encode(user), await encode(second), await encode(third)
    base_url = STREAM_URL.rstrip('/')
    raise web.HTTPFound(f"{base_url}/{data}/{user_id}/{sec_id}/{th_id}")

# 🔥 MASTER DOWNLOAD ROUTE: Ye har tarah ke link (/watch/123, /dl/123) ko properly stream karega!
@routes.get('/watch/{id}', allow_head=True)
@routes.get('/dl/{id}', allow_head=True)
@routes.get('/dl/{id}/{name}', allow_head=True)
@routes.get('/stream/{id}', allow_head=True)
async def stream_handler_master(request: web.Request):
    try:
        id_str = request.match_info.get("id")
        
        # ID extracting logic
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", id_str)
        if match:
            secure_hash = match.group(1)
            msg_id = int(match.group(2))
        else:
            id_match = re.search(r"(\d+)", id_str)
            if not id_match:
                return web.Response(status=404, text="<h1>404 Error: Invalid ID format.</h1>", content_type="text/html")
            msg_id = int(id_match.group(1))
            secure_hash = request.rel_url.query.get("hash", "")
            
        return await media_streamer(request, msg_id, secure_hash)
        
    except FIleNotFound as e:
        error_html = f"<h2>404 Error: File Not Found in Telegram!</h2><p>Reason: {e.message}</p><p>Please Ensure Bot is Admin in your Log Channel.</p>"
        return web.Response(status=404, text=error_html, content_type="text/html")
    except Exception as e:
        return web.Response(status=500, text=f"Internal Server Error: {str(e)}", content_type="text/html")

@routes.get(r"/{path}/{user_path}/{second}/{third}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        id = int(await decode(request.match_info["path"]))
        user_id = int(await decode(request.match_info["user_path"]))
        secid = int(await decode(request.match_info["second"]))
        thid = int(await decode(request.match_info["third"]))
        return web.Response(text=await render_page(id, user_id, secid, thid), content_type='text/html')
    except: return web.Response(text=html_content, content_type='text/html')

@routes.get('/{short_link}', allow_head=True)
async def get_original(request: web.Request):
    short_link = request.match_info["short_link"]
    original = await decode(short_link)
    if original:
        base_url = STREAM_URL.rstrip('/')
        raise web.HTTPFound(f"{base_url}/link?{original}")
    return web.Response(text=html_content, content_type='text/html')

class_cache = {}
async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if faster_client in class_cache: tg_connect = class_cache[faster_client]
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
