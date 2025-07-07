from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
from sqlalchemy.orm import Session

from routes import router
from config import logger

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routes
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        ssl_keyfile="/etc/ssl/daggybot.bet/mydomain.key",
        ssl_certfile="/etc/ssl/daggybot.bet/daggybot_bet.crt",
        reload=True
    )