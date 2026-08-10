# Image API

API xử lý ảnh: đổi định dạng và xoá nền (background removal).

- **Base path:** `/api/image`
- **Tag (Swagger):** `image`
- **Swagger UI:** `GET /docs` · **OpenAPI JSON:** `GET /openapi.json`

> Nếu deploy sau reverse proxy / tailscale serve với một path prefix (ví dụ `/tenmoi`),
> URL đầy đủ sẽ là `https://<host>/tenmoi/api/image/...`.

---

## POST `/api/image/convert`

Đổi định dạng ảnh sang `jpg | jpeg | png | webp | bmp | tiff`.

### Request — `multipart/form-data`

| Field     | Kiểu    | Bắt buộc | Mặc định | Mô tả |
|-----------|---------|----------|----------|-------|
| `file`    | file    | ✅       | —        | Ảnh nguồn |
| `ext`     | string  | ✅       | —        | Định dạng đích: `jpg`, `jpeg`, `png`, `webp`, `bmp`, `tiff` |
| `quality` | integer | ❌       | `90`     | Chất lượng cho JPEG/WEBP (1–100) |

### Response — `200 OK`

- **Content-Type:** theo định dạng đích (vd `image/png`, `image/jpeg`, `image/webp`…)
- **Header:** `Content-Disposition: attachment; filename="<tên>.<ext>"`
- **Body:** dữ liệu ảnh (binary)

### Ví dụ

```bash
curl -X POST http://localhost:8000/api/image/convert \
  -F "file=@avatar.jpg" \
  -F "ext=webp" \
  -F "quality=85" \
  -o avatar.webp
```

---

## POST `/api/image/remove-bg`

Xoá nền ảnh bằng AI (thư viện [`rembg`](https://github.com/danielgatis/rembg), model ONNX U2Net).
Kết quả luôn là **PNG có nền trong suốt**.

### Request — `multipart/form-data`

| Field           | Kiểu    | Bắt buộc | Mặc định | Mô tả |
|-----------------|---------|----------|----------|-------|
| `file`          | file    | ✅       | —        | Ảnh nguồn (avatar) |
| `model`         | string  | ❌       | `u2net`  | Model rembg: `u2net` (mặc định, tốt cho người), `u2netp` (nhẹ/nhanh), `isnet-general-use` |
| `alpha_matting` | boolean | ❌       | `false`  | Bật alpha matting cho viền mượt hơn (chậm hơn) |

### Response — `200 OK`

- **Content-Type:** `image/png`
- **Header:** `Content-Disposition: attachment; filename="<tên>_nobg.png"`
- **Body:** ảnh PNG (RGBA, nền trong suốt)

### Ví dụ

```bash
curl -X POST http://localhost:8000/api/image/remove-bg \
  -F "file=@avatar.jpg" \
  -F "model=u2net" \
  -o avatar_nobg.png
```

Bật alpha matting cho viền mượt hơn:

```bash
curl -X POST http://localhost:8000/api/image/remove-bg \
  -F "file=@avatar.jpg" \
  -F "alpha_matting=true" \
  -o avatar_nobg.png
```

### Ghi chú

- Lần chạy đầu, `rembg` tự tải model (`u2net.onnx` ~176MB) về `$U2NET_HOME` (mặc định `~/.u2net`). Trong Docker model đã được bake sẵn nên request đầu không phải chờ.
- Session của mỗi model được cache trong bộ nhớ (`lru_cache`) nên không load lại mỗi request.
- Mỗi worker giữ một bản model trong RAM (~200–300MB) — cân nhắc khi tăng số worker.

---

## Lỗi chung

Trả về JSON `{"detail": "<message>"}` với status:

| Status | Khi nào |
|--------|---------|
| `400`  | File rỗng, ảnh không hợp lệ, hoặc `ext` không được hỗ trợ |
| `500`  | Lỗi trong quá trình xử lý (convert / remove background) |

Ví dụ:

```json
{ "detail": "Unsupported extension: gif. Allowed: ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff']" }
```

---

## Cấu trúc code

Toàn bộ code nằm trong `src/` (giống frontend), chia theo tầng: `api` (routers) và `service` (nghiệp vụ).

```
src/
├── main.py         # entrypoint: FastAPI app + CORS + mount router
├── api/
│   ├── __init__.py # api_router, prefix="/api", gộp các router con
│   └── image.py    # endpoint image (APIRouter, prefix="/image") -> /api/image/...
└── service/
    ├── __init__.py
    └── image.py    # xử lý nghiệp vụ: convert_img(), remove_bg()
```

`main.py` chỉ mount router tổng:

```python
from api import api_router
app.include_router(api_router)
```

### Chạy local

Vì code nằm trong `src/`, chạy uvicorn với `--app-dir src`:

```bash
uvicorn main:app --app-dir src --reload
```
