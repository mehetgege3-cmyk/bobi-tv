"""
BOBİ TV — Telegram Bildirim Modülü
Tüm bildirimler, raporlar ve hatalar bu modül üzerinden iletilir.
"""
import os
import html
import requests
from datetime import datetime


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Telegram'a mesaj gönder. Başarılıysa True döner."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[Telegram] Token veya Chat ID eksik, mesaj atlandı.")
        return False
    try:
        resp = requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode},
            timeout=10
        )
        if resp.status_code == 200:
            return True
        else:
            print(f"[Telegram] Hata: {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        print(f"[Telegram] İstisna: {e}")
        return False


def notify_start(gun: str = None):
    gun = gun or datetime.now().strftime("%d.%m.%Y")
    send_message(
        f"🎬 <b>BOBİ TV Günlük Üretim Başladı</b>\n"
        f"📅 Tarih: {gun}\n"
        f"🎯 Hedef: 5 video\n"
        f"⚙️ Pipeline çalışıyor..."
    )


def notify_video_ready(baslik: str, video_no: int, toplam: int):
    send_message(
        f"✅ <b>Video Hazır #{video_no}/{toplam}</b>\n"
        f"🎬 {html.escape(baslik)}\n"
        f"📤 YouTube'a yükleniyor..."
    )


def notify_video_published(baslik: str, video_id: str, video_no: int, toplam: int):
    send_message(
        f"🚀 <b>Video Yayınlandı #{video_no}/{toplam}</b>\n"
        f"🎬 {html.escape(baslik)}\n"
        f"🔗 https://www.youtube.com/shorts/{video_id}"
    )


def notify_daily_report(hedef: int, uretilen: int, yayinlanan: int, hatalar: list):
    durum = "✅" if yayinlanan >= hedef else "⚠️"
    hata_metni = ""
    if hatalar:
        hata_metni = "\n\n<b>Hatalar:</b>\n" + "\n".join(f"• {h}" for h in hatalar[:5])

    send_message(
        f"{durum} <b>BOBİ TV Günlük Rapor</b>\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
        f"🎯 Hedef: {hedef}\n"
        f"🎬 Üretilen: {uretilen}\n"
        f"🚀 Yayınlanan: {yayinlanan}\n"
        f"❌ Başarısız: {uretilen - yayinlanan}"
        f"{hata_metni}"
    )


def notify_error(modul: str, hata: str, kritik: bool = False):
    emoji = "🔴" if kritik else "🟡"
    send_message(
        f"{emoji} <b>BOBİ TV {'KRİTİK ' if kritik else ''}Hata</b>\n"
        f"📦 Modül: {modul}\n"
        f"⚠️ {hata[:500]}"
    )


def notify_token_renewed():
    send_message(
        "🔑 <b>YouTube Token Yenilendi</b>\n"
        "OAuth token başarıyla yenilendi. Sistem çalışmaya devam ediyor."
    )


def notify_production_start_approval():
    send_message(
        "🟢 <b>BOBİ TV Sistem Hazır!</b>\n\n"
        "Tüm kurulum tamamlandı:\n"
        "✅ GitHub Actions\n"
        "✅ YouTube OAuth\n"
        "✅ Telegram Botu\n"
        "✅ Pipeline Modülleri\n\n"
        "Otonom üretim <b>aktif</b>. İlk video üretimi başlıyor..."
    )


if __name__ == "__main__":
    # Test
    result = send_message("🤖 <b>BOBİ TV Bot Test</b>\nTelegram bağlantısı başarılı!")
    print("Mesaj gönderildi:" if result else "Mesaj gönderilemedi.")
