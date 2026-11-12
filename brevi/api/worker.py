"""Polling render worker. Run separately from the FastAPI web process."""
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
import requests
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
POLL_SECONDS = int(os.getenv("VIDEO_WORKER_POLL_SECONDS", "5"))
CLEANUP_INTERVAL_SECONDS = int(os.getenv("VIDEO_CLEANUP_INTERVAL_SECONDS", "3600"))
STALE_UPLOAD_HOURS = int(os.getenv("VIDEO_STALE_UPLOAD_HOURS", "24"))


def cleanup_stale_uploads() -> None:
    """Remove incomplete source uploads after their signed URL can no longer be used."""
    cutoff = datetime.fromtimestamp(time.time() - STALE_UPLOAD_HOURS * 3600, timezone.utc).isoformat()
    stale = (supabase.table("video_assets").select("id,bucket_id,object_path")
             .eq("status", "pending_upload").lt("created_at", cutoff).execute())
    for asset in stale.data or []:
        supabase.storage.from_(asset["bucket_id"]).remove([asset["object_path"]])
        supabase.table("video_assets").update({"status": "deleted", "deleted_at": datetime.now(timezone.utc).isoformat()}).eq("id", asset["id"]).execute()


def download_to_file(bucket_id: str, object_path: str, destination: Path) -> None:
    signed = supabase.storage.from_(bucket_id).create_signed_url(object_path, 3600)
    with requests.get(signed["signedURL"], stream=True, timeout=3600) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if chunk:
                    output.write(chunk)


def process_next_job() -> bool:
    queued = (supabase.table("video_assets").select("*").eq("asset_type", "original")
              .eq("status", "queued").order("created_at").limit(1).execute())
    if not queued.data:
        return False
    source = queued.data[0]
    claimed = (supabase.table("video_assets").update({"status": "processing"})
               .eq("id", source["id"]).eq("status", "queued").execute())
    if not claimed.data:
        return True

    export_id = str(uuid4())
    export_path = f"{source['project_id']}/{export_id}/edited.mp4"
    try:
        with tempfile.TemporaryDirectory(prefix="brevi-render-") as directory:
            source_file = Path(directory) / "source"
            export_file = Path(directory) / "edited.mp4"
            download_to_file(source["bucket_id"], source["object_path"], source_file)
            subprocess.run(["ffmpeg", "-y", "-i", str(source_file), "-c:v", "libx264", "-c:a", "aac",
                            "-movflags", "+faststart", str(export_file)], check=True, capture_output=True)
            with export_file.open("rb") as output:
                supabase.storage.from_("video-exports").upload(
                    path=export_path, file=output,
                    file_options={"content-type": "video/mp4", "upsert": "false"},
                )
            supabase.table("video_assets").insert({
                "id": export_id, "project_id": source["project_id"], "owner_id": source["owner_id"],
                "bucket_id": "video-exports", "object_path": export_path, "asset_type": "export",
                "status": "ready", "source_asset_id": source["id"], "original_filename": "edited.mp4",
                "mime_type": "video/mp4", "byte_size": export_file.stat().st_size, "completed_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        supabase.storage.from_(source["bucket_id"]).remove([source["object_path"]])
        supabase.table("video_assets").update({"status": "deleted", "deleted_at": datetime.now(timezone.utc).isoformat()}).eq("id", source["id"]).execute()
    except Exception:
        supabase.table("video_assets").update({"status": "failed", "error_message": "Video processing failed"}).eq("id", source["id"]).execute()
    return True


if __name__ == "__main__":
    last_cleanup = 0.0
    while True:
        if time.monotonic() - last_cleanup >= CLEANUP_INTERVAL_SECONDS:
            cleanup_stale_uploads()
            last_cleanup = time.monotonic()
        if not process_next_job():
            time.sleep(POLL_SECONDS)
