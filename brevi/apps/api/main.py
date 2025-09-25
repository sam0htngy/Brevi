import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI(title="Brevi API")

class VideoRequest(BaseModel):
    uuid_id: str

@app.get("/health")
def root():
    return {"Status": "Good"}

@app.post("/api/v1/videos")
def post_data(request: VideoRequest):
    new_uuid = uuid.uuid4()
    return {"videos imported": f"{request.uuid_id}"}