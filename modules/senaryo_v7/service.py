"""Senaryo üretiminin uygulama servisi; IO, şema ve iş mantığını birleştirir."""

from __future__ import annotations

import logging
import random
from collections.abc import Mapping
from typing import Any

from .arsiv import ArsivDeposu
from .ayarlar import Ayarlar
from .cikti import CiktiYazici
from .dogrulama import dogrula
from .dogrulama.migration import migrate
from .exceptions import CiktiHatasi, KuyrukHatasi, SenaryoHatasi
from .kuyruk import KuyrukDeposu
from .loglama import kur_logger
from .models import Sablon, Senaryo, SenaryoPaketi
from .sablonlar import load_konu_aciklamalari, load_sablonlar
from .zenginlestirme import zenginlestir


class SenaryoUretici:
    """Typed senaryo pipeline; legacy API'ye dict çıktısı sağlayan servis."""

    def __init__(
        self,
        ayarlar: Ayarlar | None = None,
        *,
        seed: int | str | None = None,
        rng: random.Random | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Bağımlılıkları enjekte eder; `seed` aynı içeriği yeniden üretir."""
        if seed is not None and rng is not None:
            raise SenaryoHatasi("Deterministik seçim için seed veya rng verin; ikisini birlikte vermeyin.")
        self.ayarlar = ayarlar or Ayarlar.ortamdan()
        self.rng = rng or random.Random(seed)
        self.deterministik = seed is not None
        self.logger = logger or kur_logger()
        self.sablonlar: tuple[Sablon, ...] = load_sablonlar(self.ayarlar.dizi_sablon_yolu)
        self.konu_aciklamalari: dict[str, str] = load_konu_aciklamalari(self.ayarlar.konu_aciklama_yolu)
        self.arsiv = ArsivDeposu(self.ayarlar)
        self.kuyruk = KuyrukDeposu(self.ayarlar)
        self.cikti = CiktiYazici(self.ayarlar)
        self._kullanilan_kategoriler: set[str] = set()

    def senaryo_dogrula_ve_zenginlestir(
        self,
        raw: Mapping[str, object],
        video_no: int = 1,
    ) -> Senaryo:
        """v6/v7 girdi mapping'ini migrate, validate ve enrich edip typed model döndürür."""
        scenario_raw = raw.get("senaryo") if isinstance(raw.get("senaryo"), Mapping) else raw
        migrated = migrate(scenario_raw)  # type: ignore[arg-type]
        validated = dogrula(migrated, self.sablonlar, self.ayarlar, self.rng)
        enriched = zenginlestir(validated, self.ayarlar, self.sablonlar)
        if not enriched.baslik:
            raise SenaryoHatasi(f"Video #{video_no} senaryosunda başlık üretilemedi.")
        return enriched

    def siradaki_kategori(self) -> str:
        """Arşivde yakın zamanda kullanılmayan ve bu batch'te seçilmemiş kategori döndürür."""
        categories = list(dict.fromkeys(template.kategori for template in self.sablonlar))
        recent = self.arsiv.yakin_kategoriler()
        candidates = [
            category
            for category in categories
            if category not in recent and category not in self._kullanilan_kategoriler
        ]
        if not candidates:
            candidates = [category for category in categories if category not in self._kullanilan_kategoriler]
        if not candidates:
            self._kullanilan_kategoriler.clear()
            candidates = categories
        return self.rng.choice(candidates)

    def kuyruktan_arena_senaryosu_al(self, video_no: int) -> dict[str, Any] | None:
        """Sıradaki geçerli, tekrarsız Arena senaryosunu tüketir; bozukları loglayıp atlar."""
        history = self.arsiv.yukle()
        for path in self.kuyruk.bekleyenler():
            try:
                raw = self.kuyruk.oku(path)
                scenario = self.senaryo_dogrula_ve_zenginlestir(raw, video_no)
                summary = " ".join(scenario.tts_metinleri)
                if self.arsiv.tekrar_mi(summary, history):
                    self.logger.warning("Tekrar senaryo kuyruğundan çıkarıldı: %s", path.name)
                    self.kuyruk.tuket(path)
                    continue
                source = "arena_kuyruk"
                package = self._pakete_sar(scenario, video_no, source)
                self.kuyruk.tuket(path)
                self._kullanilan_kategoriler.add(scenario.kategori)
                return package.to_dict()
            except KuyrukHatasi as exc:
                self.logger.error("%s", exc)
                try:
                    self.kuyruk.tuket(path)
                except KuyrukHatasi:
                    self.logger.exception("Bozuk kayıt kuyruktan kaldırılamadı: %s", path)
            except CiktiHatasi:
                # Yazma hatasında giriş kuyruğunu koru; sonraki çalışmada yeniden denenebilir.
                raise
            except SenaryoHatasi as exc:
                self.logger.error("Geçersiz Arena senaryosu (%s): %s", path.name, exc)
                self.kuyruk.tuket(path)
        return None

    def senaryo_paketi_olustur(self, video_no: int) -> dict[str, Any]:
        """Önce Arena kuyruğunu, sonra rotasyonlu yerleşik şablonu kullanır."""
        queued = self.kuyruktan_arena_senaryosu_al(video_no)
        if queued is not None:
            return queued
        history = self.arsiv.yukle()
        recent = self.arsiv.yakin_kategoriler()
        categories = list(dict.fromkeys(template.kategori for template in self.sablonlar))
        eligible = [
            category
            for category in categories
            if category not in recent and category not in self._kullanilan_kategoriler
        ]
        if not eligible:
            eligible = [category for category in categories if category not in self._kullanilan_kategoriler]
        if not eligible:
            self._kullanilan_kategoriler.clear()
            eligible = categories
        category = self.rng.choice(eligible)
        candidates = [template for template in self.sablonlar if template.kategori in eligible]
        self.rng.shuffle(candidates)
        candidates.sort(key=lambda template: template.kategori != category)
        selected = candidates[0]
        for template in candidates:
            summary = " ".join(line.metin for line in template.diyaloglar)
            if not self.arsiv.tekrar_mi(summary, history):
                selected = template
                break
        scenario_raw = selected.to_dict()
        scenario = self.senaryo_dogrula_ve_zenginlestir(scenario_raw, video_no)
        self._kullanilan_kategoriler.add(scenario.kategori)
        return self._pakete_sar(scenario, video_no, "yerlesik_v7").to_dict()

    def _pakete_sar(self, scenario: Senaryo, video_no: int, source: str) -> SenaryoPaketi:
        """Package modeli oluşturup diske kaydeder; seeded replay deterministiktir."""
        package = self.cikti.pakete_sar(scenario, video_no, source, deterministik=self.deterministik)
        target = self.cikti.yaz(package)
        self.logger.info("Senaryo paketi hazır: #%s %s (%s)", video_no, scenario.baslik, target)
        return package

    def migrate_paket(self, raw: Mapping[str, object]) -> SenaryoPaketi:
        """Paket JSON'u ve iç senaryosunu v7'ye migrate edip typed pakete çevirir."""
        migrated = migrate(raw)
        package = SenaryoPaketi.from_dict(migrated)
        package.senaryo = zenginlestir(package.senaryo, self.ayarlar, self.sablonlar)
        package.semaversiyonu = "7.0"
        return package


def gun_senaryolari_uret(
    hedef: int = 4,
    *,
    seed: int | str | None = None,
    ayarlar: Ayarlar | None = None,
) -> list[dict[str, Any]]:
    """Aynı RNG/servis örneğiyle bir batch üretir, kategori tekrarını azaltır."""
    service = SenaryoUretici(ayarlar, seed=seed)
    return [service.senaryo_paketi_olustur(index) for index in range(1, max(0, hedef) + 1)]
