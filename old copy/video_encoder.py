"""
Video Encoder — FFmpeg pipeline to compile captured frames into MP4.
Supports H.264, H.265, quality presets, and audio tracks.
"""

import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List, Callable


class VideoEncoder:
    """Encodes captured frames into MP4 video using FFmpeg."""

    def __init__(self, config: Dict):
        self.config = config
        self.ffmpeg_path = config.get("ffmpeg_path", "ffmpeg")
        self.frame_dir = config.get("frame_dir", "/tmp/wesnoth_frames")
        self.output_path = config.get("output_path", "output.mp4")
        self.fps = config.get("output_fps", 24)
        self.resolution = config.get("resolution", (1280, 720))
        self.codec = config.get("codec", "libx264")
        self.quality = config.get("quality", "medium")  # ultrafast, fast, medium, slow
        self.crf = config.get("crf", 23)  # 0 (lossless) to 51 (worst)
        self.pix_fmt = config.get("pix_fmt", "yuv420p")
        self.audio_file = config.get("audio_file", "")  # Optional audio track
        self.title = config.get("title", "Battle for Wesnoth - AI Battle")
        self._on_log: Optional[Callable] = None
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False

    def set_log_callback(self, callback: Callable[[str], None]):
        self._on_log = callback

    def _log(self, msg: str):
        if self._on_log:
            self._on_log(msg)

    def get_presets(self) -> Dict[str, dict]:
        """Return available encoding presets."""
        return {
            "Fast (low quality)": {
                "codec": "libx264", "quality": "ultrafast", "crf": 28,
                "description": "Quick encoding, larger file size"
            },
            "Balanced": {
                "codec": "libx264", "quality": "medium", "crf": 23,
                "description": "Good balance of speed and quality"
            },
            "High Quality": {
                "codec": "libx264", "quality": "slow", "crf": 18,
                "description": "Slower encoding, better quality"
            },
            "Ultra Quality (H.265)": {
                "codec": "libx265", "quality": "medium", "crf": 22,
                "description": "Best compression, very slow"
            },
            "Lossless": {
                "codec": "libx264", "quality": "medium", "crf": 0,
                "description": "No quality loss, huge file"
            },
        }

    def encode(self, log_callback: Optional[Callable] = None) -> bool:
        """
        Encode captured frames into MP4.
        Uses FFmpeg pipe for efficient processing.
        """
        if log_callback:
            self._on_log = log_callback

        self._cancelled = False

        # Find frames
        frame_dir = Path(self.frame_dir)
        frames = sorted(frame_dir.glob("frame_*.png"))

        if not frames:
            # Also check for the Lua-captured frames pattern
            frames = sorted(frame_dir.glob("*_frame_*.png"))

        if not frames:
            self._log("ERROR: No frames found to encode!")
            return False

        self._log(f"Found {len(frames)} frames to encode")
        self._log(f"Output: {self.output_path}")
        self._log(f"Codec: {self.codec}, Preset: {self.quality}, CRF: {self.crf}")

        # Ensure output directory exists
        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        cmd = self._build_ffmpeg_cmd(len(frames))

        self._log(f"Running FFmpeg...")
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Monitor progress
            while self._process.poll() is None:
                if self._cancelled:
                    self._log("Encoding cancelled")
                    self._process.terminate()
                    return False

                # Read stderr for progress
                try:
                    if self._process.stderr:
                        line = self._process.stderr.readline()
                        if line:
                            decoded = line.decode("utf-8", errors="replace").strip()
                            if "frame=" in decoded or "time=" in decoded:
                                self._log(f"  [ffmpeg] {decoded[-80:]}")
                except Exception:
                    pass

            returncode = self._process.poll()
            self._process = None

            if returncode == 0:
                file_size = out_path.stat().st_size
                size_mb = file_size / (1024 * 1024)
                duration = len(frames) / self.fps
                self._log(f"Encoding complete!")
                self._log(f"  File: {self.output_path}")
                self._log(f"  Size: {size_mb:.1f} MB")
                self._log(f"  Duration: {duration:.1f}s ({len(frames)} frames @ {self.fps}fps)")
                return True
            else:
                self._log(f"FFmpeg exited with code {returncode}")
                return False

        except FileNotFoundError:
            self._log("ERROR: FFmpeg not found! Install with: sudo apt install ffmpeg")
            return False
        except Exception as e:
            self._log(f"Encoding error: {e}")
            return False

    def _build_ffmpeg_cmd(self, frame_count: int) -> List[str]:
        """Build the FFmpeg command line."""
        cmd = [self.ffmpeg_path, "-y"]

        # Input: image sequence
        cmd.extend([
            "-framerate", str(self.fps),
            "-i", os.path.join(self.frame_dir, "frame_%06d.png"),
        ])

        # If the Lua frames use different naming, try pattern
        # We'll create a symlink sequence as fallback

        # Video codec settings
        cmd.extend([
            "-c:v", self.codec,
            "-preset", self.quality,
            "-crf", str(self.crf),
            "-pix_fmt", self.pix_fmt,
        ])

        # Resolution
        w, h = self.resolution
        cmd.extend(["-s", f"{w}x{h}"])

        # Audio (optional)
        if self.audio_file and os.path.isfile(self.audio_file):
            cmd.extend(["-i", self.audio_file, "-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.append("-an")

        # Metadata
        cmd.extend([
            "-metadata", f"title={self.title}",
            "-metadata", "encoder=AI Movie Renderer for Battle for Wesnoth",
        ])

        # Output format
        cmd.extend([
            "-movflags", "+faststart",
            self.output_path,
        ])

        return cmd

    def encode_with_fallback(self, log_callback: Optional[Callable] = None) -> bool:
        """
        Encode with fallback: try standard pattern, then glob-based concat.
        This handles cases where frame numbering isn't sequential.
        """
        # First try standard encode
        result = self.encode(log_callback)
        if result:
            return True

        # Fallback: create a concat file and encode from it
        self._log("Standard encoding failed, trying fallback method...")

        frame_dir = Path(self.frame_dir)
        frames = sorted(frame_dir.glob("*.png"))
        if not frames:
            return False

        # Create a concat demuxer file
        concat_path = os.path.join(self.frame_dir, "concat.txt")
        with open(concat_path, "w") as f:
            for frame in frames:
                f.write(f"file '{frame}'\n")
                f.write(f"duration {1.0 / self.fps}\n")

        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_path,
            "-c:v", self.codec,
            "-preset", self.quality,
            "-crf", str(self.crf),
            "-pix_fmt", self.pix_fmt,
            "-vf", f"scale={self.resolution[0]}:{self.resolution[1]}",
            "-an",
            "-movflags", "+faststart",
            self.output_path,
        ]

        try:
            self._log(f"Fallback: encoding {len(frames)} frames...")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            if result.returncode == 0:
                self._log("Fallback encoding succeeded!")
                return True
            else:
                self._log(f"Fallback failed: {result.stderr[-300:]}")
                return False
        except Exception as e:
            self._log(f"Fallback error: {e}")
            return False

    def prepare_frames(self) -> int:
        """
        Prepare frames for encoding.
        Renames/symlinks frames to sequential numbering if needed.
        Returns the count of prepared frames.
        """
        frame_dir = Path(self.frame_dir)
        if not frame_dir.exists():
            return 0

        frames = sorted(frame_dir.glob("*.png"))
        if not frames:
            return 0

        # Check if frames are already sequentially numbered
        expected_pattern = "frame_000001.png"
        if (frame_dir / expected_pattern).exists():
            return len(list(frame_dir.glob("frame_*.png")))

        # Create a temp dir for sequential frames
        seq_dir = frame_dir / "sequential"
        seq_dir.mkdir(exist_ok=True)

        for i, frame in enumerate(frames, 1):
            target = seq_dir / f"frame_{i:06d}.png"
            if not target.exists():
                try:
                    os.symlink(str(frame.resolve()), str(target))
                except OSError:
                    # Symlink may fail, try copy
                    import shutil
                    shutil.copy2(str(frame), str(target))

        self._log(f"Prepared {len(frames)} sequential frames")
        return len(frames)

    def cancel(self):
        """Cancel encoding."""
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    def get_video_info(self, video_path: str) -> Optional[Dict]:
        """Get video metadata using ffprobe."""
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return None

        try:
            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", video_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None