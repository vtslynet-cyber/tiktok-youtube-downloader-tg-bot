import json
import re
import tempfile
from pathlib import Path
from typing import Optional
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    "Referer": "https://www.pinterest.com/",
}

def _sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\n\r\t]', "_", name).strip()

async def _fetch_text(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    r = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
    r.raise_for_status()
    return r.text, str(r.url)

def _extract_from_og_video(soup: BeautifulSoup) -> Optional[str]:
    tag = soup.find("meta", property="og:video") or soup.find(
        "meta", attrs={"name": "twitter:player:stream"}
    )
    return tag.get("content") if tag and tag.get("content") else None

def _extract_from_json_ld(soup: BeautifulSoup) -> Optional[str]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.text)
        except json.JSONDecodeError:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            url = obj.get("contentUrl")
            if isinstance(url, str) and url.endswith(".mp4"):
                return url
    return None

def _extract_from_pws_data(soup: BeautifulSoup) -> Optional[str]:
    holder = soup.find("script", id="__PWS_DATA__")
    if not holder or not holder.text:
        return None
    try:
        data = json.loads(holder.text)
    except json.JSONDecodeError:
        return None
    blob = json.dumps(data)
    m = re.search(r'https://[^"\\]+?\.mp4', blob)
    return m.group(0) if m else None

def _extract_from_video_tag(soup: BeautifulSoup) -> Optional[str]:
    v = soup.find("video")
    if not v:
        return None
    src = v.get("src") or v.get("data-src")
    if not src:
        return None
    if src.endswith(".mp4"):
        return src
    if src.endswith(".m3u8"):
        # слабый резерв — может не всегда работать
        return src.replace("/hls/", "/720p/").replace(".m3u8", ".mp4")
    return None

async def resolve_direct_video_url(pin_url: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        html, _ = await _fetch_text(client, pin_url)
        soup = BeautifulSoup(html, "html.parser")
        for extractor in (
            _extract_from_og_video,
            _extract_from_json_ld,
            _extract_from_pws_data,
            _extract_from_video_tag,
        ):
            try:
                url = extractor(soup)
            except Exception:
                url = None
            if url:
                return url
        return None

async def download_pinterest_video(pin_url: str) -> Path:
    """
    Скачивает Pinterest-видео во временный файл и возвращает путь.
    Бросает httpx.HTTPError/RuntimeError при ошибках.
    """
    direct_url = await resolve_direct_video_url(pin_url)
    if not direct_url:
        raise RuntimeError("Не удалось найти прямую ссылку на видео (возможно, это не видео-пин).")

    name = _sanitize_filename(Path(direct_url).name.split("?")[0]) or "pinterest_video.mp4"
    if not name.lower().endswith(".mp4"):
        name += ".mp4"

    out_path = Path(tempfile.gettempdir()) / name

    async with httpx.AsyncClient() as client:
        async with client.stream("GET", direct_url, headers=HEADERS, timeout=60) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                async for chunk in r.aiter_bytes(1024 * 256):
                    if chunk:
                        f.write(chunk)

    return out_path
