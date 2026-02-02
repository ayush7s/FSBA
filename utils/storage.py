from utils.supabase_client import get_supabase

supabase = get_supabase()



def upload_file(bucket: str, path: str, file_obj):
    """
    Uploads a file to Supabase Storage (safe + overwrite).
    """
    if not file_obj or not path:
        return

    # 🔥 IMPORTANT: reset pointer
    file_obj.seek(0)
    file_bytes = file_obj.read()
    file_obj.seek(0)

    supabase.storage.from_(bucket).upload(
        path,
        file_bytes,
        file_options={
            "content-type": getattr(
                file_obj, "content_type", "application/octet-stream"
            ),
            "upsert": True  # ✅ prevent 409 Duplicate
        }
    )


def get_public_url(bucket: str, path: str) -> str:
    """
    Returns public URL (bucket must be public).
    """
    if not path:
        return ""

    return supabase.storage.from_(bucket).get_public_url(path)


def get_signed_url(bucket: str, path: str, expires_in: int = 600) -> str:
    """
    Returns signed URL (safe).
    """
    if not path:
        return ""

    res = supabase.storage.from_(bucket).create_signed_url(
        path,
        expires_in
    )

    if not res or "signedURL" not in res:
        return ""

    return res["signedURL"]


def delete_file(bucket: str, path: str):
    """
    Deletes a file from Supabase Storage.
    """
    if not path:
        return

    supabase.storage.from_(bucket).remove([path])
