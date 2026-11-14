import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import MAX_VIDEO_BYTES, connect, object_info, transition
from auth import get_current_user

supabase = connect()
app = FastAPI(title="Brevi API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",") if origin.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
PLAYBACK_URL_TTL = int(os.getenv("VIDEO_PLAYBACK_URL_TTL_SECONDS", "900"))
User = Annotated[dict, Depends(get_current_user)]


@app.middleware("http")
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


class UploadRequest(BaseModel):
    attempt_id: UUID
    title: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=255)
    mime_type: Literal["video/mp4"]
    byte_size: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def projects_for(owner: str):
    return supabase.table("projects").select(
        "id,title,created_at,upload_attempt_id,video_assets(id,asset_type,status,source_asset_id,"
        "created_at,completed_at,retryable,error_message)"
    ).eq("user_id", owner).is_("deleting_at", "null")


def asset_for(asset_id: UUID, owner: str) -> dict:
    assets = supabase.table("video_assets").select("*,projects!inner(deleting_at)").eq(
        "id", str(asset_id)
    ).eq("owner_id", owner).eq("projects.user_id", owner).is_(
        "projects.deleting_at", "null"
    ).limit(1).execute().data
    if not assets:
        raise HTTPException(404, "Video asset not found")
    return assets[0]


def verify_upload(asset: dict) -> bool:
    storage = supabase.storage.from_(asset["bucket_id"])
    info = object_info(storage, asset["object_path"])
    if info is None:
        return False
    size = info.get("size") or (info.get("metadata") or {}).get("size")
    if size is None or int(size) != asset["byte_size"]:
        raise HTTPException(409, "Uploaded file does not match the reservation")
    if asset["sha256"]:
        content = storage.download(asset["object_path"])
        if len(content) != asset["byte_size"] or hashlib.sha256(content).hexdigest() != asset["sha256"]:
            raise HTTPException(409, "Uploaded file does not match the reservation")
    return True


def complete(asset: dict, owner: str) -> dict:
    updated = transition(supabase, asset["project_id"], "complete", asset=asset["id"], actor=owner)
    if not updated:
        raise HTTPException(404, "Video asset not found")
    if updated["status"] != "ready":
        raise HTTPException(410, "Upload reservation expired")
    return updated


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/projects")
def list_projects(user: User) -> list:
    return projects_for(user["sub"]).order("created_at", desc=True).execute().data


@app.get("/projects/{project_id}")
def project_detail(project_id: UUID, user: User) -> dict:
    rows = projects_for(user["sub"]).eq("id", str(project_id)).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "Project not found")
    return rows[0]


@app.get("/projects/{project_id}/upload-attempt")
def upload_attempt(project_id: UUID, user: User) -> dict:
    rows = supabase.table("projects").select("upload_attempt_id,upload_request").eq(
        "id", str(project_id)
    ).eq("user_id", user["sub"]).is_("deleting_at", "null").limit(1).execute().data
    if not rows or not rows[0]["upload_attempt_id"]:
        raise HTTPException(404, "Upload reservation not found")
    return {**rows[0]["upload_request"], "attempt_id": rows[0]["upload_attempt_id"]}


@app.post("/projects/uploads", status_code=201)
def create_upload(request: UploadRequest, user: User) -> dict:
    if request.byte_size > MAX_VIDEO_BYTES:
        raise HTTPException(413, "Video exceeds the 25 MiB upload limit")
    if not request.filename.lower().endswith(".mp4"):
        raise HTTPException(415, "Choose an MP4 file")

    owner = user["sub"]
    asset = supabase.rpc("reserve_video_upload", {
        "owner": owner,
        "attempt": str(request.attempt_id),
        "inputs": request.model_dump(exclude={"attempt_id"}),
    }).execute().data
    if asset.get("result") == "conflict":
        raise HTTPException(409, "Upload attempt already has different inputs")
    if asset.get("result") == "unavailable":
        raise HTTPException(410, "Project was deleted")

    result = {"project_id": asset["project_id"], "asset_id": asset["id"], "status": asset["status"]}
    if asset["status"] == "ready":
        return result
    if asset["status"] != "pending_upload" or datetime.fromisoformat(asset["created_at"]) <= (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ):
        raise HTTPException(410, "Upload reservation expired")
    if verify_upload(asset):
        complete(asset, owner)
        return {**result, "status": "ready"}

    authorized = transition(supabase, asset["project_id"], "authorize", asset=asset["id"], actor=owner)
    if not authorized:
        current = asset_for(UUID(asset["id"]), owner)
        if current["status"] == "ready":
            return {**result, "status": "ready"}
        raise HTTPException(410, "Upload reservation expired")
    signed = supabase.storage.from_(asset["bucket_id"]).create_signed_upload_url(asset["object_path"])
    return {
        **result, "bucket_id": asset["bucket_id"], "object_path": asset["object_path"],
        "upload_token": signed["token"],
    }


@app.post("/video-assets/{asset_id}/complete", status_code=202)
def complete_upload(asset_id: UUID, user: User) -> dict:
    asset = asset_for(asset_id, user["sub"])
    if asset["asset_type"] != "original":
        raise HTTPException(409, "Only Originals can complete an upload")
    if asset["status"] == "pending_upload" and not verify_upload(asset):
        raise HTTPException(409, "Upload has not completed")
    updated = complete(asset, user["sub"])
    return {"asset_id": updated["id"], "status": updated["status"]}


@app.post("/video-assets/{asset_id}/retry", status_code=202)
def retry_render(asset_id: UUID, user: User) -> dict:
    asset = asset_for(asset_id, user["sub"])
    if asset["asset_type"] == "export" and asset["status"] in ("queued", "processing"):
        return {"status": asset["status"]}
    result = transition(supabase, asset["project_id"], "retry", asset=asset["id"], actor=user["sub"])
    if not result:
        raise HTTPException(409, "This render cannot be retried")
    return {"status": result["status"]}


@app.get("/video-assets/{asset_id}/playback-url")
def playback_url(asset_id: UUID, user: User) -> dict:
    asset = asset_for(asset_id, user["sub"])
    if asset["asset_type"] != "export" or asset["status"] != "ready":
        raise HTTPException(409, "Export is not ready")
    signed = supabase.storage.from_(asset["bucket_id"]).create_signed_url(
        asset["object_path"], PLAYBACK_URL_TTL
    )
    # Deletion may have started while Storage was signing the URL.
    asset_for(asset_id, user["sub"])
    return {"url": signed["signedURL"], "expires_in": PLAYBACK_URL_TTL}


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: UUID, user: User) -> Response:
    if not transition(supabase, str(project_id), "delete", actor=user["sub"]):
        raise HTTPException(404, "Project not found")
    return Response(status_code=204)
