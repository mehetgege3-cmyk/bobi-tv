"""Konu üret — kullanıcının verdiği prompt, BİREBİR.

KULLANICI TALİMATI (2026-11-08): "bu promtu vericeksin" — metne hiçbir kural,
kısıtlama veya açıklama EKLENMEZ.

TEK İSTİSNA (promptun kendisi istiyor): prompt "Daha önce verdiğim konu
listesindekileri tekrar etme" diyor. Liste prompt metnine ekleniyor, çünkü
aksi hâlde kural boşta kalır. Başka hiçbir ekleme yok.

ÇIKTI (promptun istediği format):
    SESLENDİRME METNİ: ...
    BAŞLIK: ...
    AÇIKLAMA: ...
    HASHTAG: ...
    KONU: ...
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: Kullanıcının verdiği prompt — BİREBİR (2026-11-08).
PROMPT = """Sen YouTube Shorts için viral genel kültür metinleri yazan bir metin yazarısın. Yazdığın metin doğrudan yapay zeka sesiyle seslendirilip videoya çevrilecek. Her çalıştırmada 1 adet metin üret.

KONU: Şu kategorilerden rastgele birini seç: Bilim, Tarih, Doğa, Hayvanlar, İnsan vücudu, Yemek, Kültür, Günlük yaşam. Az bilinen, "yok artık" dedirten, doğruluğu kesin bir konu seç. Daha önce verdiğim konu listesindekileri tekrar etme.

METİN KURALLARI:

1. İlk cümle kanca olsun, en fazla 12 kelime. Selamlama ve giriş yasak. Şu türlerden birini kullan: yanlış bilinen bir şeyi yıkma, şok edici rakam, imkansız gibi duran soru, "Bunu herkes yanlış biliyor" iddiası.

2. İlk cümlede cevabı verme. Cevabı en sona doğru açıkla. Ortada "Ama asıl ilginç kısım şimdi geliyor" tarzı bir geçişle merakı canlı tut.

3. Her 3-4 cümlede yeni bir şaşırtıcı detay veya mini sürpriz ekle.

4. Mutlaka bir neden-sonuç ilişkisi ve günlük hayattan bir benzetme olsun.

5. Konuşma dilinde yaz. Cümleler kısa olsun, en fazla 12 kelime. Okunurken akıcı olsun.

6. Toplam 120-140 kelime (yaklaşık 45-50 saniye).

7. Bilgiler doğru olsun. Emin olmadığın rakam ve iddiayı yazma, uydurma istatistik yasak.

8. Son cümle ilk cümleye geri bağlansın (döngü etkisi). Hemen ardına konuyla ilgili, A mı B mi tarzı kolay cevaplanır tek bir yorum sorusu ekle.

ÇIKTI FORMATI (başka hiçbir şey yazma, açıklama ve not ekleme):

SESLENDİRME METNİ:

(sadece okunacak düz metin, başlık, parantez, emoji, saniye bilgisi yok)

BAŞLIK:

(en fazla 60 karakter, merak uyandıran, cevabı vermeyen)

AÇIKLAMA:

(1 cümle merak cümlesi + konuya özel yorum sorusu + "Bunu bilmeyen bir arkadaşını etiketle!")

HASHTAG:

(5 adet)

KONU:

(kategori ve konu, tek satır; bunu ben sonraki çalıştırmada yasaklı listeye ekleyeceğim)"""

#: İşlenmiş konular — promptun "tekrar etme" kuralı için.
KONULAR = (Path(__file__).resolve().parent.parent
           / "bobi_tv" / "state" / "konular.json")


def gecmis_konular() -> list[str]:
    try:
        veri = json.loads(KONULAR.read_text(encoding="utf-8"))
        return [str(k) for k in (veri if isinstance(veri, list) else [])]
    except Exception:
        return []


def konu_kaydet(konu: str) -> None:
    if not konu:
        return
    liste = gecmis_konular()
    if konu not in liste:
        liste.append(konu)
        KONULAR.parent.mkdir(parents=True, exist_ok=True)
        KONULAR.write_text(json.dumps(liste, ensure_ascii=False, indent=1),
                           encoding="utf-8")


def istem_yaz() -> str:
    """Prompt + daha önce işlenen konu listesi (promptun kendi şartı)."""
    gecmis = gecmis_konular()
    if not gecmis:
        return PROMPT
    return PROMPT + "\n\nDAHA ÖNCE İŞLENEN KONULAR:\n" + "\n".join(
        f"- {k}" for k in gecmis[-100:])


def _bolum(metin: str, baslik: str) -> str:
    """`BAŞLIK:` ile bir sonraki bölüm başlığı arasındaki değeri alır."""
    kalip = rf"{baslik}\s*:?\s*\n?(.*?)(?=\n\s*(?:SESLENDİRME METNİ|BAŞLIK|AÇIKLAMA|HASHTAG|KONU)\s*:|\Z)"
    m = re.search(kalip, metin, re.S | re.I)
    return m.group(1).strip() if m else ""


def ayikla(metin: str) -> dict | None:
    """Promptun istediği formattan alanları çıkarır."""
    if not metin or "SESLENDİRME" not in metin.upper():
        return None
    ses = _bolum(metin, "SESLENDİRME METNİ")
    # Yalnız okunacak düz metin: parantezli notları, emoji kalıntısını at.
    ses = re.sub(r"^\s*\((.*?)\)\s*$", "", ses, flags=re.M)
    ses = "\n".join(s for s in ses.splitlines() if s.strip())
    if len(ses.split()) < 40:
        return None

    baslik = _bolum(metin, "BAŞLIK").split("\n")[0].strip()
    aciklama = _bolum(metin, "AÇIKLAMA").strip()
    hashtag_ham = _bolum(metin, "HASHTAG").strip()
    konu = _bolum(metin, "KONU").split("\n")[0].strip()

    etiketler = re.findall(r"#[\wçğıöşüÇĞİÖŞÜ_]+", hashtag_ham)
    if not etiketler:
        etiketler = [f"#{e.strip()}" for e in hashtag_ham.replace(",", " ").split()
                     if e.strip()]

    return {
        "baslik": baslik or "İlginç Bilgi",
        "metin": ses,
        "aciklama": aciklama,
        "etiketler": etiketler[:5] or ["#shorts", "#ilginçbilgi", "#bilim",
                                       "#biliyor muydunuz", "#bobitv"],
        "konu": konu,
        "kelime": len(ses.split()),
    }


def konu_uret(video_no: int = 0, kategori: str | None = None) -> dict | None:
    """Gemini web'e promptu gönderir. Başarısızsa None — uydurma yok.

    `video_no` ve `kategori` ARTIK KULLANILMIYOR: prompt kategoriyi kendisi
    rastgele seçiyor. Parametreler eski çağrılar kırılmasın diye duruyor.
    """
    from modules.gemini_web import metin_uret

    istem = istem_yaz()
    print(f"[konu] prompt gönderiliyor: {len(istem)} krkt")

    ham = metin_uret(istem, sure=240)
    if not ham:
        print("[konu] ❌ Gemini cevap vermedi")
        return None

    d = ayikla(ham)
    if not d:
        print(f"[konu] ❌ format ayrıştırılamadı (ilk 300: {ham[:300]!r})")
        return None

    print(f"[konu] {d['kelime']} kelime · başlık: {d['baslik'][:60]}")
    print(f"[konu] konu: {d['konu']}")

    d["kategori"] = ""
    d["kaynak"] = ""
    d["kapak_baslik"] = d["baslik"][:34]
    return d


def main() -> int:
    k = konu_uret()
    if not k:
        return 1
    print(json.dumps(k, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
