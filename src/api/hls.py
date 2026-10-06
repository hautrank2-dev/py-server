"""HLS endpoint; prefix /api được thêm ở api/__init__.py -> /api/hls/..."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from service import hls as hls_service
from schemas.image import ErrorResponseModel

# Response lỗi dùng chung cho Swagger
ERROR_RESPONSES = {
    400: {"model": ErrorResponseModel},
    404: {"model": ErrorResponseModel},
    500: {"model": ErrorResponseModel},
}

router = APIRouter(prefix="/hls", tags=["hls"])

# `def` (không async): FastAPI chạy trong threadpool nên ffmpeg không chặn event loop.
@router.get("/{name}/{filename}", responses=ERROR_RESPONSES)
def hls_endpoint(name: str, filename: str):
    """
    Luồng HLS của video `public/video/<name>.mp4`.

    Player chỉ cần URL `/api/hls/<name>/index.m3u8`; các segment `seg_NNN.ts`
    được tải qua cùng endpoint này. Lần gọi đầu sẽ chạy ffmpeg để tạo luồng (rồi cache lại).
    """
    try:
        if filename == hls_service.PLAYLIST_NAME:
            playlist = hls_service.get_live_playlist(name)
            return Response(
                content=playlist,
                media_type=hls_service.MEDIA_TYPES[".m3u8"],
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )
        path = hls_service.get_hls_file(name, filename)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as nf:
        raise HTTPException(status_code=404, detail=str(nf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create HLS failed: {e}")

    # Phát trực tiếp (inline), không ép tải về như các endpoint trả file khác.
    return FileResponse(path, media_type=hls_service.MEDIA_TYPES[path.suffix])
