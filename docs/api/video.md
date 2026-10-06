# Video API

API video: phát một video có sẵn dưới dạng **luồng HLS** (playlist `.m3u8` + segment `.ts`).

| Mục | Giá trị |
|-----|---------|
| Base path | `/api/hls` |
| Tag (Swagger) | `video` |
| Auth | Không yêu cầu |
| CORS | Cho phép tất cả origin |

## Thư mục `public/`

File đặt trong `public/` ở gốc project được phục vụ ngay từ `/` (giống `public/` của FE):

```
public/video/car-parking_23s.mp4   ->   GET /video/car-parking_23s.mp4
```

- Hỗ trợ `Range` request nên dùng trực tiếp cho `<video src>` được.
- Các route khác (`/api/...`, `/static/...`, trang demo, `/health`) được ưu tiên hơn; `public/` chỉ là fallback.

---

# GET `/api/hls/{name}/{filename}`

Luồng HLS của video nguồn `public/video/<name>.mp4`.

Player chỉ cần URL của playlist; các segment được player tự tải qua cùng endpoint này:

```
/api/hls/car-parking_23s/index.m3u8
```

## Path params

| Param      | Ràng buộc | Mô tả |
|------------|-----------|-------|
| `name`     | Chỉ gồm chữ, số, `_`, `-` | Tên video nguồn, **không kèm đuôi** `.mp4` |
| `filename` | `index.m3u8` hoặc `seg_NNN.ts` | Playlist hoặc một segment |

## Hành vi

- **Lần gọi đầu** cho một video: server chạy ffmpeg để tạo các segment nguồn rồi cache ở `storage/hls/<name>/`; request này chậm hơn (tuỳ độ dài video).
- Nếu file nguồn được thay bằng bản mới hơn, luồng tự được tạo lại.
- Video được encode lại **H.264 + AAC**, một mức chất lượng (giữ nguyên độ phân giải gốc), mỗi segment khoảng **4 giây**.
- Playlist trả về là playlist **live** có cửa sổ trượt 6 segment và không có `#EXT-X-ENDLIST`. Server lặp lại các segment của video nguồn vô hạn, vì vậy HLS player tiếp tục tải playlist như một camera live.
- Đây là live stream mô phỏng từ một file video; không phải nguồn camera thời gian thực.

## Response `200 OK`

| `filename` | `Content-Type` | Body |
|------------|----------------|------|
| `index.m3u8` | `application/vnd.apple.mpegurl` | Playlist live được tạo theo thời gian |
| `seg_NNN.ts` | `video/mp2t` | Segment MPEG-TS; số segment trong URL tiếp tục tăng và được ánh xạ vòng về video nguồn |

Khác với Image API, response **không** có `Content-Disposition: attachment` vì file dùng để phát trực tiếp.

## Lỗi

| Status | `detail` | Khi nào |
|:------:|----------|---------|
| `400` | `Invalid video name` | `name` chứa ký tự không cho phép |
| `400` | `Invalid HLS file name` | `filename` không phải `index.m3u8` / `seg_NNN.ts` |
| `404` | `Video '<name>' not found` | Không có `public/video/<name>.mp4` |
| `404` | `HLS file '<filename>' not found` | Segment không tồn tại trong luồng |
| `500` | `Create HLS failed: <chi tiết>` | ffmpeg lỗi khi tạo luồng |

## Ví dụ

**cURL:**

```bash
curl http://localhost:8000/api/hls/car-parking_23s/index.m3u8
```

**Trình duyệt (hls.js)** — Chrome/Firefox desktop không phát HLS trực tiếp, Safari thì có:

```js
const src = "/api/hls/car-parking_23s/index.m3u8";
const video = document.querySelector("video");

if (video.canPlayType("application/vnd.apple.mpegurl")) {
  video.src = src;                       // Safari
} else {
  const hls = new Hls();                 // cần nạp thư viện hls.js
  hls.loadSource(src);
  hls.attachMedia(video);
}
```

## Ghi chú vận hành

- **ffmpeg** đi kèm gói pip `imageio-ffmpeg` (binary nằm trong venv / image Docker), không cần cài lên máy.
- **Cache** `storage/` không được commit và không có cơ chế dọn tự động.
- Trong Docker, `storage/` nằm trong container nên mất khi tạo lại container; luồng sẽ được tạo lại ở lần gọi đầu.

## Cấu trúc code

```
src/
├── api/hls.py         # endpoint (prefix "/hls") -> /api/hls/...
└── service/hls.py     # tạo segment nguồn và playlist live lặp vô hạn
```
