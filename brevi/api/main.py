
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from auth import get_current_user, get_user_id


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
def meta_data(request: VideoRequest, user: dict = Depends(get_current_user)):
    user_id = get_user_id(user)
    new_uuid = uuid.uuid4()
    file_ext = request.filename.split(".")[-1].lower()
    storage_path = f"videos/{new_uuid}.{file_ext}"
    
    data = {
        "id": new_uuid,
        "filename": request.filename,
        "storage_path": storage_path,
        "status": "pending",
        "user_id": user_id
    }
    try:
        supabase.table("videos").insert(data).execute()
        return { 
            "id": str(new_uuid), 
            "storage_path": storage_path,
            "status": "pending",
            "user_id": user_id
    }
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Database error: {str(e)}")

@app.post("/api/video/upload", tags = ["video"])
async def upload_video(file: UploadFile = File(...),user: dict = Depends(get_current_user)):
    user_id = get_user_id(user)

    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSION:
        raise HTTPException(
            status_code = 500,
            detail=f"Invaild file type please use allowed types {', '.join(ALLOWED_EXTENSION)}"
        )

    video_id = uuid.uuid4()
    storage_path = f"videos/{video_id}{file_ext}"
    
    try:
        file_content = await file.read()
        if len(file_content) > MAX_FILE: ## reading file content
            raise HTTPException(
                status_code= 400,
                detail = f"File too large the Maxium size for a file is {MAX_FILE / (1024*1024)}MB"
            )
        supabase.storage.from_("videos").upload( ## uploading storage ainto supabase (temp)
            path = storage_path,
            file = file_content,
            file_options = {"content-type": file.content_type}
    )
        data = { ## database record
            "id": str(video_id),
            "filename": file.filename,
            "storage_path": storage_path,
            "file_size": len(file_content)
    }
 
        supabase.table("videos").insert(data).execute()
        
        return{
            "id": str(video_id),
            "filename": file.filename,
            "storage_path": storage_path,
            "status": "success",
            "user_id": user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Upload failed: {str(e)}")

@app.get("/api/video/{video_id}" , tags = ["video"])
def get_video (video_id:str, user: dict = Depends(get_current_user)):
    user_id = get_user_id(user) 
    try:
        reponse = supabase.table("videos").select("*").eq("id", video_id).execute()
        if not reponse.data:
            raise HTTPException(status_code= 404, detail="Video not found")
        return reponse.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@app.get("/api/video/user/{user_id}", tags= ["video"])
def get_user_videos(user_id: str, user: dict = Depends(get_current_user)):
    authenticated_user_id = get_user_id(user)
    if authenticated_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only acess your own video. ")
    try:
        response = supabase.table("videos").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return{
            "user_id": user_id,
            "videos": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")