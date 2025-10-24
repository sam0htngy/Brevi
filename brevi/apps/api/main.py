
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

app.add_middleware( 
                   CORSMiddleware,
                   allow_origins = ["*"],
                   allow_credentials = True,
                   allow_methods = ["*"],
                   allow_headers = ["*"])

class VideoRequest(BaseModel):
    filename: str

# Allowed video formats 
ALLOWED_EXTENSION = {'.mp4', '.mov', 'avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
MAX_FILE = 500 * 1024 * 1024


@app.get("/health")
def root():
    return {"Status": "Good"}

@app.post("/api/video/metadata", tags = ["video"])
def meta_data(request: VideoRequest):
    new_uuid = uuid.uuid4()
    file_ext = request.filename.split(".")[-1].lower()
    storage_path = f"videos/{new_uuid}.{file_ext}"
    
    data = {
        "id": new_uuid,
        "filename": request.filename,
        "storage_path": storage_path,
        "status": "pending"
    }
    try:
        supabase.table("videos").insert(data).execute()
        return { 
            "id": str(new_uuid), 
            "storage_path": storage_path,
            "status": "pending"
    }
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Database error: {str(e)}")

@app.post("/api/video/upload", tags = ["video"])
async def upload_video(file: uploadeFile - file(...)):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSION:
        raise HTTPException(
            status_code = 400,
            detail=f"Invaild file type please use allowed types {', '.join(ALLOWED_EXTENSION)}"
        )