import uvicorn
from app.api.router import app

if __name__ == "__main__":
    uvicorn.run("app.api.router:app", host="0.0.0.0", port=8000, reload=True)