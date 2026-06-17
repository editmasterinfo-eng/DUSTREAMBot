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
