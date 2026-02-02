import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options={
        "schema": "public",
        "auto_refresh_token": False,
        "persist_session": False,
        "headers": {},
        "realtime": {},
        "storage": {},
        "global": {
            "fetch": None
        },
        "http_client": None   # 🔥 THIS LINE STOPS THE PROXY CRASH
    }
)
