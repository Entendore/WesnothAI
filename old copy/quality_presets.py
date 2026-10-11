"""
Video Quality Presets — Pre-configured encoding profiles for common use cases.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class QualityPreset:
    name: str
    resolution: str  # "WxH"
    fps: int
    codec: str
    preset: str  # ffmpeg preset
    crf: int
    audio_bitrate: str
    description: str
    icon: str  # emoji-free label


QUALITY_PRESETS: List[QualityPreset] = [
    QualityPreset(
        name="YouTube 1080p",
        resolution="1920x1080",
        fps=30,
        codec="libx264",
        preset="medium",
        crf=23,
        audio_bitrate="192k",
        description="Recommended for YouTube uploads. Good quality at reasonable file size.",
        icon="[YT]",
    ),
    QualityPreset(
        name="YouTube 720p",
        resolution="1280x720",
        fps=30,
        codec="libx264",
        preset="medium",
        crf=23,
        audio_bitrate="128k",
        description="Smaller file for YouTube. Good for longer battles.",
        icon="[YT]",
    ),
    QualityPreset(
        name="Discord Share",
        resolution="1280x720",
        fps=24,
        codec="libx264",
        preset="fast",
        crf=28,
        audio_bitrate="128k",
        description="Optimized for Discord's 25MB file limit for short clips.",
        icon="[DC]",
    ),
    QualityPreset(
        name="High Quality",
        resolution="1920x1080",
        fps=30,
        codec="libx264",
        preset="slow",
        crf=18,
        audio_bitrate="192k",
        description="Best visual quality. Larger files, slower encoding.",
        icon="[HQ]",
    ),
    QualityPreset(
        name="Archive Master",
        resolution="1920x1080",
        fps=30,
        codec="libx264",
        preset="veryslow",
        crf=15,
        audio_bitrate="256k",
        description="Maximum quality for archiving. Very slow encoding.",
        icon="[AR]",
    ),
    QualityPreset(
        name="Fast Preview",
        resolution="1024x576",
        fps=24,
        codec="libx264",
        preset="ultrafast",
        crf=30,
        audio_bitrate="96k",
        description="Quick preview. Low quality but very fast encoding.",
        icon="[Q]",
    ),
    QualityPreset(
        name="4K Ultra HD",
        resolution="2560x1440",
        fps=30,
        codec="libx264",
        preset="slow",
        crf=20,
        audio_bitrate="192k",
        description="Ultra HD for high-end displays. Requires powerful machine.",
        icon="[4K]",
    ),
    QualityPreset(
        name="H.265 Compact",
        resolution="1280x720",
        fps=24,
        codec="libx265",
        preset="medium",
        crf=28,
        audio_bitrate="128k",
        description="H.265/HEVC codec. Much smaller files, very slow encoding.",
        icon="[H5]",
    ),
    QualityPreset(
        name="Custom",
        resolution="1280x720",
        fps=30,
        codec="libx264",
        preset="medium",
        crf=23,
        audio_bitrate="128k",
        description="Use your own settings below.",
        icon="[--]",
    ),
]

PRESET_NAMES = [p.name for p in QUALITY_PRESETS]


def get_preset_by_name(name: str) -> QualityPreset:
    """Get a preset by its name."""
    for p in QUALITY_PRESETS:
        if p.name == name:
            return p
    return QUALITY_PRESETS[8]  # Custom


def get_preset_menu_items() -> List[str]:
    """Get formatted preset names for menu display."""
    return [f"{p.icon} {p.name}" for p in QUALITY_PRESETS]