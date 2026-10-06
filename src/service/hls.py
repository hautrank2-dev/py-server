"""Tạo và phục vụ HLS từ các video nguồn."""
import math
import re
import shutil
import subprocess
import threading
import time
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
SEGMENT_PATTERN = re.compile(r"^seg_(\d{3,})\.ts$")
LIVE_WINDOW_SEGMENTS = 6

MEDIA_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".ts": "video/mp2t",
}

# Mỗi video một lock để 2 request đồng thời không cùng chạy ffmpeg cho một video
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_stream_started_at = time.monotonic()


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


def _ensure_hls(name: str) -> Path:
    if not NAME_PATTERN.match(name):
        raise ValueError("Invalid video name")

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

    return out_dir


def _source_segments(name: str) -> tuple[Path, list[float]]:
    out_dir = _ensure_hls(name)
    durations = []
    for line in (out_dir / PLAYLIST_NAME).read_text(encoding="utf-8").splitlines():
        if line.startswith("#EXTINF:"):
            durations.append(float(line.split(":", 1)[1].split(",", 1)[0]))
    if not durations:
        raise RuntimeError("Generated HLS playlist contains no segments")
    return out_dir, durations


def get_live_playlist(name: str) -> str:
    """Build a sliding live playlist that loops the cached source segments forever."""
    _, durations = _source_segments(name)
    cycle_duration = sum(durations)
    initial_offset = sum(durations[:LIVE_WINDOW_SEGMENTS - 1])
    elapsed = max(0.0, time.monotonic() - _stream_started_at) + initial_offset
    cycle = int(elapsed // cycle_duration)
    position = elapsed % cycle_duration
    segment_in_cycle = 0
    for duration in durations:
        if position < duration:
            break
        position -= duration
        segment_in_cycle += 1
    current_sequence = cycle * len(durations) + segment_in_cycle
    first_sequence = max(0, current_sequence - LIVE_WINDOW_SEGMENTS + 1)
    target_duration = math.ceil(max(durations))

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{target_duration}",
        f"#EXT-X-MEDIA-SEQUENCE:{first_sequence}",
    ]
    for sequence in range(first_sequence, current_sequence + 1):
        if sequence > 0 and sequence % len(durations) == 0:
            lines.append("#EXT-X-DISCONTINUITY")
        source_index = sequence % len(durations)
        lines.extend((f"#EXTINF:{durations[source_index]:.6f},", f"seg_{sequence:06d}.ts"))
    return "\n".join(lines) + "\n"


def get_hls_file(name: str, filename: str) -> Path:
    """Resolve a virtual live segment to the corresponding cached source segment."""
    if not FILE_PATTERN.match(filename):
        raise ValueError("Invalid HLS file name")
    out_dir, durations = _source_segments(name)
    if filename == PLAYLIST_NAME:
        return out_dir / PLAYLIST_NAME
    match = SEGMENT_PATTERN.match(filename)
    if not match:
        raise ValueError("Invalid HLS file name")
    source_index = int(match.group(1)) % len(durations)
    path = out_dir / f"seg_{source_index:03d}.ts"
    if not path.is_file():
        raise FileNotFoundError(f"HLS file '{filename}' not found")
    return path
