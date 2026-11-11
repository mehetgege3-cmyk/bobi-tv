"""Süre tavanı testleri (2026-11-11 kullanıcı talimatı).

KULLANICI:
  "YouTube'un güncel kuralları: Maksimum 180 saniye (3 dakika). Dikey 9:16,
   1080x1920. Sana bu kısıtlamayı dayatan kodları ve kuralları ÇÖPE AT."

Eski kodda `maksimum_yayin_suresi = 59.5` vardı. Bu bir YouTube kuralı
DEĞİLDİ; içeriği 45-60 kelimeye sıkıştırıyordu ve bilgi anlatımını
imkânsız kılıyordu. Bu dosya yeni sözleşmeyi kilitler.
"""

from __future__ import annotations

from pathlib import Path

KOK = Path(__file__).resolve().parents[1]


def test_ust_sinir_180_saniye():
    from modules.senaryo_v7.ayarlar import Ayarlar

    a = Ayarlar.ortamdan()
    assert a.maksimum_yayin_suresi == 180.0, "Shorts 3 dakika = 180 sn"
    assert a.minimum_yayin_suresi == 15.0


def test_eski_59_5_tavani_kodda_kalmadi():
    kaynak = (KOK / "modules/senaryo_v7/ayarlar.py").read_text(encoding="utf-8")
    assert "default=59.5" not in kaynak
    assert "default=180.0" in kaynak


def test_180_saniyelik_metin_reddedilmez():
    """180 sn'lik bir diyalog üst sınır kontrolünü GEÇMELİ."""
    from modules.senaryo_v7.ayarlar import Ayarlar

    a = Ayarlar.ortamdan()
    assert 15 <= 175.0 <= a.maksimum_yayin_suresi


def test_kelime_butcesi_200_300_kelimeye_izin_verir():
    """Kullanıcının istediği 200-300 kelimelik anlatım artık MÜMKÜN."""
    from modules.ilginc_bilgi_sozlugu import kelime_butcesi, tahmini_sure

    alt, ust = kelime_butcesi(90)  # 90 sn = "ai_anlatim" profili
    assert alt <= 200 and ust >= 300 or (alt <= 300 and ust >= 200)
    # 200-300 kelime 180 sn sınırının ALTINDA kalmalı (Shorts'ta yayınlanabilir)
    assert tahmini_sure(300) <= 180
    assert tahmini_sure(200) <= 180


def test_kelime_butcesi_sinirlari_asla_asmaz():
    from modules.ilginc_bilgi_sozlugu import SHORTS_MAKS_SN, kelime_butcesi

    _alt, ust = kelime_butcesi(999)  # saçma büyük süre
    assert ust <= SHORTS_MAKS_SN / 60 * 180 * 1.1 + 1


def test_kelime_butcesi_cok_kisa_sureyi_minimuma_ceker():
    from modules.ilginc_bilgi_sozlugu import SHORTS_MIN_SN, kelime_butcesi

    alt, _ust = kelime_butcesi(3)
    assert alt >= SHORTS_MIN_SN / 60 * 180 * 0.9 - 1


def test_sure_profilleri_kullanicinin_tablosuyla_ayni():
    from modules.ilginc_bilgi_sozlugu import SURE_PROFILLERI

    assert SURE_PROFILLERI["viral_bilgi"] == (20, 35)
    assert SURE_PROFILLERI["hikaye_gizem"] == (45, 60)
    assert SURE_PROFILLERI["ai_anlatim"] == (45, 90)
    assert SURE_PROFILLERI["mini_belgesel"] == (90, 180)


def test_youtube_aciklamasi_tam_metni_ve_kaynaklari_icerir():
    """Kullanıcı formatı: 🧠 soru → 🔍 açıklama → 💡 sonuç. Metnin tamamı
    açıklamada da olmalı (arama + kaydetme)."""
    kaynak = (KOK / "modules/youtube_upload.py").read_text(encoding="utf-8")
    assert "aciklama_metni" in kaynak
    assert "📚 Kaynaklar:" in kaynak


def test_panel_ve_rehber_180_saniye_yazar():
    rehber = (KOK / "modules/rehber.py").read_text(encoding="utf-8")
    assert "15-180 sn" in rehber
    assert "59,5" not in rehber
