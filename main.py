from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from services.image import convert_img
from services.background import remove_background
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}


@app.post("/convert")
async def convert_endpoint(
    file: UploadFile = File(..., description="Ảnh nguồn"),
    ext: str = Form(..., description="Định dạng đầu ra: jpg|jpeg|png|webp|bmp|tiff"),
    quality: int = Form(90, description="Chất lượng cho JPEG/WEBP (1–100)"),
):
    print('@app.post("/convert")', file, ext, quality)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        buf, content_type, out_name = convert_img(
            raw, ext, filename=file.filename, quality=quality
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Convert failed: {e}")

    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return StreamingResponse(buf, media_type=content_type, headers=headers)


@app.post("/remove-bg")
async def remove_bg_endpoint(
    file: UploadFile = File(..., description="Ảnh nguồn (avatar)"),
    model: str = Form("u2net", description="Model rembg: u2net|u2netp|isnet-general-use"),
    alpha_matting: bool = Form(False, description="Bật alpha matting cho viền mượt hơn (chậm hơn)"),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        buf, content_type, out_name = remove_background(
            raw, filename=file.filename, model=model, alpha_matting=alpha_matting
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remove background failed: {e}")

    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return StreamingResponse(buf, media_type=content_type, headers=headers)
