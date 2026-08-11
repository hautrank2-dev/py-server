import zipfile
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from service import image as image_service
from schemas.image import ImageFormatEnum, ErrorResponseModel

# Response lỗi dùng chung cho Swagger
ERROR_RESPONSES = {
    400: {"model": ErrorResponseModel},
    500: {"model": ErrorResponseModel},
}

# Endpoint domain image; prefix /api được thêm ở api/__init__.py -> /api/image/...
router = APIRouter(prefix="/image", tags=["image"])


@router.post("/convert", responses=ERROR_RESPONSES)
async def convert_endpoint(
    file: UploadFile = File(..., description="Ảnh nguồn"),
    ext: ImageFormatEnum = Form(..., description="Định dạng đầu ra"),
    quality: int = Form(
        90, ge=1, le=100, description="Chất lượng cho JPEG/WEBP (1–100)"
    ),
):
    """Đổi định dạng ảnh sang jpg/png/webp/bmp/tiff."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = image_service.convert_img(
            raw, ext.value, filename=file.filename, quality=quality
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Convert failed: {e}")

    headers = {"Content-Disposition": f'attachment; filename="{result.filename}"'}
    return StreamingResponse(
        result.buffer, media_type=result.content_type, headers=headers
    )


@router.post("/remove-bg", responses=ERROR_RESPONSES)
async def remove_bg_endpoint(request: Request, crop: bool = False):
    """
    Xoá nền một hoặc nhiều ảnh, trả về file ZIP.

    Query param:
        crop (bool): cắt sát chủ thể (bỏ viền trong suốt). Mặc định false.
    Body: multipart/form-data, mỗi phần là { key: <tên>, file: <ảnh> }.
    Response: file ZIP, mỗi ảnh đã xoá nền được đặt tên "<key>.png".
    """
    form = await request.form()

    # Chỉ lấy các phần là file; key chính là field name trong FormData.
    files = [
        (key, value)
        for key, value in form.multi_items()
        if isinstance(value, StarletteUploadFile)
    ]
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    zip_buf = BytesIO()
    used_names = set()

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for key, upload in files:
            raw = await upload.read()
            if not raw:
                raise HTTPException(
                    status_code=400, detail=f"Empty file for key '{key}'"
                )

            print("crop", crop)
            try:
                result = image_service.remove_bg(raw, filename=key, crop=crop)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=f"[{key}] {ve}")
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"[{key}] Remove background failed: {e}"
                )

            # Lấy key làm tên file; tránh trùng tên nếu có key giống nhau.
            name = f"{key}.png"
            i = 1
            while name in used_names:
                name = f"{key}_{i}.png"
                i += 1
            used_names.add(name)

            zf.writestr(name, result.buffer.getvalue())

    zip_buf.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="avatars-nobg.zip"'}
    return StreamingResponse(zip_buf, media_type="application/zip", headers=headers)
