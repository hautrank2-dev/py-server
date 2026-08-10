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

Xoá nền một hoặc nhiều ảnh bằng AI (thư viện [`rembg`](https://github.com/danielgatis/rembg), model ONNX U2Net).
Kết quả trả về **file ZIP**, mỗi ảnh là PNG nền trong suốt.

### Request — `multipart/form-data`

Mỗi phần là một cặp `key → file`. **`key` chính là field name** trong `FormData`, và được dùng làm tên file trong zip.

```js
const fd = new FormData();
fd.append("avatar1", file1);   // -> avatar1.png
fd.append("avatar2", file2);   // -> avatar2.png
```

| Phần    | Kiểu    | Mặc định | Mô tả |
|---------|---------|----------|-------|
| `<key>` | file    | —        | Ảnh nguồn. Gửi bao nhiêu phần cũng được, mỗi phần một key. Chỉ cần 1 phần cho trường hợp 1 ảnh. |
| `crop`  | boolean | `false`  | Cắt sát chủ thể — bỏ phần trong suốt thừa quanh 4 cạnh. Áp dụng cho tất cả ảnh trong request. |

> Model mặc định `u2net` (endpoint chưa nhận tham số `model`/`alpha_matting`).

### Response — `200 OK`

- **Content-Type:** `application/zip`
- **Header:** `Content-Disposition: attachment; filename="avatars-nobg.zip"`
- **Body:** file zip, mỗi ảnh đã xoá nền có tên `<key>.png` (nếu key trùng nhau sẽ thành `<key>_1.png`, `<key>_2.png`…).

### Ví dụ

Nhiều ảnh:

```bash
curl -X POST http://localhost:8000/api/image/remove-bg \
  -F "avatar1=@a.jpg" \
  -F "avatar2=@b.jpg" \
  -o avatars-nobg.zip
```

Một ảnh (vẫn trả về zip chứa 1 file):

```bash
curl -X POST http://localhost:8000/api/image/remove-bg \
  -F "avatar=@avatar.jpg" \
  -o avatars-nobg.zip
```

Cắt sát chủ thể:

```bash
curl -X POST http://localhost:8000/api/image/remove-bg \
  -F "avatar=@avatar.jpg" \
  -F "crop=true" \
  -o avatars-nobg.zip
```

### Ghi chú

- Lần chạy đầu, `rembg` tự tải model (`u2net.onnx` ~176MB) về `$U2NET_HOME` (mặc định `~/.u2net`). Trong Docker model đã được bake sẵn nên request đầu không phải chờ.
- Session của mỗi model được cache trong bộ nhớ (`lru_cache`) nên không load lại mỗi request.
- Mỗi worker giữ một bản model trong RAM (~200–300MB) — cân nhắc khi tăng số worker.
- Ảnh được xử lý **tuần tự** trong một request.

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
