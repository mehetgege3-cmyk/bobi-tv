"""Senaryo paketini legacy JSON sözleşmesiyle diske yazma."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from ..ayarlar import Ayarlar
from ..exceptions import CiktiHatasi
from ..models import Senaryo, SenaryoPaketi


class CiktiYazici:
    """Paket adı, tekrar hash'i ve JSON dosya yazımını yönetir."""

    def __init__(self, ayarlar: Ayarlar) -> None:
        """Çıktı yolu ve JSON girinti ayarlarıyla yazıcı oluşturur."""
        self._ayarlar = ayarlar

    def pakete_sar(
        self,
        senaryo: Senaryo,
        video_no: int,
        kaynak: str,
        deterministik: bool = False,
    ) -> SenaryoPaketi:
        """Senaryoyu eski ana pipeline sözleşmesini koruyan pakete dönüştürür."""
        summary = " ".join(senaryo.tts_metinleri)
        digest = hashlib.md5(summary[:120].encode("utf-8"), usedforsecurity=False).hexdigest()
        senaryo.hash = digest
        date_tag = "20000101" if deterministik else datetime.now().strftime("%Y%m%d")
        created = "2000-01-01T00:00:00+00:00" if deterministik else datetime.now(UTC).isoformat()
        package_name = f"{date_tag}_{video_no:04d}_{_dosya_slug(senaryo.kategori)}"
        return SenaryoPaketi(
            video_no=video_no,
            dosya_adi=package_name,
            baslik=senaryo.baslik,
            aciklama=senaryo.sabit_yorum,
            senaryo=senaryo,
            kaynak=kaynak,
            olusturuldu=created,
            hash=digest,
        )

    def yaz(self, package: SenaryoPaketi) -> Path:
        """Paketi JSON olarak yazar; klasör/izin hatasını anlamlı istisnaya çevirir."""
        target = self._ayarlar.senaryo_yolu / f"{package.dosya_adi}.json"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(package.to_dict(), ensure_ascii=False, indent=self._ayarlar.dosya_indent) + "\n",
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            raise CiktiHatasi(f"Senaryo paketi yazılamadı ({target}): {exc}") from exc
        return target


def _dosya_slug(value: str) -> str:
    """Dosya adı güvenliği için kategori karakterlerini normalize eder."""
    cleaned = "".join(char.lower() if char.isalnum() or char in "-_" else "_" for char in value.strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("._-") or "senaryo"
