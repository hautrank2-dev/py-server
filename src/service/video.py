"""Nghiệp vụ domain video: tạo luồng HLS (playlist .m3u8 + segment .ts) bằng ffmpeg."""
import re
import shutil
import subprocess
import threading
from pathlib import Path

import imageio_ffmpeg

# Thư mục gốc project (cha của src/)
ROOT_DIR = Path(__file__).resolve().parents[2]

# Video nguồn: public/video/<name>.mp4 (cũng truy cập trực tiếp được qua /video/<name>.mp4)
VIDEO_DIR = ROOT_DIR / "public" / "video"
# Nơi cache kết quả HLS: storage/hls/<name>/ — sinh ra lúc chạy, không commit
HLS_DIR = ROOT_DIR / "storage" / "hls"

PLAYLIST_NAME = "index.m3u8"
SEGMENT_SECONDS = 4

# Chỉ cho phép tên an toàn để không thoát khỏi VIDEO_DIR / HLS_DIR
NAME_PATTERN = re.compile(r"^[\w-]+$")
FILE_PATTERN = re.compile(r"^(index\.m3u8|seg_\d{3,}\.ts)$")

MEDIA_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".ts": "video/mp2t",
}

# Mỗi video một lock để 2 request đồng thời không cùng chạy ffmpeg cho một video
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_lock(name: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(name, threading.Lock())


def _build_hls(source: Path, out_dir: Path) -> None:
    """Chạy ffmpeg cắt `source` thành HLS (VOD) trong `out_dir`."""
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        # Encode lại H.264/AAC và ép keyframe đúng mốc để mọi segment dài đều nhau
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-force_key_frames", f"expr:gte(t,n_forced*{SEGMENT_SECONDS})",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "hls",
        "-hls_time", str(SEGMENT_SECONDS),
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(out_dir / "seg_%03d.ts"),
        str(out_dir / PLAYLIST_NAME),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[-500:] or "ffmpeg failed")


def get_hls_file(name: str, filename: str) -> Path:
    """
    Trả về đường dẫn một file của luồng HLS; tự tạo luồng ở lần gọi đầu.

    Args:
        name (str): tên video nguồn, không kèm đuôi (public/video/<name>.mp4)
        filename (str): "index.m3u8" hoặc tên segment "seg_NNN.ts"

    Returns:
        Path: file trong storage/hls/<name>/

    Raises:
        ValueError: `name` hoặc `filename` không hợp lệ
        FileNotFoundError: không có video nguồn hoặc không có segment đó
    """
    if not NAME_PATTERN.match(name):
        raise ValueError("Invalid video name")
    if not FILE_PATTERN.match(filename):
        raise ValueError("Invalid HLS file name")

    source = VIDEO_DIR / f"{name}.mp4"
    if not source.is_file():
        raise FileNotFoundError(f"Video '{name}' not found")

    out_dir = HLS_DIR / name
    playlist = out_dir / PLAYLIST_NAME

    with _get_lock(name):
        # Tạo mới nếu chưa có, hoặc video nguồn đã được thay bằng bản mới hơn
        if not playlist.is_file() or playlist.stat().st_mtime < source.stat().st_mtime:
            # Ghi vào thư mục tạm rồi mới đổi tên -> không bao giờ phục vụ luồng dở dang
            tmp_dir = HLS_DIR / f".{name}.tmp"
            shutil.rmtree(tmp_dir, ignore_errors=True)
            tmp_dir.mkdir(parents=True)
            try:
                _build_hls(source, tmp_dir)
                shutil.rmtree(out_dir, ignore_errors=True)
                tmp_dir.rename(out_dir)
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    path = out_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"HLS file '{filename}' not found")
    return path
