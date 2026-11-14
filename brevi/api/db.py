import os
from pathlib import Path

from dotenv import load_dotenv
from storage3.exceptions import StorageApiError
from supabase import Client, ClientOptions, create_client

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MAX_VIDEO_BYTES = 25 * 1024 * 1024


def connect() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        options=ClientOptions(
            auto_refresh_token=False, persist_session=False,
            postgrest_client_timeout=10, storage_client_timeout=20,
        ),
    )


def transition(client: Client, project: str, action: str, **fields):
    return client.rpc("transition_video", {"project": project, "action": action, **fields}).execute().data


def object_info(bucket, path: str) -> dict | None:
    try:
        return bucket.info(path)
    except StorageApiError as error:
        if str(error.status) == "404" or error.code in ("NoSuchKey", "not_found"):
            return None
        raise
