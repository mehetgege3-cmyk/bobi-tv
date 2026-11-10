"""
BOBİ TV — İnteraktif Telegram Kontrol Paneli (güvenlik düzeltmeli)
- Inline button'lar ile tam kontrol
- Manuel tetikleme, durum sorgulama, istatistikler
- GÜVENLİK: gelen her update CHAT_ID ile doğrulanır (process_update)
- GÜVENLİK: GH_TOKEN asla argv'ye girmez (requests header)
"""
import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

CALLBACK_PREFIX = {
    "status": "status_", "trigger": "trigger_", "stats": "stats_",
    "quality": "quality_", "quota": "quota_", "help": "help_", "menu": "menu_",
}


def _izinli_chat_idleri() -> set[int]:
    """TELEGRAM_CHAT_ID virgülle ayrılmış olabilir; int kümesi döndürür."""
    out = set()
    for parca in CHAT_ID.split(","):
        parca = parca.strip()
        if parca:
            try:
                out.add(int(parca))
            except ValueError:
                pass
    return out


def update_authorized(update: dict) -> bool:
    """Gelen update'in izinli sohbetten geldiğini doğrular (güvenlik kapısı)."""
    izinli = _izinli_chat_idleri()
    if not izinli:
        return False
    if "message" in update:
        chat_id = update["message"].get("chat", {}).get("id")
        from_id = update["message"].get("from", {}).get("id")
        return chat_id in izinli or from_id in izinli
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq.get("message", {}).get("chat", {}).get("id")
        from_id = cq.get("from", {}).get("id")
        return chat_id in izinli or from_id in izinli
    return False


def process_update(update: dict) -> bool:
    """Tek tüketim noktası: önce yetki kontrolü, sonra dispatch.
    True = işlendi, False = reddedildi (yetkisiz)."""
    if not update_authorized(update):
        print(f"⚠️ Yetkisiz update reddedildi: update_id={update.get('update_id')}")
        return False
    if "callback_query" in update:
        cq = update["callback_query"]
        callback_id = cq["id"]
        callback_data = cq.get("data", "")
        if callback_data:
            handle_callback(callback_data, callback_id)
            print(f"✅ Callback işlendi: {callback_data}")
    elif "message" in update:
        msg = update["message"]
        text = msg.get("text", "")
        if text:
            handle_message(text)
            print(f"✅ Mesaj işlendi: {text[:30]}")
    return True


def api_call(method: str, data: dict) -> Optional[dict]:
    if not BOT_TOKEN:
        print("[Telegram Bot] Token eksik")
        return None
    try:
        resp = requests.post(f"{BASE_URL}/{method}", json=data, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        print(f"[Telegram Bot] API hatası: {resp.status_code}")
        return None
    except Exception as e:
        print(f"[Telegram Bot] İstisna: {e}")
        return None


def send_message_with_buttons(text: str, buttons: list[list[dict]], parse_mode: str = "HTML") -> bool:
    result = api_call("sendMessage", {
        "chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": buttons},
    })
    return result is not None and result.get("ok", False)


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    result = api_call("sendMessage", {"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode})
    return result is not None and result.get("ok", False)


def answer_callback(callback_id: str, text: str = "", show_alert: bool = False) -> bool:
    result = api_call("answerCallbackQuery", {
        "callback_query_id": callback_id, "text": text, "show_alert": show_alert,
    })
    return result is not None and result.get("ok", False)


def get_main_menu_buttons() -> list[list[dict]]:
    return [
        [{"text": "📊 Durum", "callback_data": "status_now"},
         {"text": "🎬 Üret", "callback_data": "trigger_now"}],
        [{"text": "📈 İstatistik", "callback_data": "stats_today"},
         {"text": "🎯 Kalite", "callback_data": "quality_today"}],
        [{"text": "🚫 Kota", "callback_data": "quota_status"},
         {"text": "❓ Yardım", "callback_data": "help_show"}],
    ]


def get_status_text() -> str:
    from modules.kota_state import kota_dolu_mu, kota_state_oku
    arsiv = Path("bobi_tv/archive/videos.json")
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bugunki = 0
    if arsiv.exists():
        try:
            kayitlar = json.loads(arsiv.read_text(encoding="utf-8"))
            bugunki = sum(1 for k in kayitlar if k.get("tarih", "")[:10] == bugun)
        except Exception:
            pass
    kota_state = kota_state_oku()
    kota_durum = "🚫 DOLU" if kota_dolu_mu() else "✅ BOŞ"
    kuyruk = Path("bobi_tv/queue")
    kuyruk_sayisi = len(list(kuyruk.glob("*.json"))) if kuyruk.exists() else 0
    log_dosya = Path(f"bobi_tv/logs/{bugun}.log")
    son_calisma = "Bilinmiyor"
    if log_dosya.exists():
        try:
            with open(log_dosya, "r", encoding="utf-8") as f:
                for line in reversed(f.readlines()):
                    if "===" in line:
                        son_calisma = line.split("[")[1].split("]")[0] if "[" in line else "Bilinmiyor"
                        break
        except Exception:
            pass
    return (
        f"📊 <b>BOBİ TV Sistem Durumu</b>\n\n"
        f"📅 Tarih: {bugun}\n🎬 Bugün Üretilen: {bugunki}/24\n"
        f"📦 Kuyrukta: {kuyruk_sayisi} video\n🚫 YouTube Kota: {kota_durum}\n"
        f"⏰ Son Çalışma: {son_calisma}\n\n⚙️ Pipeline: v6.4 PRO"
    )


def get_stats_text() -> str:
    from modules.kalite_log import kalite_istatistik
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    istatistik = kalite_istatistik(bugun)
    if istatistik["toplam"] == 0:
        return f"📈 <b>İstatistik ({bugun})</b>\n\nBugün için veri yok."
    return (
        f"📈 <b>Günlük İstatistik ({bugun})</b>\n\n"
        f"🎬 Toplam Video: {istatistik['toplam']}\n"
        f"📊 Ortalama Puan: {istatistik['ortalama_puan']}/100\n"
        f"✅ Geçen: {istatistik['gecen']}\n❌ Kalan: {istatistik['kalan']}\n"
        f"📉 Min Puan: {istatistik['min_puan']}\n📈 Max Puan: {istatistik['max_puan']}"
    )


def get_quality_text() -> str:
    from modules.kalite_log import kalite_istatistik
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    istatistik = kalite_istatistik(bugun)
    if istatistik["toplam"] == 0:
        return f"🎯 <b>Kalite Raporu ({bugun})</b>\n\nBugün için kalite verisi yok."
    gecme_orani = round(istatistik['gecen'] / istatistik['toplam'] * 100, 1) if istatistik['toplam'] > 0 else 0
    return (
        f"🎯 <b>Kalite Raporu ({bugun})</b>\n\n"
        f"📊 Ortalama: {istatistik['ortalama_puan']}/100\n✅ Geçme Oranı: {gecme_orani}%\n\n"
        f"<b>Detaylar:</b>\n• Loop + Hook: %50\n• Timing: %25\n• Dialogue: %25\n\n🎯 Eşik: 70/100"
    )


def get_quota_text() -> str:
    from modules.kota_state import kota_state_oku, kota_dolu_mu
    state = kota_state_oku()
    kota_durum = "🚫 DOLU" if kota_dolu_mu() else "✅ BOŞ"
    guncelleme = state.get("guncelleme", "Bilinmiyor")
    kalan_saat = state.get("kalan_saat", 0)
    video_sayisi = state.get("video_sayisi", 0)
    return (
        f"🚫 <b>YouTube Kota Durumu</b>\n\nDurum: {kota_durum}\n"
        f"📅 Son Güncelleme: {guncelleme[:16] if guncelleme else 'Bilinmiyor'}\n"
        f"🎬 Bugün Yüklenen: {video_sayisi}\n⏰ Kalan Süre: ~{kalan_saat} saat\n\n"
        f"💡 Kota her gün UTC 00:00'da sıfırlanır."
    )


def get_help_text() -> str:
    return (
        "❓ <b>BOBİ TV Kontrol Paneli</b>\n\n<b>Komutlar:</b>\n"
        "📊 <b>Durum</b> - Sistem durumu\n🎬 <b>Üret</b> - Manuel video üret\n"
        "📈 <b>İstatistik</b> - Günlük istatistikler\n🎯 <b>Kalite</b> - Kalite raporu\n"
        "🚫 <b>Kota</b> - YouTube kota durumu\n\n<b>Otomatik Üretim:</b>\n"
        "• Her saat başı (cron: 0 * * * *)\n• Günlük hedef: 24 video\n"
        "• Kalite eşiği: 70/100\n\n<b>Not:</b> Kota doluyken üretim duraklar."
    )


def trigger_production() -> str:
    """Manuel üretim tetikle. GH_TOKEN asla argv'ye girmez (requests header).
    Başarı için HTTP 204 (dispatch standart yanıtı) zorunludur."""
    tok = os.environ.get("GH_TOKEN", "")
    if not tok:
        return "❌ Hata: GH_TOKEN tanımlı değil, tetiklenemedi."
    repo = "mehetgege3-cmyk/bobi-tv"
    workflow = "hourly_production.yml"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches"
    try:
        resp = requests.post(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {tok}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"ref": "main", "inputs": {"force": "true"}},
            timeout=30,
        )
    except Exception as e:
        return f"❌ İstisna: {str(e)[:100]}"
    if resp.status_code in (204, 201, 202):
        return "✅ Üretim tetiklendi! Workflow başlatılıyor..."
    return f"❌ Hata {resp.status_code}: {resp.text[:120]}"


def handle_callback(callback_data: str, callback_id: str) -> str:
    if callback_data == "menu_main":
        send_message_with_buttons("🎬 <b>BOBİ TV Kontrol Paneli</b>\n\nHoş geldiniz! Bir işlem seçin:", get_main_menu_buttons())
        answer_callback(callback_id); return ""
    if callback_data == "status_now":
        answer_callback(callback_id, "Durum yükleniyor...")
        send_message_with_buttons(get_status_text(), [
            [{"text": "🔄 Yenile", "callback_data": "status_now"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}],
        ]); return ""
    if callback_data == "trigger_now":
        answer_callback(callback_id, "Üretim tetikleniyor...")
        send_message_with_buttons(trigger_production(), [
            [{"text": "📊 Durum", "callback_data": "status_now"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}],
        ]); return ""
    if callback_data == "stats_today":
        answer_callback(callback_id, "İstatistik yükleniyor...")
        send_message_with_buttons(get_stats_text(), [
            [{"text": "🔄 Yenile", "callback_data": "stats_today"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}],
        ]); return ""
    if callback_data == "quality_today":
        answer_callback(callback_id, "Kalite raporu yükleniyor...")
        send_message_with_buttons(get_quality_text(), [
            [{"text": "🔄 Yenile", "callback_data": "quality_today"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}],
        ]); return ""
    if callback_data == "quota_status":
        answer_callback(callback_id, "Kota durumu yükleniyor...")
        send_message_with_buttons(get_quota_text(), [
            [{"text": "🔄 Yenile", "callback_data": "quota_status"}],
            [{"text": "🏠 Menü", "callback_data": "menu_main"}],
        ]); return ""
    if callback_data == "help_show":
        answer_callback(callback_id)
        send_message_with_buttons(get_help_text(), [[{"text": "🏠 Menü", "callback_data": "menu_main"}]])
        return ""
    answer_callback(callback_id, "Bilinmeyen komut")
    return "❌ Bilinmeyen komut"


def handle_message(text: str) -> str:
    text = text.strip().lower()
    menu = [[{"text": "🏠 Menü", "callback_data": "menu_main"}]]
    if text in ["/start", "/menu", "menü", "menu"]:
        send_message_with_buttons("🎬 <b>BOBİ TV Kontrol Paneli</b>\n\nHoş geldiniz! Bir işlem seçin:", get_main_menu_buttons())
        return ""
    if text in ["/status", "durum", "status"]:
        send_message_with_buttons(get_status_text(), menu); return ""
    if text in ["/trigger", "üret", "uret", "produce"]:
        send_message_with_buttons(trigger_production(), menu); return ""
    if text in ["/stats", "istatistik", "stats"]:
        send_message_with_buttons(get_stats_text(), menu); return ""
    if text in ["/help", "yardım", "yardim", "help"]:
        send_message_with_buttons(get_help_text(), menu); return ""
    send_message_with_buttons("❓ Anlamadım. Bir işlem seçin:", get_main_menu_buttons())
    return ""


# NOT: run_bot() uzun polling döngüsü GÜVENLİK TUZAĞIYDIR (workflow poller ile çakışır).
# Tek tüketim noktası: telegram_bot.yml workflow poller'ıdır. Yerelde çalıştırmak yerine
# `python -c "from modules.telegram_bot import process_update; ..."` kullanın.
