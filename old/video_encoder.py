"""
Video Encoder — FFmpeg-based screen recording for Wesnoth battles.
Extracted from wesnoth_bridge.py for clean separation.
"""

import os
import sys
import time
import shutil
import subprocess
import json
import signal
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple, Callable


@dataclass
class VideoConfig:
    """Configuration for a recording session."""
    wesnoth_path: str = "wesnoth"
    scenario_id: str = "classic_battlefield"
    addon_path: str = ""
    resolution: Tuple[int, int] = (1280, 720)
    fps: int = 30
    output_path: str = "output.mp4"
    video_codec: str = "libx264"
    video_crf: int = 23
    video_preset: str = "medium"
    audio_file: str = ""


class VideoEncoder:
    """FFmpeg X11 grab recorder for Wesnoth display."""

    def __init__(self, config: VideoConfig = None):
        self.config = config or VideoConfig()
        self._ffmpeg_process: Optional[subprocess.Popen] = None
        self._log_lines: List[str] = []
        self._on_log: Optional[Callable[[str], None]] = None
        self._recording_start_time: float = 0

    def set_log_callback(self, callback: Callable[[str], None]):
        self._on_log = callback

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append(line)
        if self._on_log:
            self._on_log(line)

    def start_recording(self, display: str = ":99") -> bool:
        """Start ffmpeg X11 grab to record the display."""
        w, h = self.config.resolution

        out_path = Path(self.config.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-video_size", f"{w}x{h}",
            "-framerate", str(self.config.fps),
            "-f", "x11grab",
            "-draw_mouse", "0",
            "-i", display,
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-crf", str(self.config.video_crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]

        if self.config.audio_file and os.path.isfile(self.config.audio_file):
            cmd.extend(["-i", self.config.audio_file, "-c:a", "aac", "-b:a", "128k", "-shortest"])
        else:
            cmd.append("-an")

        cmd.extend([
            "-metadata", f"title={self.config.scenario_id}",
            "-metadata", "encoder=WesnothAI Video Encoder",
            str(self.config.output_path),
        ])

        self._log(f"Starting ffmpeg recording...")
        self._log(f"  Display: {display}, Output: {self.config.output_path}")

        try:
            env = os.environ.copy()
            env["DISPLAY"] = display
            self._ffmpeg_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
            )
            self._recording_start_time = time.time()
            self._log("ffmpeg recording started")
            return True
        except FileNotFoundError:
            self._log("ERROR: ffmpeg not found! Install: sudo apt install ffmpeg")
            return False
        except Exception as e:
            self._log(f"ERROR starting ffmpeg: {e}")
            return False

    def stop_recording(self):
        """Stop ffmpeg recording gracefully."""
        if self._ffmpeg_process:
            self._log("Stopping ffmpeg recording...")
            try:
                self._ffmpeg_process.stdin.write(b'q')
                self._ffmpeg_process.stdin.flush()
            except Exception:
                pass
            try:
                self._ffmpeg_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._terminate(self._ffmpeg_process, "ffmpeg")
            self._ffmpeg_process = None

            if os.path.isfile(self.config.output_path):
                size_mb = os.path.getsize(self.config.output_path) / (1024 * 1024)
                duration = time.time() - self._recording_start_time
                self._log(f"Recording saved: {self.config.output_path}")
                self._log(f"  Size: {size_mb:.1f} MB, Duration: {duration:.1f}s")

    def cancel(self):
        if self._ffmpeg_process:
            self._terminate(self._ffmpeg_process, "ffmpeg")
            self._ffmpeg_process = None

    def get_info(self) -> dict:
        """Get info about the recording."""
        info = {
            "output": self.config.output_path,
            "resolution": f"{self.config.resolution[0]}x{self.config.resolution[1]}",
            "fps": self.config.fps,
        }
        if os.path.isfile(self.config.output_path):
            info["file_size_mb"] = round(os.path.getsize(self.config.output_path) / (1024 * 1024), 2)
            ffprobe = shutil.which("ffprobe")
            if ffprobe:
                try:
                    result = subprocess.run(
                        [ffprobe, "-v", "quiet", "-print_format", "json",
                         "-show_format", self.config.output_path],
                        capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        info["duration_seconds"] = round(float(data.get("format", {}).get("duration", 0)), 1)
                except Exception:
                    pass
        return info

    @staticmethod
    def _terminate(proc, name):
        if not proc:
            return
        try:
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
