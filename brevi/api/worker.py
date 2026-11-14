"""Run separately from FastAPI with FFmpeg installed."""
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db import connect, object_info, transition

supabase = connect()
logger = logging.getLogger(__name__)
POLL_SECONDS = int(os.getenv("VIDEO_WORKER_POLL_SECONDS", "5"))


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def remove_assets(assets):
    for asset in assets:
        bucket = supabase.storage.from_(asset["bucket_id"])
        bucket.remove([asset["object_path"]])
        if object_info(bucket, asset["object_path"]) is not None:
            raise RuntimeError("Storage object remains after deletion")


def cleanup() -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    abandoned = supabase.table("video_assets").select("id,project_id").eq(
        "status", "pending_upload"
    ).lt("created_at", cutoff).limit(100).execute().data
    for asset in abandoned:
        transition(supabase, asset["project_id"], "expire", asset=asset["id"])

    for timestamp_field in ("cleanup_started_at", "cleaned_at"):
        query = supabase.table("projects").select("id").not_.is_("deleting_at", "null").is_(
            timestamp_field, "null"
        )
        if timestamp_field == "cleaned_at":
            query = query.lte("cleanup_after", timestamp())
        for project in query.limit(100).execute().data:
            try:
                cleanup_project(project["id"], timestamp_field)
            except Exception:
                logger.exception("Could not clean up Project %s", project["id"])

    expired = supabase.table("video_assets").select(
        "id,bucket_id,object_path,projects!inner(cleanup_after,deleting_at)"
    ).eq("asset_type", "original").eq("status", "deleted").is_(
        "completed_at", "null"
    ).is_("projects.deleting_at", "null").or_(
        f"cleanup_after.is.null,cleanup_after.lte.{timestamp()}", reference_table="projects"
    ).limit(100).execute().data
    for asset in expired:
        try:
            remove_assets([asset])
            supabase.table("video_assets").update({"completed_at": timestamp()}).eq("id", asset["id"]).execute()
        except Exception:
            logger.exception("Could not remove expired upload %s", asset["id"])


def cleanup_project(project_id: str, timestamp_field: str):
    assets = supabase.table("video_assets").select("bucket_id,object_path").eq(
        "project_id", project_id
    ).execute().data
    remove_assets(assets)
    supabase.table("projects").update({timestamp_field: timestamp()}).eq("id", project_id).execute()


def process_next_job() -> bool:
    pending = supabase.table("video_assets").select(
        "id,project_id,projects!inner(deleting_at)"
    ).eq("asset_type", "export").is_("projects.deleting_at", "null").or_(
        f"status.eq.queued,and(status.eq.processing,render_deadline.lte.{timestamp()})"
    ).order("created_at").limit(1).execute().data
    if not pending:
        return False

    candidate = pending[0]
    project = candidate["project_id"]
    job = transition(supabase, project, "claim", asset=candidate["id"])
    if not job:
        return False

    deadline = datetime.fromisoformat(job["render_deadline"])
    fields = {"asset": job["id"], "deadline": job["render_deadline"]}
    target = supabase.storage.from_(job["bucket_id"])
    try:
        info = object_info(target, job["object_path"])
        if info is not None:
            size = int(info.get("size") or (info.get("metadata") or {}).get("size") or 0)
            if size <= 0:
                raise RuntimeError("Export size unavailable")
        elif job["render_attempts"] > 2:
            transition(supabase, project, "fail", **fields,
                       failure="Render was interrupted. Try again.", transient=True)
            return True
        else:
            source = supabase.table("video_assets").select("bucket_id,object_path").eq(
                "id", job["source_asset_id"]
            ).eq("project_id", project).single().execute().data
            with tempfile.TemporaryDirectory(prefix="brevi-render-") as directory:
                input_file = Path(directory) / "source.mp4"
                output_file = Path(directory) / "export.mp4"
                input_file.write_bytes(supabase.storage.from_(source["bucket_id"]).download(source["object_path"]))
                # Leave time for the Storage request and database update.
                remaining = (deadline - datetime.now(timezone.utc)).total_seconds() - 35
                if remaining <= 0:
                    raise TimeoutError("Render deadline exceeded")
                subprocess.run(
                    ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(input_file),
                     "-map", "0:V:0", "-map", "0:a:0?", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-movflags", "+faststart", str(output_file)],
                    check=True, capture_output=True, timeout=remaining,
                )
                size = output_file.stat().st_size
                if (deadline - datetime.now(timezone.utc)).total_seconds() <= 30:
                    raise TimeoutError("Render deadline exceeded")
                if not transition(supabase, project, "write", **fields):
                    return True
                with output_file.open("rb") as output:
                    target.upload(job["object_path"], output, file_options={
                        "content-type": "video/mp4", "upsert": "false", "cache-control": "0",
                    })
        transition(supabase, project, "publish", **fields, bytes=size)
    except subprocess.CalledProcessError:
        transition(supabase, project, "fail", **fields,
                   failure="This video could not be decoded or encoded. Choose a different MP4.")
    except Exception:
        logger.exception("Render attempt failed for export %s", job["id"])
        transition(supabase, project, "fail", **fields,
                   failure="Render could not finish. Try again.", transient=True)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            cleanup()
            if process_next_job():
                continue
        except Exception:
            logger.exception("Video worker operation failed")
        time.sleep(POLL_SECONDS)
