import os
from supabase import create_client, Client
from supabase.client import ClientOptions

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )
)
