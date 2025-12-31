
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
from auth import get_current_user
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

current_folder = Path(__file__).resolve().parent
env_path = current_folder.parent / ".env"

load_dotenv(dotenv_path=env_path)


from supabase import create_client, Client
SUPABASE_URL = os.getenv("REACT_APP_SUPABASE_URL")
SUPABASE_KEY = os.getenv("REACT_APP_SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL,SUPABASE_KEY)

app = FastAPI(title="Brevi API")

app.add_middleware( 
        CORSMiddleware,
        allow_origins = ["*"],
        allow_credentials = True,
        allow_methods = ["*"],
        allow_headers = ["*"])

class Projects(BaseModel):
    title: str
    video_url: Optional[str] = None
    user_id: str = Field(..., alias = "userId")
    
    class Config:
        populate_by_name = True 

@app.get("/health")
def root():
    return {"Status": "Good"}

@app.post("/projects")
async def create_project(project: Projects):
    try:
        data = {
            "title": project.title,
            "video_url": project.video_url,
            "user_id": project.user_id
        }
        response = supabase.table("projects").insert(data).execute()
        
        return {"status": "sucess", "data": response.data}
        
    except Exception as e:
        print(f"Error creating project {e}")
        raise HTTPException(status_code=500, detail=str(e))