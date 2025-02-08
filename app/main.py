from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, Azure Container Registry and Container Apps with Github CI/CD!"}