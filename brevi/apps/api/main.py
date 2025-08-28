from fastapi import FASTAPI


app = FASTAPI(title="Brevi API")

@app.get("/health")
def root():
    return {"Status": "Good"}