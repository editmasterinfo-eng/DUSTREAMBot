# Don't Remove Credit @VJ_Botz
import re, math, logging, secrets, mimetypes, time, json
from aiohttp import web
from datetime import datetime, timezone

# 🔥 FIX: Routes Top par define kiya hai taaki Import Error kabhi na aaye
routes = web.RouteTableDef()

from info import *
from aiohttp.http_exceptions import BadStatusLine
from plugins.start import decode, encode 
from plugins.database import record_visit, get_count
from TechVJ.bot import multi_clients, work_loads, TechVJBot
from TechVJ.server.exceptions import FIleNotFound, InvalidHash
from TechVJ import StartTime, __version__
from TechVJ.util.custom_dl import ByteStreamer
from TechVJ.util.time_format import get_readable_time
from TechVJ.util.render_template import render_page
from TechVJ.util.file_properties import get_file_ids

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkillNeast — Master New Skills For Free</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #0088cc;
            --primary-hover: #0077b5;
            --primary-light: #e6f5fc;
            --primary-glow: rgba(0, 136, 204, 0.25);
            --bg-body: #f8fafc;
            --bg-card: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
            --radius-lg: 20px;
            --radius-md: 14px;
            --radius-pill: 9999px;
            --shadow-sm: 0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -2px rgba(0, 0, 0, 0.04);
            --shadow-card: 0 10px 30px -5px rgba(0, 0, 0, 0.05), 0 0 1px 1px rgba(0, 0, 0, 0.03);
            --shadow-hover: 0 20px 35px -8px rgba(0, 136, 204, 0.18), 0 1px 3px 0 rgba(0, 0, 0, 0.04);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            position: relative;
            overflow-x: hidden;
            padding: 40px 20px 60px;
        }

        /* Ambient Glow Background */
        .ambient-glow {
            position: fixed;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 1200px;
            height: 500px;
            background: radial-gradient(circle at 50% 20%, rgba(0, 136, 204, 0.12) 0%, rgba(99, 102, 241, 0.06) 45%, transparent 70%);
            z-index: 0;
            pointer-events: none;
        }

        .container {
            width: 100%;
            max-width: 960px;
            z-index: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            animation: fadeIn 0.8s ease-out;
        }

        /* Hero Header */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 18px;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-pill);
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--primary);
            box-shadow: var(--shadow-sm);
            margin-bottom: 24px;
            letter-spacing: 0.3px;
        }

        .badge-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e;
            animation: pulse 2s infinite;
        }

        .hero-title {
            font-size: clamp(2.4rem, 5vw, 3.6rem);
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.15;
            text-align: center;
            color: var(--text-main);
            margin-bottom: 12px;
        }

        .hero-title span {
            background: linear-gradient(135deg, #0088cc 0%, #3b82f6 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .tagline {
            font-size: clamp(1.05rem, 2.5vw, 1.25rem);
            font-weight: 600;
            color: #334155;
            text-align: center;
            margin-bottom: 8px;
        }

        .description {
            font-size: 1rem;
            color: var(--text-muted);
            text-align: center;
            max-width: 620px;
            line-height: 1.6;
            margin-bottom: 40px;
        }

        /* Telegram Cards Section */
        .cards-grid {
            width: 100%;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
            gap: 24px;
            margin-bottom: 35px;
        }

        .channel-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 32px 28px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: var(--shadow-card);
            transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            overflow: hidden;
        }

        .channel-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #0088cc, #38bdf8);
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .channel-card:hover {
            transform: translateY(-6px);
            box-shadow: var(--shadow-hover);
            border-color: rgba(0, 136, 204, 0.4);
        }

        .channel-card:hover::before {
            opacity: 1;
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }

        .tg-icon-wrapper {
            width: 54px;
            height: 54px;
            background: var(--primary-light);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary);
            flex-shrink: 0;
            transition: transform 0.3s ease, background-color 0.3s ease;
        }

        .channel-card:hover .tg-icon-wrapper {
            transform: scale(1.08) rotate(4deg);
            background: #0088cc;
            color: #ffffff;
            box-shadow: 0 8px 16px var(--primary-glow);
        }

        .card-header-meta h2 {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-main);
            line-height: 1.3;
        }

        .card-handle {
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--primary);
            margin-top: 2px;
        }

        .card-desc {
            font-size: 0.95rem;
            color: var(--text-muted);
            line-height: 1.55;
            margin-bottom: 24px;
            flex-grow: 1;
        }

        .join-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 14px 20px;
            background: #0088cc;
            color: #ffffff;
            font-size: 0.96rem;
            font-weight: 600;
            text-decoration: none;
            border-radius: var(--radius-md);
            box-shadow: 0 6px 14px var(--primary-glow);
            transition: all 0.25s ease;
        }

        .join-btn:hover {
            background: var(--primary-hover);
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 136, 204, 0.35);
        }

        .join-btn:active {
            transform: translateY(0);
        }

        .join-btn svg {
            transition: transform 0.25s ease;
        }

        .join-btn:hover svg {
            transform: translateX(4px);
        }

        /* Highlights strip */
        .features-strip {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 14px;
            margin-top: 10px;
        }

        .feature-item {
            background: #ffffff;
            border: 1px solid var(--border-color);
            padding: 8px 18px;
            border-radius: var(--radius-pill);
            font-size: 0.85rem;
            font-weight: 600;
            color: #475569;
            box-shadow: var(--shadow-sm);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Footer */
        footer {
            margin-top: 40px;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(18px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulse {
            0% { opacity: 0.6; transform: scale(0.95); }
            50% { opacity: 1; transform: scale(1.1); }
            100% { opacity: 0.6; transform: scale(0.95); }
        }
    </style>
</head>
<body>
    <div class="ambient-glow"></div>

    <div class="container">
        <!-- Top Badge -->
        <div class="badge">
            <span class="badge-dot"></span>
            100% Free Premium Resources
        </div>

        <!-- Hero Title & Tagline -->
        <h1 class="hero-title">Welcome to <span>SkillNeast</span></h1>
        <p class="tagline">Master New Skills • Paid Courses Free Me Payein</p>
        <p class="description">
            Top-rated premium courses, development roadmaps, learning resources aur certifications bilkul free access karein. Join our Telegram channels niche diye links se!
        </p>

        <!-- 2 Modern Cards Grid -->
        <div class="cards-grid">
            <!-- Card 1: About & Info -->
            <div class="channel-card">
                <div>
                    <div class="card-header">
                        <div class="tg-icon-wrapper">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.19-.08-.05-.19-.02-.27 0-.12.03-1.99 1.27-5.62 3.72-.53.36-1.01.54-1.44.53-.47-.01-1.38-.27-2.06-.49-.83-.27-1.49-.42-1.43-.88.03-.24.37-.49 1.02-.75 3.99-1.74 6.66-2.88 7.99-3.44 3.81-1.59 4.6-1.87 5.12-1.88.11 0 .37.03.54.17.14.12.18.28.2.45-.02.07-.02.13-.04.22z"/>
                            </svg>
                        </div>
                        <div class="card-header-meta">
                            <h2>SkillNeast Updates</h2>
                            <p class="card-handle">@aboutskillneast</p>
                        </div>
                    </div>
                    <p class="card-desc">
                        Hamare official updates, course index, backup links aur request group se connected rehne ke liye channel ko follow karein.
                    </p>
                </div>
                <a href="https://t.me/aboutskillneast" target="_blank" rel="noopener noreferrer" class="join-btn">
                    <span>Join About Channel</span>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </a>
            </div>

            <!-- Card 2: Main Courses Channel -->
            <div class="channel-card">
                <div>
                    <div class="card-header">
                        <div class="tg-icon-wrapper">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.19-.08-.05-.19-.02-.27 0-.12.03-1.99 1.27-5.62 3.72-.53.36-1.01.54-1.44.53-.47-.01-1.38-.27-2.06-.49-.83-.27-1.49-.42-1.43-.88.03-.24.37-.49 1.02-.75 3.99-1.74 6.66-2.88 7.99-3.44 3.81-1.59 4.6-1.87 5.12-1.88.11 0 .37.03.54.17.14.12.18.28.2.45-.02.07-.02.13-.04.22z"/>
                            </svg>
                        </div>
                        <div class="card-header-meta">
                            <h2>SkillNeast Main Hub</h2>
                            <p class="card-handle">@skillneastreal1</p>
                        </div>
                    </div>
                    <p class="card-desc">
                        Sabhi top paid courses, coding tutorials, premium drives aur study materials bilkul free download & stream karne ke liye join karein.
                    </p>
                </div>
                <a href="https://t.me/skillneastreal1" target="_blank" rel="noopener noreferrer" class="join-btn">
                    <span>Join Main Channel</span>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </a>
            </div>
        </div>

        <!-- Features Badges -->
        <div class="features-strip">
            <div class="feature-item">⚡ High-Speed Direct Stream</div>
            <div class="feature-item">📚 Daily New Premium Courses</div>
            <div class="feature-item">💎 100% Free Lifetime Access</div>
        </div>

        <!-- Footer -->
        <footer>
            &copy; 2026 SkillNeast • Empowering Learning Everyday
        </footer>
    </div>
</body>
</html>
"""

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text=html_content, content_type='text/html')

# 🔥 LIGHTWEIGHT HEALTH-CHECK / PING ROUTES (Render & 24/7 Uptime Keep-Alive)
@routes.get("/ping", allow_head=True)
@routes.get("/health", allow_head=True)
@routes.get("/uptime", allow_head=True)
async def health_check_handler(request: web.Request):
    data = {
        "status": "alive",
        "service": "DUSTREAM Bot",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return web.json_response(data)

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
