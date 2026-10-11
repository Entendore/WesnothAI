"""
Wesnoth Bridge — Interfaces with the ACTUAL Battle for Wesnoth game binary.
Uses Xvfb for headless rendering + ffmpeg x11grab for video recording.

Workflow:
  1. Start Xvfb virtual display
  2. Launch Wesnoth on Xvfb with the AI addon (both sides AI)
  3. ffmpeg captures the Xvfb display in real-time → MP4
  4. When Wesnoth exits, stop ffmpeg → final MP4 ready

Based on: https://github.com/wesnoth/wesnoth
"""

import os
import sys
import importlib.util
import time
import signal
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass, field

from wesnoth_scanner import WesnothScanner, ScanResult


@dataclass
class WesnothPaths:
    """Resolved paths for Wesnoth installation."""
    wesnoth_binary: str
    data_dir: str = ""
    user_dir: str = ""
    addon_dir: str = ""


@dataclass
class RecordingConfig:
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
    use_xvfb: bool = True
    xvfb_display: str = ":99"
    max_turns: int = 30
    game_speed: float = 1.0  # 1.0 = normal, 2.0 = double speed
    audio_file: str = ""  # Optional background music


class WesnothBridge:
    """
    Bridge to the actual Battle for Wesnoth game.
    Handles: Xvfb display, Wesnoth launch, ffmpeg recording, and process management.
    """

    def __init__(self, config: RecordingConfig = None):
        self.config = config or RecordingConfig()
        self._xvfb_process: Optional[subprocess.Popen] = None
        self._wesnoth_process: Optional[subprocess.Popen] = None
        self._ffmpeg_process: Optional[subprocess.Popen] = None
        self._log_lines: List[str] = []
        self._on_log: Optional[Callable[[str], None]] = None
        self._cancelled = False
        self._recording_start_time: float = 0

    def set_log_callback(self, callback: Callable[[str], None]):
        self._on_log = callback

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append(line)
        if self._on_log:
            self._on_log(line)

    # =========================================================================
    # WESNOTH DISCOVERY
    # =========================================================================

    @staticmethod
    def find_wesnoth() -> Optional[WesnothPaths]:
        """Auto-detect Wesnoth installation on the system.

        Uses the comprehensive cross-platform WesnothScanner to locate
        the binary, user data dir, game data dir, and addon dirs on
        Windows, macOS, and Linux.
        """
        scanner = WesnothScanner()
        result = scanner.find_best_installation()
        if not result:
            return None

        # Pick the first existing addon dir for backward compatibility
        addon_dir = ""
        for ad in result.addon_dirs:
            if os.path.isdir(ad):
                addon_dir = ad
                break
        if not addon_dir and result.user_dir:
            addon_dir = os.path.join(result.user_dir, "data", "add-ons")

        return WesnothPaths(
            wesnoth_binary=result.wesnoth_binary,
            data_dir=result.data_dir,
            user_dir=result.user_dir,
            addon_dir=addon_dir,
        )

    @staticmethod
    def find_all_installations() -> List[WesnothPaths]:
        """Find ALL Wesnoth installations on the system.

        Returns a list of WesnothPaths for each discovered installation.
        """
        scanner = WesnothScanner()
        results = scanner.find_all_installations()
        paths_list = []
        for r in results:
            addon_dir = ""
            for ad in r.addon_dirs:
                if os.path.isdir(ad):
                    addon_dir = ad
                    break
            if not addon_dir and r.user_dir:
                addon_dir = os.path.join(r.user_dir, "data", "add-ons")
            paths_list.append(WesnothPaths(
                wesnoth_binary=r.wesnoth_binary,
                data_dir=r.data_dir,
                user_dir=r.user_dir,
                addon_dir=addon_dir,
            ))
        return paths_list

    @staticmethod
    def get_scan_summary() -> str:
        """Get a human-readable summary of all found Wesnoth paths."""
        scanner = WesnothScanner()
        return scanner.get_scan_summary()

    @staticmethod
    def find_addon_dirs() -> List[str]:
        """Find all addon directories that exist on disk."""
        scanner = WesnothScanner()
        return scanner.find_existing_addon_dirs()

    @staticmethod
    def _find_user_dir() -> str:
        """Find the Wesnoth user data directory (backward compat)."""
        scanner = WesnothScanner()
        return scanner.find_wesnoth_user_dir()

    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """Check which tools are available."""
        return {
            "wesnoth": shutil.which("wesnoth") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "xvfb": shutil.which("Xvfb") is not None,
            "python3": shutil.which("python3") is not None,
            "pip/Pillow": importlib.util.find_spec("PIL") is not None,
        }

    # =========================================================================
    # XVFB MANAGEMENT
    # =========================================================================

    def start_xvfb(self) -> bool:
        """Start Xvfb virtual display for headless rendering."""
        if not self.config.use_xvfb:
            self._log("Xvfb disabled — will use direct display")
            return True

        xvfb_path = shutil.which("Xvfb")
        if not xvfb_path:
            self._log("WARNING: Xvfb not found. Install: sudo apt install xvfb")
            self._log("Recording will try to use the current display instead.")
            self.config.use_xvfb = False
            return True

        self.stop_xvfb()

        w, h = self.config.resolution
        display = self.config.xvfb_display

        try:
            self._xvfb_process = subprocess.Popen(
                [xvfb_path, display, "-screen", "0", f"{w}x{h}x24",
                 "-ac", "+extension", "GLX", "+render", "-noreset"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)

            if self._xvfb_process.poll() is not None:
                self._log("ERROR: Xvfb failed to start")
                self.config.use_xvfb = False
                return False

            self._log(f"Xvfb started on display {display} ({w}x{h}x24)")
            return True
        except Exception as e:
            self._log(f"ERROR starting Xvfb: {e}")
            self.config.use_xvfb = False
            return True

    def stop_xvfb(self):
        """Stop Xvfb."""
        if self._xvfb_process:
            try:
                self._xvfb_process.terminate()
                self._xvfb_process.wait(timeout=5)
            except Exception:
                try:
                    self._xvfb_process.kill()
                except Exception:
                    pass
            self._xvfb_process = None

    # =========================================================================
    # WESNOTH EXECUTION
    # =========================================================================

    def _build_wesnoth_cmd(self) -> List[str]:
        """Build the Wesnoth command line for AI vs AI recording."""
        w, h = self.config.resolution
        is_flatpak = self.config.wesnoth_path.startswith("flatpak")
        cmd = self.config.wesnoth_path.split() if is_flatpak else [self.config.wesnoth_path]

        # Core options
        cmd.extend([
            "--resolution", f"{w}x{h}",
            "--fps", str(self.config.fps),
            "--nosound",
            "--nomusic",
        ])

        # Load addon path if specified
        if self.config.addon_path:
            cmd.extend(["--path", self.config.addon_path])

        # Run as multiplayer with both sides AI
        cmd.extend([
            "--multiplayer",
            "--scenario", self.config.scenario_id,
            "--controller", "1:ai",
            "--controller", "2:ai",
        ])

        # Exit when done (no GUI interaction needed)
        cmd.append("--exit-at-end")

        # No delay between animations for faster recording
        # (Lua delays handle cinematic pacing instead)
        if self.config.game_speed > 1.5:
            cmd.append("--nodelay")

        # Log level
        cmd.extend(["--log-warning", "all"])

        return cmd

    def _terminate_process(self, proc: Optional[subprocess.Popen], name: str):
        """Gracefully terminate a process."""
        if not proc:
            return
        try:
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # =========================================================================
    # FFMPEG RECORDING
    # =========================================================================

    def start_ffmpeg_recording(self) -> bool:
        """Start ffmpeg X11 grab to record the Wesnoth display."""
        w, h = self.config.resolution

        # Ensure output directory exists
        out_path = Path(self.config.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        display = self.config.xvfb_display if self.config.use_xvfb else os.environ.get("DISPLAY", ":0")

        cmd = [
            "ffmpeg", "-y",
            "-video_size", f"{w}x{h}",
            "-framerate", str(self.config.fps),
            "-f", "x11grab",
            "-draw_mouse", "0",  # No mouse cursor
            "-i", display,
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-crf", str(self.config.video_crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]

        # Audio
        if self.config.audio_file and os.path.isfile(self.config.audio_file):
            cmd.extend(["-i", self.config.audio_file, "-c:a", "aac", "-b:a", "128k",
                        "-shortest"])
        else:
            cmd.append("-an")

        # Metadata
        cmd.extend([
            "-metadata", f"title={self.config.scenario_id}",
            "-metadata", "encoder=AI Movie Renderer for Battle for Wesnoth",
            str(self.config.output_path),
        ])

        self._log(f"Starting ffmpeg recording...")
        self._log(f"  Display: {display}")
        self._log(f"  Output: {self.config.output_path}")
        self._log(f"  Codec: {self.config.video_codec} preset={self.config.video_preset} crf={self.config.video_crf}")

        try:
            env = os.environ.copy()
            if self.config.use_xvfb:
                env["DISPLAY"] = self.config.xvfb_display

            self._ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
            )
            self._recording_start_time = time.time()
            self._log("ffmpeg recording started successfully")
            return True
        except FileNotFoundError:
            self._log("ERROR: ffmpeg not found! Install: sudo apt install ffmpeg")
            return False
        except Exception as e:
            self._log(f"ERROR starting ffmpeg: {e}")
            return False

    def stop_ffmpeg_recording(self):
        """Stop ffmpeg recording gracefully."""
        if self._ffmpeg_process:
            self._log("Stopping ffmpeg recording...")
            # Send 'q' to ffmpeg's stdin for clean termination
            try:
                self._ffmpeg_process.stdin.write(b'q')
                self._ffmpeg_process.stdin.flush()
            except Exception:
                pass

            try:
                self._ffmpeg_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._terminate_process(self._ffmpeg_process, "ffmpeg")

            self._ffmpeg_process = None

            # Check output
            if os.path.isfile(self.config.output_path):
                size_mb = os.path.getsize(self.config.output_path) / (1024 * 1024)
                duration = time.time() - self._recording_start_time
                self._log(f"Recording saved: {self.config.output_path}")
                self._log(f"  Size: {size_mb:.1f} MB, Duration: {duration:.1f}s")

    # =========================================================================
    # MAIN RECORDING WORKFLOW
    # =========================================================================

    def run_recording(self, log_callback: Optional[Callable] = None) -> bool:
        """
        Execute the full recording workflow:
        1. Start Xvfb
        2. Start ffmpeg recording
        3. Launch Wesnoth (AI vs AI)
        4. Wait for completion
        5. Stop recording
        """
        if log_callback:
            self._on_log = log_callback
        self._cancelled = False

        self._log("=" * 50)
        self._log("AI Movie Renderer — Starting Recording")
        self._log("=" * 50)

        # Step 1: Start Xvfb
        if not self.start_xvfb():
            self._log("FATAL: Cannot start virtual display. Aborting.")
            return False

        # Step 2: Start ffmpeg recording
        if not self.start_ffmpeg_recording():
            self.stop_xvfb()
            self._log("FATAL: Cannot start recording. Aborting.")
            return False

        # Small delay so ffmpeg can initialize
        time.sleep(1.0)

        # Step 3: Launch Wesnoth
        cmd = self._build_wesnoth_cmd()
        self._log(f"Launching Wesnoth...")
        self._log(f"  Scenario: {self.config.scenario_id}")
        self._log(f"  Command: {' '.join(cmd[:8])}...")

        env = os.environ.copy()
        if self.config.use_xvfb:
            env["DISPLAY"] = self.config.xvfb_display
            env["SDL_VIDEODRIVER"] = "x11"

        success = False
        try:
            self._wesnoth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
            )

            # Monitor Wesnoth process
            while self._wesnoth_process.poll() is None:
                if self._cancelled:
                    self._log("Recording cancelled by user")
                    break

                # Log stderr periodically (contains game messages)
                try:
                    if self._wesnoth_process.stderr:
                        import select
                        if select.select([self._wesnoth_process.stderr], [], [], 0.1)[0]:
                            line = self._wesnoth_process.stderr.readline()
                            if line:
                                decoded = line.decode("utf-8", errors="replace").strip()
                                if decoded and "ai_movie" in decoded.lower():
                                    self._log(f"  [game] {decoded[:200]}")
                except Exception:
                    pass

                time.sleep(0.5)

            returncode = self._wesnoth_process.poll()
            self._wesnoth_process = None

            if returncode == 0:
                self._log("Wesnoth battle completed successfully!")
                success = True
            else:
                self._log(f"Wesnoth exited with code {returncode}")
                # Still might have useful recording
                if os.path.isfile(self.config.output_path):
                    self._log("Video file exists — recording may be partial but usable.")
                    success = True

        except FileNotFoundError:
            self._log("ERROR: Wesnoth binary not found!")
            self._log("Install Battle for Wesnoth: https://github.com/wesnoth/wesnoth")
            self._log("Or: sudo apt install wesnoth / flatpak install org.wesnoth.Wesnoth")
        except Exception as e:
            self._log(f"ERROR running Wesnoth: {e}")
        finally:
            # Step 4 & 5: Cleanup
            self.stop_ffmpeg_recording()
            self.stop_xvfb()

        self._log("=" * 50)
        if success:
            self._log("Recording complete!")
        else:
            self._log("Recording failed.")
        self._log("=" * 50)

        return success

    def cancel(self):
        """Cancel the current recording."""
        self._cancelled = True
        if self._wesnoth_process:
            self._terminate_process(self._wesnoth_process, "wesnoth")
        if self._ffmpeg_process:
            self._stop_ffmpeg_recording()
        self.stop_xvfb()

    def get_recording_info(self) -> Dict:
        """Get info about the current/last recording."""
        info = {
            "scenario": self.config.scenario_id,
            "resolution": f"{self.config.resolution[0]}x{self.config.resolution[1]}",
            "fps": self.config.fps,
            "output": self.config.output_path,
        }
        if os.path.isfile(self.config.output_path):
            info["file_size_mb"] = round(
                os.path.getsize(self.config.output_path) / (1024 * 1024), 2
            )
            # Get duration from ffprobe
            ffprobe = shutil.which("ffprobe")
            if ffprobe:
                try:
                    result = subprocess.run(
                        [ffprobe, "-v", "quiet", "-print_format", "json",
                         "-show_format", str(self.config.output_path)],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        import json
                        data = json.loads(result.stdout)
                        duration = float(data.get("format", {}).get("duration", 0))
                        info["duration_seconds"] = round(duration, 1)
                except Exception:
                    pass
        return info