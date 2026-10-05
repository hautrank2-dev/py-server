"""Endpoint domain video; prefix /api được thêm ở api/__init__.py -> /api/video/..."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from service import video as video_service
from schemas.image import ErrorResponseModel

# Response lỗi dùng chung cho Swagger
ERROR_RESPONSES = {
    400: {"model": ErrorResponseModel},
    404: {"model": ErrorResponseModel},
    500: {"model": ErrorResponseModel},
}

router = APIRouter(prefix="/video", tags=["video"])


# `def` (không async): FastAPI chạy trong threadpool nên ffmpeg không chặn event loop.
@router.get("/hls/{name}/{filename}", responses=ERROR_RESPONSES)
def hls_endpoint(name: str, filename: str) -> FileResponse:
    """
    Luồng HLS của video `public/video/<name>.mp4`.

    Player chỉ cần URL `/api/video/hls/<name>/index.m3u8`; các segment `seg_NNN.ts`
    được tải qua cùng endpoint này. Lần gọi đầu sẽ chạy ffmpeg để tạo luồng (rồi cache lại).
    """
    try:
        path = video_service.get_hls_file(name, filename)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as nf:
        raise HTTPException(status_code=404, detail=str(nf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create HLS failed: {e}")

    # Phát trực tiếp (inline), không ép tải về như các endpoint trả file khác.
    return FileResponse(path, media_type=video_service.MEDIA_TYPES[path.suffix])
