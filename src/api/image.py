from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

from service import image as image_service

# Endpoint domain image; prefix /api được thêm ở api/__init__.py -> /api/image/...
router = APIRouter(prefix="/image", tags=["image"])


@router.post("/convert")
async def convert_endpoint(
    file: UploadFile = File(..., description="Ảnh nguồn"),
    ext: str = Form(..., description="Định dạng đầu ra: jpg|jpeg|png|webp|bmp|tiff"),
    quality: int = Form(90, description="Chất lượng cho JPEG/WEBP (1–100)"),
):
    """Đổi định dạng ảnh sang jpg/png/webp/bmp/tiff."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        buf, content_type, out_name = image_service.convert_img(
            raw, ext, filename=file.filename, quality=quality
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Convert failed: {e}")

    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return StreamingResponse(buf, media_type=content_type, headers=headers)


@router.post("/remove-bg")
async def remove_bg_endpoint(
    file: UploadFile = File(..., description="Ảnh nguồn (avatar)"),
    model: str = Form("u2net", description="Model rembg: u2net|u2netp|isnet-general-use"),
    alpha_matting: bool = Form(False, description="Bật alpha matting cho viền mượt hơn (chậm hơn)"),
):
    """Xoá nền ảnh, trả về PNG nền trong suốt."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        buf, content_type, out_name = image_service.remove_bg(
            raw, filename=file.filename, model=model, alpha_matting=alpha_matting
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remove background failed: {e}")

    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return StreamingResponse(buf, media_type=content_type, headers=headers)
