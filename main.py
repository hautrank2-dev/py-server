from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image.router import router as image_router

app = FastAPI(title="Media Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domain routers
app.include_router(image_router)
# app.include_router(video_router)  # sau này thêm domain video ở đây


@app.get("/")
def read_root():
    return {"status": "ok"}
