from io import BytesIO
from functools import lru_cache

from PIL import Image
from rembg import remove, new_session


# ======================= Convert format =======================

EXT_META = {
    "jpg": ("JPEG", "image/jpeg"),
    "jpeg": ("JPEG", "image/jpeg"),
    "png": ("PNG", "image/png"),
    "webp": ("WEBP", "image/webp"),
    "bmp": ("BMP", "image/bmp"),
    "tiff": ("TIFF", "image/tiff"),
}


# Convert all imgs from any extension to .jpg
def convert_img(img_bytes: bytes, ext: str, filename: str = "image", quality: int = 90):
    """
    Convert image bytes to another format.

    Args:
        img_bytes (bytes): dữ liệu ảnh gốc
        ext (str): định dạng đích (jpg, png, webp, bmp, tiff)
        filename (str): tên gốc của ảnh (không bắt buộc)
        quality (int): chất lượng cho JPEG/WEBP (1–100)

    Returns:
        (BytesIO, str, str): buffer, content_type, out_filename
    """

    ext = ext.lower().strip()
    if ext not in EXT_META:
        raise ValueError(
            f"Unsupported extension: {ext}. Allowed: {list(EXT_META.keys())}"
        )

    fmt = get_img_format(img_bytes)
    if fmt is None:
        raise ValueError("Invalid or unsupported image file")

    im = Image.open(BytesIO(img_bytes))

    pil_format, content_type = EXT_META[ext]
    if pil_format == "JPEG":
        im = im.convert("RGB")  # tránh lỗi alpha channel

    # Lưu ra buffer
    buf = BytesIO()
    save_kwargs = {"format": pil_format}

    if pil_format in {"JPEG", "WEBP"}:
        q = max(1, min(100, int(quality)))
        save_kwargs.update({"quality": q, "optimize": True})
        if pil_format == "WEBP":
            save_kwargs.update({"method": 6})

    im.save(buf, **save_kwargs)
    buf.seek(0)

    out_name = f"{filename.rsplit('.',1)[0]}.{ 'jpg' if ext=='jpeg' else ext }"
    return buf, content_type, out_name


def get_img_format(img_bytes: bytes):
    try:
        with Image.open(BytesIO(img_bytes)) as im:
            return im.format  # ví dụ "PNG", "JPEG", "WEBP"
    except Exception:
        return None


# ======================= Remove background =======================

# Model mặc định: u2net (chất lượng tốt cho ảnh/người nói chung).
# Có thể đổi sang: "u2netp" (nhẹ hơn), "isnet-general-use", "birefnet-portrait"...
DEFAULT_MODEL = "u2net"


@lru_cache(maxsize=4)
def _get_session(model_name: str):
    """Tạo & cache session theo model để không phải load lại mỗi request."""
    return new_session(model_name)


def remove_bg(
    img_bytes: bytes,
    filename: str = "image",
    model: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
):
    """
    Xoá nền của ảnh, trả về ảnh PNG có nền trong suốt.

    Args:
        img_bytes (bytes): dữ liệu ảnh gốc
        filename (str): tên gốc của ảnh (không bắt buộc)
        model (str): tên model rembg (u2net, u2netp, isnet-general-use, ...)
        alpha_matting (bool): bật alpha matting cho viền mượt hơn (chậm hơn)

    Returns:
        (BytesIO, str, str): buffer, content_type, out_filename
    """
    try:
        src = Image.open(BytesIO(img_bytes))
    except Exception:
        raise ValueError("Invalid or unsupported image file")

    session = _get_session(model)

    # rembg.remove nhận PIL.Image và trả về PIL.Image (RGBA) khi input là PIL.
    out = remove(
        src,
        session=session,
        alpha_matting=alpha_matting,
        # các tham số alpha matting mặc định hợp lý; chỉ tác dụng khi bật
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    )

    out = out.convert("RGBA")  # đảm bảo có kênh alpha (nền trong suốt)

    buf = BytesIO()
    out.save(buf, format="PNG")  # PNG để giữ nền trong suốt
    buf.seek(0)

    base = filename.rsplit(".", 1)[0] if filename else "image"
    out_name = f"{base}_nobg.png"
    return buf, "image/png", out_name
