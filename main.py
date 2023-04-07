from fastapi import FastAPI
from router import ssh, server, user
from db import models
from db.database import engine
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.include_router(ssh.router)
app.include_router(user.router)
app.include_router(server.router)
models.Base.metadata.create_all(engine)
