import os
from supabase import create_client, Client
from supabase.client import ClientOptions

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase

    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("Supabase credentials are not set")

        _supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
            options=ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            )
        )

    return _supabase
