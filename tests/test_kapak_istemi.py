"""KAPAK İSTEMİ KİLİDİ — isteme ekleme yapılmasını engeller.

KULLANICI TALİMATI (2026-11-13):
  "ornek_kapak_istemi.txt bunu çöpe at. Şablonu çöpe at. Sadece benim dediğimi
   yap. 'Video başlığı + İsimli short video için kapak fotoğrafı istiyorum
   etkileşim ve izlenme rekorları kırması için profesyonel şekilde tasarla kapak
   fotoğrafını gören merak edip tıklasın.' Tüm kapak fotoğrafları için bunu kullan."

NİÇİN TEST: Bir kez isteme kendi kuralımı ekledim ("Yazı yazma, sadece görsel
olsun") ve kapak yazısız çıktı. Kullanıcı bunu istememişti. Bu test o hatanın
tekrarını imkânsız kılar.
"""
from __future__ import annotations

import pytest

from modules.yeni_motor.motor import kapak_istemini_yaz

BASLIK = "Su İçerken Hiç Düşündün mü?"

#: Kullanıcının cümlesi — BİREBİR. Değiştirme.
BEKLENEN = (
    "Su İçerken Hiç Düşündün mü? İsimli short video için kapak fotoğrafı "
    "istiyorum etkileşim ve izlenme rekorları kırması için profesyonel şekilde "
    "tasarla kapak fotoğrafını gören merak edip tıklasın."
)


def test_istem_birebir_kullanicinin_cumlesi() -> None:
    assert kapak_istemini_yaz(BASLIK) == BEKLENEN


def test_baslik_yerine_konuyor() -> None:
    cikti = kapak_istemini_yaz("Başka Bir Başlık")
    assert cikti.startswith("Başka Bir Başlık İsimli short video için")
    assert BASLIK not in cikti


@pytest.mark.parametrize(
    "yasak",
    [
        "yazı yaz",          # kapakta yazı isteme (kullanıcı istemedi)
        "Yazı yazma",        # kapakta yazı YASAKLAMA (benim eklediğim hatalı kural)
        "16:9",              # oran istemde değil; teknik dönüşüm ayrı yapılır
        "1280",              # çözünürlük istemde değil
        "yatay",             # yön istemde değil
        "dikey",
        "fotogerçekçi",
        "sinematik",
        "stil",
        "piksel",
        "manşet",
        "sadece görsel",
    ],
)
def test_isteme_ek_kural_eklenmemis(yasak: str) -> None:
    """İstemde kullanıcının cümlesi DIŞINDA hiçbir talimat olmamalı."""
    cikti = kapak_istemini_yaz(BASLIK).lower()
    assert yasak.lower() not in cikti, (
        f"istemde '{yasak}' var — kullanıcı sadece kendi cümlesini istedi"
    )


def test_istem_tek_cumle_uzunlugunda() -> None:
    """Anlamlı ölçü: kullanıcının cümlesi ~200 karakter, ekleme yapılırsa büyür."""
    uzunluk = len(kapak_istemini_yaz(BASLIK))
    assert uzunluk < 250, f"istem {uzunluk} karakter — ekleme yapılmış olabilir"
