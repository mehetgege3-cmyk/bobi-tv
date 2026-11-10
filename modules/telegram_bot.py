"""
BOBİ TV — İnteraktif Telegram Kontrol Paneli
- Inline button'lar ile tam kontrol
- Manuel tetikleme, durum sorgulama, istatistikler
"""
import os
import json
import requests
import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Callback data prefix'leri
CALLBACK_PREFIX = {
    "status": "status_",
    "trigger": "trigger_",
    "stats": "stats_",
    "quality": "quality_",
    "quota": "quota_",
    "help": "help_",
    "menu": "menu_",
}


def api_call(method: str, data: dict) -> Optional[dict]:
    """Telegram API çağrısı."""
    if not BOT_TOKEN:
        print("[Telegram Bot] Token eksik")
        return None

    try:
        resp = requests.post(
            f"{BASE_URL}/{method}",
            json=data,
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[Telegram Bot] API hatası: {resp.status_code}")
            return None
    except Exception as e:
        print(f"[Telegram Bot] İstisna: {e}")
        return None


def send_message_with_buttons(
    text: str,
    buttons: list[list[dict]],
    parse_mode: str = "HTML"
) -> bool:
    """
    Inline button'lu mesaj gönder.

    Args:
        text: Mesaj metni
        buttons: Button grid [[{text, callback_data}, ...], ...]
        parse_mode: HTML veya Markdown

    Returns:
        Başarılı mı?
    """
    result = api_call("sendMessage", {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": buttons}
    })

    return result is not None and result.get("ok", False)


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Basit mesaj gönder."""
    result = api_call("sendMessage", {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode
    })
    return result is not None and result.get("ok", False)


def answer_callback(callback_id: str, text: str = "", show_alert: bool = False) -> bool:
    """Callback query'yi cevapla."""
    result = api_call("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": show_alert
    })
    return result is not None and result.get("ok", False)


def get_main_menu_buttons() -> list[list[dict]]:
    """Ana menü button'larını döndür."""
    return [
        [
            {"text": "📊 Durum", "callback_data": "status_now"},
            {"text": "🎬 Üret", "callback_data": "trigger_now"}
        ],
        [
            {"text": "📈 İstatistik", "callback_data": "stats_today"},
            {"text": "🎯 Kalite", "callback_data": "quality_today"}
        ],
        [
            {"text": "🚫 Kota", "callback_data": "quota_status"},
            {"text": "❓ Yardım", "callback_data": "help_show"}
        ]
    ]


def get_status_text() -> str:
    """Sistem durumunu getir."""
    from modules.kota_state import kota_dolu_mu, kota_state_oku

    # Arşivden bugünkü video sayısı
    arsiv = Path("bobi_tv/archive/videos.json")
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bugunki = 0

    if arsiv.exists():
        try:
            kayitlar = json.loads(arsiv.read_text(encoding="utf-8"))
            bugunki = sum(1 for k in kayitlar if k.get("tarih", "")[:10] == bugun)
        except Exception:
            pass

    # Kota durumu
    kota_state = kota_state_oku()
    kota_durum = "🚫 DOLU" if kota_dolu_mu() else "✅ BOŞ"

    # Kuyruk sayısı
    kuyruk = Path("bobi_tv/queue")
    kuyruk_sayisi = len(list(kuyruk.glob("*.json"))) if kuyruk.exists() else 0

    # Son çalışma
    log_dosya = Path(f"bobi_tv/logs/{bugun}.log")
    son_calisma = "Bilinmiyor"
    if log_dosya.exists():
        try:
            with open(log_dosya, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if "===" in line:
                        son_calisma = line.split("[")[1].split("]")[0] if "[" in line else "Bilinmiyor"
                        break
        except Exception:
            pass

    return (
        f"📊 <b>BOBİ TV Sistem Durumu</b>\n\n"
        f"📅 Tarih: {bugun}\n"
        f"🎬 Bugün Üretilen: {bugunki}/24\n"
        f"📦 Kuyrukta: {kuyruk_sayisi} video\n"
        f"🚫 YouTube Kota: {kota_durum}\n"
        f"⏰ Son Çalışma: {son_calisma}\n\n"
        f"⚙️ Pipeline: v6.4 PRO"
    )


def get_stats_text() -> str:
    """Günlük istatistikleri getir."""
    from modules.kalite_log import kalite_istatistik

    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    istatistik = kalite_istatistik(bugun)

    if istatistik["toplam"] == 0:
        return f"📈 <b>İstatistik ({bugun})</b>\n\nBugün için veri yok."

    return (
        f"📈 <b>Günlük İstatistik ({bugun})</b>\n\n"
        f"🎬 Toplam Video: {istatistik['toplam']}\n"
        f"📊 Ortalama Puan: {istatistik['ortalama_puan']}/100\n"
        f"✅ Geçen: {istatistik['gecen']}\n"
        f"❌ Kalan: {istatistik['kalan']}\n"
        f"📉 Min Puan: {istatistik['min_puan']}\n"
        f"📈 Max Puan: {istatistik['max_puan']}"
    )


def get_quality_text() -> str:
    """Kalite raporunu getir."""
    from modules.kalite_log import kalite_istatistik

    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    istatistik = kalite_istatistik(bugun)

    if istatistik["toplam"] == 0:
        return f"🎯 <b>Kalite Raporu ({bugun})</b>\n\nBugün için kalite verisi yok."

    gecme_orani = round(istatistik['gecen'] / istatistik['toplam'] * 100, 1) if istatistik['toplam'] > 0 else 0

    return (
        f"🎯 <b>Kalite Raporu ({bugun})</b>\n\n"
        f"📊 Ortalama: {istatistik['ortalama_puan']}/100\n"
        f"✅ Geçme Oranı: {gecme_orani}%\n\n"
        f"<b>Detaylar:</b>\n"
        f"• Loop + Hook: %50\n"
        f"• Timing: %25\n"
        f"• Dialogue: %25\n\n"
        f"🎯 Eşik: 70/100"
    )


def get_quota_text() -> str:
    """Kota durumunu getir."""
    from modules.kota_state import kota_state_oku, kota_dolu_mu

    state = kota_state_oku()
    kota_durum = "🚫 DOLU" if kota_dolu_mu() else "✅ BOŞ"

    guncelleme = state.get("guncelleme", "Bilinmiyor")
    kalan_saat = state.get("kalan_saat", 0)
    video_sayisi = state.get("video_sayisi", 0)

    return (
        f"🚫 <b>YouTube Kota Durumu</b>\n\n"
        f"Durum: {kota_durum}\n"
        f"📅 Son Güncelleme: {guncelleme[:16] if guncelleme else 'Bilinmiyor'}\n"
        f"🎬 Bugün Yüklenen: {video_sayisi}\n"
        f"⏰ Kalan Süre: ~{kalan_saat} saat\n\n"
        f"💡 Kota her gün UTC 00:00'da sıfırlanır."
    )


def get_help_text() -> str:
    """Yardım metni."""
    return (
        "❓ <b>BOBİ TV Kontrol Paneli</b>\n\n"
        "<b>Komutlar:</b>\n"
        "📊 <b>Durum</b> - Sistem durumu\n"
        "🎬 <b>Üret</b> - Manuel video üret\n"
        "📈 <b>İstatistik</b> - Günlük istatistikler\n"
        "🎯 <b>Kalite</b> - Kalite raporu\n"
        "🚫 <b>Kota</b> - YouTube kota durumu\n\n"
        "<b>Otomatik Üretim:</b>\n"
        "• Her saat başı (cron: 0 * * * *)\n"
        "• Günlük hedef: 24 video\n"
        "• Kalite eşiği: 70/100\n\n"
        "<b>Not:</b> Kota doluyken üretim duraklar."
    )


def trigger_production() -> str:
    """
    Manuel video üretimi tetikle.
    GitHub Actions workflow'ını çalıştırır.
    """
    try:
        # curl ile workflow dispatch
        import subprocess

        repo = "mehetgege3-cmyk/bobi-tv"
        workflow = "hourly_production.yml"

        # curl komutu
        cmd = [
            "curl", "-X", "POST",
            "-H", "Accept: application/vnd.github+json",
            "-H", f"Authorization: Bearer {os.environ.get('GH_TOKEN', '')}",
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches",
            "-d", '{"ref":"main","inputs":{"force":"true"}}'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return "✅ Üretim tetiklendi! Workflow başlatılıyor..."
        else:
            return f"❌ Hata: {result.stderr[:100] if result.stderr else 'Bilinmeyen hata'}"

    except Exception as e:
        return f"❌ İstisna: {str(e)[:100]}"


def handle_callback(callback_data: str, callback_id: str) -> str:
    """
    Callback query'yi işle.

    Args:
        callback_data: Button'dan gelen data
        callback_id: Callback query ID

    Returns:
        Cevap metni
    """
    # Menü
    if callback_data == "menu_main":
        send_message_with_buttons(
            "🎬 <b>BOBİ TV Kontrol Paneli</b>\n\nHoş geldiniz! Bir işlem seçin:",
            get_main_menu_buttons()
        )
        answer_callback(callback_id)
        return ""

    # Durum
    if callback_data == "status_now":
        answer_callback(callback_id, "Durum yükleniyor...")
        send_message_with_buttons(get_status_text(), [
            [{"text": "🔄 Yenile", "callback_data": "status_now"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    # Üret
    if callback_data == "trigger_now":
        answer_callback(callback_id, "Üretim tetikleniyor...")
        sonuc = trigger_production()
        send_message_with_buttons(sonuc, [
            [{"text": "📊 Durum", "callback_data": "status_now"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    # İstatistik
    if callback_data == "stats_today":
        answer_callback(callback_id, "İstatistik yükleniyor...")
        send_message_with_buttons(get_stats_text(), [
            [{"text": "🔄 Yenile", "callback_data": "stats_today"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    # Kalite
    if callback_data == "quality_today":
        answer_callback(callback_id, "Kalite raporu yükleniyor...")
        send_message_with_buttons(get_quality_text(), [
            [{"text": "🔄 Yenile", "callback_data": "quality_today"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    # Kota
    if callback_data == "quota_status":
        answer_callback(callback_id, "Kota durumu yükleniyor...")
        send_message_with_buttons(get_quota_text(), [
            [{"text": "🔄 Yenile", "callback_data": "quota_status"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    # Yardım
    if callback_data == "help_show":
        answer_callback(callback_id)
        send_message_with_buttons(get_help_text(), [
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    # Bilinmeyen
    answer_callback(callback_id, "Bilinmeyen komut")
    return "❌ Bilinmeyen komut"


def handle_message(text: str) -> str:
    """
    Metin mesajını işle.

    Args:
        text: Mesaj metni

    Returns:
        Cevap metni
    """
    text = text.strip().lower()

    # Komutlar
    if text in ["/start", "/menu", "menü", "menu"]:
        send_message_with_buttons(
            "🎬 <b>BOBİ TV Kontrol Paneli</b>\n\nHoş geldiniz! Bir işlem seçin:",
            get_main_menu_buttons()
        )
        return ""

    if text in ["/status", "durum", "status"]:
        send_message_with_buttons(get_status_text(), [
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    if text in ["/trigger", "üret", "uret", "produce"]:
        sonuc = trigger_production()
        send_message_with_buttons(sonuc, [
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    if text in ["/stats", "istatistik", "stats"]:
        send_message_with_buttons(get_stats_text(), [
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    if text in ["/help", "yardım", "yardim", "help"]:
        send_message_with_buttons(get_help_text(), [
            [{"text": "🏠 Menü", "callback_data": "menu_main"}]
        ])
        return ""

    # Bilinmeyen komut - menüyü göster
    send_message_with_buttons(
        "❓ Anlamadım. Bir işlem seçin:",
        get_main_menu_buttons()
    )
    return ""


def poll_updates(timeout: int = 60, offset: int = 0) -> list[dict]:
    """
    Telegram'dan güncelleme al (long polling).

    Args:
        timeout: Saniye cinsinden timeout
        offset: Son güncelleme ID'si

    Returns:
        Güncelleme listesi
    """
    result = api_call("getUpdates", {
        "timeout": timeout,
        "offset": offset,
        "allowed_updates": ["message", "callback_query"]
    })

    if result and result.get("ok"):
        return result.get("result", [])
    return []


def run_bot():
    """Bot'u çalıştır (main loop)."""
    print("🤖 BOBİ TV Telegram Bot başlatılıyor...")
    print(f"📱 Chat ID: {CHAT_ID}")

    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Token veya Chat ID eksik!")
        return

    # Başlangıç mesajı
    send_message_with_buttons(
        "🎬 <b>BOBİ TV Kontrol Paneli</b>\n\nBot aktif! Bir işlem seçin:",
        get_main_menu_buttons()
    )

    # Polling loop
    offset = 0
    print("✅ Bot çalışıyor... (Ctrl+C ile durdur)")

    try:
        while True:
            updates = poll_updates(timeout=60, offset=offset)

            for update in updates:
                offset = update["update_id"] + 1

                # Callback query
                if "callback_query" in update:
                    cq = update["callback_query"]
                    callback_id = cq["id"]
                    callback_data = cq.get("data", "")

                    if callback_data:
                        handle_callback(callback_data, callback_id)

                # Mesaj
                elif "message" in update:
                    msg = update["message"]
                    text = msg.get("text", "")

                    if text:
                        handle_message(text)

    except KeyboardInterrupt:
        print("\n🛑 Bot durduruldu.")
    except Exception as e:
        print(f"❌ Bot hatası: {e}")


if __name__ == "__main__":
    run_bot()
