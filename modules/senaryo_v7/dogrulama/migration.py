"""Eski v6/satirlar senaryo ve paketlerini v7 şemasına taşır."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from ..exceptions import SenaryoHatasi

SEMAVERSIYONU = "7.0"


def migrate(raw: Mapping[str, object]) -> dict[str, Any]:
    """v6.0, `satirlar` veya eski paket formatını v7 JSON mapping'ine yükseltir.

    Fonksiyon input'u değiştirmez; senaryo nesnesi paket içinde yer alıyorsa nested
    nesneyi de migrate eder. Gelecek bir şema sürümünü sessizce düşürmez.
    """
    migrated = deepcopy(dict(raw))
    nested = migrated.get("senaryo")
    if isinstance(nested, Mapping):
        migrated["senaryo"] = migrate(nested)
        migrated["semaversiyonu"] = SEMAVERSIYONU
        return migrated

    old_version = str(migrated.get("semaversiyonu") or "6.0").strip().lower().removeprefix("v")
    try:
        major = int(old_version.split(".", 1)[0])
    except ValueError as exc:
        raise SenaryoHatasi(f"Bilinmeyen senaryo şema sürümü: {old_version!r}") from exc
    if major > 7:
        raise SenaryoHatasi(f"Daha yeni şema sürümü desteklenmiyor: {old_version}")

    if not isinstance(migrated.get("diyaloglar"), list):
        legacy_lines = migrated.get("satirlar", [])
        if isinstance(legacy_lines, list):
            migrated["diyaloglar"] = _satirlari_diyaloga_cevir(legacy_lines)
        else:
            migrated["diyaloglar"] = []

    migrated.setdefault("kategori", "absurt_komedi")
    migrated.setdefault("ortam_etiketi", "gündelik hayat")
    migrated.setdefault("ruh_hali", "komedi")
    migrated.setdefault("hook_ust_bant", str(migrated.get("hook_metni") or ""))
    dialogue_data = migrated.get("diyaloglar")
    dialogue_count = len(dialogue_data) if isinstance(dialogue_data, list) else 0
    migrated.setdefault("twist_indeksi", max(0, dialogue_count - 2))
    _upgrade_dialogue_model(migrated)
    migrated.setdefault("etiketler", [])
    migrated.setdefault("hedefkitle", "Genel, 13+ Türkçe Shorts izleyicisi")
    migrated.setdefault("mevsimsellik", [])
    migrated.setdefault("tekrarkullanimgunsayisi", 30)
    migrated.setdefault("performanspuani", 0.0)
    migrated.setdefault("yasakkelimekontrolugecti", False)
    migrated.setdefault("semaversiyonu", SEMAVERSIYONU)
    migrated["semaversiyonu"] = SEMAVERSIYONU
    return migrated


def _upgrade_dialogue_model(data: dict[str, Any]) -> None:
    """Legacy satırları ref'li karakter kartları ve tam v7 satır alanlarıyla zenginleştirir."""
    lines = data.get("diyaloglar")
    if not isinstance(lines, list):
        return
    characters_raw = data.get("karakterler")
    characters = characters_raw if isinstance(characters_raw, list) else []
    if isinstance(characters_raw, dict):
        for ref, value in characters_raw.items():
            if isinstance(ref, str) and isinstance(value, dict):
                character_data = dict(value)
                character_data.setdefault("ref", ref)
                character_data.setdefault("ad", ref)
                characters.append(character_data)
    character_by_name: dict[str, dict[str, Any]] = {}
    for existing_character in characters:
        if isinstance(existing_character, dict):
            name = str(existing_character.get("ad") or "BOBİ")
            ref = str(
                existing_character.get("ref") or existing_character.get("id") or f"karakter_{_slug(name)}"
            )
            gender = _gender(existing_character.get("cinsiyet"))
            existing_character["ref"] = ref
            existing_character["cinsiyet"] = gender
            existing_character["sesid"] = "tr-TR-EmelNeural" if gender == "kadin" else "tr-TR-AhmetNeural"
            existing_character.setdefault("yasaraligi", "yetişkin")
            existing_character.setdefault("kisiliknotu", "")
            existing_character["varsayilanduygu"] = _emotion(
                existing_character.get("varsayilanduygu", "normal")
            )
            character_by_name[name] = existing_character
            character_by_name[ref] = existing_character

    for line_index, raw_line in enumerate(lines):
        if not isinstance(raw_line, dict):
            continue
        name = str(raw_line.get("karakter") or raw_line.get("karakter_ref") or "BOBİ")
        character = character_by_name.get(str(raw_line.get("karakter_ref") or name)) or character_by_name.get(
            name
        )
        if character is None:
            gender = _gender(raw_line.get("cinsiyet"))
            ref = str(raw_line.get("karakter_ref") or f"karakter_{_slug(name)}")
            character = {
                "ref": ref,
                "ad": name,
                "cinsiyet": gender,
                "sesid": "tr-TR-EmelNeural" if gender == "kadin" else "tr-TR-AhmetNeural",
                "yasaraligi": "yetişkin",
                "kisiliknotu": "Legacy senaryodan türetilmiş karakter; kimlik boyunca sabit ses.",
                "varsayilanduygu": _emotion(raw_line.get("ses", "normal")),
            }
            characters.append(character)
            character_by_name[name] = character
            character_by_name[ref] = character
        raw_line["karakter_ref"] = character["ref"]
        raw_line["karakter"] = character["ad"]
        raw_line["cinsiyet"] = character["cinsiyet"]
        raw_line["sesid"] = character["sesid"]
        raw_line["ses"] = _emotion(raw_line.get("ses", "normal"))
        raw_line["hiz"] = _bounded_float(raw_line.get("hiz"), 1.0, 0.85, 1.25)
        raw_line["duraklamams"] = _bounded_int(raw_line.get("duraklamams"), 120, 0, 3000)
        raw_line["vurgukelimeler"] = _keywords(
            str(raw_line.get("metin") or ""), raw_line.get("vurgukelimeler", raw_line.get("vurgu_kelimeler"))
        )
        raw_line["vurgu_kelimeler"] = list(raw_line["vurgukelimeler"])
        raw_line["altyazistili"] = str(
            raw_line.get("altyazistili") or ("büyük" if raw_line.get("twist") else "normal")
        )
        raw_line["kamera"] = str(raw_line.get("kamera") or ("shake" if raw_line.get("twist") else "cut"))
        raw_line.setdefault("emojioverlay", None)
        words = len(str(raw_line.get("metin") or "").split())
        raw_line["tahminisuresn"] = max(
            0.0,
            _bounded_float(
                raw_line.get("tahminisuresn"), round(words * 0.36 / raw_line["hiz"], 2), 0.0, 120.0
            ),
        )
        raw_line["rol"] = _role(raw_line, line_index, len(lines), data.get("twist_indeksi"))
        raw_line["twist"] = bool(raw_line.get("twist", raw_line["rol"] == "twist"))
    data["karakterler"] = characters


def _gender(value: object) -> str:
    """Eski cinsiyet etiketini iki desteklenen forma normalize eder."""
    return "kadin" if str(value or "").strip().lower() in {"kadın", "kadin", "female", "f"} else "erkek"


def _emotion(value: object) -> str:
    """Bilinen bozuk/aksanlı emotion tag'lerini kanonik yazıma dönüştürür."""
    raw = str(value or "normal").strip().lower()
    return {
        "suprized": "sasirmis",
        "surprised": "sasirmis",
        "şaşkın": "sasirmis",
        "bikeyn": "bikkin",
        "bikeyn_dramatik": "bikkin_dramatik",
        "yavas_bikkin": "bikkin",
        "soğuk": "soguk",
    }.get(raw, raw)


def _role(line: dict[str, Any], index: int, count: int, twist_index: object) -> str:
    """Mevcut role/twist'i korur, eski twist index'ini satır rolüne taşır."""
    role = str(line.get("rol") or "").lower()
    if role in {"hook", "setup", "escalation", "twist", "loopkapanis"}:
        return role
    try:
        twist = int(twist_index) if isinstance(twist_index, (int, float, str)) else max(0, count - 2)
    except ValueError:
        twist = max(0, count - 2)
    if index == 0:
        return "hook"
    if index == twist or bool(line.get("twist")):
        return "twist"
    if index == count - 1:
        return "loopkapanis"
    return "setup" if index == 1 else "escalation"


def _slug(text: str) -> str:
    """Build deterministic, simple ref from a display name."""
    import re
    import unicodedata

    value = (
        text.lower()
        .replace("ı", "i")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    return (
        re.sub(
            r"[^a-z0-9]+", "_", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        ).strip("_")
        or "karakter"
    )


def _keywords(text: str, raw: object) -> list[str]:
    """Use provided keywords, otherwise extract a short list from spoken text."""
    if isinstance(raw, list):
        provided = [str(word).strip() for word in raw if isinstance(word, str) and word.strip()]
        if provided:
            return provided
    import re

    tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9'-]+", text)
    meaningful = [word for word in tokens if len(word) >= 4]
    return meaningful[-3:] or tokens[-3:] or ["..."]


def _bounded_float(value: object, default: float, lower: float, upper: float) -> float:
    """Parse and clamp numeric setting."""
    if not isinstance(value, (int, float, str)):
        return default
    try:
        return min(upper, max(lower, float(value)))
    except ValueError:
        return default


def _bounded_int(value: object, default: int, lower: int, upper: int) -> int:
    """Parse and clamp integer setting."""
    if not isinstance(value, (int, float, str)):
        return default
    try:
        return min(upper, max(lower, int(value)))
    except ValueError:
        return default


def _satirlari_diyaloga_cevir(lines: list[object]) -> list[dict[str, str]]:
    """Eski `satirlar` stringlerini çift karakterli diyalog alanına map eder."""
    roles = (("MERT", "erkek"), ("AYŞE", "kadin"))
    converted: list[dict[str, str]] = []
    for index, item in enumerate(lines):
        text = str(item).strip()
        role, gender = roles[index % len(roles)]
        if ":" in text:
            possible_role, possible_text = text.split(":", 1)
            if possible_role.strip() and len(possible_role.strip()) <= 18:
                role, text = possible_role.strip().upper(), possible_text.strip()
        if text:
            converted.append(
                {
                    "karakter": role,
                    "cinsiyet": gender,
                    "metin": text,
                    "ses": "enerjik" if index == 0 else "normal",
                    "sfx": "whoosh" if index == 0 else "pop",
                }
            )
    return converted
