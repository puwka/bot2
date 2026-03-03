"""Яндекс.Диск: папки по категориям, загрузка видео, удаление после отправки результата."""
from __future__ import annotations

import re
import uuid
from urllib.parse import quote

import requests

from app.config import settings

BASE_URL = "https://cloud-api.yandex.net/v1/disk"


def _headers() -> dict:
    token = (settings.YANDEX_DISK_TOKEN or "").strip()
    if not token:
        raise ValueError("YANDEX_DISK_TOKEN не задан в .env")
    return {"Authorization": f"OAuth {token}", "Accept": "application/json"}


def _path_join(*parts: str) -> str:
    """Собирает путь, убирает лишние слэши."""
    path = "/" + "/".join(p.strip().strip("/") for p in parts if (p or "").strip())
    return path or "/"


def _path_encode(path: str) -> str:
    return quote(path, safe="")


def _client_file_url(file_path: str) -> str:
    """Ссылка на файл в веб-интерфейсе (для владельца диска). Путь с ведущим / или без. # в имени кодируется в %23."""
    path = (file_path or "").strip().strip("/")
    if not path:
        return "https://disk.yandex.ru/client/disk"
    # Кодируем всё, кроме слэшей, чтобы # и др. не ломали URL
    encoded = quote(path, safe="/")
    return f"https://disk.yandex.ru/client/disk/{encoded}"


def get_file_public_url(file_path: str) -> str | None:
    """Возвращает публичную ссылку на файл, если он опубликован; иначе None."""
    try:
        url = f"{BASE_URL}/resources?path={_path_encode(file_path)}&fields=public_url"
        r = requests.get(url, headers=_headers(), timeout=15)
        if r.status_code != 200:
            return None
        return (r.json().get("public_url") or "").strip() or None
    except Exception:
        return None


def get_link_to_file(file_path: str) -> str:
    """
    Возвращает ссылку, открывающую именно файл (а не папку).
    Сначала пробует публичную ссылку; если файл не опубликован — публикует и возвращает публичную ссылку.
    Иначе — клиентская ссылка (путь с # кодируется в %23).
    """
    path = (file_path or "").strip()
    if not path:
        return _client_file_url(path)
    # Путь для API: полное кодирование (включая # и /)
    path_encoded = _path_encode(path)
    try:
        public = get_file_public_url(path)
        if public:
            return public
        # Опубликовать файл, чтобы ссылка открывала файл, а не папку
        publish_url = f"{BASE_URL}/resources/publish?path={path_encoded}"
        r = requests.put(publish_url, headers=_headers(), timeout=15)
        if r.status_code == 200:
            public = get_file_public_url(path)
            if public:
                return public
    except Exception:
        pass
    return _client_file_url(path)


def create_folder(path: str) -> None:
    """Создаёт папку на Яндекс.Диске. path — например /bot_videos/Категория1."""
    url = f"{BASE_URL}/resources?path={_path_encode(path)}"
    r = requests.put(url, headers=_headers(), timeout=30)
    if r.status_code == 201:
        return
    if r.status_code == 409:
        return  # уже существует
    r.raise_for_status()


def get_or_create_folder_in_parent(parent_path: str, folder_name: str) -> str:
    """
    Ищет в parent_path папку с именем folder_name; если есть — возвращает её путь,
    иначе создаёт и возвращает путь. parent_path — например /bot_videos.
    """
    parent_path = (parent_path or "").strip().rstrip("/") or "/"
    folder_name = (folder_name or "").strip() or "unnamed"
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", folder_name)[:255]
    folder_path = _path_join(parent_path, safe_name)

    url = f"{BASE_URL}/resources?path={_path_encode(parent_path)}&limit=100"
    r = requests.get(url, headers=_headers(), timeout=60)
    if r.status_code == 200:
        data = r.json()
        want = safe_name.strip().lower()
        for item in (data.get("_embedded") or {}).get("items") or []:
            if item.get("type") != "dir":
                continue
            name = (item.get("name") or "").strip().lower()
            if name == want:
                raw = (item.get("path") or "").replace("disk:", "").strip()
                return (raw if raw.startswith("/") else f"/{raw}") if raw else folder_path
    create_folder(folder_path)
    return folder_path


def upload_file(
    folder_path: str,
    data: bytes,
    content_type: str,
    file_name: str | None = None,
) -> tuple[str, str]:
    """
    Загружает файл в папку на Яндекс.Диске. Публикует файл и возвращает (path, public_url).
    """
    name = file_name or f"{uuid.uuid4()}.mp4"
    if "mp4" not in (content_type or "") and "webm" not in (content_type or ""):
        name = f"{uuid.uuid4()}.mp4"
    name = re.sub(r'[<>:"/\\|?*]', "_", name)[:255]
    file_path = _path_join(folder_path, name)

    upload_url = f"{BASE_URL}/resources/upload?path={_path_encode(file_path)}&overwrite=true"
    r = requests.get(upload_url, headers=_headers(), timeout=30)
    r.raise_for_status()
    href = r.json().get("href")
    if not href:
        raise RuntimeError("Яндекс.Диск не вернул URL для загрузки")

    up = requests.put(href, data=data, headers={"Content-Type": content_type or "video/mp4"}, timeout=120)
    if up.status_code not in (201, 202):
        up.raise_for_status()

    publish_url = f"{BASE_URL}/resources/publish?path={_path_encode(file_path)}"
    pub = requests.put(publish_url, headers=_headers(), timeout=30)
    if pub.status_code != 200:
        pass  # не критично, ссылка может быть через meta

    meta_url = f"{BASE_URL}/resources?path={_path_encode(file_path)}&fields=public_url"
    meta = requests.get(meta_url, headers=_headers(), timeout=30)
    public_url = ""
    if meta.status_code == 200:
        public_url = (meta.json().get("public_url") or "").strip()
    if not public_url:
        public_url = _client_file_url(file_path)
    return file_path, public_url


def delete_file(file_path: str) -> None:
    """Удаляет файл с Яндекс.Диска (путь к файлу). Путь с # кодируется для API."""
    path = (file_path or "").strip()
    if not path:
        return
    if not path.startswith("/"):
        path = "/" + path
    url = f"{BASE_URL}/resources?path={_path_encode(path)}&permanently=true"
    r = requests.delete(url, headers=_headers(), timeout=30)
    if r.status_code in (204, 202):
        return
    if r.status_code == 404:
        return  # уже удалён
    r.raise_for_status()


def remove_file_from_drive(file_path: str) -> None:
    """Удаляет файл с Яндекс.Диска по пути."""
    delete_file(file_path)


def download_file(file_path: str, max_size_bytes: int | None = 50 * 1024 * 1024) -> bytes | None:
    """Скачивает файл с Яндекс.Диска. Возвращает bytes или None если размер превышает лимит."""
    meta_url = f"{BASE_URL}/resources?path={_path_encode(file_path)}&fields=size"
    r = requests.get(meta_url, headers=_headers(), timeout=60)
    if r.status_code != 200:
        return None
    size = int((r.json().get("size") or 0))
    if max_size_bytes and size > max_size_bytes:
        return None
    down_url = f"{BASE_URL}/resources/download?path={_path_encode(file_path)}"
    r2 = requests.get(down_url, headers=_headers(), timeout=60)
    if r2.status_code != 200:
        return None
    href = r2.json().get("href")
    if not href:
        return None
    r3 = requests.get(href, headers=_headers(), timeout=120)
    if r3.status_code != 200:
        return None
    return r3.content


def list_video_files_in_folder(folder_path: str) -> list[tuple[str, str, str]]:
    """Список видеофайлов в папке. Возвращает [(path, name, mime_type), ...]. path всегда с ведущим /."""
    url = f"{BASE_URL}/resources?path={_path_encode(folder_path)}&limit=100"
    r = requests.get(url, headers=_headers(), timeout=60)
    if r.status_code != 200:
        return []
    items = (r.json().get("_embedded") or {}).get("items") or []
    video_ext = (".mp4", ".webm", ".mov", ".avi", ".mkv")
    out = []
    for f in items:
        if f.get("type") != "file":
            continue
        name = f.get("name") or ""
        mime = f.get("mime_type") or ""
        raw = (f.get("path") or "").replace("disk:", "").strip()
        path = raw if raw.startswith("/") else f"/{raw}"
        if mime.startswith("video/") or any(name.lower().endswith(ext) for ext in video_ext):
            out.append((path, name, mime))
    return out
