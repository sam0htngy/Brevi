
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os

from supabase import create_client, Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


app = FastAPI(title="Brevi API")

class VideoRequest(BaseModel):
    filename: str

@app.get("/health")
def root():
    return {"Status": "Good"}

@app.post("/api/video", tags = ["video"])
def post_data(request: VideoRequest):
    new_uuid = uuid.uuid4()
    file_ext = request.filename.split(".")[-1].lower()
    storage_path = f"videos/{new_uuid}.{file_ext}"
    
    data = {
        "id": new_uuid,
        "filename": request.filename,
        "storage _path": storage_path,
        "status": "pending"
    }
    supabase.table("videos").insert(data).execute()

    return { "id": new_uuid, 
            "storage_path": storage_path,
            "status": "pending"}
