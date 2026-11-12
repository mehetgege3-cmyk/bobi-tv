"""Arena diyaloğu → `senaryo_paketi` sözleşmesi (video hattı değişmeden çalışır).

AKIŞ
  1. Kategori seç (tekrarsız rastgele)      → `kategoriler.siradaki_kategori`
  2. Etkileşim taktiği seç (rotasyon)        → `etkilesim.taktik_sec`
  3. Arena'ya TEK istek at (soru+cevap+sonuç JSON) → `arena_bilgi_uret`
     Arena çökerse → `yedek_bilgiler.bilgi_sec` (doğrulanmış banka)
  4. 12 kuralı denetle                       → `kurallar.denetle`
  5. Reddedilirse 1 kez onarım isteği, sonra bankaya düş
  6. Metni 3 bölümlü diyaloglara çevir → `tts_engine` + `video_render` uyumlu

TASARIM KARARI — neden tek anlatıcı: eski format iki karakterin VS
düellosuydu ve kullanıcı bunu çöpe attı. Yeni format bilgi anlatımı; ses
tek (BOBİ). Video hattı `ses_dosyalari`/`diyaloglar` beklediği için her bölüm
bir "diyalog" satırına dönüşür — ama render tarafında tek karakter görünür.

SES/PAYLAŞIM
  180 sn üst sınır, 15 sn alt sınır (YouTube Shorts 2026). 220-260 kelime
  ~75-90 sn → güvenli aralık.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from modules.ilginc_bilgi import etkilesim, kategoriler, kurallar, yedek_bilgiler
from modules.ilginc_bilgi.dogruluk import arena_dogruluk_talimati

KARAKTER = "BOBİ"
STATE = Path("bobi_tv/state/ilginc_bilgi_gecmisi.json")

#: Bölüm başına konuşma hızı (kelime/dk) — 180 sn'lik sınırı aşmamak için.
KONUSMA_KELIME_DK = int(os.environ.get("KONUSMA_KELIME_DK", "180") or 180)


# ---------------------------------------------------------------------------
# Durum (geçmiş konular + seçilen kategoriler + yedek banka kullanımı)
# ---------------------------------------------------------------------------


def durum_yukle(yol: Path | None = None) -> dict:
    hedef = yol or STATE
    try:
        veri = json.loads(hedef.read_text(encoding="utf-8"))
        if isinstance(veri, dict):
            veri.setdefault("videolar", [])
            veri.setdefault("kullanilan_yedekler", [])
            return veri
    except Exception:
        pass
    return {"sur": 1, "videolar": [], "kullanilan_yedekler": []}


def durum_yaz(veri: dict, yol: Path | None = None) -> None:
    hedef = yol or STATE
    try:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:  # pragma: no cover
        print(f"[İlginçBilgi] Durum yazılamadı: {str(e)[:100]}")


# ---------------------------------------------------------------------------
# Arena diyaloğu
# ---------------------------------------------------------------------------


def arena_promptu(kategori: str, taktik: etkilesim.TaktikSecimi, kacirilacaklar: list[str]) -> str:
    """Arena'ya giden TEK istek. Çıktı katı JSON'dur."""
    kat = kategoriler.kategori_al(kategori)
    kacin = "; ".join(kacirilacaklar[-12:]) or "(yok)"
    return (
        'SADECE şu JSON ile cevap ver (şablonu tekrar yazma, doldur): '
        '{"soru":"...","cevap":"...","sonuc":"...","baslik":"...",'
        '"kaynak":"...","sayilar":["..."],"dogru_bilgi":"...","kapak_baslik":"..."}\n\n'
        "Sen BOBİ TV için Türkçe kısa bilgi videoları yazan bir editörsün. "
        "YouTube Shorts için 'ilginç bilgi' içeriği üretiyorsun. Aşağıdaki "
        "kategori ve taktiğe uy.\n\n"
        f"KATEGORİ: {kat['ad']} {kat['emoji']}\n"
        f"ÖRNEK KONU ALANLARI: {', '.join(kat['ornek_konular'])}\n\n"
        f"ETKİLEŞİM TAKTİĞİ: {taktik.kod} — {taktik.ad}\n{taktik.talimat}\n\n"
        f"{arena_dogruluk_talimati()}\n\n"
        "YAZIM KURALLARI:\n"
        f"1) 'cevap' alanı {kurallar.KELIME_MIN}-{kurallar.KELIME_MAKS} KELİME olmalı "
        "(ne az ne çok).\n"
        "2) 'soru' merak uyandıran, tek cümlelik bir soru; cevabı içermez.\n"
        "3) 'cevap' sohbet tonunda, 'sen' diliyle, sade Türkçe. İçinde günlük "
        "hayattan somut bir örnek/karşılaştırma olsun.\n"
        "4) 'sonuc' 1-2 cümlelik şaşırtıcı kapanış; cevabı özetler.\n"
        "5) 'baslik' en fazla 70 karakter, merak uyandıran, TÜMÜ BÜYÜK HARF DEĞİL, "
        "sonunda '#shorts' yok.\n"
        "6) 'kaynak' gerçek bir kurum/kitap/dergi adı (NASA, Britannica, Nature, "
        "WHO, National Geographic...). Uydurma.\n"
        "7) 'sayilar' cevapta geçen tüm sayıların listesi (metin olarak).\n"
        "8) 'dogru_bilgi' cevabın 1-2 cümlelik ÖZETİ (yorum cevaplarında "
        "kullanılacak; kesin ve doğru olmalı).\n"
        "9) 'kapak_baslik' en fazla 34 karakter, kapakta kullanılacak çarpıcı ifade.\n"
        f"10) Şu konulara YAKLAŞMA (daha önce yapıldı): {kacin}\n"
        "11) TAMAMEN TÜRKÇE. İngilizce kelime yok.\n"
        "12) Emoji kullan ama abartma (2-5 arası).\n"
        "13) JSON dışında HİÇBİR ŞEY yazma; şablonu yankılama.\n"
        "14) 'cevap' alanında bölüm başlığı (🧠/🔍/💡) KULLANMA; sadece metin yaz."
    )


#: Arena, prompt'un sonundaki JSON şablonunu "cevap" diye yankılayabiliyor
#: (canlı koşu 43111414945: 883 karakterlik yankı → içerik hiç üretilmedi).
SABLON_ISARETLERI = ('"soru": "..."', '"cevap": "..."', '"kapak_baslik": "..."')


def sablon_yankisi_mi(metin: str) -> bool:
    """Dönen metin, gönderdiğimiz JSON şablonunun yankısı mı?"""
    t = str(metin or "")
    if any(isaret in t for isaret in SABLON_ISARETLERI):
        return True
    return t.count('"..."') >= 3


def _sablon_izini_sil(metin: str) -> str:
    """Arena'nın yankıladığı JSON şablonunu baştan keser.

    CANLI KANIT (koşu 43138461248, 2026-11-12 02:06): Arena 3193 karakter
    döndürdü; ilk ~1000 karakter bizim gönderdiğimiz JSON şablonunun yankısı,
    GERÇEK cevap hemen ARDINDAN geliyordu. Yankıyı görüp tümden reddetmek
    içeriği çöpe atıyordu (her seferinde yedek bankaya düşüyordu).
    Artık: son şablon kapanışından sonrası = gerçek cevap.
    """
    t = str(metin or "")
    if not sablon_yankisi_mi(t):
        return t
    for kapanis in ('"kapak_baslik": "..."}', '"kapak_baslik":"..."}'):
        i = t.rfind(kapanis)
        if i != -1:
            return t[i + len(kapanis):].strip()
    i = t.rfind('"..."}')
    if i != -1:
        return t[i + len('"..."}'):].strip()
    return t


def _prompt_kuyrugunu_sil(metin: str) -> str:
    """Şablon yankısından SONRA gelen prompt gövdesini de keser."""
    t = str(metin or "")
    for iz in (
        "Sen BOBİ TV için Türkçe kısa bilgi",
        "KATEGORİ: ",
        "YAZIM KURALLARI:",
        "Respond in Turkish",
        "Simple question.",
    ):
        i = t.rfind(iz)
        if i != -1 and i < len(t) - len(iz):
            t = t[i + len(iz):]
    return t


def _json_ayikla(metin: str) -> dict | None:
    """Arena cevabından JSON nesnesini çıkarır (kod bloğu/ön söz toleranslı)."""
    metin = _prompt_kuyrugunu_sil(_sablon_izini_sil(metin)).strip()
    if not metin or sablon_yankisi_mi(metin):
        return None
    adaylar = re.findall(r"\{.*\}", metin, re.DOTALL)
    for aday in reversed(adaylar):
        try:
            veri = json.loads(aday)
            if isinstance(veri, dict) and veri.get("cevap"):
                return veri
        except Exception:
            continue
    return None


def arena_bilgi_uret(
    kategori: str,
    taktik: etkilesim.TaktikSecimi,
    kacirilacaklar: list[str],
    arena_fn=None,
) -> dict | None:
    """Arena'dan bilgi kartı ister. Erişilemezse None (çağıran bankaya düşer)."""
    if arena_fn is None:
        try:
            from modules.arena_api import arena_kisa_cevap_al as arena_fn  # type: ignore
        except Exception:
            return None
    prompt = arena_promptu(kategori, taktik, kacirilacaklar)
    try:
        ham = arena_fn(prompt)
    except Exception as e:
        print(f"[İlginçBilgi] Arena hatası: {str(e)[:120]}")
        return None
    # Teşhis: Arena'nın ne döndürdüğü logda görünsün (yankı mı, gerçek cevap mı)
    if ham:
        _t = str(ham).strip()
        print(f"[İlginçBilgi] Arena ham cevap {len(_t)} karakter | baş: {_t[:90]!r} | son: {_t[-90:]!r}")
    kart = _json_ayikla(ham or "")
    if not kart:
        # Arena JSON yerine düz metin döndürdüyse metni yine de kullan:
        # başlıklardan ayrıştır, yoksa tek parça cevap say (boşa üretim yapma).
        kart = _duz_metinden_kart(ham or "")
        if kart:
            print("[İlginçBilgi] Arena düz metin döndürdü — başlıklardan ayrıştırıldı")
        else:
            print("[İlginçBilgi] Arena cevabı kullanılabilir değil — bankaya düşülecek")
            return None
    return kart


def _duz_metinden_kart(metin: str) -> dict | None:
    """JSON olmayan Arena cevabını bilgi kartına çevirir (başlık tabanlı)."""
    metin = _prompt_kuyrugunu_sil(_sablon_izini_sil(metin)).strip()
    # Soru cevabın başında yoksa sonda/kapak ifadesinde aranır; yoksa uydurma
    # soru yazmak yerine reddedilir (YouTube deceptive practices riski).
    if len(metin) < 120 or sablon_yankisi_mi(metin) or "?" not in metin:
        return None
    bolumler = kurallar.bolumleri_ayir(metin)
    cevap = bolumler.get(kurallar.BASLIK_CEVAP, "").strip()
    soru = bolumler.get(kurallar.BASLIK_SORU, "").strip()
    sonuc = bolumler.get(kurallar.BASLIK_SONUC, "").strip()
    if not cevap:
        # Başlık yoksa: ilk satır soru, kalanı cevap
        satirlar = [x for x in metin.split("\n") if x.strip()]
        if len(satirlar) < 2:
            return None
        soru, cevap, sonuc = satirlar[0], "\n".join(satirlar[1:]), ""
    return {
        "soru": re.sub(r"^[#*\s🧠🔍💡]+", "", soru)[:200],
        "cevap": cevap,
        "sonuc": re.sub(r"^[#*\s🧠🔍💡]+", "", sonuc)[:300] or cevap.split(".")[-2].strip() + ".",
        "baslik": re.sub(r"^[#*\s🧠🔍💡]+", "", soru)[:70] or "İlginç Bilgi",
        "kaynak": "Arena AI içerik üretimi (kaynak alanı model tarafından doldurulmadı)",
        "sayilar": re.findall(r"\d+", cevap)[:10],
        "dogru_bilgi": cevap.split(".")[0].strip() + ".",
        "kapak_baslik": "",
    }


def _baslik_temizle(metin: str) -> str:
    """Başlık alanına bölüm emojileri/başlıkları sızmasın + 70 karakter sınırı."""
    t = str(metin or "").strip()
    for baslik in kurallar.ZORUNLU_BASLIKLAR:
        t = t.replace(baslik, "")
    t = re.sub(r"^[#*\s\-–—•·:]+", "", t)
    t = " ".join(t.split())
    return t[:70].strip()


def metne_cevir(kart: dict) -> str:
    """Bilgi kartını zorunlu formata (🧠 / 🔍 / 💡) çevirir."""
    return (
        f"{kurallar.BASLIK_SORU}\n{str(kart.get('soru', '')).strip()}\n\n"
        f"{kurallar.BASLIK_CEVAP}\n{str(kart.get('cevap', '')).strip()}\n\n"
        f"{kurallar.BASLIK_SONUC}\n{str(kart.get('sonuc', '')).strip()}"
    )


# ---------------------------------------------------------------------------
# Senaryo paketi (video hattı sözleşmesi)
# ---------------------------------------------------------------------------


def kapak_basligi(baslik: str, azami: int = 34) -> str:
    """Kapak başlığını TAM KELİME sınırında kısaltır.

    Neden: `baslik[:34]` gibi bir kesme "…BİRİ Y!" gibi anlamsız kırıntı
    üretiyordu (amatör görünüm). Uzunsa son kelime atılır ve '…' eklenir.
    """
    metin = str(baslik or "").strip()
    for ek in (" #shorts", "#shorts"):
        metin = metin.replace(ek, "")
    temiz = " ".join(metin.split())
    if len(temiz) <= azami:
        return temiz
    kelimeler = temiz.split()
    kisa = ""
    for kelime in kelimeler:
        aday = (kisa + " " + kelime).strip()
        if len(aday) > azami - 1:
            break
        kisa = aday
    return (kisa or kelimeler[0]) + "…"


def _slug(metin: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(metin or "").translate(tr)).strip("_").lower()
    return (s[:40] or "ilginc_bilgi")


def _govde_paylastir(cevap: str, parca: int = 5) -> list[str]:
    """Uzun cevabı paragraflara böler; yoksa cümle gruplarına ayırır."""
    cevap = str(cevap or "").strip()
    paragraflar = [p.strip() for p in re.split(r"\n\s*\n", cevap) if p.strip()]
    if len(paragraflar) >= parca:
        # Eşit uzunlukta `parca` gruba indir
        boyut = (len(paragraflar) + parca - 1) // parca
        return ["\n".join(paragraflar[i:i + boyut]) for i in range(0, len(paragraflar), boyut)][:parca]
    cumleler = [c.strip() for c in re.split(r"(?<=[.!?…])\s+", cevap) if c.strip()]
    # Kısa cümleler ekranda daha iyi okunur: parça başına en çok 2 cümle,
    # ama parça sayısı hedefini de tut (kelime yoğun cümlelerde 1'e düş).
    boyut = max(1, min(2, (len(cumleler) + parca - 1) // parca))
    gruplar = [" ".join(cumleler[i:i + boyut]) for i in range(0, len(cumleler), boyut)]
    return gruplar[:parca] or [cevap]


def _bloklar(kart: dict) -> list[tuple[str, str, str, str, int]]:
    """(rol, konuşma_metni, ekran_başlığı, kısa_etiket, duraklama_ms) — 3 bölüm.

    ÖNEMLİ: TTS'e giden metin (**konuşma_metni**) asla bölüm başlığını
    içermez. "🧠 Günün Merak Uyandıran Sorusu" ekranda görünür, sesli
    okunmaz — aksi hâlde video robotik olur ve 3 parçada aynı cümle 3 kez
    söylenir (eski hatanın tekrarı olurdu).
    """
    soru = str(kart.get("soru", "")).strip()
    cevap = str(kart.get("cevap", "")).strip()
    sonuc = str(kart.get("sonuc", "")).strip()
    bloklar: list[tuple[str, str, str, str, int]] = [
        ("hook", soru + " 🤔", kurallar.BASLIK_SORU, "SORU", 450),
    ]
    # Parça sayısı kelime sayısına göre: balon ekranı taşmasın, metin
    # kırpılmasın (canlı testte "Tarihi te…" kırpılması görüldü).
    # Hedef: parça başına ~30 kelime (≈7 satır).
    kelime = kurallar.kelime_say(cevap)
    parca_sayisi = max(4, min(9, round(kelime / 30)))
    parcalar = _govde_paylastir(cevap, parca_sayisi)
    for parca in parcalar:
        bloklar.append(("govde", parca, kurallar.BASLIK_CEVAP, "CEVAP", 220))
    bloklar.append(("sonuc", sonuc, kurallar.BASLIK_SONUC, "SONUÇ", 0))
    return bloklar


def paket_olustur(
    kart: dict,
    kategori: str,
    taktik: etkilesim.TaktikSecimi,
    video_no: int = 1,
    *,
    kaynak_turu: str = "arena",
) -> dict:
    """Bilgi kartından `senaryo_paketi` üretir (video hattı bu sözleşmeyi bekler)."""
    anahtar = str(kart.get("anahtar") or _slug(kart.get("soru", ""))[:24])
    zaman = datetime.now(UTC)
    dosya_adi = f"{zaman.strftime('%Y%m%d_%H%M')}_{video_no:04d}_{_slug(anahtar)}"
    bloklar = _bloklar(kart)

    diyaloglar = []
    for sira, (rol, metin, ekran_basligi, etiket, duraklama) in enumerate(bloklar):
        diyaloglar.append(
            {
                "karakter": KARAKTER,
                "metin": metin,
                "ekran_basligi": ekran_basligi,
                "cinsiyet": "erkek",
                "ses": "vurgu" if rol == "sonuc" else "normal",
                "sfx": "vine_boom" if rol == "sonuc" else ("whoosh" if rol == "hook" else "pop"),
                "karakter_ref": "karakter_bobi",
                "hiz": 1.02,
                "duraklamams": int(duraklama),
                "vurgukelimeler": [],
                "altyazistili": "buyuk" if rol == "hook" else "normal",
                "kamera": "zoom_in" if rol == "hook" else "cut",
                "emojioverlay": kategoriler.kategori_emojisi(kategori) if sira == 0 else None,
                "rol": rol,
                "twist": rol == "sonuc",
                "etiket": etiket,
            }
        )

    toplam_kelime = kurallar.kelime_say(kart.get("cevap", "")) + kurallar.kelime_say(
        kart.get("soru", "")
    ) + kurallar.kelime_say(kart.get("sonuc", ""))
    tahmini_sure = round(toplam_kelime / max(1, KONUSMA_KELIME_DK) * 60, 1)

    baslik = _baslik_temizle(kart.get("baslik") or kart.get("soru") or "İlginç Bilgi")
    return {
        "video_no": video_no,
        "dosya_adi": dosya_adi,
        "baslik": f"{baslik} #shorts"[:100],
        "aciklama": (
            f"{str(kart.get('dogru_bilgi') or kart.get('sonuc') or '')[:180]}\n\n"
            f"📚 Kaynak: {kart.get('kaynak', '')}"
        ).strip(),
        "senaryo": {
            "semaversiyonu": "8.0-ilginc",
            "kategori": kategori,
            "ortam_etiketi": kategoriler.kategori_adi(kategori),
            "ruh_hali": "bilgi",
            "hook_metni": str(kart.get("soru", ""))[:80],
            "hook_ust_bant": kapak_basligi(str(kart.get("kapak_baslik") or kart.get("soru") or ""), 40),
            "hook_suresi": 3.0,
            "diyaloglar": diyaloglar,
            "karakterler": [{"ad": KARAKTER, "cinsiyet": "erkek", "ref": "karakter_bobi"}],
            "toplam_sure": tahmini_sure,
            "baslik": f"{baslik} #shorts"[:100],
            # --- yeni alanlar (yorum cevap + ölçüm + kapak için) ---
            "soru": str(kart.get("soru", "")),
            "dogru_bilgi": str(kart.get("dogru_bilgi") or kart.get("sonuc") or ""),
            "kaynak": str(kart.get("kaynak", "")),
            "sayilar": list(kart.get("sayilar") or []),
            "kapak_baslik": kapak_basligi(str(kart.get("kapak_baslik") or kart.get("baslik") or "")),
            "taktik": taktik.kod,
            "taktik_adi": taktik.ad,
            "icerik_kaynagi": kaynak_turu,
            "tam_metin": metne_cevir(kart),
            "kelime_sayisi": kurallar.kelime_say(kart.get("cevap", "")),
            "format": "🧠/🔍/💡",
        },
        "kaynak": kaynak_turu,
        "olusturuldu": zaman.isoformat(),
        "hash": hashlib.md5(
            str(kart.get("cevap", ""))[:200].encode(), usedforsecurity=False
        ).hexdigest(),
        "semaversiyonu": "8.0-ilginc",
    }


# ---------------------------------------------------------------------------
# Tam akış
# ---------------------------------------------------------------------------


def uret(
    video_no: int,
    *,
    arena_fn=None,
    state_yolu: Path | None = None,
    yayin_sayisi: int | None = None,
    zorla_kategori: str | None = None,
    zorla_taktik: str | None = None,
    kuru_calisma: bool = False,
) -> dict:
    """Tam içerik üretimi: kategori → taktik → Arena → denetim → senaryo paketi.

    Döner: {"paket": ..., "rapor": ..., "kategori": ..., "taktik": ...,
            "kaynak_turu": "arena"|"yedek", "uyarilar": [...]}
    Hiçbir koşulda exception fırlatmaz; her yol kayıtlıdır.
    """
    durum = durum_yukle(state_yolu)
    gecmis = durum.get("videolar") or []
    son_kategoriler = [str(v.get("kategori")) for v in reversed(gecmis[-8:])]
    onceki_metinler = [str(v.get("cevap_ozeti") or "") for v in gecmis[-30:]]
    kacirilacaklar = [str(v.get("konu") or "") for v in gecmis[-12:]]
    uyarilar: list[str] = []

    kategori = zorla_kategori or kategoriler.siradaki_kategori(son_kategoriler, video_no=video_no)
    if yayin_sayisi is None:
        yayin_sayisi = len(gecmis)

    if zorla_taktik:
        taktik = etkilesim.TaktikSecimi(
            kod=zorla_taktik,
            ad=etkilesim.TAKTIKLER.get(zorla_taktik, "?"),
            talimat=etkilesim.TALIMATLAR.get(zorla_taktik, ""),
        )
    else:
        taktik = etkilesim.taktik_sec(video_no, kategori, yayin_sayisi, state_yolu)
    uyarilar.extend(taktik.uyarilar)

    # 1) Arena
    kart = arena_bilgi_uret(kategori, taktik, kacirilacaklar, arena_fn=arena_fn)
    kaynak_turu = "arena"

    # 2) Arena yoksa doğrulanmış banka
    if not kart:
        bilgi = yedek_bilgiler.bilgi_sec(kategori, durum.get("kullanilan_yedekler"))
        if bilgi:
            kart = {
                "anahtar": bilgi["anahtar"],
                "soru": bilgi["soru"],
                "cevap": bilgi["cevap"],
                "sonuc": bilgi["sonuc"],
                "baslik": bilgi["baslik"],
                "kaynak": bilgi["kaynak"],
                "sayilar": bilgi["sayilar"],
                "dogru_bilgi": bilgi["sonuc"],
                "kapak_baslik": bilgi["baslik"][:34],
            }
            kaynak_turu = "yedek"
            if bilgi["anahtar"] in (durum.get("kullanilan_yedekler") or []):
                uyarilar.append(
                    f"banka havuzu boşaldı → en eski kayıt yeniden kullanıldı: {bilgi['anahtar']}"
                )
            else:
                uyarilar.append(f"Arena yok → doğrulanmış bankadan: {bilgi['anahtar']}")
            if bilgi["kategori"] != kategori:
                uyarilar.append(
                    f"banka '{kategori}' için boş → '{bilgi['kategori']}' bilgisi kullanıldı"
                )
        else:
            raise RuntimeError(
                "İçerik üretilemedi: Arena erişilemedi ve yedek banka tükendi "
                "(uydurma bilgi yazmak yerine tur durduruldu)."
            )

    # 3) Kalite denetimi (12 kural + doğruluk)
    metin = metne_cevir(kart)
    rapor = kurallar.denetle(
        metin,
        kaynak=str(kart.get("kaynak", "")),
        sayilar=kart.get("sayilar") or [],
        kategori=kategori,
        son_kategoriler=son_kategoriler,
        onceki_metinler=onceki_metinler,
        curutme_icerigi=taktik.kod == "T1",
    )

    # 4) Reddedilirse tek onarım denemesi
    if not rapor.yayinlanabilir and kaynak_turu == "arena":
        uyarilar.append(f"1. deneme reddedildi: {rapor.ozet()[:180]} → onarım isteniyor")
        kart2 = arena_bilgi_uret(kategori, taktik, kacirilacaklar, arena_fn=arena_fn)
        if kart2:
            metin2 = metne_cevir(kart2)
            rapor2 = kurallar.denetle(
                metin2,
                kaynak=str(kart2.get("kaynak", "")),
                sayilar=kart2.get("sayilar") or [],
                kategori=kategori,
                son_kategoriler=son_kategoriler,
                onceki_metinler=onceki_metinler,
                curutme_icerigi=taktik.kod == "T1",
            )
            if rapor2.skor >= rapor.skor:
                kart, metin, rapor = kart2, metin2, rapor2
                uyarilar.append(f"onarım denemesi kullanıldı (skor {rapor2.skor})")

    # 5) Hâlâ reddediliyorsa bankaya düş (yayınlanamaz içerik yayına gitmez)
    if not rapor.yayinlanabilir:
        bilgi = yedek_bilgiler.bilgi_sec(kategori, durum.get("kullanilan_yedekler") + [
            str(kart.get("anahtar") or "")
        ])
        if bilgi:
            kart = {
                "anahtar": bilgi["anahtar"], "soru": bilgi["soru"], "cevap": bilgi["cevap"],
                "sonuc": bilgi["sonuc"], "baslik": bilgi["baslik"], "kaynak": bilgi["kaynak"],
                "sayilar": bilgi["sayilar"], "dogru_bilgi": bilgi["sonuc"],
                "kapak_baslik": bilgi["baslik"][:34],
            }
            metin = metne_cevir(kart)
            rapor = kurallar.denetle(
                metin, kaynak=bilgi["kaynak"], sayilar=bilgi["sayilar"],
                kategori=kategori, son_kategoriler=[], onceki_metinler=[],
            )
            kaynak_turu = "yedek"
            uyarilar.append(f"Arena içeriği kalite kapısından geçemedi → banka: {bilgi['anahtar']}")
        else:
            raise RuntimeError(
                f"İçerik kalite kapısından geçemedi ve banka tükendi: {rapor.ozet()[:200]}"
            )

    paket = paket_olustur(kart, kategori, taktik, video_no, kaynak_turu=kaynak_turu)

    # 6) Geçmişe yaz (rotasyon + yorum cevapları + tekrar kontrolü)
    if not kuru_calisma:
        durum["videolar"].append(
            {
                "video_no": video_no,
                "kategori": kategori,
                "taktik": taktik.kod,
                "anahtar": kart.get("anahtar") or _slug(kart.get("soru", ""))[:24],
                "konu": str(kart.get("baslik") or "")[:80],
                "cevap_ozeti": str(kart.get("cevap") or "")[:400],
                "skor": rapor.skor,
                "tarih": datetime.now(UTC).isoformat(),
            }
        )
        durum["videolar"] = durum["videolar"][-500:]
        if kaynak_turu == "yedek" and kart.get("anahtar"):
            durum["kullanilan_yedekler"].append(str(kart["anahtar"]))
        durum_yaz(durum, state_yolu)
        # Etkileşim geçmişi, içerik geçmişiyle AYNI klasöre yazılır; böylece
        # testler/önizleme çalışmaları üretim durum dosyasını kirletmez.
        etkilesim_yolu = (
            (state_yolu.parent / "etkilesim_gecmisi.json") if state_yolu else None
        )
        etkilesim.kaydet(
            video_no, taktik.kod, kategori, datetime.now(UTC).isoformat(), etkilesim_yolu
        )

    return {
        "paket": paket,
        "rapor": rapor,
        "kategori": kategori,
        "taktik": taktik.kod,
        "kaynak_turu": kaynak_turu,
        "uyarilar": uyarilar,
    }
