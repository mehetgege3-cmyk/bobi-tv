"""KANALIN GERÇEK ENVANTERİ — YouTube Data API v3 (secret'tan jeton).

NEDEN (2026-11-13, kullanıcı uyarısı): "60 video yok kanalda."
  Ben `bobi_tv/archive/videos.json` dosyasını saydım ve 60 dedim. O dosya
  KANAL DEĞİL, geçmiş kayıt defteri: 37 kayıt `silindi_dusuk_izlenme`,
  9 kayıt `kaldirildi`. Gerçek envanter yalnız API'den alınır.

ÇIKTI: her video için  video_id | durum | süre | izlenme | kapak_var | baslik
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    from modules import youtube_upload

    access = youtube_upload.token_yenile(youtube_upload.token_yukle())
    if not access:
        print("❌ YouTube erişim jetonu alınamadı")
        return 2
    H = {"Authorization": f"Bearer {access}"}

    import urllib.request

    def api(url: str) -> dict:
        istek = urllib.request.Request(url, headers=H)
        with urllib.request.urlopen(istek, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    # 1) Kanalın kendisi
    kanal = api(
        "https://www.googleapis.com/youtube/v3/channels"
        "?part=snippet,statistics,contentDetails&mine=true"
    )
    if not kanal.get("items"):
        print("❌ Kanal bulunamadı (jeton izinleri?)")
        return 2
    ch = kanal["items"][0]
    ch_id = ch["id"]
    yukleme = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    st = ch["statistics"]
    print(f"KANAL: {ch['snippet']['title']}  ({ch_id})")
    print(
        f"  abone={st.get('subscriberCount')}  video={st.get('videoCount')}  "
        f"izlenme={st.get('viewCount')}"
    )
    print()

    # 2) Yüklenen TÜM videolar
    videolar, sayfa = [], None
    while True:
        url = (
            "https://www.googleapis.com/youtube/v3/playlistItems"
            f"?part=contentDetails&playlistId={yukleme}&maxResults=50"
        )
        if sayfa:
            url += f"&pageToken={sayfa}"
        d = api(url)
        videolar += [i["contentDetails"]["videoId"] for i in d.get("items", [])]
        sayfa = d.get("nextPageToken")
        if not sayfa:
            break

    print(f">>> API'deki GERÇEK video sayısı: {len(videolar)}")
    print()

    # 3) Detaylar
    print("video_id       | durum    | süre   | izlenme | kapak        | baslik")
    print("-" * 100)
    for i in range(0, len(videolar), 50):
        parca = ",".join(videolar[i : i + 50])
        d = api(
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=snippet,statistics,contentDetails,status&id={parca}"
        )
        for v in d.get("items", []):
            sn = v["snippet"]
            kapak = sn.get("thumbnails", {}).get("maxres", {}).get("url", "")
            print(
                f"{v['id']:14s} | {v['status'].get('privacyStatus',''):8s} | "
                f"{v['contentDetails']['duration']:6s} | "
                f"{v['statistics'].get('viewCount','0'):>7s} | "
                f"{'VAR' if kapak else 'yok':12s} | "
                f"{sn.get('title','')[:42]}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
