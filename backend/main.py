from fastapi import FastAPI

app = FastAPI(title="Nagomi")

@app.get("/")
def home():
    return {"message": "Nagomi Backend Running"}