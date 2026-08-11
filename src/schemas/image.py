"""Kiểu dữ liệu (types/schemas) cho domain image: tham số request & kết quả trả về.

Quy ước đặt tên: mỗi type có suffix theo loại — Enum / Dto / Model / Type.
"""
from enum import Enum
from io import BytesIO
from typing import NamedTuple

from pydantic import BaseModel


class ImageFormatEnum(str, Enum):
    """Định dạng ảnh đầu ra hợp lệ cho endpoint convert."""
    jpg = "jpg"
    jpeg = "jpeg"
    png = "png"
    webp = "webp"
    bmp = "bmp"
    tiff = "tiff"


class FileResultDto(NamedTuple):
    """Kết quả xử lý ở tầng service: buffer nhị phân + content-type + tên file."""
    buffer: BytesIO
    content_type: str
    filename: str


class ErrorResponseModel(BaseModel):
    """Khuôn JSON trả về khi lỗi (khớp `HTTPException.detail`)."""
    detail: str
