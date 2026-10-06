import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(tags=["web"], include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "active": "home"},
    )


@router.get("/monitor", response_class=HTMLResponse)
async def monitor(request: Request):
    cameras = [
        {"id": "CAM-01", "name": "Bãi đỗ xe · Lối vào", "location": "Tầng trệt · Khu A"},
        {"id": "CAM-02", "name": "Bãi đỗ xe · Khu trung tâm", "location": "Tầng trệt · Khu B"},
        {"id": "CAM-03", "name": "Bãi đỗ xe · Lối ra", "location": "Tầng trệt · Khu C"},
        {"id": "CAM-04", "name": "Bãi đỗ xe · Tầng hầm", "location": "Tầng B1 · Khu D"},
    ]
    return templates.TemplateResponse(
        request=request,
        name="monitor.html",
        context={"request": request, "active": "monitor", "cameras": cameras},
    )


@router.get("/image", response_class=HTMLResponse)
async def image_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="image.html",
        context={"request": request, "active": "image"},
    )


@router.get("/image/convert", response_class=HTMLResponse)
async def image_convert(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="convert.html",
        context={"request": request, "active": "image"},
    )


@router.get("/image/remove-bg", response_class=HTMLResponse)
async def image_remove_bg(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="remove_bg.html",
        context={"request": request, "active": "image"},
    )
