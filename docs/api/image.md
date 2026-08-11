# Image API

API xử lý ảnh: **đổi định dạng** và **xoá nền (background removal)**.

| Mục | Giá trị |
|-----|---------|
| Base path | `/api/image` |
| Tag (Swagger) | `image` |
| Auth | Không yêu cầu |
| CORS | Cho phép tất cả origin (`Access-Control-Allow-Origin` phản chiếu origin) |
| Swagger UI | `GET /docs` |
| OpenAPI JSON | `GET /openapi.json` |

> Khi deploy sau reverse proxy / `tailscale serve` có path prefix (vd `/tenmoi`),
> URL đầy đủ là `https://<host>/tenmoi/api/image/...`.

## Quy ước chung

- **Request** dùng `multipart/form-data` (vì có upload file).
- **Response thành công** là **dữ liệu nhị phân** (ảnh hoặc file zip) kèm header `Content-Disposition: attachment` để tải về — *không phải JSON*.
- **Response lỗi** luôn là JSON theo cùng một khuôn:

  ```json
  { "detail": "<mô tả lỗi>" }
  ```

  với HTTP status `4xx`/`5xx` tương ứng (chi tiết ở từng endpoint và mục [Bảng lỗi](#bảng-lỗi-chung)).

---

# 1) POST `/api/image/convert`

Đổi định dạng một ảnh sang `jpg | jpeg | png | webp | bmp | tiff`.

## Request

| | |
|---|---|
| Method | `POST` |
| Path | `/api/image/convert` |
| Content-Type | `multipart/form-data` |

### Form fields

| Field     | Kiểu    | Bắt buộc | Mặc định | Ràng buộc / Giá trị hợp lệ | Mô tả |
|-----------|---------|:--------:|:--------:|----------------------------|-------|
| `file`    | file    | ✅ | — | Là một ảnh hợp lệ (đọc được bằng Pillow) | Ảnh nguồn |
| `ext`     | string  | ✅ | — | `jpg`, `jpeg`, `png`, `webp`, `bmp`, `tiff` (không phân biệt hoa/thường) | Định dạng đích |
| `quality` | integer | ❌ | `90` | `1`–`100`; giá trị ngoài khoảng bị kẹp về biên | Chất lượng nén — **chỉ áp dụng cho `jpg/jpeg/webp`**, bỏ qua với định dạng khác |

### Hành vi

- Khi `ext` là `jpg/jpeg`: ảnh được chuyển sang **RGB**, nên **mất kênh trong suốt** (vùng trong suốt bị làm phẳng trên nền đen). Muốn giữ trong suốt hãy dùng `png` hoặc `webp`.
- Tên file kết quả = `<tên gốc bỏ đuôi>.<ext>`, riêng `jpeg` xuất ra đuôi `.jpg`.

## Response `200 OK`

| Header | Giá trị |
|--------|---------|
| `Content-Type` | Theo `ext`: `image/jpeg` (jpg/jpeg), `image/png`, `image/webp`, `image/bmp`, `image/tiff` |
| `Content-Disposition` | `attachment; filename="<tên>.<ext>"` |

**Body:** dữ liệu ảnh (binary).

## Lỗi

| Status | `detail` | Khi nào |
|:------:|----------|---------|
| `400` | `Empty file` | Body `file` rỗng |
| `400` | `Invalid or unsupported image file` | `file` không phải ảnh đọc được |
| `422` | *(FastAPI validation)* | Thiếu field bắt buộc `file`/`ext`, `ext` không thuộc `ImageFormat`, hoặc `quality` ngoài `[1,100]` |
| `500` | `Convert failed: <chi tiết>` | Lỗi không lường trước khi convert |

> `ext` được validate bằng enum `ImageFormatEnum` (xem `src/schemas/image.py`) nên giá trị lạ trả `422` — Swagger cũng hiện dropdown chọn sẵn.

## Ví dụ

**cURL:**

```bash
curl -X POST http://localhost:8000/api/image/convert \
  -F "file=@avatar.jpg" \
  -F "ext=webp" \
  -F "quality=85" \
  -o avatar.webp
```

**JavaScript (fetch):**

```js
const fd = new FormData();
fd.append("file", fileInput.files[0]);
fd.append("ext", "png");

const res = await fetch("/api/image/convert", { method: "POST", body: fd });
if (!res.ok) throw new Error((await res.json()).detail);
const blob = await res.blob();               // image/png
const url = URL.createObjectURL(blob);       // dùng cho <img> hoặc link tải
```

---

# 2) POST `/api/image/remove-bg`

Xoá nền **một hoặc nhiều ảnh** bằng AI (thư viện [`rembg`](https://github.com/danielgatis/rembg), model ONNX **U2Net**). Kết quả trả về **một file ZIP**, mỗi ảnh bên trong là **PNG nền trong suốt (RGBA)**.

## Request

| | |
|---|---|
| Method | `POST` |
| Path | `/api/image/remove-bg` |
| Content-Type | `multipart/form-data` |

### Query params

| Param  | Kiểu    | Bắt buộc | Mặc định | Mô tả |
|--------|---------|:--------:|:--------:|-------|
| `crop` | boolean | ❌ | `false` | `true` → cắt sát chủ thể (bỏ phần trong suốt thừa quanh 4 cạnh). Áp dụng cho **mọi** ảnh trong request. |

> FastAPI ép kiểu bool: `true/false`, `1/0`, `on/off`, `yes/no` đều hợp lệ (không phân biệt hoa/thường).

### Form fields (body)

Body gồm **N phần file** (mỗi phần một ảnh).

| Field   | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---------|------|:--------:|:--------:|-------|
| `<key>` | file | ✅ (≥1) | — | Ảnh nguồn. **`key` là field name** và được dùng làm **tên file kết quả** (`<key>.png`). Gửi nhiều phần để xử lý hàng loạt. |

### Ngữ nghĩa `key` (quan trọng)

Trong `FormData`, `key` chính là **field name**:

```js
const fd = new FormData();
fd.append("avatar1", file1);   // -> avatar1.png trong zip
fd.append("user_42", file2);   // -> user_42.png trong zip
```

- Chỉ những phần **là file** mới được xử lý.
- **Key trùng nhau** được phép: file thứ hai cùng key sẽ đặt tên `<key>_1.png`, thứ ba `<key>_2.png`… để không đè trong zip.

### Tham số chưa hỗ trợ

Endpoint này **luôn dùng model `u2net`** và **không** nhận `model` / `alpha_matting` (khác với hàm service nội bộ). Nếu cần, sẽ bổ sung sau dưới dạng field dùng chung cho cả batch.

## Response `200 OK`

| Header | Giá trị |
|--------|---------|
| `Content-Type` | `application/zip` |
| `Content-Disposition` | `attachment; filename="avatars-nobg.zip"` |

**Body:** file ZIP (nén DEFLATE). Mỗi entry:

| | |
|---|---|
| Tên entry | `<key>.png` (dedupe `_1`, `_2`… nếu key trùng) |
| Định dạng | PNG, RGBA (có kênh alpha trong suốt) |
| Kích thước | Bằng ảnh gốc; nếu `crop=true` thì bằng bounding box của chủ thể |

> **Luôn trả zip** — kể cả khi chỉ gửi 1 ảnh (zip chứa đúng 1 file).
> Nếu `crop=true` mà ảnh **không còn pixel nào** sau khi xoá nền (toàn bộ là nền), ảnh giữ nguyên kích thước (không cắt).

## Lỗi

| Status | `detail` | Khi nào |
|:------:|----------|---------|
| `400` | `No files uploaded` | Không có phần nào là file |
| `400` | `Empty file for key '<key>'` | Một phần file bị rỗng |
| `400` | `[<key>] <mô tả>` | Ảnh của `<key>` không hợp lệ (vd `Invalid or unsupported image file`) |
| `500` | `[<key>] Remove background failed: <chi tiết>` | Lỗi không lường trước khi xoá nền |

## Ví dụ

**cURL — nhiều ảnh:**

```bash
curl -X POST http://localhost:8000/api/image/remove-bg \
  -F "avatar1=@a.jpg" \
  -F "avatar2=@b.jpg" \
  -o avatars-nobg.zip
```

**cURL — một ảnh, cắt sát chủ thể (`crop` ở query):**

```bash
curl -X POST "http://localhost:8000/api/image/remove-bg?crop=true" \
  -F "avatar=@avatar.jpg" \
  -o avatars-nobg.zip
```

**JavaScript (fetch) — gửi nhiều file + tuỳ chọn crop qua query:**

```js
const fd = new FormData();
files.forEach((f, i) => fd.append(`avatar${i + 1}`, f));  // key -> avatarN.png

const res = await fetch("/api/image/remove-bg?crop=true", { method: "POST", body: fd });
if (!res.ok) throw new Error((await res.json()).detail);
const zipBlob = await res.blob();            // application/zip
```

> Muốn hiển thị từng ảnh trong zip trên trình duyệt mà không cần thư viện, có thể giải nén bằng `DecompressionStream("deflate-raw")` (xem `src/web/templates/remove_bg.html`).

## Ghi chú vận hành

- **Model:** lần chạy đầu `rembg` tự tải `u2net.onnx` (~176MB) về `$U2NET_HOME` (mặc định `~/.u2net`). Trong Docker model đã được **bake sẵn** nên request đầu không phải chờ.
- **Cache:** session của model được cache trong RAM (`lru_cache`) — không load lại mỗi request.
- **Bộ nhớ:** mỗi worker giữ một bản model (~200–300MB). Cân nhắc khi tăng số worker.
- **Xử lý tuần tự:** các ảnh trong cùng một request được xử lý lần lượt (chưa song song).

---

## Bảng lỗi chung

Mọi lỗi đều trả JSON `{ "detail": "<message>" }`.

| Status | Ý nghĩa |
|:------:|---------|
| `400` | Request hợp lệ về cú pháp nhưng dữ liệu sai (file rỗng, ảnh hỏng, `ext` sai, không có file…) |
| `422` | Thiếu/không đúng kiểu field bắt buộc (validation của FastAPI) |
| `500` | Lỗi không lường trước phía server |

Ví dụ:

```json
{ "detail": "Unsupported extension: gif. Allowed: ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff']" }
```

---

## Phụ lục — Cấu trúc code

Toàn bộ code trong `src/`, chia theo tầng: `api` (routers) và `service` (nghiệp vụ).

```
src/
├── main.py           # entrypoint: FastAPI app + CORS + mount router + static
├── api/
│   ├── __init__.py   # api_router, prefix="/api", gộp các router con
│   └── image.py      # endpoint image (prefix "/image") -> /api/image/...
├── service/
│   ├── __init__.py
│   └── image.py      # nghiệp vụ: convert_img(), remove_bg()
├── schemas/
│   ├── __init__.py
│   └── image.py      # kiểu dữ liệu: ImageFormatEnum, FileResultDto, ErrorResponseModel
└── web/              # trang demo (templates + static)
```

> ⚠️ Không đặt tên thư mục là `types` — sẽ che module chuẩn `types` của Python (vì `src` nằm đầu `sys.path`) và làm hỏng app. Dùng `schemas`.

### Chạy local

Cách gọn (khuyên dùng):

```bash
python run.py
```

Tương đương lệnh đầy đủ:

```bash
uvicorn main:app --app-dir src --reload
```
