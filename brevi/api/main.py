import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, create_client

from auth import get_current_user

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
ORIGINALS_BUCKET = "video-originals"
VIDEO_MAX_BYTES = int(os.getenv("VIDEO_MAX_BYTES", str(5 * 1024 * 1024 * 1024)))
UPLOAD_URL_TTL = int(os.getenv("VIDEO_UPLOAD_URL_TTL_SECONDS", "7200"))
PLAYBACK_URL_TTL = int(os.getenv("VIDEO_PLAYBACK_URL_TTL_SECONDS", "900"))
ALLOWED_SOURCE_TYPES = {"video/mp4", "video/quicktime", "video/webm", "video/x-matroska"}

app = FastAPI(title="Brevi API")
app.add_middleware(CORSMiddleware, allow_origins=[origin for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class UploadRequest(ProjectCreate):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str
    byte_size: int = Field(gt=0)


class AssetResponse(BaseModel):
    project_id: UUID
    asset_id: UUID
    object_path: str
    bucket_id: str
    upload_token: str
    upload_expires_in: int


def _opaque_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        suffix = ".mp4"
    return f"source{suffix}"


def _asset_for_owner(asset_id: UUID, owner_id: str) -> dict:
    response = supabase.table("video_assets").select("*").eq("id", str(asset_id)).eq("owner_id", owner_id).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Video asset not found")
    return response.data[0]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/projects/uploads", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(request: UploadRequest, user: dict = Depends(get_current_user)) -> AssetResponse:
    if request.mime_type not in ALLOWED_SOURCE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported source video type")
    if request.byte_size > VIDEO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Video exceeds the upload size limit")
    owner_id = user["sub"]
    project = supabase.table("projects").insert({"title": request.title, "user_id": owner_id}).execute()
    if not project.data:
        raise HTTPException(status_code=500, detail="Could not create project")
    project_id, asset_id = UUID(str(project.data[0]["id"])), uuid4()
    object_path = f"{project_id}/{asset_id}/{_opaque_filename(request.filename)}"
    try:
        supabase.table("video_assets").insert({"id": str(asset_id), "project_id": str(project_id), "owner_id": owner_id, "bucket_id": ORIGINALS_BUCKET, "object_path": object_path, "asset_type": "original", "status": "pending_upload", "original_filename": _opaque_filename(request.filename), "mime_type": request.mime_type, "byte_size": request.byte_size}).execute()
        signed = supabase.storage.from_(ORIGINALS_BUCKET).create_signed_upload_url(object_path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not prepare secure upload") from exc
    return AssetResponse(project_id=project_id, asset_id=asset_id, object_path=object_path, bucket_id=ORIGINALS_BUCKET, upload_token=signed["token"], upload_expires_in=UPLOAD_URL_TTL)


@app.post("/video-assets/{asset_id}/complete", status_code=status.HTTP_202_ACCEPTED)
async def complete_upload(asset_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    asset = _asset_for_owner(asset_id, user["sub"])
    if asset["asset_type"] != "original" or asset["status"] != "pending_upload":
        raise HTTPException(status_code=409, detail="Asset cannot be queued")
    try:
        info = supabase.storage.from_(ORIGINALS_BUCKET).info(asset["object_path"])
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Upload has not completed") from exc
    metadata = info.get("metadata") or {}
    actual_size = metadata.get("size") or info.get("size")
    if actual_size is None or int(actual_size) != asset["byte_size"]:
        raise HTTPException(status_code=409, detail="Uploaded file size does not match reservation")
    supabase.table("video_assets").update({"status": "queued", "uploaded_at": datetime.now(timezone.utc).isoformat()}).eq("id", str(asset_id)).eq("status", "pending_upload").execute()
    return {"asset_id": str(asset_id), "status": "queued"}


@app.get("/video-assets/{asset_id}/playback-url")
async def playback_url(asset_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    asset = _asset_for_owner(asset_id, user["sub"])
    if asset["asset_type"] != "export" or asset["status"] != "ready":
        raise HTTPException(status_code=409, detail="Export is not ready")
    signed = supabase.storage.from_(asset["bucket_id"]).create_signed_url(asset["object_path"], PLAYBACK_URL_TTL)
    return {"url": signed["signedURL"], "expires_in": PLAYBACK_URL_TTL}


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, user: dict = Depends(get_current_user)) -> None:
    project = supabase.table("projects").select("id").eq("id", str(project_id)).eq("user_id", user["sub"]).limit(1).execute()
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")
    assets = supabase.table("video_assets").select("bucket_id,object_path").eq("project_id", str(project_id)).eq("owner_id", user["sub"]).execute()
    for asset in assets.data:
        supabase.storage.from_(asset["bucket_id"]).remove([asset["object_path"]])
    supabase.table("projects").delete().eq("id", str(project_id)).eq("user_id", user["sub"]).execute()
