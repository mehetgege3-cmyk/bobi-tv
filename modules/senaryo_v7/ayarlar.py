"""Senaryo v7 için varsayılanlar ve ortam değişkeni override'ları."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .exceptions import SenaryoHatasi


@dataclass(frozen=True, slots=True)
class Ayarlar:
    """Senaryo üretimindeki ayarlanabilir sınırlar ve dosya yolları."""

    arsiv_yolu: Path = field(
        default=Path("bobi_tv/archive/videos.json"), metadata={"description": "Yayın geçmişi JSON yolu."}
    )
    senaryo_yolu: Path = field(
        default=Path("bobi_tv/production/scripts"),
        metadata={"description": "Üretilen senaryo paketi dizini."},
    )
    arena_kuyruk_yolu: Path = field(
        default=Path("bobi_tv/production/scripts/arena"),
        metadata={"description": "Önceden üretilen Arena senaryoları dizini."},
    )
    dizi_sablon_yolu: Path = field(
        default=Path("modules/senaryo_v7/sablonlar/veri.json"),
        metadata={"description": "JSON senaryo şablonları."},
    )
    konu_aciklama_yolu: Path = field(
        default=Path("modules/senaryo_v7/sablonlar/konular.json"),
        metadata={"description": "Konu açıklamaları JSON'u."},
    )
    en_az_diyalog: int = field(
        default=3, metadata={"description": "Geçerli senaryodaki minimum replik sayısı."}
    )
    en_fazla_diyalog: int = field(
        default=8, metadata={"description": "İlk doğrulamada kabul edilen maksimum replik sayısı."}
    )
    genisletme_diyalog_azami: int = field(
        default=12, metadata={"description": "15sn altı senaryolar için uzatma sonrası replik sınırı."}
    )
    karakter_uzunluk_limiti: int = field(
        default=18, metadata={"description": "Normalize karakter adı uzunluğu."}
    )
    tahmini_saniye_kelime: float = field(
        default=0.36, metadata={"description": "Yaklaşık konuşma süresi katsayısı."}
    )
    minimum_replik_saniyesi: float = field(
        default=1.6, metadata={"description": "Tahminde tek repliğe uygulanan alt sınır."}
    )
    hedef_tahmini_sure: float = field(
        default=19.0, metadata={"description": "TTS değişkenliği için hedeflenen güvenli tahmini süre."}
    )
    minimum_yayin_suresi: float = field(
        default=15.0, metadata={"description": "Yayımlanabilir videonun kesin minimum süresi."}
    )
    maksimum_yayin_suresi: float = field(
        default=59.5, metadata={"description": "Bu üretim hattının Shorts render üst sınırı."}
    )
    tts_guvenlik_payi: float = field(
        default=1.0, metadata={"description": "Gerçek TTS süresinde minimumun üzerine eklenecek pay."}
    )
    tts_uzatma_cift_azami: int = field(
        default=6, metadata={"description": "Gerçek TTS kısa kalırsa eklenecek replik çifti üst sınırı."}
    )
    hook_bant_azami: int = field(
        default=38, metadata={"description": "Hook üst bandının maksimum karakter sayısı."}
    )
    hook_kesim_uzunlugu: int = field(
        default=34, metadata={"description": "Uzun hook için ilk kesim uzunluğu."}
    )
    baslik_kesim_uzunlugu: int = field(
        default=88, metadata={"description": "Shorts etiketi öncesi başlık kesim uzunluğu."}
    )
    baslik_azami: int = field(default=100, metadata={"description": "Platform başlığının maksimum uzunluğu."})
    yakin_kategori_sayisi: int = field(
        default=6, metadata={"description": "Kategori rotasyonunda geriye atılacak son yayın sayısı."}
    )
    dosya_indent: int = field(default=2, metadata={"description": "JSON çıktılarının girinti seviyesi."})

    @classmethod
    def ortamdan(cls, environ: Mapping[str, str] | None = None) -> Ayarlar:
        """BOBI_SCENARIO_* değişkenlerinden override alarak Ayarlar üretir."""
        env = os.environ if environ is None else environ
        defaults = cls()
        path_fields = {
            "arsiv_yolu": "ARSIV_YOLU",
            "senaryo_yolu": "SENARYO_YOLU",
            "arena_kuyruk_yolu": "ARENA_KUYRUK_YOLU",
            "dizi_sablon_yolu": "SABLON_YOLU",
            "konu_aciklama_yolu": "KONU_YOLU",
        }
        int_fields = {
            "en_az_diyalog": "EN_AZ_DIYALOG",
            "en_fazla_diyalog": "EN_FAZLA_DIYALOG",
            "genisletme_diyalog_azami": "GENISLETME_DIYALOG_AZAMI",
            "tts_uzatma_cift_azami": "TTS_UZATMA_CIFT_AZAMI",
            "karakter_uzunluk_limiti": "KARAKTER_UZUNLUK_LIMITI",
            "hook_bant_azami": "HOOK_BANT_AZAMI",
            "hook_kesim_uzunlugu": "HOOK_KESIM_UZUNLUGU",
            "baslik_kesim_uzunlugu": "BASLIK_KESIM_UZUNLUGU",
            "baslik_azami": "BASLIK_AZAMI",
            "yakin_kategori_sayisi": "YAKIN_KATEGORI_SAYISI",
            "dosya_indent": "DOSYA_INDENT",
        }
        float_fields = {
            "tahmini_saniye_kelime": "TAHMINI_SANIYE_KELIME",
            "minimum_replik_saniyesi": "MINIMUM_REPLIK_SANIYESI",
            "hedef_tahmini_sure": "HEDEF_TAHMINI_SURE",
            "minimum_yayin_suresi": "MINIMUM_YAYIN_SURESI",
            "maksimum_yayin_suresi": "MAKSIMUM_YAYIN_SURESI",
            "tts_guvenlik_payi": "TTS_GUVENLIK_PAYI",
        }
        changes: dict[str, object] = {}
        for name, suffix in path_fields.items():
            raw = env.get(f"BOBI_SCENARIO_{suffix}")
            if raw:
                changes[name] = Path(raw)
        for name, suffix in int_fields.items():
            raw = env.get(f"BOBI_SCENARIO_{suffix}")
            if raw is not None:
                try:
                    changes[name] = int(raw)
                except ValueError as exc:
                    raise SenaryoHatasi(f"BOBI_SCENARIO_{suffix} tam sayı olmalı: {raw!r}") from exc
        for name, suffix in float_fields.items():
            raw = env.get(f"BOBI_SCENARIO_{suffix}")
            if raw is not None:
                try:
                    changes[name] = float(raw)
                except ValueError as exc:
                    raise SenaryoHatasi(f"BOBI_SCENARIO_{suffix} sayı olmalı: {raw!r}") from exc
        values = {field_name: getattr(defaults, field_name) for field_name in defaults.__dataclass_fields__}
        values.update(changes)
        settings = cls(**values)
        if settings.en_az_diyalog < 1 or settings.en_fazla_diyalog < settings.en_az_diyalog:
            raise SenaryoHatasi(
                "Diyalog sınırları geçersiz: en_fazla_diyalog en_az_diyalog'dan küçük olamaz."
            )
        if settings.tahmini_saniye_kelime <= 0 or settings.minimum_replik_saniyesi < 0:
            raise SenaryoHatasi("Süre katsayıları pozitif/geçerli olmalıdır.")
        if settings.minimum_yayin_suresi <= 0 or settings.hedef_tahmini_sure < settings.minimum_yayin_suresi:
            raise SenaryoHatasi("Hedef tahmini süre, minimum yayın süresinden kısa olamaz.")
        return settings
