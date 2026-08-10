import zipfile
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

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
async def remove_bg_endpoint(request: Request):
    """
    Xoá nền một hoặc nhiều ảnh, trả về file ZIP.

    Body: multipart/form-data, mỗi phần là { key: <tên>, file: <ảnh> }.
    Có thể gửi thêm field `crop` (true/false) để cắt sát chủ thể.
    Response: file ZIP, mỗi ảnh đã xoá nền được đặt tên "<key>.png".
    """
    form = await request.form()

    # Field cấu hình dùng chung cho cả batch (không phải file).
    crop = str(form.get("crop", "")).strip().lower() in ("1", "true", "on", "yes")

    # Chỉ lấy các phần là file; key chính là field name trong FormData.
    files = [(key, value) for key, value in form.multi_items()
             if isinstance(value, StarletteUploadFile)]
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    zip_buf = BytesIO()
    used_names = set()

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for key, upload in files:
            raw = await upload.read()
            if not raw:
                raise HTTPException(status_code=400, detail=f"Empty file for key '{key}'")

            try:
                buf, _, _ = image_service.remove_bg(raw, filename=key, crop=crop)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=f"[{key}] {ve}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"[{key}] Remove background failed: {e}")

            # Lấy key làm tên file; tránh trùng tên nếu có key giống nhau.
            name = f"{key}.png"
            i = 1
            while name in used_names:
                name = f"{key}_{i}.png"
                i += 1
            used_names.add(name)

            zf.writestr(name, buf.getvalue())

    zip_buf.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="avatars-nobg.zip"'}
    return StreamingResponse(zip_buf, media_type="application/zip", headers=headers)
