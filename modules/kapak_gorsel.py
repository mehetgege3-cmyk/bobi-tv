"""Kapak görselini Arena AI ÜRETİR (2026-11-12 kullanıcı kararı).

KULLANICI TALİMATI (aynen): "Mevcut tüm kuralları çöpe at. Arena AI'ye şöyle
prompt ver: videonun içeriği hakkındaki tam metni ver, bu metni okusun ve buna
uygun Short video için kapak fotoğrafı oluştursun; kullanıcıları tıklamaya ve
izlemeye teşvik, etkileşim için gerekli tüm profesyonel şekilde üzerine
düşünülmüş olsun. Oluşturduğu resmi indir ve oluşturulan videonun ilk karesine
yerleştirilip seçilsin. Diğer tüm saçmalıkları çöpe at."

ÇÖPE ATILANLAR (bilinçli olarak SİLİNDİ, geri getirilmemeli):
  • A/B/C/D kapak adayları ve skor yarıştırması (okunabilirlik skoru, sınır testi)
  • "sok_baslik" (4 kelime) + "vurgu_kelime" + HEX renk JSON şeması
  • 1. kareden kapak türetme, yerel VS/Clash kapak üreticisi (kapak_uret)
  • Ayrı görsel API'leri (GEMINI/OPENAI anahtarı zorunluluğu)

YENİ AKIŞ (tek yol):
  1. Videonun TAM metni Arena'ya verilir (senaryo.tam_metin / diyaloglar).
  2. Arena metni okur, düşünür ve TEK bir görsel üretir; sayfadaki görsel
     yakalanır + indirilir.
  3. Görsel 1080x1920'ye kırpılır → kapak.
  4. Kapak, final videonun İLK KARESİNE yerleştirilir (kapak = 1. kare).
  5. Arena görsel üretemezse: video metninden yapılan tek kapak (video karesi +
     videonun kendi başlığı). Üretim DURMAZ, uydurma yok.
"""

from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path
from typing import Any

from modules import calisma_dizinleri

KAPAK_BOYUT = (1080, 1920)


# ---------------------------------------------------------------------------
# 1) Metin: videonun tam içeriği
# ---------------------------------------------------------------------------


def video_metni(paket: dict[str, Any]) -> str:
    """Videonun TAM metnini çıkarır (senaryo tam_metin → diyaloglar → başlık)."""
    senaryo = paket.get("senaryo") or {}
    tam = str(senaryo.get("tam_metin") or "").strip()
    if tam:
        return tam
    # Paket doğrudan `metin` taşıyabilir (kapak hattı ve testler bu yolu kullanır;
    # koşu 43321910940'da metin 21 karakter görünüyordu çünkü bu alan okunmuyordu).
    duz = str(paket.get("metin") or "").strip()
    if duz:
        return duz
    parcalar = [
        str(d.get("metin") or "").strip()
        for d in (senaryo.get("diyaloglar") or [])
        if str(d.get("metin") or "").strip()
    ]
    if parcalar:
        return "\n".join(parcalar)
    # İLGİNÇ BİLGİ BANKASI (2026-11-13, koşu 43375662500'de YAKALANDI):
    # Banka kaydında `senaryo` da `metin` de yok; içerik `soru`+`cevap`+`sonuc`
    # alanlarında. Bu yol olmadığı için video_metni BAŞLIĞA düşüyordu ve kapağa
    # 41 karakterlik başlık gidiyordu — "tam video metni" kuralı ihlal ediliyordu.
    bilgi = "\n\n".join(
        str(paket.get(k) or "").strip()
        for k in ("soru", "cevap", "sonuc")
        if str(paket.get(k) or "").strip()
    ).strip()
    if bilgi:
        return bilgi
    return str(paket.get("baslik") or senaryo.get("baslik") or "").strip()


# ---------------------------------------------------------------------------
# 2) Prompt: metni oku, düşün, tek görsel üret
# ---------------------------------------------------------------------------


def gorsel_promptu(paket: dict[str, Any]) -> str:
    """KULLANICININ BELİRLEDİĞİ TEK İSTEM (2026-11-13).

    Kullanıcı: "Şablonu çöpe at. Sadece benim dediğimi yap."
    Eski 1488 karakterlik 7 kurallı şablon İPTAL; tek kaynak bu cümle.
    """
    baslik = str(
        paket.get("baslik")
        or paket.get("kapak_baslik")
        or (paket.get("senaryo") or {}).get("baslik")
        or ""
    ).strip()
    return (
        f"{baslik} İsimli short video için kapak fotoğrafı istiyorum; etkileşim "
        "ve izlenme rekorları kırması için profesyonel şekilde tasarla. Kapak "
        "fotoğrafını gören merak edip tıklasın."
    )


# ---------------------------------------------------------------------------
# 3) Görseli yakala + indir
# ---------------------------------------------------------------------------


async def _sayfadaki_gorseli_indir(page, hedef: Path) -> Path | None:
    """Sayfada beliren üretilmiş görseli yakalar ve indirir.

    Strateji (sırayla): <img> kaynakları → canvas data URL → arka plan görselleri.
    """
    adaylar: list[str] = []
    try:
        adaylar = await page.evaluate(
            """() => {
                const out = [];
                for (const img of document.querySelectorAll('img')) {
                    const s = img.currentSrc || img.src || '';
                    if (s && (s.startsWith('data:image') || s.includes('blob:') ||
                              /\\.(png|jpe?g|webp)/i.test(s))) out.push(s);
                }
                for (const c of document.querySelectorAll('canvas')) {
                    try { out.push(c.toDataURL('image/png')); } catch (e) {}
                }
                for (const el of document.querySelectorAll('*')) {
                    const bg = getComputedStyle(el).backgroundImage || '';
                    const m = bg.match(/url\\("?([^")]+)"?\\)/);
                    if (m && m[1]) out.push(m[1]);
                }
                return out;
            }"""
        )
    except Exception as e:
        print(f"[Kapak] Sayfa tarama hatası: {str(e)[:100]}")
        return None

    # En büyük/en yeni görseller önce denenir (üretilen görsel genelde sonradır)
    # HTMLImageElement'lerin gerçek bitmap'ini canvas üzerinden data URL'e çevir
    # (Arena görseli blob: URL ile gösterirse requests ile indirilemez; kurtarma yolu)
    try:
        data_url_listesi = await page.evaluate(
            """() => {
                const out = [];
                for (const img of document.querySelectorAll('img')) {
                    const s = img.currentSrc || img.src || '';
                    if (!s.startsWith('blob:') || !img.complete || !img.naturalWidth) continue;
                    try {
                        const c = document.createElement('canvas');
                        c.width = img.naturalWidth; c.height = img.naturalHeight;
                        c.getContext('2d').drawImage(img, 0, 0);
                        out.push(c.toDataURL('image/png'));
                    } catch (e) {}
                }
                return out;
            }"""
        )
        adaylar = (adaylar or []) + list(data_url_listesi or [])
    except Exception:
        pass

    for kaynak in reversed(adaylar or []):
        try:
            if kaynak.startswith("data:image"):
                ham = kaynak.split(",", 1)[1]
                hedef.write_bytes(base64.b64decode(ham))
            elif kaynak.startswith("http") or kaynak.startswith("blob:"):
                if kaynak.startswith("blob:"):
                    continue
                import requests

                r = requests.get(kaynak, timeout=60)
                if r.status_code != 200 or len(r.content) < 20000:
                    continue
                hedef.write_bytes(r.content)
            else:
                continue
            if hedef.exists() and hedef.stat().st_size > 20000 and _gorsel_yeterli(hedef):
                return hedef
        except Exception:
            continue
    return None


def _gorsel_yeterli(yol: Path) -> bool:
    """Yakalanan görsel gerçekten kapak mı? (min 400x400 — logo/ikon/avatar değil)"""
    try:
        from PIL import Image

        with Image.open(yol) as img:
            return img.width >= 400 and img.height >= 400
    except Exception:
        return False

def gorseli_karesine_oturt(ham: Path, hedef: Path) -> Path | None:
    """Görseli 1080x1920'ye kırpar (Shorts kapağı)."""
    try:
        from PIL import Image

        img = Image.open(ham).convert("RGB")
        oran = max(KAPAK_BOYUT[0] / img.width, KAPAK_BOYUT[1] / img.height)
        img = img.resize((int(img.width * oran) + 1, int(img.height * oran) + 1))
        sol = (img.width - KAPAK_BOYUT[0]) // 2
        ust = (img.height - KAPAK_BOYUT[1]) // 2
        img = img.crop((sol, ust, sol + KAPAK_BOYUT[0], ust + KAPAK_BOYUT[1]))
        hedef.parent.mkdir(parents=True, exist_ok=True)
        img.save(hedef, "JPEG", quality=94, optimize=True)
        return hedef if hedef.exists() else None
    except Exception as e:
        print(f"[Kapak] Kırpma hatası: {str(e)[:120]}")
        return None
