from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import api_router
from web.router import router as web_router, STATIC_DIR

app = FastAPI(title="Media Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tài nguyên tĩnh (CSS/JS) cho trang demo
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# API + trang web demo
app.include_router(api_router)
app.include_router(web_router)


@app.get("/health")
def health():
    return {"status": "ok"}
