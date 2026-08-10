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
    return templates.TemplateResponse("index.html", {"request": request, "active": "home"})


@router.get("/image", response_class=HTMLResponse)
async def image_home(request: Request):
    return templates.TemplateResponse("image.html", {"request": request, "active": "image"})


@router.get("/image/convert", response_class=HTMLResponse)
async def image_convert(request: Request):
    return templates.TemplateResponse("convert.html", {"request": request, "active": "image"})


@router.get("/image/remove-bg", response_class=HTMLResponse)
async def image_remove_bg(request: Request):
    return templates.TemplateResponse("remove_bg.html", {"request": request, "active": "image"})
