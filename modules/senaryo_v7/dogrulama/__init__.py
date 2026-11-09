"""Senaryo input migration ve alan/biçim doğrulaması."""

from __future__ import annotations

import logging
import random
import re
from collections.abc import Mapping, Sequence
from typing import cast

from ..ayarlar import Ayarlar
from ..exceptions import SenaryoHatasi
from ..models import Sablon, Senaryo
from .migration import migrate

_LOG = logging.getLogger("bobi_tv.senaryo_v7.dogrulama")


def dogrula(
    raw: Mapping[str, object],
    sablonlar: Sequence[Sablon],
    ayarlar: Ayarlar,
    rng: random.Random,
) -> Senaryo:
    """Input'u migrate eder, gerekli alanları normalize edip Senaryo modeline taşır."""
    migrated = migrate(raw)
    dialogue_raw = migrated.get("diyaloglar", [])
    if not isinstance(dialogue_raw, list):
        raise SenaryoHatasi("'diyaloglar' alanı liste olmalı.")
    prepared: list[dict[str, object]] = []
    for index, item in enumerate(dialogue_raw[: ayarlar.en_fazla_diyalog]):
        if isinstance(item, Mapping):
            role = _tr_upper(str(item.get("karakter") or ("MERT" if index % 2 == 0 else "AYŞE")))
            line = str(item.get("metin") or "").strip()
            if line:
                converted = dict(item)
                converted["karakter"] = role[: ayarlar.karakter_uzunluk_limiti] or "BOBİ"
                converted["metin"] = line
                prepared.append(converted)
        elif isinstance(item, str) and item.strip():
            role = "MERT" if index % 2 == 0 else "AYŞE"
            prepared.append(
                {"karakter": role, "metin": item.strip(), "cinsiyet": "erkek" if index % 2 == 0 else "kadin"}
            )
    if len(prepared) < ayarlar.en_az_diyalog:
        if not sablonlar:
            raise SenaryoHatasi("Gelen senaryoda yeterli replik yok ve kullanılabilir şablon bulunamadı.")
        fallback = rng.choice(sablonlar)
        _LOG.warning("Replik sayısı yetersiz; yedek şablona geçiliyor: %s", fallback.kategori)
        prepared = [dialog.to_dict() for dialog in fallback.diyaloglar]
        migrated["kategori"] = fallback.kategori
        migrated["ortam_etiketi"] = fallback.ortam_etiketi
        migrated["ruh_hali"] = fallback.ruh_hali
        migrated["hook_ust_bant"] = fallback.hook_ust_bant
        migrated["baslik"] = fallback.baslik
        migrated["sabit_yorum"] = fallback.sabit_yorum
        migrated["etkilesim"] = fallback.etkilesim
        migrated["karakterler"] = [character.to_dict() for character in fallback.karakterler]
        migrated["etiketler"] = list(fallback.etiketler)
        migrated["hedefkitle"] = fallback.hedefkitle
        migrated["mevsimsellik"] = list(fallback.mevsimsellik)
        migrated["tekrarkullanimgunsayisi"] = fallback.tekrarkullanimgunsayisi
        migrated["performanspuani"] = fallback.performanspuani
        migrated["yasakkelimekontrolugecti"] = fallback.yasakkelimekontrolugecti
        migrated["twist_indeksi"] = next(
            (
                index
                for index, line in enumerate(fallback.diyaloglar)
                if line.twist or line.rol.value == "twist"
            ),
            max(0, len(fallback.diyaloglar) - 2),
        )
    try:
        twist = int(migrated.get("twist_indeksi", max(0, len(prepared) - 2)))
    except (TypeError, ValueError):
        twist = max(0, len(prepared) - 2)
    twist = min(max(0, twist), len(prepared) - 1)
    migrated["twist_indeksi"] = twist
    migrated["diyaloglar"] = prepared
    migrated["semaversiyonu"] = "7.0"
    if not str(migrated.get("baslik") or "").strip():
        migrated["baslik"] = "Özgün Türkçe komedi hikâyesi #shorts"
    if not str(migrated.get("kategori") or "").strip():
        migrated["kategori"] = "absurt_komedi"
    for required in ("ortam_etiketi", "ruh_hali"):
        if not str(migrated.get(required) or "").strip():
            migrated[required] = "gündelik hayat" if required == "ortam_etiketi" else "komedi"
    return Senaryo.from_dict(cast(Mapping[str, object], migrated))


def _tr_upper(value: str) -> str:
    """Türkçe I/İ kurallarını koruyarak karakter etiketini büyük harfe çevirir."""
    return re.sub(r"\s+", " ", value.replace("i", "İ").replace("ı", "I").upper()).strip()
