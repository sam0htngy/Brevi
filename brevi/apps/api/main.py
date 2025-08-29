import uvicorn
from fastapi import FASTAPI
from fastapi.middleware.cors import CORSMiddleware

app = FASTAPI(title="Brevi API")

@app.get("/health")
def root():
    return {"Status": "Good"}