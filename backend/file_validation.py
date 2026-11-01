"""Allowlisted document/media types; active web content and executables are rejected."""
import io
import json
import unicodedata
import warnings
import zipfile
from pathlib import PurePosixPath

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

MAX_FILE_SIZE = 25 * 1024 * 1024
FILE_TYPES = {
    ".pdf": ("application/pdf", "document"),
    ".txt": ("text/plain", "document"),
    ".csv": ("text/csv", "document"),
    ".json": ("application/json", "document"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document"),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "document"),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "document"),
    ".jpg": ("image/jpeg", "image"), ".jpeg": ("image/jpeg", "image"),
    ".png": ("image/png", "image"), ".webp": ("image/webp", "image"), ".gif": ("image/gif", "image"),
    ".mp4": ("video/mp4", "video"), ".mov": ("video/quicktime", "video"), ".webm": ("video/webm", "video"),
    ".mp3": ("audio/mpeg", "audio"), ".wav": ("audio/wav", "audio"), ".ogg": ("audio/ogg", "audio"),
}


def validate_image(data, ext):
    expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP", ".gif": "GIF"}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format != expected[ext] or image.width * image.height > 40_000_000:
                    return False
                image.verify()
            # verify() checks structure; decoding also rejects truncated pixel data.
            with Image.open(io.BytesIO(data)) as image:
                image.load()
        return True
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        return False


def file_info(filename):
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in name if not unicodedata.category(c).startswith("C")).strip()
    ext = PurePosixPath(name).suffix.lower()
    if ext not in FILE_TYPES:
        raise HTTPException(415, "Formato não permitido. Envie um documento, imagem, vídeo ou áudio compatível.")
    if len(name) > 180:
        name = name[:180 - len(ext)] + ext
    mime, kind = FILE_TYPES[ext]
    return name, ext, mime, kind


def validate_content(data, ext):
    if not data:
        raise HTTPException(400, "O arquivo está vazio.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, "Cada arquivo pode ter no máximo 25 MB.")
    valid = False
    if ext in (".txt", ".csv", ".json"):
        try:
            text = data.decode("utf-8-sig")
            valid = "\x00" not in text
            if ext == ".json":
                json.loads(text)
        except (UnicodeError, ValueError, RecursionError):
            valid = False
    elif ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        valid = validate_image(data, ext)
    elif ext in (".docx", ".xlsx", ".pptx"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                folder = {".docx": "word/", ".xlsx": "xl/", ".pptx": "ppt/"}[ext]
                valid = (len(names) <= 10000 and "[Content_Types].xml" in names
                         and any(n.startswith(folder) for n in names)
                         and not any(n.lower().endswith("vbaproject.bin") for n in names))
        except (zipfile.BadZipFile, ValueError):
            valid = False
    else:
        checks = {
            ".pdf": data.startswith(b"%PDF-"),
            ".jpg": data.startswith(b"\xff\xd8\xff"), ".jpeg": data.startswith(b"\xff\xd8\xff"),
            ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
            ".gif": data[:6] in (b"GIF87a", b"GIF89a"),
            ".webp": data[:4] == b"RIFF" and data[8:12] == b"WEBP",
            ".mp4": data[4:8] == b"ftyp", ".mov": data[4:8] in (b"ftyp", b"moov", b"mdat", b"wide"),
            ".webm": data.startswith(b"\x1a\x45\xdf\xa3"),
            ".mp3": data.startswith(b"ID3") or (len(data) > 1 and data[0] == 255 and data[1] & 224 == 224),
            ".wav": data[:4] == b"RIFF" and data[8:12] == b"WAVE",
            ".ogg": data.startswith(b"OggS"),
        }
        valid = checks.get(ext, False)
    if not valid:
        raise HTTPException(415, "O conteúdo não corresponde ao formato do arquivo ou está inválido.")