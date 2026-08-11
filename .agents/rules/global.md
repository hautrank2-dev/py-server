# Quy tắc code — Global

Tổng hợp các quy ước áp dụng cho toàn bộ project (Python / FastAPI).

## 1. Style & đặt tên (PEP 8)

- `snake_case` cho hàm, biến, module/file: `convert_img`, `remove_bg`, `image.py`.
- `PascalCase` cho class: `ImageFormat`, `FileResult`.
- `UPPER_CASE` cho hằng số, đặt ở đầu file: `EXT_META`, `DEFAULT_MODEL`.
- Có **type hints** cho tham số và giá trị trả về.
- Có **docstring** cho module và hàm public.

## 2. Import

- **Import module, không import hàm lẻ** — để đọc code biết ngay hàm đến từ đâu:
  ```python
  from service import image as image_service
  image_service.remove_bg(...)      # rõ nguồn gốc
  ```
- Nhóm import thành 3 khối, cách nhau dòng trống: **stdlib → third-party → local**.
- **Không dùng** `from x import *`.

## 3. Kiến trúc thư mục

- **Toàn bộ code nằm trong `src/`** (giống frontend). Chạy với `--app-dir src`.
- Chia theo **tầng (layer)**, mỗi tầng một thư mục:

  ```
  src/
  ├── main.py       # entrypoint: app + middleware + mount router
  ├── api/          # router (định nghĩa endpoint)
  ├── service/      # nghiệp vụ (xử lý logic)
  ├── schemas/      # kiểu dữ liệu (Enum, model, NamedTuple)
  └── web/          # trang demo (templates + static)
  ```

- Mỗi file trong `api/` và `service/` đặt tên theo **domain/media**: `image.py`, sau này `video.py`.
- **Single Responsibility**: tách module theo *lý do thay đổi* và *dependency*, không gộp bừa vì "cùng chủ đề". Việc nặng dependency (vd `rembg`) nên tách riêng khỏi việc nhẹ (vd Pillow) khi hợp lý.

## 4. Quy ước API

- **Mọi endpoint đều dưới prefix `/api`** (đặt một lần ở `api/__init__.py`), gộp router con theo domain → `/api/image/...`, `/api/video/...`.
- Tham số cấu hình đơn giản (bool, số) → **query param**; dữ liệu file/form → **body** (`multipart/form-data`).
- **Response file** dùng `StreamingResponse` + header `Content-Disposition: attachment`.
- **Response lỗi** luôn là JSON `{ "detail": "<message>" }` với status phù hợp (`400` dữ liệu sai, `422` validation, `500` lỗi server).
- Validate đầu vào bằng **type/schema** (Enum, `ge/le`…) để FastAPI tự trả `422` và hiện đúng trong Swagger.

## 5. Types / Schemas

- Đặt kiểu dữ liệu dùng chung trong `src/schemas/<domain>.py` (Enum, Pydantic model, NamedTuple).
- ⚠️ **KHÔNG đặt tên thư mục là `types`** — sẽ che module chuẩn `types` của Python (vì `src` nằm đầu `sys.path`) và làm hỏng app. Dùng `schemas`.
- **Mỗi type phải có suffix theo loại:** `Enum` (enum), `Model` (Pydantic model), `Dto` (dữ liệu truyền/trả về), `Type` (kiểu khác). Ví dụ: `ImageFormatEnum`, `ErrorResponseModel`, `FileResultDto`.
- Hàm service trả về kiểu có tên rõ ràng (vd `FileResultDto` thay cho tuple trần `(buf, str, str)`).

## 6. Môi trường & chạy

- **Chạy dev:** `python run.py` (bọc sẵn `uvicorn main:app --app-dir src --reload`).
- **Venv dùng Python 3.13.** Tránh 3.14 (nhiều thư viện chưa có wheel → phải biên dịch, cần compiler). Docker dùng 3.12.
- **`requirements.txt` tối giản** — chỉ dependency trực tiếp project dùng, không `pip freeze` cả môi trường global.
- **Deploy bằng Docker** (`docker compose up -d --build`); container tự cô lập, không cần cài Python/thư viện trên server.
- CORS: cho phép tất cả origin (`allow_origins=["*"]`).

## 7. Tài liệu & Git

- Mỗi domain có tài liệu API trong `docs/api/<domain>.md`; **cập nhật docs mỗi khi đổi API** (path, param, response, lỗi). Header/message trong docs phải khớp thực tế.
- Khi di chuyển/đổi tên file, dùng **`git mv`** để giữ lịch sử.
