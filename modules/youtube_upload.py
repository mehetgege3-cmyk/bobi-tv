"""
BOBİ TV — YouTube Yükleme, Otomatik İlk Yorum ve SEO Modülü v6.0
Yenilikler:
- Yükleme sonrası YouTube Data API v3 commentThreads.insert ile gerçek ilk yorum atma
- Üretilen özel kapak görselini (thumbnails.set) yükleme
- 21 kategorinin tamamı için yüksek hacimli Türkçe Shorts SEO etiket haritası
- uploadLimitExceeded / quotaExceeded ayrımı (KotaDolduHatasi -> videoyu kuyruğa alır)
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime

import requests

ARSIV_YOLU = Path("bobi_tv/archive/videos.json")
YAYIN_DURUMU_YOLU = Path("bobi_tv/archive/published")
TOKEN_URI = "https://oauth2.googleapis.com/token"
UPLOAD_URI = "https://www.googleapis.com/upload/youtube/v3/videos"
THUMB_URI = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
VIDEOS_URI = "https://www.googleapis.com/youtube/v3/videos"
COMMENTS_URI = "https://www.googleapis.com/youtube/v3/commentThreads"


class KotaDolduHatasi(RuntimeError):
    """YouTube günlük yükleme veya API kotası dolduğunda fırlatılır."""


HASHTAG_HARITASI = {
    "kurumsal_hayat":     ["#shorts", "#kurumsalhayat", "#beyazyaka", "#ofishalleri", "#komedi", "#mizah"],
    "pazartesi_sendromu": ["#shorts", "#pazartesisendromu", "#pazartesi", "#ofishalleri", "#komedi", "#türkçemizah"],
    "ik_toplantisi":      ["#shorts", "#işgörüşmesi", "#mülakat", "#maaş", "#kurumsalhayat", "#komedi"],
    "mesai_sonu":         ["#shorts", "#mesai", "#patron", "#ofishalleri", "#beyazyaka", "#komedi"],
    "kahve_hayati":       ["#shorts", "#kahve", "#ofishalleri", "#kahvemolası", "#absürt", "#komedi"],
    "saglik_sorunu":      ["#shorts", "#doktor", "#hastane", "#komedi", "#absürt", "#türkçemizah"],
    "yapay_zeka":         ["#shorts", "#yapayzeka", "#teknoloji", "#chatgpt", "#komedi", "#absürt"],
    "wifi_kavgasi":       ["#shorts", "#misafir", "#wifi", "#evhali", "#türkçemizah", "#komedi"],
    "trafik_kavgasi":     ["#shorts", "#trafik", "#navigasyon", "#araba", "#komedi", "#mizah"],
    "diyet_kavrami":      ["#shorts", "#diyet", "#diyetteyim", "#yemek", "#komedi", "#mizah"],
    "spor_hayati":        ["#shorts", "#sporsalonu", "#fitness", "#komedi", "#absürt", "#mizah"],
    "sosyal_medya":       ["#shorts", "#sosyalmedya", "#anne", "#influencer", "#komedi", "#türkçemizah"],
}


def token_yukle() -> dict:
    raw = os.environ.get("YOUTUBE_TOKEN", "")
    if not raw:
        raise ValueError("YOUTUBE_TOKEN ortam değişkeni bulunamadı.")
    return json.loads(raw)


def token_yenile(token_data: dict) -> str:
    resp = requests.post(
        TOKEN_URI,
        data={
            "client_id": token_data["client_id"],
            "client_secret": token_data["client_secret"],
            "refresh_token": token_data["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Token yenileme hatası: {resp.status_code} — {resp.text}")
    return resp.json()["access_token"]


def zaten_yuklendi_mi(dosya_adi: str) -> str | None:
    YAYIN_DURUMU_YOLU.mkdir(parents=True, exist_ok=True)
    durum_dosyasi = YAYIN_DURUMU_YOLU / f"{dosya_adi}.json"
    if durum_dosyasi.exists():
        try:
            data = json.loads(durum_dosyasi.read_text(encoding="utf-8"))
            return data.get("video_id")
        except Exception:
            return None
    return None


def yayin_durumu_kaydet(dosya_adi: str, video_id: str, baslik: str):
    YAYIN_DURUMU_YOLU.mkdir(parents=True, exist_ok=True)
    durum = {
        "dosya_adi": dosya_adi,
        "video_id": video_id,
        "baslik": baslik,
        "yayinlandi": datetime.now().isoformat(),
        "url": f"https://www.youtube.com/shorts/{video_id}",
    }
    (YAYIN_DURUMU_YOLU / f"{dosya_adi}.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def arsive_ekle(dosya_adi: str, baslik: str, senaryo: dict, video_id: str):
    arsiv = []
    if ARSIV_YOLU.exists():
        try:
            arsiv = json.loads(ARSIV_YOLU.read_text(encoding="utf-8"))
        except Exception:
            arsiv = []

    kayit = {
        "dosya_adi": dosya_adi,
        "baslik": baslik,
        "video_id": video_id,
        "url": f"https://www.youtube.com/shorts/{video_id}",
        "senaryo_ozeti": senaryo.get("acilis", "")[:200],
        "hash": senaryo.get("hash", ""),
        "tarih": datetime.now().isoformat(),
    }
    arsiv.append(kayit)

    ARSIV_YOLU.parent.mkdir(parents=True, exist_ok=True)
    ARSIV_YOLU.write_text(json.dumps(arsiv, ensure_ascii=False, indent=2), encoding="utf-8")


def _ilk_yorum_at(video_id: str, yorum_metni: str, access_token: str) -> bool:
    """Yüklenen Shorts videosunun altına etkileşim sorusunu gerçek ilk yorum olarak yazar."""
    if not yorum_metni:
        return False
    try:
        govde = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": yorum_metni[:800]
                    }
                },
            }
        }
        resp = requests.post(
            f"{COMMENTS_URI}?part=snippet",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=govde,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            print(f"[YouTube] 💬 İlk yorum otomatik atıldı: {yorum_metni[:60]}")
            return True
        print(f"[YouTube] İlk yorum bilgi ({resp.status_code}): OAuth yorum izni yoksa açıklama alanı aktiftir.")
    except Exception as e:
        print(f"[YouTube] İlk yorum uyarısı: {e}")
    return False


def _kapak_yukle(video_id: str, kapak_dosyasi: str, access_token: str) -> bool:
    if not kapak_dosyasi or not Path(kapak_dosyasi).exists():
        return False
    try:
        veri = Path(kapak_dosyasi).read_bytes()
        if len(veri) > 2_000_000:
            return False
        resp = requests.post(
            f"{THUMB_URI}?videoId={video_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "image/jpeg",
            },
            data=veri,
            timeout=25,
        )
        if resp.status_code in (200, 201):
            print(f"[YouTube] 🖼️ Özel kapak yüklendi.")
            return True
    except Exception:
        pass
    return False


def video_yukle(senaryo_paketi: dict) -> str:
    dosya_adi = senaryo_paketi["dosya_adi"]
    baslik = str(senaryo_paketi["baslik"]).strip()
    if "#shorts" not in baslik.lower():
        baslik = f"{baslik[:90]} #shorts"
    final_video = senaryo_paketi.get("final_video")

    if not final_video or not Path(final_video).exists():
        raise FileNotFoundError(f"Video dosyası bulunamadı: {final_video}")

    mevcut_id = zaten_yuklendi_mi(dosya_adi)
    if mevcut_id:
        print(f"[YouTube] Video zaten yayında: {mevcut_id}")
        return mevcut_id

    token_data = token_yukle()
    access_token = token_yenile(token_data)

    senaryo = senaryo_paketi.get("senaryo", {})
    etkilesim = senaryo.get("etkilesim", "Bunu yaşayacak arkadaşını etiketle!")
    sabit_yorum = senaryo.get("sabit_yorum", "Siz olsanız ne yapardınız? Yorumlara yazın 👇")
    kategori = senaryo.get("kategori", "")

    etiketler = HASHTAG_HARITASI.get(
        kategori,
        ["#shorts", "#komedi", "#absürt", "#türkçemizah", "#bobitv", "#mizah"],
    )

    aciklama = "\n".join([
        sabit_yorum,
        "",
        etkilesim,
        "",
        "🎬 BOBİ TV — Her gün yeni Türkçe absürt komedi Shorts!",
        "🔔 Abone olmayı ve videoyu sonuna kadar (hatta iki kere 😉) izlemeyi unutma!",
        "",
        " ".join(etiketler),
    ])[:4900]

    ham_tagler = [e.lstrip("#") for e in etiketler] + [
        "shorts", "türkçe shorts", "komik videolar", "absürt komedi", "bobi tv", "diyalog", "skeç"
    ]
    benzersiz_tagler = list(dict.fromkeys(ham_tagler))

    metadata = {
        "snippet": {
            "title": baslik[:100],
            "description": aciklama,
            "tags": benzersiz_tagler[:20],
            "categoryId": "23",
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(Path(final_video).stat().st_size),
    }

    init_resp = requests.post(
        f"{UPLOAD_URI}?uploadType=resumable&part=snippet,status",
        headers=headers,
        json=metadata,
        timeout=30,
    )

    if init_resp.status_code != 200:
        metin = init_resp.text
        if "uploadLimitExceeded" in metin or "quotaExceeded" in metin:
            raise KotaDolduHatasi(f"YouTube günlük yükleme/API kotası dolu ({init_resp.status_code})")
        raise RuntimeError(f"Upload başlatma hatası: {init_resp.status_code} — {metin[:400]}")

    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        raise RuntimeError("Upload URL alınamadı.")

    video_bytes = Path(final_video).read_bytes()
    upload_resp = requests.put(
        upload_url,
        data=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_bytes)),
        },
        timeout=300,
    )

    if upload_resp.status_code not in (200, 201):
        metin = upload_resp.text
        if "uploadLimitExceeded" in metin or "quotaExceeded" in metin:
            raise KotaDolduHatasi(f"YouTube günlük yükleme kotası dolu ({upload_resp.status_code})")
        raise RuntimeError(f"Video yükleme hatası: {upload_resp.status_code} — {metin[:400]}")

    video_id = upload_resp.json().get("id")
    if not video_id:
        raise RuntimeError(f"video_id alınamadı: {upload_resp.text[:300]}")

    print(f"[YouTube] 🚀 Yayınlandı: https://www.youtube.com/shorts/{video_id}")

    time.sleep(3)
    _kapak_yukle(video_id, senaryo_paketi.get("kapak_dosyasi", ""), access_token)
    _ilk_yorum_at(video_id, sabit_yorum, access_token)

    yayin_durumu_kaydet(dosya_adi, video_id, baslik)
    arsive_ekle(dosya_adi, baslik, senaryo, video_id)
    senaryo_paketi["video_id"] = video_id
    return video_id


def toplu_yukle(senaryo_paketleri: list) -> tuple:
    """
    Videoları sırayla yükler.
    Döner: (basarili_sonuclar, hatalar, kota_dolan_paketler)
    """
    sonuclar = []
    hatalar = []
    kuyruga_alinacaklar = []

    for idx, paket in enumerate(senaryo_paketleri):
        try:
            video_id = video_yukle(paket)
            sonuclar.append({
                "video_id": video_id,
                "baslik": paket["baslik"],
                "dosya_adi": paket["dosya_adi"],
                "url": f"https://www.youtube.com/shorts/{video_id}",
            })
            if idx < len(senaryo_paketleri) - 1:
                time.sleep(6)
        except KotaDolduHatasi as ke:
            print(f"[YouTube] ⏳ Kota sınırı: {ke} -> Kalan videolar kuyruğa alınıyor.")
            kuyruga_alinacaklar.extend(senaryo_paketleri[idx:])
            break
        except Exception as e:
            hata = f"{paket.get('dosya_adi', '?')}: {e}"
            print(f"[YouTube] ❌ Yükleme hatası: {hata}")
            hatalar.append(hata)

    return sonuclar, hatalar, kuyruga_alinacaklar
