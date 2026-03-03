import re
from dataclasses import dataclass


@dataclass
class PlatformInfo:
    platform: str
    external_id: str | None


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tiktok", re.compile(r"tiktok\.com/@[^/]+/video/(\d+)")),
    ("tiktok", re.compile(r"vm\.tiktok\.com/([A-Za-z0-9]+)")),
    ("reels", re.compile(r"instagram\.com/reels?/([A-Za-z0-9_-]+)")),
    ("reels", re.compile(r"instagram\.com/p/([A-Za-z0-9_-]+)")),
    ("shorts", re.compile(r"youtube\.com/shorts/([A-Za-z0-9_-]+)")),
    ("shorts", re.compile(r"youtu\.be/([A-Za-z0-9_-]+)")),
    ("vk", re.compile(r"vk\.com/clip-?(\d+_\d+)")),
    ("vk", re.compile(r"vk\.com/video-?(\d+_\d+)")),
]


def detect_platform(url: str) -> PlatformInfo:
    url = url.strip()
    for platform, pattern in _PATTERNS:
        m = pattern.search(url)
        if m:
            return PlatformInfo(platform=platform, external_id=m.group(1))

    if "tiktok.com" in url:
        return PlatformInfo(platform="tiktok", external_id=None)
    if "instagram.com" in url:
        return PlatformInfo(platform="reels", external_id=None)
    if "youtube.com" in url or "youtu.be" in url:
        return PlatformInfo(platform="shorts", external_id=None)
    if "vk.com" in url:
        return PlatformInfo(platform="vk", external_id=None)

    return PlatformInfo(platform="unknown", external_id=None)
