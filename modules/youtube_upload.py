"""
BOBİ TV — YouTube Yükleme Modülü
YouTube Data API v3 ile video yükler, yayınlar ve durumu doğrular.
İdempotency kontrolü ile aynı videonun iki kez yüklenmesini önler.
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
VIDEOS_URI = "https://www.googleapis.com/youtube/v3/videos"


def token_yukle() -> dict:
    """YOUTUBE_TOKEN'dan token verisi yükle."""
    raw = os.environ.get("YOUTUBE_TOKEN", "")
    if not raw:
        raise ValueError("YOUTUBE_TOKEN bulunamadı.")
    return json.loads(raw)


def token_yenile(token_data: dict) -> str:
    """Access token'ı yenile ve döndür."""
    resp = requests.post(TOKEN_URI, data={
        "client_id": token_data["client_id"],
        "client_secret": token_data["client_secret"],
        "refresh_token": token_data["refresh_token"],
        "grant_type": "refresh_token"
    }, timeout=15)

    if resp.status_code != 200:
        raise RuntimeError(f"Token yenileme hatası: {resp.status_code} — {resp.text}")

    return resp.json()["access_token"]


def zaten_yuklendi_mi(dosya_adi: str) -> str | None:
    """
    Bu video daha önce yüklendi mi kontrol et.
    Yüklendiyse video_id döner, yoksa None.
    """
    YAYIN_DURUMU_YOLU.mkdir(parents=True, exist_ok=True)
    durum_dosyasi = YAYIN_DURUMU_YOLU / f"{dosya_adi}.json"
    if durum_dosyasi.exists():
        with open(durum_dosyasi) as f:
            data = json.load(f)
            video_id = data.get("video_id")
            if video_id:
                return video_id
    return None


def yayin_durumu_kaydet(dosya_adi: str, video_id: str, baslik: str):
    """Yayın durumunu kaydet."""
    YAYIN_DURUMU_YOLU.mkdir(parents=True, exist_ok=True)
    durum = {
        "dosya_adi": dosya_adi,
        "video_id": video_id,
        "baslik": baslik,
        "yayinlandi": datetime.now().isoformat(),
        "url": f"https://www.youtube.com/shorts/{video_id}"
    }
    with open(YAYIN_DURUMU_YOLU / f"{dosya_adi}.json", "w") as f:
        json.dump(durum, f, ensure_ascii=False, indent=2)


def arsive_ekle(dosya_adi: str, baslik: str, senaryo: dict, video_id: str):
    """Yayınlanan videoyu arşive ekle."""
    arsiv = []
    if ARSIV_YOLU.exists():
        with open(ARSIV_YOLU) as f:
            arsiv = json.load(f)

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
    with open(ARSIV_YOLU, "w", encoding="utf-8") as f:
        json.dump(arsiv, f, ensure_ascii=False, indent=2)


def video_yukle(senaryo_paketi: dict) -> str:
    """
    YouTube'a video yükle.
    Döner: video_id
    """
    dosya_adi = senaryo_paketi["dosya_adi"]
    baslik = senaryo_paketi["baslik"]
    final_video = senaryo_paketi.get("final_video")

    if not final_video or not Path(final_video).exists():
        raise FileNotFoundError(f"Video dosyası bulunamadı: {final_video}")

    # İdempotency: daha önce yüklendi mi?
    mevcut_id = zaten_yuklendi_mi(dosya_adi)
    if mevcut_id:
        print(f"[YouTube] Video zaten yüklendi: {mevcut_id}")
        return mevcut_id

    # Token al
    token_data = token_yukle()
    access_token = token_yenile(token_data)

    # Video meta verileri — viralite odaklı
    senaryo = senaryo_paketi.get("senaryo", {})
    etkilesim = senaryo.get("etkilesim", "")
    sabit_yorum = senaryo.get("sabit_yorum", "")
    kategori = senaryo.get("kategori", "")

    # Kategoriye göre hashtag'ler
    hashtag_haritasi = {
        "kurumsal_hayat": ["#kurumsalhayat", "#beyazyaka", "#ofishalleri", "#varoluşkrizi", "#pazartesisendromu"],
        "pazartesi_sendromu": ["#pazartesisendromu", "#pazartesi", "#mentalhealth", "#ofishalleri", "#kurumsalhayat"],
        "ik_toplantisi": ["#ik", "#maaşpazarlığı", "#kurumsalhayat", "#işgörüşmesi", "#beyazyaka"],
        "mesai_sonu": ["#mesai", "#kurumsalhayat", "#patron", "#ofishalleri", "#aciliş"],
        "bar_fikrasi": ["#barfikrası", "#komedi", "#absürt", "#türkçemizah", "#shorts"],
        "diyet_kavrami": ["#diyet", "#komedi", "#absürt", "#sağlık", "#shorts"],
        "google_sorusu": ["#varoluşsal", "#komedi", "#absürt", "#felsefe", "#shorts"],
        "trafik_kavgasi": ["#trafik", "#komedi", "#absürt", "#türkçemizah", "#shorts"]
    }

    etiketler = hashtag_haritasi.get(kategori, ["#shorts", "#komedi", "#absürt", "#türkçe", "#bobitv", "#mizah"])

    # Açıklama — etkileşim odaklı
    aciklama_parcalari = []
    if sabit_yorum:
        aciklama_parcalari.append(sabit_yorum + " 👇")
    aciklama_parcalari.append("")
    aciklama_parcalari.append("BOBİ TV'de her gün yeni absürt animasyon Shorts!")
    aciklama_parcalari.append("Abone ol: @BOBİTİVİ")
    if etkilesim:
        aciklama_parcalari.append("")
        aciklama_parcalari.append(etkilesim)
    aciklama_parcalari.append("")
    aciklama_parcalari.append(" ".join(etiketler))

    aciklama = "\n".join(aciklama_parcalari)[:5000]

    metadata = {
        "snippet": {
            "title": baslik[:100],
            "description": aciklama,
            "tags": ["shorts", "komedi", "absürt", "türkçe", "bobitv", "mizah", "animasyon"] + etiketler,
            "categoryId": "23",  # Comedy
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        }
    }

    # Resumable upload başlat
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
        timeout=30
    )

    if init_resp.status_code != 200:
        raise RuntimeError(f"Upload başlatma hatası: {init_resp.status_code} — {init_resp.text}")

    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        raise RuntimeError("Upload URL alınamadı.")

    # Video içeriğini yükle
    with open(final_video, "rb") as f:
        video_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        data=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_bytes)),
        },
        timeout=300
    )

    if upload_resp.status_code not in (200, 201):
        raise RuntimeError(f"Video yükleme hatası: {upload_resp.status_code} — {upload_resp.text[:500]}")

    upload_data = upload_resp.json()
    video_id = upload_data.get("id")

    if not video_id:
        raise RuntimeError(f"video_id alınamadı: {upload_data}")

    print(f"[YouTube] Video yüklendi: {video_id} — https://www.youtube.com/shorts/{video_id}")

    # Yayın durumunu doğrula
    time.sleep(5)
    dogrula = _yayin_dogrula(video_id, access_token)
    if not dogrula:
        print(f"[YouTube] UYARI: Video yüklendi ama yayın durumu henüz doğrulanamadı. video_id: {video_id}")

    # Kayıtları güncelle
    yayin_durumu_kaydet(dosya_adi, video_id, baslik)
    arsive_ekle(dosya_adi, baslik, senaryo_paketi.get("senaryo", {}), video_id)
    senaryo_paketi["video_id"] = video_id

    return video_id


def _yayin_dogrula(video_id: str, access_token: str) -> bool:
    """YouTube API ile video'nun yayında olduğunu doğrula."""
    try:
        resp = requests.get(
            VIDEOS_URI,
            params={"part": "status", "id": video_id},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15
        )
        if resp.status_code != 200:
            return False
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return False
        durum = items[0].get("status", {}).get("privacyStatus")
        return durum == "public"
    except Exception:
        return False


def toplu_yukle(senaryo_paketleri: list) -> list:
    """
    Birden fazla videoyu yükle.
    Döner: (video_id, baslik) çiftlerinin listesi.
    """
    sonuclar = []
    hatalar = []

    for paket in senaryo_paketleri:
        try:
            video_id = video_yukle(paket)
            sonuclar.append({
                "video_id": video_id,
                "baslik": paket["baslik"],
                "dosya_adi": paket["dosya_adi"],
                "url": f"https://www.youtube.com/shorts/{video_id}"
            })
            time.sleep(10)  # API kota koruması
        except Exception as e:
            hata = f"{paket.get('dosya_adi', '?')}: {e}"
            print(f"[YouTube] Yükleme hatası: {hata}")
            hatalar.append(hata)

    print(f"[YouTube] {len(sonuclar)}/{len(senaryo_paketleri)} video yüklendi.")
    return sonuclar, hatalar


if __name__ == "__main__":
    print("YouTube modülü yüklendi. Direkt çalıştırma için senaryo paketi gerekli.")
