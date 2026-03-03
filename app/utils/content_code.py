"""
Код контента ролика: исполнитель (A) + порядковый номер (#); при выдаче добавляется дистрибьютор (D).
Формат: A3#0042 при загрузке, A3#0042D7 после выдачи дистрибьютору.
"""
from __future__ import annotations

import re
from typing import Optional
from uuid import UUID


def user_id_to_code(user_id: UUID) -> int:
    """Стабильный код 1–99 из id пользователя (для A и D в content_code)."""
    return (abs(hash(str(user_id))) % 99) + 1


# Паттерн: A + число, # + число; опционально D + число в конце
_CODE_RE = re.compile(r"^A(\d+)#(\d+)(?:D(\d+))?$", re.IGNORECASE)


def build_performer_code(performer: int, sequence: int) -> str:
    """Код при загрузке: A{performer}#{sequence}, например A3#0042."""
    performer = max(0, min(99, int(performer)))
    sequence = max(1, int(sequence))
    return f"A{performer}#{sequence:04d}"


def append_distributor(content_code: Optional[str], distributor_code: int) -> str:
    """Добавить к коду сегмент дистрибьютора: A3#0042 -> A3#0042D7. Если код уже содержит D — не дублировать."""
    if not content_code or not content_code.strip():
        return build_performer_code(0, 1) + f"D{distributor_code}"
    code = content_code.strip()
    if "D" in code.upper() and re.search(r"D\d+", code, re.IGNORECASE):
        return code
    d = max(0, min(99, int(distributor_code)))
    return code + f"D{d}"


def parse(content_code: Optional[str]) -> Optional[dict]:
    """
    Разобрать код. Возвращает {"performer": int, "sequence": int, "distributor": int | None} или None.
    """
    if not content_code or not isinstance(content_code, str):
        return None
    code = content_code.strip()
    m = _CODE_RE.match(code)
    if m:
        return {
            "performer": int(m.group(1)),
            "sequence": int(m.group(2)),
            "distributor": int(m.group(3)) if m.group(3) else None,
        }
    # Поддержка кода с D в конце (A3#0042D7)
    m = re.match(r"^A(\d+)#(\d+)D(\d+)$", code, re.IGNORECASE)
    if m:
        return {
            "performer": int(m.group(1)),
            "sequence": int(m.group(2)),
            "distributor": int(m.group(3)),
        }
    return None


def filename_for_code(content_code: str, ext: str = "mp4") -> str:
    """Имя файла для кода: A3#0042 -> A3#0042.mp4. Символ # в имени допустим на Яндекс.Диске."""
    safe = (content_code or "").strip()
    if not safe:
        safe = "A0#0001"
    if not safe.lower().endswith(f".{ext}"):
        safe = f"{safe}.{ext}"
    return safe


def parse_from_filename(filename: str) -> Optional[str]:
    """Извлечь код из имени файла: A3#0042.mp4 или A3#0042D7.mp4 -> A3#0042 или A3#0042D7."""
    if not filename:
        return None
    base = filename.rsplit(".", 1)[0] if "." in filename else filename
    m = re.match(r"^(A\d+#\d+(?:D\d+)?)", base, re.IGNORECASE)
    return m.group(1) if m else None
