from fastapi import APIRouter

from api import image, hls

# Router tổng của tầng API, mọi endpoint đều dưới prefix /api
api_router = APIRouter(prefix="/api")
api_router.include_router(image.router)
api_router.include_router(hls.router)  # Thêm router hls vào api_router
