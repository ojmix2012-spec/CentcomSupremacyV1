import html
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TAG_RE = re.compile(r"<[^>]+>")
MAX_VIDEO_LINKS = 3
MAX_TRANSCRIPT_CHARS = 20000


def extract_video_id(url: str) -> str:
    value = url.strip()
    if _VIDEO_ID_RE.fullmatch(value):
        return value

    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    video_id = ""

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif host == "youtube.com" or host.endswith(".youtube.com") or host == "youtube-nocookie.com":
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
                video_id = path_parts[1]

    if not _VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError(f"Enlace de YouTube no válido: {url}")
    return video_id


def parse_video_links(text: str) -> list[str]:
    urls = []
    seen = set()
    for line in text.splitlines():
        candidate = line.strip().strip("<>").strip()
        if not candidate:
            continue
        video_id = extract_video_id(candidate)
        if video_id not in seen:
            urls.append(candidate)
            seen.add(video_id)
    if len(urls) > MAX_VIDEO_LINKS:
        raise ValueError(f"Puedes analizar hasta {MAX_VIDEO_LINKS} videos por informe.")
    return urls


def _timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def fetch_transcript(url: str, languages: list[str]) -> dict[str, str | bool]:
    video_id = extract_video_id(url)
    fetched = YouTubeTranscriptApi().fetch(video_id, languages=languages)
    lines = []
    for snippet in fetched:
        clean_text = html.unescape(_TAG_RE.sub("", snippet.text)).strip()
        if clean_text:
            lines.append(f"[{_timestamp(snippet.start)}] {clean_text}")

    transcript_text = "\n".join(lines)
    if not transcript_text:
        raise ValueError("El video no contiene texto de subtítulos.")
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        transcript_text = transcript_text[:MAX_TRANSCRIPT_CHARS].rstrip()
        transcript_text += "\n[Transcripción recortada para el análisis]"

    return {
        "url": url,
        "language": fetched.language_code,
        "is_generated": fetched.is_generated,
        "text": transcript_text,
    }
