"""
BOBİ TV — İnteraktif Telegram Kontrol Paneli (hiyerarşik ayarlar sürümü)
- Hiyerarşik menü: Ana(4 düğme) → Rapor → Üret → Ayarlar → Grup → Ayar → Onay
- TEK MESAJ KURALI (TODO 4): her etkileşim AYNI panel mesajını düzenler
  (editMessageText + reply_markup). Yeni mesaj yalnızca: /start, panel >48 saat,
  düzenlenecek mesaj bulunamadı.
- callback_data ASLA değer taşımaz, sadece kimlik taşır; değer sunucuda
  katalog + state'ten çözülür (uydurma payload işe yaramaz).
- GÜVENLİK: gelen her update CHAT_ID ile doğrulanır (process_update)
- GÜVENLİK: GH_TOKEN asla argv'ye girmez (requests header); secret değeri
  panelde ASLA gösterilmez (yalnız ✅ tanımlı / ⛔ eksik)
- GÜVENLİK: subprocess import EDİLMEZ (PAT argv sızıntısı tuzağı); git işleri
  modules/ayar_deposu.commit_ve_yukle içinde kalır.
"""

import html
import json
import os
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

import modules.ayar_deposu as ayar_deposu
from modules import denetim, mini_app_eylem, rehber, render_karti, tekillestirme
from modules.ayar_katalogu import (
    GRUPLAR,
    TEMIZLIK_UYARI,
    ayar_getir,
    degistirilebilir_mi,
    grup_ayarlari,
)
from modules.kota_kapisi import kota_durumu_ozeti

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

MENU_STATE_YOLU = Path("bobi_tv/state/telegram_menu.json")
AYARLAR_STATE_YOLU = ayar_deposu.AYARLAR_YOLU
GECMIS_YOLU = ayar_deposu.GECMIS_YOLU
BEKLEYEN_YOLU = ayar_deposu.BEKLEYEN_YOLU
KOTA_YOLU = Path("bobi_tv/state/youtube_quota.json")

#: Ana panel metni ARTIK canlı durum kartıdır (ekran_ana). Eski statik başlık
#: yalnız geriye dönük uyumluluk için duruyor (çağıranlar ekran_ana kullanır).
MENU_BASLIGI = "🎬 <b>BOBİ TV</b>"
PANEL_48_SAAT = timedelta(hours=48)
BILINMIYOR = "bilinmiyor"

#: TEK EMOJİ SÖZLÜĞÜ (TODO 16). Ekranlar bu sabitleri kullanır; serbest
#: emoji yazımı ekranlar arasında tutarsızlık üretiyordu.
EMOJI = {
    "tamam": "✅",       # başarılı
    "dikkat": "⚠️",      # dikkat
    "engel": "⛔",       # eksik / engel
    "test": "🧪",        # test / render testi
    "sil": "🗑️",        # silme
    "yukle": "🚀",       # yükleme / yayın
    "para": "💰",        # kota / birim
}

#: Buton arka plan renkleri (Bot API 9.4). API alanı reddederse düz butona
#: düşülür — panel ASLA çökmez (TODO 16 fallback kuralı).
BUTON_RENK = {"onay": "success", "vazgec": None, "riskli": "danger"}


def renkli_buton(metin: str, callback_data: str, tur: str = "vazgec") -> dict[str, Any]:
    """Renk destekli buton üretir. Renk alanı reddedilirse panel düz butona düşer
    (`_renk_fallback` ile tekrar gönderilir) — kullanıcıya hata gösterilmez."""
    b: dict[str, Any] = {"text": metin, "callback_data": callback_data}
    renk = BUTON_RENK.get(tur)
    if renk:
        b["style"] = renk
    return b

#: TODO 32 — KALICI ALT KLAVYE. Kullanıcı isteği (2026-11-11):
#: "bot başlayınca menüler açık görünsün, her şey elimin altında olsun".
#: Telegram'da KALICI MENÜ ancak ReplyKeyboard ile olur (inline butonlar mesaja
#: bağlıdır, sohbet açılınca kendiliğinden görünmez). `is_persistent` + `resize`
#: ile ekranın altında durur; klavyeyi kapatmaz, yazmayı engellemez.
REPLY_KLAVYE: list[list[str]] = [
    ["📊 Durum", "🎬 Üret"],
    ["📈 Rapor", "⚙️ Ayarlar"],
    ["📦 Stok", "❓ Yardım"],
]

#: Alt klavye metni → panel ekranı eşlemesi (emoji duyarsız arama için).
REPLY_ESLEME: dict[str, str] = {
    # "Durum" = canlı durum ekranı (system.status_now); "Rapor" = rapor ekranı.
    # İkisi farklı ekran: durum düğmesi raporu açmamalı.
    "durum": "status_now",
    "üret": "uret_menu",
    "uret": "uret_menu",
    "rapor": "rapor_goster",
    "ayarlar": "ay:kok",
    "stok": "kuyruk_liste",
    "yardım": "yardim_goster",
    "yardim": "yardim_goster",
}

#: Ekran hiyerarşisi (2026-11-11): callback → BİR ÜST ekranın callback'i.
#: "← Geri" düğmesi bu haritayla GERÇEK üst ekrana döner; her ekranda aynı
#: yere (ana kart) dönmek kullanıcıyı kaybettiriyordu.
EKRAN_UST: dict[str, str | None] = {
    "menu_main": None,
    "rapor_goster": "menu_main",
    "kanal_sagligi": "rapor_goster",
    "uret_menu": "menu_main",
    "status_now": "rapor_goster",
    "sistem_kok": "menu_main",
    "rapor_7gun": "rapor_goster",
    "performans": "rapor_goster",
    "kuyruk_liste": "rapor_goster",
    "render_kart": "uret_menu",
    "denetim_goster": "sistem_kok",
    "bildirim_goster": "sistem_kok",
    "mini_app_goster": "sistem_kok",
    "sistem_goster": "sistem_kok",
    "ay:kok": "menu_main",
    "ay:hizli": "ay:kok",
    "ay:gecmis": "ay:kok",
    "yardim_goster": "menu_main",
}

#: Şu an gösterilen ekranın callback'i (Geri hedefini hesaplamak için).
_SON_CALLBACK: str | None = None


def ekran_ust(cb: str | None) -> str:
    """Verilen callback'in BİR ÜST ekranının callback'ini döndürür.

    Bilinmiyorsa güvenli varsayılan: ana kart (`menu_main`). Dinamik ayar
    callback'leri (`ay:s:<anahtar>`) ayarın grubuna, grup da köke döner.
    """
    if not cb:
        return "menu_main"
    if cb in EKRAN_UST:
        return EKRAN_UST[cb] or "menu_main"
    p = cb.split(":")
    if len(p) >= 3 and p[0] == "ay":
        if p[1] in {"s", "nedir", "onay", "onayd"}:
            a = ayar_getir(p[2])
            if a is not None:
                return f"ay:g:{a['grup']}"
        return "ay:kok" if p[1] != "g" else "ay:kok"
    return "menu_main"


GERI_MENUSU: list[dict[str, str]] = [
    # 2026-11-11: "← Geri" MENÜ'ye dönüyordu (ikisi de aynı işi yapıyordu).
    # Artık Geri = bir üst ekran (ayarlarda grup, grupta kök, kökte ana kart).
    {"text": "← Geri", "callback_data": "geri"},
    {"text": "🏠 Menü", "callback_data": "menu_main"},
]

# TODO 3 — menü derinliği: ana(0) → ayarlar(1) → grup(2) → ayar/onay(3).
# Onay/dry-run ekranları derinlik 3'ün EŞİDİR (ay-detay ekranının yerine geçer).
#: Tek doğruluk kaynağı: GitHub repo ve pipeline sürümü (TODO 13).
#: Üç ayrı yerde sabit yazılıydı; repo adı değişince panel sessizce bozulurdu.
GITHUB_REPO = os.environ.get("GITHUB_REPO", "mehetgege3-cmyk/bobi-tv")
PIPELINE_SURUM = os.environ.get("PIPELINE_SURUM", "v6.4 PRO")

#: TODO 31 — Mini App adresi (GitHub Pages). BotFather'a KAYITLI domain olmalı
#: (20 Temmuz 2026 kısıtı). Panelde yalnız bilgi olarak gösterilir.
MINI_APP_URL = os.environ.get(
    "MINI_APP_URL", "https://mehetgege3-cmyk.github.io/bobi-tv/"
)

CALLBACK_DERINLIK: dict[str, int] = {
    "menu_main": 0,
    "geri": 1,
    "sistem_kok": 1,
    "denetim_goster": 1,
    "mini_app_goster": 1,
    "rapor_goster": 1,
    "kanal_sagligi": 2,
    "uret_menu": 1,
    "status_now": 1,
    "trigger_now": 1,
    "stats_today": 1,
    "quality_today": 1,
    "quota_status": 1,
    "help_show": 1,
    "ay:kok": 1,
    "ay:gir": 3,
    "ay:hizli": 1,
    "bildirim_goster": 1,
    "performans": 2,
    "bildirim_sustur1": 1,
    "bildirim_sustur24": 1,
    "bildirim_ac": 1,
    "bildirim_ozet": 1,
    "ay:tumu": 1,
    "ay:t": 1,
    "ay:d": 1,
    "ay:onayd": 3,
    "panelleri_temizle": 1,
    "rapor_7gun": 2,
    "kuyruk_liste": 2,
    "kuyruk_at_onay": 3,
    "kuyruk_at_uygula": 3,
    "kuyruk_geri_al": 2,
    "render_kart": 2,
    "ay:nedir": 3,
    "sistem_nedir": 2,
    "ay:gecmis": 2,
    "sistem_goster": 2,
    "ay:g": 2,
    "ay:s": 3,
    "ay:v": 3,
    "ay:onay": 3,
    "ay:iptal": 3,
    "ay:test": 3,
    "uret_baslat": 2,
    "uret_onay": 2,
    "uret_render_test": 2,
}


def _izinli_chat_idleri() -> set[int]:
    """TELEGRAM_CHAT_ID virgülla ayrılmış olabilir; int kümesi döndürür."""
    out = set()
    for parca in CHAT_ID.split(","):
        parca = parca.strip()
        if parca:
            with suppress(ValueError):
                out.add(int(parca))
    return out


def update_authorized(update: dict[str, Any]) -> bool:
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


def process_update(update: dict[str, Any]) -> bool:
    """Tek tüketim noktası: önce yetki kontrolü, sonra dispatch.
    True = işlendi, False = reddedildi (yetkisiz)."""
    if not update_authorized(update):
        print(f"⚠️ Yetkisiz update reddedildi: update_id={update.get('update_id')}")
        return False
    # TODO 29 — TEKİLLEŞTİRME: aynı update kısa süre içinde tekrar geldiyse
    # İKİNCİ kez işlenmez (ikinci üretim/yükleme tetiklenmesin). Sessiz yutma
    # yok: her tekrar loga yazılır.
    if tekillestirme.tekrar_mi(update):
        print(
            f"♻️ Tekrar eden update yutuldu: update_id={update.get('update_id')} "
            f"({tekillestirme.gorulme_sayisi(update)}. geliş)"
        )
        return True
    if "callback_query" in update:
        cq = update["callback_query"]
        callback_id = cq["id"]
        callback_data = cq.get("data", "")
        if callback_data:
            kullanici_id = cq.get("from", {}).get("id")
            handle_callback(callback_data, callback_id, kullanici_id)
            print(f"✅ Callback işlendi: {callback_data}")
    elif "message" in update:
        msg = update["message"]
        # TODO 31 v2 — Mini App YAZMA: butonlar sendData gönderir, bot onay açar.
        # Öncelik: web_app_data varsa metin işlenmez (tek yol, karışıklık yok).
        if msg.get("web_app_data") is not None:
            handle_web_app_data(msg["web_app_data"])
            print("✅ Mini App verisi işlendi (onay akışına yönlendirildi)")
            return True
        text = msg.get("text", "")
        if text:
            handle_message(text)
            print(f"✅ Mesaj işlendi: {text[:30]}")
    return True


def handle_web_app_data(veri: Any) -> str:
    """Mini App'ten gelen yazma niyetini ONAY ekranına çevirir.

    Mini App hiçbir şeyi doğrudan çalıştırmaz: payload doğrulanır, sonra var
    olan panel akışı (onay ekranı → imzalı callback → denetim) tetiklenir.

    Döner: "onay" | "goster" | "red"
    """
    ham = veri.get("data") if isinstance(veri, dict) else veri
    kayit, sebep = mini_app_eylem.payload_coz(ham)
    if kayit is None:
        panel_goster(*ekran_metin_dugme(mini_app_eylem.red_metni(sebep)))
        denetim.kaydet("mini_app_red", "basarisiz", ayrinti={"sebep": sebep})
        return "red"

    hedef = str(kayit["callback"])
    # Onay gerektiren eylemler: panele "Mini App'ten geldi" notu + onay ekranı.
    if mini_app_eylem.onay_gerekli(str(kayit["eylem"])) and hedef == "uret_baslat":
        metin, dugmeler = ekran_uret_onay()
        panel_goster(f"{mini_app_eylem.niyet_metni(kayit)}\n\n➖➖➖\n\n{metin}", dugmeler)
        denetim.kaydet("mini_app_niyet", "onay_bekliyor", ayrinti={"eylem": kayit["eylem"]})
        return "onay"

    # Diğer eylemler var olan panel yönlendirmesine düşer (yeni yol açılmaz).
    if hedef == "menu_main":
        panel_goster(*ekran_ana())
        return "goster"
    if hedef == "denetim_goster":
        panel_goster(*ekran_denetim())
        return "goster"
    if hedef == "uret_render_test":
        metin, dugmeler = ekran_uret()
        panel_goster(
            f"{mini_app_eylem.niyet_metni(kayit)}\n\n➖➖➖\n\n{metin}", dugmeler
        )
        denetim.kaydet("mini_app_niyet", "onay_bekliyor", ayrinti={"eylem": kayit["eylem"]})
        return "onay"
    if hedef == "kuyruk_at_onay":
        panel_goster(*ekran_kuyruk_at_onay())
        denetim.kaydet("mini_app_niyet", "onay_bekliyor", ayrinti={"eylem": kayit["eylem"]})
        return "onay"
    # Bilinmeyen hedef: güvenli taraf → ana ekran.
    panel_goster(*ekran_ana())
    return "goster"


#: Bir turda işlenecek AZAMİ update sayısı (TODO 28): poller uzun sustuğunda
#: biriken kuyruk tek turu kilitlemesin, offset güvenli noktada ilerlesin.
POLLER_TUR_AZAMI = int(os.environ.get("TELEGRAM_TUR_AZAMI", "20") or "20")


def updates_isle(
    updates: list[dict[str, Any]],
    offset: int,
    azami: int | None = None,
) -> tuple[int, int, int, bool]:
    """Güncelleme yığınını sırayla işler (offset kaybı koruması).

    Offset YALNIZCA update başarılı şekilde ele alındığında ilerler:
    - process_update True dönerse (işlendi) offset ilerler.
    - process_update False dönerse (yetkisiz — bilinçli red kararı) offset ilerler.
    - process_update İSTİSNA fırlatırsa döngü durur, offset o update'ten ÖNCE kalır:
      mesaj kaybolmaz, bir sonraki koşuda yeniden denemek için korunur.

    Döner: (yeni_offset, islenen, reddedilen, kesinti_olustu)
    """
    islenen = 0
    reddedilen = 0
    kesinti = False
    # TODO 28: tur başına iş sınırı — kalan update'ler sonraki turda işlenir
    # (offset yalnız İŞLENEN update'ler kadar ilerler, kayıp olmaz).
    sinir = azami if azami is not None else POLLER_TUR_AZAMI
    if sinir > 0:
        updates = updates[:sinir]
    for update in updates:
        try:
            ok = process_update(update)
        except Exception as e:
            print(f"::error::process_update başarısız (update_id={update.get('update_id')}): {e}")
            kesinti = True
            break
        if ok:
            islenen += 1
        else:
            reddedilen += 1
        offset = update["update_id"] + 1
    return offset, islenen, reddedilen, kesinti


def bosuk_uyarisi_gonder(bosuk: int, onceki_guncelleme: str | None) -> bool:
    """Uzun kesinti sonrası ilk koşuda düşen update sayısını raporlar."""
    sure_metni = "bilinmeyen süre"
    if onceki_guncelleme:
        try:
            gz = datetime.fromisoformat(str(onceki_guncelleme))
            if gz.tzinfo is None:
                gz = gz.replace(tzinfo=UTC)
            dk = int((datetime.now(UTC) - gz).total_seconds() / 60)
            sure_metni = f"~{dk} dakika" if dk < 120 else f"~{dk // 60} saat"
        except Exception:
            pass
    metin = (
        "⚠️ <b>BOBİ TV — Mesaj kaybı uyarısı</b>\n"
        f"Bot {sure_metni} çalışmadı; aradaki {bosuk} güncelleme Telegram kuyruğundan "
        "düştü (getUpdates 24 saatlik pencere). Kayıp mesajlar geri getirilemez."
    )
    return send_message(metin)


# ---------------------------------------------------------------------------
# Telegram API yardımcıları
# ---------------------------------------------------------------------------


def api_call(method: str, data: dict[str, Any]) -> dict[str, Any] | None:
    if not BOT_TOKEN:
        print("[Telegram Bot] Token eksik")
        return None
    try:
        resp = requests.post(f"{BASE_URL}/{method}", json=data, timeout=15)
        try:
            json_degeri: Any = resp.json()
        except ValueError:
            json_degeri = None
        body: dict[str, Any] | None = json_degeri if isinstance(json_degeri, dict) else None
        if resp.status_code == 200:
            return body
        # Hata gövdesi de döndürülür: çağıran "message is not modified" gibi
        # durumlara ayırt edici davranabilsin diye (tek mesaj kuralı buna muhtaç).
        aciklama = str(body.get("description", "")) if body else ""
        print(f"[Telegram Bot] API hatası: {resp.status_code} {aciklama}")
        return body
    except Exception as e:
        print(f"[Telegram Bot] İstisna: {e}")
        return None


def _renkleri_temizle(butonlar: Any) -> Any:
    """Butonlardan `style` alanını atar (renk desteklenmeyen API için).

    Tek buton dict'i, satır listesi veya 2B klavye — hepsi desteklenir.
    """
    if isinstance(butonlar, dict):
        return {k: v for k, v in butonlar.items() if k != "style"}
    if isinstance(butonlar, list):
        return [_renkleri_temizle(x) for x in butonlar]
    return butonlar


def butonlari_renkle_gonder(
    yontem: str, govde: dict[str, Any], butonlar: Any
) -> dict[str, Any] | None:
    """Butonları renkle gönderir; API `style` alanını reddederse DÜZ butonla
    tekrar dener. Kural: renk yüzünden panel ASLA çökmez (TODO 16)."""
    govde = dict(govde)
    govde["reply_markup"] = {"inline_keyboard": butonlar}
    yanit = api_call(yontem, govde)
    if yanit is None or yanit.get("ok"):
        return yanit
    aciklama = str(yanit.get("description", "")).lower()
    if any(k in aciklama for k in ("style", "unknown field", "button", "parse")):
        govde["reply_markup"] = {"inline_keyboard": _renkleri_temizle(butonlar)}
        yanit = api_call(yontem, govde)
    return yanit


#: Metin içinde kullanılabilen HTML etiketleri. Telegram `parse_mode=HTML`
#: bunları destekler; geri kalan HER ŞEY kaçırılır (XSS/parse hatası olmaz).
IZINLI_ETIKETLER = ("b", "i", "u", "s", "code", "pre", "blockquote")


def _html_guvenli(text: str) -> str:
    """TEK escape noktası: veri alanlarını (& < >) kaçır, İZİNLİ etiketleri koru.

    TODO 13: eski sürüm yalnız `<b>` koruyordu → `ekran_giris` içindeki
    `<code>60</code>` kaçırılıp ekranda düz metin olarak görünüyordu
    ("&lt;code&gt;60&lt;/code&gt;"). Artık izinli etiket listesi geniştir.
    """
    kacirilmis = html.escape(text, quote=False)
    for etiket in IZINLI_ETIKETLER:
        kacirilmis = kacirilmis.replace(f"&lt;{etiket}&gt;", f"<{etiket}>")
        kacirilmis = kacirilmis.replace(f"&lt;/{etiket}&gt;", f"</{etiket}>")
    return kacirilmis


def send_message_with_buttons(
    text: str, buttons: list[list[dict[str, Any]]], parse_mode: str = "HTML"
) -> bool:
    result = api_call(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": _html_guvenli(text),
            "parse_mode": parse_mode,
            "reply_markup": {"inline_keyboard": buttons},
        },
    )
    return result is not None and result.get("ok", False)


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Düz mesaj gönderir. Escape TEK noktadan (`_html_guvenli`) yapılır.

    TODO 13: eskiden send_message escape YAPMIYORDU, panel_goster yapıyordu →
    aynı metin iki yoldan iki farklı sonuç veriyordu (çift escape / ham HTML).
    """
    govde: dict[str, Any] = {"chat_id": CHAT_ID, "text": _html_guvenli(text)}
    if parse_mode:
        govde["parse_mode"] = parse_mode
    result = api_call("sendMessage", govde)
    return result is not None and result.get("ok", False)


def answer_callback(callback_id: str, text: str = "", show_alert: bool = False) -> bool:
    result = api_call(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": text,
            "show_alert": show_alert,
        },
    )
    return result is not None and result.get("ok", False)


# ---------------------------------------------------------------------------
# TODO 4 — TEK MESAJ KURALI: panel mesajı izleme + edit-in-place
# ---------------------------------------------------------------------------


def _panel_oku() -> tuple[int | None, datetime | None]:
    """Saklanan panel mesaj id'si + zamanı (hedef sohbet eşleşiyorsa)."""
    try:
        if MENU_STATE_YOLU.exists():
            veri = json.loads(MENU_STATE_YOLU.read_text(encoding="utf-8"))
            if str(veri.get("chat_id", "")) == str(CHAT_ID):
                mesaj_id = int(veri.get("message_id"))
                zaman = datetime.fromisoformat(str(veri.get("zaman")))
                if zaman.tzinfo is None:
                    zaman = zaman.replace(tzinfo=UTC)
                return mesaj_id, zaman
    except Exception:
        pass
    return None, None


#: Panelde "değer yaz" bekleyen ayar (kullanıcı sayı yazacak).
#: Ayrı dosya değil, telegram_menu.json içinde tek alan — ek commit üretmez.
def _bekleyen_giris_yaz(anahtar: str | None) -> None:
    """Hangi ayar için klavyeden değer beklendiğini kaydeder (None = temizle)."""
    try:
        veri: dict[str, Any] = {}
        if MENU_STATE_YOLU.exists():
            with suppress(Exception):
                veri = json.loads(MENU_STATE_YOLU.read_text(encoding="utf-8"))
        if anahtar:
            veri["bekleyen_giris"] = anahtar
        else:
            veri.pop("bekleyen_giris", None)
        MENU_STATE_YOLU.parent.mkdir(parents=True, exist_ok=True)
        MENU_STATE_YOLU.write_text(json.dumps(veri), encoding="utf-8")
    except Exception:
        pass


def _bekleyen_giris_oku() -> str | None:
    """Klavyeden değer beklenen ayarın anahtarı (yoksa None)."""
    try:
        if MENU_STATE_YOLU.exists():
            veri = json.loads(MENU_STATE_YOLU.read_text(encoding="utf-8"))
            deger = veri.get("bekleyen_giris")
            return str(deger) if deger else None
    except Exception:
        return None
    return None


def _panel_yaz(message_id: int) -> None:
    try:
        MENU_STATE_YOLU.parent.mkdir(parents=True, exist_ok=True)
        # MEVCUT ALANLAR KORUNUR (2026-11-11 düzeltmesi): burada sözlüğü sıfırdan
        # yazmak `klavye_kuruldu` bayrağını siliyordu → her /start'ta alt klavye
        # yeniden gönderiliyordu (ekranda "Menü hazır" mesajı birikiyordu).
        onceki: dict[str, Any] = {}
        with suppress(Exception):
            if MENU_STATE_YOLU.exists():
                onceki = json.loads(MENU_STATE_YOLU.read_text(encoding="utf-8")) or {}
        veri_panel = dict(onceki) if isinstance(onceki, dict) else {}
        veri_panel.update(
                {
                    "chat_id": CHAT_ID,
                    "message_id": message_id,
                    "zaman": datetime.now(UTC).isoformat(),
                    # bekleyen_giris KORUNUR: kullanıcı paneli yenilerken değer
                    # girişi kaybolmasın.
                    **({"bekleyen_giris": g} if (g := _bekleyen_giris_oku()) else {}),
                }
        )
        MENU_STATE_YOLU.write_text(json.dumps(veri_panel), encoding="utf-8")
    except Exception:
        pass


def _panel_temizle() -> None:
    with suppress(Exception):
        MENU_STATE_YOLU.unlink(missing_ok=True)


def eski_panelleri_sil(adet: int = 10) -> int:
    """Telegram'dan son N mesajı silerek birikmiş panelleri temizler.

    Neden gerekli: poller uzun süre çalışmadığında kuyrukta biriken /start'lar
    toplu işlenir ve ekranda art arda paneller birikir (2026-11-11'de 5 panel).
    Tek panel felsefesi yalnızca ileriye dönük çalışır — geçmiş birikimi bu
    fonksiyon temizler. Silme başarısız olursa (48 saatten eski mesaj vb.)
    sessizce geçilir; asla exception fırlatmaz.

    Döner: silinen mesaj sayısı (en iyi gayretle).
    """
    silinen = 0
    # Paneli kaydımızdan başlayarak geriye doğru dene: kayıtlı panel + öncesi.
    for mesaj_id in range(_panel_son_id(), _panel_son_id() - adet, -1):
        if mesaj_id <= 0:
            break
        sonuc = api_call("deleteMessage", {"chat_id": CHAT_ID, "message_id": mesaj_id})
        if sonuc is not None and sonuc.get("ok"):
            silinen += 1
    if silinen:
        print(f"[Panel] {silinen} eski mesaj silindi")
        _panel_temizle()
    return silinen


def _panel_son_id() -> int:
    panel_id, _ = _panel_oku()
    return int(panel_id or 0)


def _panel_yeni_gonder(metin: str, butonlar: list[list[dict[str, Any]]]) -> bool:
    """Taze panel mesajı açar ve kimliğini izler (tek panel felsefesi)."""
    resp = api_call(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": _html_guvenli(metin),
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": butonlar},
        },
    )
    if resp is not None and resp.get("ok"):
        mesaj_id = (resp.get("result") or {}).get("message_id")
        if mesaj_id:
            _panel_yaz(int(mesaj_id))
        return True
    return False


def panel_goster(metin: str, butonlar: list[list[dict[str, Any]]], yeni_mesaj: bool = False) -> bool:
    """Panelde HER etkileşim aynı mesajı düzenler (TODO 4 — istisnasız).

    editMessageText + reply_markup kullanılır. Yeni mesaj yalnızca:
    (a) panel kaydı yok / kayıt >48 saat,
    (b) düzenlenecek mesaj Telegram'da bulunamadı (kullanıcı silmiş).

    `yeni_mesaj` parametresi geriye dönük uyumluluk içindir ve YOK SAYILIR
    (2026-11-11 düzeltmesi). Sebep: kuyrukta biriken N adet /start art arda
    işlenince N taze panel açılıyordu — kullanıcının gördüğü "üst üste menüler".

    "message is not modified" hatası değişiklik-yok demektir: yakalanır, sessizce
    yutulur (hata sayılmaz).

    Döner: True = panel güncellendi/oluşturuldu.
    """
    del yeni_mesaj  # kasıtlı olarak yok sayılır — aşağıdaki mantık tek doğru kaynaktır
    panel_id, zaman = _panel_oku()
    if panel_id is not None and zaman is not None:
        if datetime.now(UTC) - zaman <= PANEL_48_SAAT:
            sonuc = api_call(
                "editMessageText",
                {
                    "chat_id": CHAT_ID,
                    "message_id": panel_id,
                    "text": _html_guvenli(metin),
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": butonlar},
                },
            )
            if sonuc is not None and sonuc.get("ok"):
                return True
            aciklama = str(sonuc.get("description", "")) if isinstance(sonuc, dict) else ""
            if "message is not modified" in aciklama.lower():
                print("[Panel] İçerik zaten güncel — sessizce geçildi")
                return True
            print("[Panel] Panel mesajı düzenlenemedi — taze panel açılıyor")
        else:
            print("[Panel] Panel mesajı 48 saatten eski — taze panel açılıyor")
        _panel_temizle()
    return _panel_yeni_gonder(metin, butonlar)


def _ilerleme_cubugu(oran: float, genislik: int = 6) -> str:
    """Metin ilerleme çubuğu: ▰▰▰▱▱▱ 3/6 (TODO 16 görsel dil, TODO 14'te kullanılır)."""
    oran = max(0.0, min(1.0, oran))
    dolu = int(round(oran * genislik))
    return "▰" * dolu + "▱" * (genislik - dolu)


SPARKLINE_KARAKTER = "▁▂▃▄▅▆▇█"


def _sparkline(degerler: list[float]) -> str:
    """7 günlük metin grafiği (TODO 16) — Telegram'da grafik yerine geçer.

    Tüm değerler eşitse orta seviye karakter döner (yanıltıcı zirve çizmez).
    Boş liste → boş metin (ekran satırı düşer, uydurma yok).
    """
    if not degerler:
        return ""
    en_az, en_cok = min(degerler), max(degerler)
    if en_cok == en_az:
        return SPARKLINE_KARAKTER[3] * len(degerler)
    adim = len(SPARKLINE_KARAKTER) - 1
    return "".join(
        SPARKLINE_KARAKTER[round((d - en_az) / (en_cok - en_az) * adim)] for d in degerler
    )


def _yas_turkce(dakika: int) -> str:
    """Dakika → insan dilinde yaş ('az önce', '12 dk önce', '3 sa önce', '2 gün önce')."""
    if dakika < 2:
        return "az önce"
    if dakika < 90:
        return f"{dakika} dk önce"
    if dakika < 60 * 48:
        return f"{dakika // 60} sa önce"
    return f"{dakika // (60 * 24)} gün önce"


def _kadans_etiketi() -> str:
    """Panelde kadans ifadesi (tek kaynak: modules/kadans.py)."""
    with suppress(Exception):
        from modules.kadans import KADANS_DK

        if KADANS_DK % 60 == 0:
            return f"{KADANS_DK // 60} sa"
        return f"{KADANS_DK} dk"
    return "bilinmiyor"


def _saglik_satiri() -> str:
    """Kanal sağlığı: ölçülmüş izlenme + akışa giriş oranı (yoksa dürüst boş)."""
    with suppress(Exception):
        from modules.kanal_sagligi import panel_satiri

        return panel_satiri()
    return "🩺 Kanal: ölçüm yok"


def _cadans_satiri() -> str:
    """Son ÖLÇÜLMÜŞ cron cadansı (cron ifadesine değil, gerçek koşulara bakar)."""
    with suppress(Exception):
        from modules.cadans_olcum import panel_satiri

        return panel_satiri()
    return "📉 Cadans: bilinmiyor (ölçüm yok)"


def _cadans_ozeti() -> str:
    """`_cadans_satiri()`nin öneksiz hâli (kartta '📉' iki kez yazılmasın)."""
    return _cadans_satiri().removeprefix("📉 Cadans: ")


def _durum_turkce(ham: object) -> str:
    """GitHub koşu sonucunu Türkçeleştirir (panelde 'in_progress'/'timed_out' kalmasın)."""
    return {
        "success": "✅ başarılı",
        "failure": "❌ başarısız",
        "cancelled": "⛔ iptal",
        "skipped": "⏭ atlandı",
        "timed_out": "⌛ zaman aşımı",
        "in_progress": "🔄 çalışıyor",
        "queued": "⏳ sırada",
        "waiting": "⏳ sırada",
        "requested": "⏳ sırada",
    }.get(str(ham), f"❔ {ham}")


def _bugun_kalite_ozeti() -> tuple[str, str]:
    """Bugünün geçen video sayısı + ortalama kalite puanı (veri yoksa '—').

    Ana kartta görünür: kullanıcı "her şey elimin altında olsun" dedi; geçen
    sayısı ve kalite ortalaması daha önce yalnız Rapor ekranındaydı.
    """
    with suppress(Exception):
        from modules.kalite_log import kalite_istatistik

        ist = kalite_istatistik(datetime.now(UTC).strftime("%Y-%m-%d"))
        if ist.get("toplam"):
            return str(ist.get("gecen", 0)), f"{ist.get('ortalama_puan', 0)}/100"
    return "—", "—"


def _son_7gun_seri() -> list[float]:
    """Son 7 günün günlük yayın sayısı (eski → yeni). Veri yoksa boş liste."""
    arsiv = Path("bobi_tv/archive/videos.json")
    if not arsiv.exists():
        return []
    try:
        veri = json.loads(arsiv.read_text(encoding="utf-8"))
        kayitlar = list(veri.values()) if isinstance(veri, dict) else list(veri)
    except Exception:
        return []
    seri: list[float] = []
    for geri in range(6, -1, -1):
        gun = (datetime.now(UTC) - timedelta(days=geri)).strftime("%Y-%m-%d")
        seri.append(float(sum(1 for k in kayitlar if str(k.get("tarih", ""))[:10] == gun)))
    return seri


def _bugun_arsiv_ozeti() -> tuple[int, int]:
    """(bugün üretilen, bugün yayına alınan) — uydurma yok: okunamazsa (0, 0)."""
    arsiv = Path("bobi_tv/archive/videos.json")
    bugun = datetime.now(UTC).strftime("%Y-%m-%d")
    if not arsiv.exists():
        return 0, 0
    try:
        veri = json.loads(arsiv.read_text(encoding="utf-8"))
        kayitlar = list(veri.values()) if isinstance(veri, dict) else list(veri)
        bugunkuler = [k for k in kayitlar if str(k.get("tarih", ""))[:10] == bugun]
        # "Yayında" = kanalda DURAN geçerli kayıt. 2026-11-11 düzeltmesi:
        # kaldırılan (kaldirildi / silindi_dusuk_izlenme) videolar sayıya
        # girmiyordu ama `durum` alanı hiç yazılmamış eski kayıtlar da
        # sayılmıyordu → panel 8 "yayında" gösterirken kanalda 0 video vardı.
        # Artık: durum alanı yoksa video geçerli sayılır (esitleme bunu
        # kanaldan doğrular).
        gecersiz = {"kaldirildi", "silindi_dusuk_izlenme"}
        return len(bugunkuler), sum(
            1 for k in bugunkuler if str(k.get("durum", "yayinda")) not in gecersiz
        )
    except Exception:
        return 0, 0


def ekran_ana() -> tuple[str, list[list[dict[str, Any]]]]:
    """ANA EKRAN = canlı durum kartı (TODO 14).

    Statik karşılama yerine 4-5 satır canlı özet. Veri okunamazsa her satır
    'bilinmiyor' der — sayı UYDURULMAZ (mevcut felsefe korunur).
    """
    uretilen, yayinda = _bugun_arsiv_ozeti()
    # KOTA KALDIRILDI (2026-11-11): kota_state okuması da kaldırıldı — ana
    # ekranda "kota dolu" diye bir durum yok, gereksiz import da yok.
    kuyruk = Path("bobi_tv/queue")
    kuyruk_sayisi = len(list(kuyruk.glob("*.json"))) if kuyruk.exists() else 0

    # KULLANICI KARARI (2026-11-11): "Kota 6 istemiyorum, kotayı kaldır."
    # Kota satırı ve ilerleme çubuğu KALDIRILDI — yükleme tavanı yok.
    #
    # TASARIM (2026-11-11, kullanıcı: "modern, kullanıcı dostu, her şey elim
    # altında"): düz satır listesi yerine 3 blok — DURUM / BUGÜN / SİSTEM.
    # Bloklar ince ayırıcıyla ayrılır (Telegram'da kutu yok, '─' evrensel).
    # KALİTE ORTALAMASI + geçen video sayısı da kartta (rapor ekranında vardı,
    # ana kartta yoktu → kullanıcı "her şey elimin altında" istedi).
    gecen, kalite = _bugun_kalite_ozeti()
    ayirici = "─────────────"
    # TASARIM (2026-11-11, 2. tur): "Bugün" iki kez yazılıyordu (başlık +
    # hem Üretilen hem Yayında satırı). Tek blok + kanal sağlığı satırı:
    # kullanıcının asıl sorduğu "kanal ne durumda" sorusu kartın içinde.
    metin = (
        "🎬 <b>BOBİ TV</b>  ·  <i>kontrol paneli</i>\n"
        f"{ayirici}\n"
        f"🎥 Bugün <b>{uretilen}</b> üretim · 🚀 <b>{yayinda}</b> yayında · "
        f"📦 Stok <b>{kuyruk_sayisi}</b>\n"
        f"✅ Geçen <b>{gecen}</b> · 🎯 Kalite <b>{kalite}</b> · "
        f"📐 Tavan <b>YOK</b>\n"
        f"{_saglik_satiri()}\n"
        f"{ayirici}\n"
        "🛠 <b>Sistem</b>\n"
        f"│ 🕐 Son koşu: {_son_kosu_ozeti()}\n"
        f"│ 📡 Bot: {_poller_ozeti()}\n"
        f"│ 📉 Kadans: {_kadans_etiketi()} hedef · {_cadans_ozeti()}"
    )
    try:
        from modules.bildirim import susturulmus_mu

        if susturulmus_mu():
            metin += "\n⏸ Bildirimler susturuldu (Ayarlar → Sistem'den aç)"
    except Exception:
        pass
    seri = _son_7gun_seri()
    if seri:
        # <code> içinde: sabit genişlikli görünüm. TODO 13 ile <code> korunuyor.
        metin += f"\n📈 7 gün: <code>{_sparkline(seri)}</code> ({int(sum(seri))} video)"
    return metin, get_main_menu_buttons()


#: "← Geri" için callback → ekran üreticisi (geri hedefi yeniden çizilir).

def get_main_menu_buttons() -> list[list[dict[str, Any]]]:
    """Ana menü: 6 düğmeden 4'e iner (TODO 3).
    İstatistik + Kalite + Yükleme 'Rapor' altına girer."""
    # KOTA KALDIRILDI: buton her zaman "🎬 Üret" — "kota dolu" durumu yok.
    uret_etiketi = "🎬 Üret"
    return [
        [
            {"text": "📊 Durum", "callback_data": "status_now"},
            {"text": uret_etiketi, "callback_data": "uret_menu"},
        ],
        [
            {"text": "📈 Rapor", "callback_data": "rapor_goster"},
            {"text": "⚙️ Ayarlar", "callback_data": "ay:kok"},
        ],
    ]


def _duz_metin(metin: str) -> str:
    """Emoji/işaretleri atıp küçük harfe indirger (alt klavye eşlemesi için)."""
    temiz = "".join(c for c in str(metin) if c.isalnum() or c.isspace() or c in "çğıöşüÇĞİÖŞÜ")
    return " ".join(temiz.lower().split())


def _klavye_kuruldu_mu() -> bool:
    """Alt klavye daha önce kuruldu mu? (BİR KEZ kuralı — mesaj şişmesin.)"""
    try:
        if MENU_STATE_YOLU.exists():
            veri = json.loads(MENU_STATE_YOLU.read_text(encoding="utf-8"))
            return bool(veri.get("klavye_kuruldu"))
    except Exception:
        pass
    return False


def _klavye_kuruldu_isaretle() -> None:
    try:
        veri: dict[str, Any] = {}
        if MENU_STATE_YOLU.exists():
            with suppress(Exception):
                veri = json.loads(MENU_STATE_YOLU.read_text(encoding="utf-8"))
        veri["klavye_kuruldu"] = True
        MENU_STATE_YOLU.parent.mkdir(parents=True, exist_ok=True)
        MENU_STATE_YOLU.write_text(json.dumps(veri), encoding="utf-8")
    except Exception:
        pass


def klavye_gonder(zorla: bool = False) -> bool:
    """KALICI alt menüyü BİR KEZ gönderir (kısa taşıyıcı mesaj).

    NEDEN AYRI MESAJ: Telegram'da kalıcı klavye yalnız `sendMessage` ile
    kurulabilir (`editMessageText` klavye değiştiremez). Bu yüzden ilk
    /start'ta tek satırlık bir taşıyıcı mesaj gönderilir; sonraki /start'larda
    TEKRAR GÖNDERİLMEZ (mesaj şişmesi yok) — panel yine tek mesajda düzenlenir.
    """
    if not BOT_TOKEN or not CHAT_ID:
        return False
    if not zorla and _klavye_kuruldu_mu():
        return False
    govde = api_call(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": "🎛 <b>Menü hazır</b> — aşağıdaki düğmeler her zaman elinin altında.",
            "parse_mode": "HTML",
            "reply_markup": {
                "keyboard": [[{"text": m} for m in satir] for satir in REPLY_KLAVYE],
                "resize_keyboard": True,
                "is_persistent": True,
                "input_field_placeholder": "Menüden seç veya yaz…",
            },
        },
    )
    if govde and govde.get("ok"):
        _klavye_kuruldu_isaretle()
        return True
    return False


def klavye_gizle() -> bool:
    """Alt klavyeyi kaldırır (kullanıcı isterse)."""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    govde = api_call(
        "sendMessage",
        {"chat_id": CHAT_ID, "text": "Klavye kapatıldı. /start ile geri gelir.",
         "reply_markup": {"remove_keyboard": True}},
    )
    return bool(govde and govde.get("ok"))


def menyu_gonder(yeni_mesaj: bool = False) -> bool:
    """Ana menüyü göster — edit-in-place (tek panel felsefesi).

    `yeni_mesaj` parametresi geriye dönük uyumluluk için durur ama artık YOK SAYILIR:
    panel geçerliyse her zaman aynı mesaj düzenlenir. Yeni mesaj kararı yalnızca
    panel_goster'in kayıt/48 saat/edit-404 mantığıyla verilir.
    """
    metin, butonlar = ekran_ana()
    return panel_goster(metin, butonlar, yeni_mesaj=yeni_mesaj)


# ---------------------------------------------------------------------------
# Durum / rapor metinleri
# ---------------------------------------------------------------------------


def _kota_birim_ozeti() -> str:
    """TODO 10 panel satırı — modules/kota_kapisi.kota_durumu_ozeti'ne delegasyon.
    Birim bilgisi youtube_quota.json'da YOKSA 'bilinmiyor' yazar — sayı UYDURULMAZ."""
    return kota_durumu_ozeti(KOTA_YOLU)


def get_status_text() -> str:
    arsiv = Path("bobi_tv/archive/videos.json")
    bugun = datetime.now(UTC).strftime("%Y-%m-%d")
    bugunki = 0
    if arsiv.exists():
        try:
            kayitlar = json.loads(arsiv.read_text(encoding="utf-8"))
            bugunki = sum(1 for k in kayitlar if str(k.get("tarih", ""))[:10] == bugun)
        except Exception:
            pass
    kuyruk = Path("bobi_tv/queue")
    kuyruk_sayisi = len(list(kuyruk.glob("*.json"))) if kuyruk.exists() else 0
    log_dosya = Path(f"bobi_tv/logs/{bugun}.log")
    son_calisma = "Bilinmiyor"
    if log_dosya.exists():
        try:
            with open(log_dosya, encoding="utf-8") as f:
                for line in reversed(f.readlines()):
                    if "===" in line:
                        son_calisma = line.split("[")[1].split("]")[0] if "[" in line else "Bilinmiyor"
                        break
        except Exception:
            pass
    ayirici = "─────────────"
    return (
        f"🖥 <b>Sistem Durumu</b>  ·  <i>{bugun}</i>\n"
        f"{ayirici}\n"
        "📊 <b>Bugün</b>\n"
        f"│ 🎬 Üretilen: <b>{bugunki}</b>   📦 Stokta: <b>{kuyruk_sayisi}</b>\n"
        f"│ 📈 Yükleme tavanı: <b>YOK</b>\n"
        f"{ayirici}\n"
        "⚙️ <b>Sistem</b>\n"
        f"│ 🕐 Son çalışma: {son_calisma}\n"
        f"│ 🤖 Pipeline: {PIPELINE_SURUM}"
    )


def get_stats_text() -> str:
    from modules.kalite_log import kalite_istatistik

    bugun = datetime.now(UTC).strftime("%Y-%m-%d")
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

    bugun = datetime.now(UTC).strftime("%Y-%m-%d")
    istatistik = kalite_istatistik(bugun)
    if istatistik["toplam"] == 0:
        return f"🎯 <b>Kalite Raporu ({bugun})</b>\n\nBugün için kalite verisi yok."
    gecme_orani = (
        round(istatistik["gecen"] / istatistik["toplam"] * 100, 1) if istatistik["toplam"] > 0 else 0
    )
    return (
        f"🎯 <b>Kalite Raporu ({bugun})</b>\n\n"
        f"📊 Ortalama: {istatistik['ortalama_puan']}/100\n✅ Geçme Oranı: {gecme_orani}%\n\n"
        f"<b>Detaylar:</b>\n• Loop + Hook: %50\n• Timing: %25\n• Dialogue: %25\n\n🎯 Eşik: 70/100"
    )


def get_quota_text() -> str:
    from modules.kota_state import kota_state_oku

    state = kota_state_oku()
    guncelleme = state.get("guncelleme", "Bilinmiyor")
    video_sayisi = state.get("video_sayisi", 0)
    # KULLANICI KARARI (2026-11-11): "kotayı kaldır" → kota durumu ekranı YOK.
    # Ekran bilgi amaçlı kalır: yüklenen video sayısı + "tavan yok".
    return (
        "<b>Yükleme Durumu</b>\n\n"
        "✅ Günlük yükleme tavanı: YOK\n"
        f"🎬 Bugün yüklenen: {video_sayisi}\n"
        f"📅 Son güncelleme: {guncelleme[:16] if guncelleme else 'Bilinmiyor'}\n\n"
        "Üretilen her video yüklenir. Sınır yok."
    )


def get_help_text() -> str:
    return (
        "❓ <b>BOBİ TV Kontrol Paneli</b>\n\n<b>Düğmeler:</b>\n"
        "📊 <b>Durum</b> - Sistem durumu\n🎬 <b>Üret</b> - Manuel üretim + render testi\n"
        "📈 <b>Rapor</b> - İstatistik + Kalite + Yükleme\n⚙️ <b>Ayarlar</b> - Hiyerarşik ayar menüsü\n\n"
        "<b>Üretim:</b>\n"
        "• Günlük yükleme tavanı: YOK (kota kaldırıldı — üretilen her video yüklenir)\n"
        "• Günlük hedef / mod: Ayarlar → Üretim ve Kota\n"
        "• Kalite eşiği: 70/100\n\n"
        "<b>Not:</b> Kota doluyken ÜRETİM SÜRER; video STOĞA alınır ve kota açılınca yüklenir.\n"
        "⏰ <b>Not:</b> Komutlar GitHub cron zamanlamasıyla işlenir; GitHub gecikmesiyle "
        "cevap genellikle 15-60 dakika içinde gelir."
    )


def ekran_7gun() -> tuple[str, list[list[dict[str, Any]]]]:
    """📅 7 günlük trend (TODO 19, Kaan): sparkline + geçme oranı + kota tahmini.

    TAHMİN açıkça "tahmin" olarak etiketlenir (uydurma kesinlik yok).
    """
    from modules.kalite_log import kalite_istatistik

    seri = _son_7gun_seri()
    satirlar = ["📅 <b>7 Günlük Trend</b>", ""]
    if not seri or sum(seri) == 0:
        satirlar.append(f"⛔ Veri yok: {BILINMIYOR}")
        butonlar = [[{"text": "🔄 Yenile", "callback_data": "rapor_7gun"}], list(GERI_MENUSU)]
        return "\n".join(satirlar), butonlar

    satirlar.append(f"📈 Üretim: <code>{_sparkline(seri)}</code>")
    satirlar.append(f"📊 Toplam: {int(sum(seri))} video · günlük ort. {sum(seri) / len(seri):.1f}")
    satirlar.append("")

    # Kalite: son 7 günün geçme oranı (veri yoksa bilinmiyor)
    gecen, toplam = 0, 0
    for geri in range(7):
        gun = (datetime.now(UTC) - timedelta(days=geri)).strftime("%Y-%m-%d")
        try:
            ist = kalite_istatistik(gun)
            toplam += int(ist.get("toplam", 0) or 0)
            gecen += int(ist.get("gecti", 0) or 0)
        except Exception:
            continue
    if toplam:
        satirlar.append(f"✅ Kalite geçme: {gecen}/{toplam} (%{round(gecen / toplam * 100)})")
    else:
        satirlar.append(f"✅ Kalite geçme: {BILINMIYOR} (kayıt yok)")

    # Kota harcama tahmini: bugünkü yayın hızından gün sonu
    uretilen, yayinda = _bugun_arsiv_ozeti()
    simdi = datetime.now(UTC)
    gecen_saat = simdi.hour + simdi.minute / 60
    if yayinda and gecen_saat > 0.5:
        tahmin = round(yayinda / gecen_saat * 24, 1)
        satirlar.append(f"💰 Tahmin: bu hızla gün sonu ≈ {tahmin} yükleme (tavan yok)")
        satirlar.append("   <i>tahmin</i> — geçmiş hıza dayanır, garanti değil")
    else:
        satirlar.append(f"💰 Kota tahmini: {BILINMIYOR} (yeterli veri yok)")

    butonlar = [
        [{"text": "🏆 Performans", "callback_data": "performans"}],
        [{"text": "🔄 Yenile", "callback_data": "rapor_7gun"}],
        list(GERI_MENUSU),
    ]
    return "\n".join(satirlar), butonlar


def ekran_performans() -> tuple[str, list[list[dict[str, Any]]]]:
    """🏆 Performans ekranı (TODO 17): son 10 video, outlier skoru, en iyi/kötü 3.

    Veri okunamazsa "bilinmiyor" yazar — sayı UYDURULMAZ.
    """
    from modules.performans import en_iyi_en_kotu, performans_ozeti

    sonuc = performans_ozeti(azami=10)
    satirlar = ["🏆 <b>Performans</b>", ""]
    if sonuc["hata"]:
        satirlar.append(f"⛔ Veri okunamadı: {sonuc['hata']}")
        satirlar.append("Uydurma sayı yazmıyoruz.")
        butonlar = [
            # Hata olsa bile trende erişim kalır (kullanıcı yolu tıkanmaz).
            [{"text": "📅 7 günlük trend", "callback_data": "rapor_7gun"}],
            [{"text": "🔄 Yenile", "callback_data": "performans"}],
            list(GERI_MENUSU),
        ]
        return "\n".join(satirlar), butonlar

    videolar = sonuc["videolar"]
    medyan = sonuc["medyan"]
    satirlar.append(f"📊 Kanal medyanı: {medyan if medyan is not None else BILINMIYOR} izlenme")
    satirlar.append("")
    en_iyi, en_kotu = en_iyi_en_kotu(videolar, 3)
    satirlar.append("<b>En iyi 3:</b>")
    for v in en_iyi:
        skor = f"{v['skor']}x" if v["skor"] is not None else "—"
        satirlar.append(f"• {v['baslik']} — {v['izlenme']} ({skor})")
    satirlar.append("<b>En kötü 3:</b>")
    for v in en_kotu:
        skor = f"{v['skor']}x" if v["skor"] is not None else "—"
        satirlar.append(f"• {v['baslik']} — {v['izlenme']} ({skor})")
    butonlar = [
        [{"text": "📅 7 günlük trend", "callback_data": "rapor_7gun"}],
        [{"text": "🔄 Yenile", "callback_data": "performans"}],
        list(GERI_MENUSU),
    ]
    return "\n".join(satirlar), butonlar


def ekran_bildirim() -> tuple[str, list[list[dict[str, Any]]]]:
    """Bildirim ayarları ekranı (TODO 24): sustur + özet + sessiz saat özeti."""
    from modules.bildirim import OZET_SAATI, SESSIZ_BASLANGIC, SESSIZ_BITIS, _ayar, durum_oku

    veri = durum_oku()
    sustur_bitis = veri.get("sustur_until")
    satirlar = [
        "🔔 <b>Bildirimler</b>",
        "",
        f"🌙 Sessiz saat: {_ayar('SESSIZ_BASLANGIC', SESSIZ_BASLANGIC)}–"
        f"{_ayar('SESSIZ_BITIS', SESSIZ_BITIS)} (TR)",
        f"📋 Günlük özet: {_ayar('OZET_SAATI', OZET_SAATI)} (TR)",
        "",
    ]
    if sustur_bitis:
        satirlar.append(f"⏸ <b>Susturuldu</b> — {str(sustur_bitis)[:16]}'e kadar")
        satirlar.append("Ayarlar silinmedi, yalnız ertelendi.")
        butonlar = [
            [{"text": "▶️ Bildirimleri aç", "callback_data": "bildirim_ac"}],
            [{"text": "📋 Özeti şimdi gönder", "callback_data": "bildirim_ozet"}],
            list(GERI_MENUSU),
        ]
    else:
        satirlar.append("✅ Bildirimler açık")
        satirlar.append(f"📥 Bekleyen: {len(veri.get('bekleyen') or [])} olay")
        satirlar.append("")
        satirlar.append("🔴 Kritik: sessiz saati deler")
        satirlar.append("🔔 Normal: sessiz saatte bekler")
        butonlar = [
            [
                {"text": "⏸ 1 saat sustur", "callback_data": "bildirim_sustur1"},
                {"text": "⏸ 1 gün", "callback_data": "bildirim_sustur24"},
            ],
            [{"text": "📋 Özeti şimdi gönder", "callback_data": "bildirim_ozet"}],
            list(GERI_MENUSU),
        ]
    return "\n".join(satirlar), butonlar


def ekran_yardim() -> tuple[str, list[list[dict[str, Any]]]]:
    """Yardım ekranı — /help metin komutu da buraya yönlenir (tek panel)."""
    return get_help_text(), [
        # 2026-11-11: kullanıcı Mini App İSTEMİYOR → yardım ekranındaki açılış
        # düğmesi kaldırıldı. Mini App kodu/sayfası duruyor ama erişim yolu
        # yalnız /help menüsünden değil, paneldeki "📱 Mini App" ekranından.
        [
            {"text": "❓ Sistem ne yapar", "callback_data": "sistem_nedir"},
            {"text": "📊 Rapor", "callback_data": "rapor_goster"},
        ],
        [{"text": "⚙️ Ayarlar", "callback_data": "ay:kok"}],
        [{"text": "← Geri", "callback_data": "menu_main"}, {"text": "🏠 Menü", "callback_data": "menu_main"}],
    ]


# ---------------------------------------------------------------------------
# GitHub tetikleme (workflow_dispatch + repository_dispatch)
# ---------------------------------------------------------------------------


#: Üretim tetikleme cooldown'u (saniye). Çift dokunuş = iki workflow koşusu
#: olmasın; ayrıca ücretli/kotalı bir işi yanlışlıkla iki kez başlatmayı keser.
URETIM_COOLDOWN_SN = 120

#: TODO 26 — yanlış tetiklemeyi 10 dakika içinde İPTAL edebilme penceresi.
IPTAL_PENCERESI_SN = 600


def _cooldown_dosyasi() -> Path:
    return Path(os.environ.get("BOBI_COOLDOWN_YOLU", "bobi_tv/state/uretim_cooldown.json"))


# ---------------------------------------------------------------------------
# TODO 25 — İMZALI + SÜRELİ CALLBACK (Emre / güvenlik)
#
# SORUN: Eski bir panel mesajındaki buton haftalar sonra basılırsa hâlâ
# çalışıyordu (bayat aksiyon). Riskli aksiyonlarda (üret, onayla, sil)
# butonun tazeliği kanıtlanmalı.
#
# ÇÖZÜM: callback_data içine kısa HMAC etiketi + bitiş zamanı gömülür.
# Anahtar bot token'ından TÜRETİLİR (ayrı secret yok) ve chat_id'ye bağlanır
# (başka sohbetten kopyalanan buton çalışmaz).
#
# SINIR: Telegram callback_data en fazla 64 BAYT. Bu yüzden etiket kısa
# tutulur: "<aksiyon>:<son_kullanma>:<imza>" → ör. uret_onay:1a2b3c:9f8e7d
# ---------------------------------------------------------------------------

#: İmza gerektiren riskli aksiyonlar (diğerleri imzasız kalır — 64 bayt sınırı).
IMZALI_AKSIYONLAR: tuple[str, ...] = ("uret_onay", "uret_baslat", "ay:onay", "ay:onayd")

#: İmza geçerlilik süresi (saniye). 30 dk: kullanıcı paneli açık bırakabilir.
IMZA_GECERLILIK_SN = 30 * 60


def _imza_anahtari() -> bytes:
    """HMAC anahtarı: bot token'ından türetilir (ayrı secret saklanmaz)."""
    import hashlib

    tohum = f"{BOT_TOKEN}|{CHAT_ID}|bobi-imza-v1".encode()
    return hashlib.sha256(tohum).digest()


def imzali_callback(aksiyon: str, simdi: float | None = None) -> str:
    """Riskli aksiyon için imzalı + süreli callback_data üretir (≤64 bayt)."""
    import hashlib
    import hmac
    import time as _time

    son = int((simdi if simdi is not None else _time.time()) + IMZA_GECERLILIK_SN)
    son_kisa = format(son, "x")  # hex → kısa
    imza = hmac.new(
        _imza_anahtari(), f"{aksiyon}:{son_kisa}".encode(), hashlib.sha256
    ).hexdigest()[:10]
    return f"{aksiyon}:{son_kisa}:{imza}"


def imza_dogrula(callback_data: str) -> tuple[bool, str]:
    """İmzalı callback'i doğrular. Döner: (geçerli_mi, aksiyon|sebep).

    İmzasız aksiyonlar buraya gelmez (çağıran `imza_gerekli` ile ayırır).
    """
    import hashlib
    import hmac
    import time as _time

    parcalar = callback_data.split(":")
    # "ay:onay:<son>:<imza>" gibi iki noktalı aksiyonlar da desteklenir.
    if len(parcalar) < 3:
        return False, "biçim"
    imza, son_hex = parcalar[-1], parcalar[-2]
    aksiyon = ":".join(parcalar[:-2])
    try:
        son = int(son_hex, 16)
    except ValueError:
        return False, "biçim"
    beklenen = hmac.new(
        _imza_anahtari(), f"{aksiyon}:{son_hex}".encode(), hashlib.sha256
    ).hexdigest()[:10]
    if not hmac.compare_digest(imza, beklenen):
        return False, "imza uyuşmuyor"
    if son < _time.time():
        return False, "süresi geçti"
    return True, aksiyon


def imzali_ay_callback(aksiyon: str, *parcalar: Any, simdi: float | None = None) -> str:
    """`ay:onay:<anahtar>:<indeks>` gibi payload'lı imzalı callback üretir.

    ÖNEMLİ: payload (anahtar/indeks) İMZAYA DAHİL edilir; aksi halde
    imza payload'ı korumaz ve doğrulama sonrası aksiyon bozulur.
    Biçim: <aksiyon>:<payload...>:<son_hex>:<imza>
    """
    import hashlib
    import hmac
    import time as _time

    govde = ":".join([aksiyon, *[str(p) for p in parcalar]])
    son = int((simdi if simdi is not None else _time.time()) + IMZA_GECERLILIK_SN)
    son_kisa = format(son, "x")
    imza = hmac.new(
        _imza_anahtari(), f"{govde}:{son_kisa}".encode(), hashlib.sha256
    ).hexdigest()[:10]
    return f"{govde}:{son_kisa}:{imza}"


def imza_gerekli(callback_data: str) -> bool:
    """Bu callback imza taşımalı mı? (riskli aksiyonlar)

    İMZALI veri de tanınır: "uret_onay:<son>:<imza>" → aksiyon "uret_onay".
    Sondaki iki parça (son kullanma + imza) atılır, kalanı aksiyondur.
    """
    parcalar = callback_data.split(":")
    if callback_data in IMZALI_AKSIYONLAR:
        return True
    # İki noktalı aksiyonlar (ay:onay) imzasız hâlde de tanınmalı.
    if len(parcalar) >= 2 and f"{parcalar[0]}:{parcalar[1]}" in IMZALI_AKSIYONLAR:
        return True
    # İmzalı biçim: son iki parça (hex zaman + hex imza) atılır.
    if len(parcalar) >= 3:
        aday = ":".join(parcalar[:-2])
        return aday in IMZALI_AKSIYONLAR
    return False


def uretim_cooldown_kalan() -> int:
    """Kalan cooldown süresi (sn). 0 → tetikleme serbest."""
    try:
        veri = json.loads(_cooldown_dosyasi().read_text(encoding="utf-8"))
        son = float(veri.get("son_tetik", 0))
        return max(0, int(URETIM_COOLDOWN_SN - (time.time() - son)))
    except Exception:
        return 0


def uretim_cooldown_baslat() -> None:
    try:
        yol = _cooldown_dosyasi()
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps({"son_tetik": time.time()}), encoding="utf-8")
    except Exception as e:
        print(f"[Telegram Bot] cooldown yazılamadı: {str(e)[:80]}")


def trigger_production_kontrollu() -> str:
    """Onaylanmış tetikleme: cooldown kontrolü + kayıt. Çift koşu üretmez."""
    kalan = uretim_cooldown_kalan()
    if kalan > 0:
        return (
            f"⏳ Zaten tetiklendi — {kalan} sn sonra tekrar denenebilir. "
            "İkinci workflow koşusu başlatılmadı."
        )
    sonuc = trigger_production()
    # Yalnız BAŞARILI tetiklemede cooldown başlat (hata → tekrar denenebilsin).
    if sonuc.startswith("✅") or "tetiklendi" in sonuc.lower():
        uretim_cooldown_baslat()
        # TODO 26/27: iptal penceresi + denetim kaydı (geri alınamaz aksiyon).
        _iptal_penceresi_baslat()
        denetim.kaydet(
            "uretim_tetikle",
            "ok",
            ayrinti={"iptal_penceresi_sn": IPTAL_PENCERESI_SN},
        )
    else:
        denetim.kaydet("uretim_tetikle", "basarisiz", ayrinti={"mesaj": sonuc[:120]})
    return sonuc


# ---------------------------------------------------------------------------
# TODO 26 — 10 dk cool-off + İPTAL
# ---------------------------------------------------------------------------


def _iptal_dosyasi() -> Path:
    return Path(os.environ.get("BOBI_IPTAL_YOLU", "bobi_tv/state/uretim_iptal.json"))


def _iptal_penceresi_baslat(simdi: float | None = None) -> None:
    """Tetikleme sonrası iptal penceresini açar (yanlış tetikleme telafisi)."""
    import time as _time

    simdi = simdi if simdi is not None else _time.time()
    yol = _iptal_dosyasi()
    try:
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(
            json.dumps({"tetikleme": simdi, "bitis": simdi + IPTAL_PENCERESI_SN}),
            encoding="utf-8",
        )
    except OSError:
        pass


def iptal_kalan_sn(simdi: float | None = None) -> int:
    """İptal penceresi açıksa kalan saniye; kapalıysa 0."""
    import time as _time

    simdi = simdi if simdi is not None else _time.time()
    try:
        veri = json.loads(_iptal_dosyasi().read_text(encoding="utf-8"))
        bitis = float(veri.get("bitis", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0
    return max(0, int(bitis - simdi))


def uretim_iptal_et() -> tuple[bool, str]:
    """Son tetiklemeyi İPTAL eder (10 dk içinde). Döner: (başarılı, mesaj).

    Video üretimi çoktan başladıysa yükleme yine de olabilir; bu yüzden mesaj
    bunu AÇIKÇA söyler — yalan vaat yok.
    """
    kalan = iptal_kalan_sn()
    if kalan <= 0:
        return False, (
            "⛔ İptal penceresi kapandı (10 dk geçti).\n"
            "Koşu GitHub Actions'ta görünüyorsa oradan elle iptal edilebilir."
        )
    yol = _iptal_dosyasi()
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        veri["iptal"] = True
        yol.write_text(json.dumps(veri), encoding="utf-8")
    except (OSError, ValueError):
        return False, "⛔ İptal kaydı yazılamadı."
    denetim.kaydet("uretim_iptal", "ok", ayrinti={"kalan_sn": kalan})
    return True, (
        f"🛑 İptal kaydedildi (pencereden {kalan} sn kaldı).\n"
        "Pipeline bu turda yüklemeyi durdurur. Zaten render alınmışsa video "
        "stoğa yazılır, KAYBOLMAZ."
    )


def ekran_uret_onay() -> tuple[str, list[list[dict[str, Any]]]]:
    """Üretim tetikleme ONAY ekranı (TODO 13: onaysız tetikleme kapatıldı).

    Riskli işlem tek dokunuşla olmaz kuralı: üretim GitHub Actions koşusu
    başlatır, video yayınlar ve YouTube kotası harcar → onay gerekir.
    """
    kalan = uretim_cooldown_kalan()
    if kalan > 0:
        metin = (
            "⏳ <b>Üretim zaten tetiklendi</b>\n\n"
            f"Çift dokunuşu engellemek için {kalan} sn beklemelisin.\n"
            "Koşu başladıysa sonuç birkaç dakika içinde Rapor ekranına düşer."
        )
        butonlar = [
            [{"text": "📊 Rapora git", "callback_data": "rapor_goster"}],
            [
                {"text": "← Geri", "callback_data": "uret_menu"},
                {"text": "🏠 Menü", "callback_data": "menu_main"},
            ],
        ]
        return metin, butonlar
    metin = (
        "⚠️ <b>Üretimi başlatmak üzeresin</b>\n\n"
        "Bu işlem GitHub Actions koşusu başlatır: video üretilir ve\n"
        "kota varsa <b>YouTube'a yüklenir</b>.\n\n"
        f"{_kota_birim_ozeti()}"
    )
    butonlar = [
        [renkli_buton("✅ Evet, başlat", imzali_callback("uret_onay"), "onay")],
        [
            {"text": "← Vazgeç", "callback_data": "uret_menu"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ],
    ]
    return metin, butonlar


def trigger_production() -> str:
    """Manuel üretim tetikle. GH_TOKEN asla argv'ye girmez (requests header).
    Başarı için HTTP 204 (dispatch standart yanıtı) zorunludur."""
    tok = os.environ.get("GH_TOKEN", "")
    if not tok:
        return "❌ Hata: GH_TOKEN tanımlı değil, tetiklenemedi."
    repo = GITHUB_REPO
    workflow = "hourly_production.yml"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches"
    try:
        resp = requests.post(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                **( {"Authorization": f"Bearer {tok}"} if tok else {} ),
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


def render_testi_tetikle() -> str:
    """TODO 12 — YÜKLEMSİZ test düğmesi.

    repository_dispatch (bobi-tv-produce) + client_payload:
      yukleme_atla=1, force=true
    → hourly_production.yml videoları YERELDE üretir, YouTube'a YÜKLEME YAPMAZ.
    Canlı kanalı riske atmadan 'video üretiliyor mu?' cevabı budur."""
    tok = os.environ.get("GH_TOKEN", "")
    if not tok:
        return "❌ Hata: GH_TOKEN tanımlı değil, render testi tetiklenemedi."
    repo = GITHUB_REPO
    url = f"https://api.github.com/repos/{repo}/dispatches"
    try:
        resp = requests.post(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                **( {"Authorization": f"Bearer {tok}"} if tok else {} ),
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "event_type": "bobi-tv-produce",
                "client_payload": {"yukleme_atla": "1", "force": "true"},
            },
            timeout=30,
        )
    except Exception as e:
        return f"❌ İstisna: {str(e)[:100]}"
    if resp.status_code == 204:
        # TODO 21: tetikleme kaydı — canlı kart bu zaman damgasıyla süre gösterir.
        render_karti.tetikleme_kaydet()
        return (
            "🧪 Render testi başlatıldı — YouTube'a yükleme yapılmadı.\n"
            "Canlı durum kartı: 🧪 Render testi → 🔄 Yenile\n"
            "Süre, çıktı boyutu ve QC sonucu koşu bitince ayrı mesajla gelir."
        )
    return f"❌ Hata {resp.status_code}: {resp.text[:120]}"


#: GitHub GET önbelleği (TODO 30): sistem ekranı 3 ardışık çağrı yapıyordu.
#: 60 sn TTL, süreç içi sözlük (state dosyası YOK → ek commit üretmez).
_GITHUB_CACHE: dict[str, tuple[float, Any]] = {}
GITHUB_CACHE_TTL_SN = 60


def _github_get_onbellekli(yol: str) -> dict[str, Any] | None:
    """60 sn önbellekli GitHub GET. Hata/eksik token → None (panel 'bilinmiyor')."""
    simdi = time.time()
    kayit = _GITHUB_CACHE.get(yol)
    if kayit and (simdi - kayit[0]) < GITHUB_CACHE_TTL_SN:
        return kayit[1]
    veri = _github_get(yol)
    _GITHUB_CACHE[yol] = (simdi, veri)
    return veri


def _github_get(yol: str) -> dict[str, Any] | None:
    """GitHub API GET yardımcısı; hata → None (panel bilinmiyor der).

    TOKEN YOKSA ANONİM DENER (2026-11-11 düzeltmesi): repo public olduğu için
    anonim çağrı çalışır. Önceki hâlde token yoksa hemen None dönüyordu ve
    yerelde/ellerinde GH_TOKEN olmayan her ortamda panel "son koşu: bilinmiyor"
    diyordu — kullanıcının gördüğü boş panelin bir nedeni buydu.
    """
    tok = os.environ.get("GH_TOKEN", "")
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/{yol}",
            headers={
                "Accept": "application/vnd.github+json",
                **( {"Authorization": f"Bearer {tok}"} if tok else {} ),
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        veri = resp.json()
        return veri if isinstance(veri, dict) else None
    except Exception:
        return None


def _son_kosu_ozeti() -> str:
    """Son üretim koşusu (dürüst: veri yoksa 'bilinmiyor')."""
    veri = _github_get_onbellekli("actions/workflows/hourly_production.yml/runs?per_page=1")
    kosular = (veri or {}).get("workflow_runs") or []
    if not kosular:
        return f"{BILINMIYOR} (koşu kaydı okunamadı)"
    k = kosular[0]
    sonuc = _durum_turkce(k.get("conclusion") or k.get("status") or BILINMIYOR)
    dk = _gecen_dakika(str(k.get("created_at", "")))
    if dk is None:
        return sonuc
    return f"{sonuc} · {_yas_turkce(dk)}"


def _poller_ozeti() -> str:
    """Bot poller'ının son koşusu ve gecikmesi — 'tepki yok' şikâyetinin kökü.

    Telegram update'leri poller çalışana kadar kuyrukta bekler; poller 3 saat
    susarsa kullanıcı 3 saat cevap alamaz ve sonra tüm mesajlar toplu işlenir.
    Bu satır durumu panelde görünür kılar (uydurma sayı yok).
    """
    veri = _github_get_onbellekli("actions/workflows/telegram_bot.yml/runs?per_page=1")
    kosular = (veri or {}).get("workflow_runs") or []
    if not kosular:
        return f"{BILINMIYOR} (koşu kaydı okunamadı)"
    k = kosular[0]
    sonuc = _durum_turkce(k.get("conclusion") or k.get("status") or BILINMIYOR)
    gecikme = _gecen_dakika(str(k.get("created_at", "")))
    if gecikme is None:
        return sonuc
    return f"{sonuc} · {_yas_turkce(gecikme)}"


def _gecen_dakika(iso_damga: str) -> int | None:
    """ISO zaman damgasından bu yana geçen dakika; okunamazsa None."""
    if not iso_damga:
        return None
    try:
        an = datetime.fromisoformat(iso_damga.replace("Z", "+00:00"))
    except Exception:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=UTC)
    return int((datetime.now(UTC) - an).total_seconds() // 60)


def _tetikleyici_sagligi() -> str:
    """repository_dispatch ile gelen koşu sayısı (dış tetikleyici kanıtı)."""
    veri = _github_get_onbellekli("actions/runs?event=repository_dispatch&per_page=1")
    toplam = (veri or {}).get("total_count")
    if toplam is None:
        return f"{BILINMIYOR} (API okunamadı)"
    if toplam == 0:
        return "dış tetikleyici (repository_dispatch) hiç çalışmamış — cron yedeği aktif"
    return f"dış tetikleyici aktif ({toplam} koşu)"


# ---------------------------------------------------------------------------
# TODO 3 — ekran üreticileri (metin + düğmeler; callback_data kimlik taşır)
# ---------------------------------------------------------------------------


def _grup_etiketleri() -> dict[str, str]:
    return {
        "tetikleme": "🚀 Tetikleme",
        "uretim_kota": "🎯 Üretim & Kota",
        "temizlik": "🧹 Temizlik",
        "bildirim": "🔔 Bildirim",
        "sistem": "🔑 Sistem durumu",
    }


def _deger_ve_kaynak(anahtar: str) -> tuple[Any | None, str]:
    """Ayarın etkin değeri + katmanı: '6 (state)' / '5 (env)' / '6 (varsayılan)'."""
    a = ayar_getir(anahtar)
    if a is None:
        return None, BILINMIYOR
    ham = ayar_deposu.state_ham_ayarlari(AYARLAR_STATE_YOLU)
    if anahtar in ham:
        return ham[anahtar], "state"
    env_deger = os.environ.get(str(a["env_adi"]))
    if env_deger is not None and degistirilebilir_mi(a):
        return env_deger, "env"
    return a.get("varsayilan"), "varsayılan"


#: En sık değişen ayarlar — kökte TEK dokunuşla erişilir (TODO 15).
#: Derinlik 3 (kok → grup → ayar) bu ayarlar için 2'ye iner.
HIZLI_AYARLAR: tuple[str, ...] = (
    "GUNLUK_HEDEF",       # günlük üretim/yükleme hedefi
    "KOTA_DOLU_DAVRANIS",  # kota dolunca ne olsun
    "YUKLEME_ATLA",       # yüklemesiz test modu
)


def _hizli_toggle(anahtar: str, callback_id: str) -> None:
    """Satır içi AÇ/KAPAT (TODO 15). Riskli ayar → ONAY ekranına düşer."""
    a = ayar_getir(anahtar)
    if a is None:
        answer_callback(callback_id, "Ayar bulunamadı", show_alert=True)
        return
    deger, _ = _deger_ve_kaynak(anahtar)
    yeni = "0" if str(deger).lower() in ("1", "true", "evet", "acik") else "1"
    _hizli_uygula(anahtar, yeni, callback_id)


def _hizli_stepper(anahtar: str, yon: int, callback_id: str) -> None:
    """Satır içi ➖/➕ (TODO 15): değeri adım kadar değiştir, sınırda dur."""
    a = ayar_getir(anahtar)
    if a is None:
        answer_callback(callback_id, "Ayar bulunamadı", show_alert=True)
        return
    deger, _ = _deger_ve_kaynak(anahtar)
    try:
        mevcut = int(str(deger))
    except (TypeError, ValueError):
        mevcut = int(a.get("min", 1) or 1)
    adim = int(a.get("adim", 1) or 1)
    yeni = mevcut + (adim * yon)
    alt, ust = int(a.get("min", 1) or 1), int(a.get("max", 10**6) or 10**6)
    yeni = max(alt, min(ust, yeni))
    if yeni == mevcut:
        answer_callback(callback_id, f"Sınır: {mevcut}")
        return
    _hizli_uygula(anahtar, str(yeni), callback_id)


def _hizli_uygula(anahtar: str, yeni: str, callback_id: str) -> None:
    """Hızlı ayar uygulaması — riskli ayarlarda onay ekranı ZORUNLU."""
    a = ayar_getir(anahtar)
    if a is not None and a["risk"] == "yuksek":
        _bekleyen_giris_yaz(f"{anahtar}#{yeni}")
        answer_callback(callback_id, "Onay gerekiyor")
        _ekran_goster(ekran_onay_deger(anahtar, int(yeni) if yeni.isdigit() else yeni))
        return
    ok, durum = ayar_uygula(anahtar, yeni, None)
    answer_callback(callback_id, "Kaydedildi" if ok else "Uygulanamadı")
    metin, butonlar = ekran_hizli_ayarlar()
    if not ok and durum:
        metin += f"\n\n❌ <b>Uygulanamadı:</b> {durum}"
    _ekran_goster((metin, butonlar))


def ekran_hizli_ayarlar() -> tuple[str, list[list[dict[str, Any]]]]:
    """⭐ Hızlı ayarlar: kökten, detay ekranına girmeden değişir (TODO 15).

    Satır içi toggle (anahtar) ve stepper (sayı) kullanılır. Riskli ayarlar
    yine ONAY ekranından geçer (güvenlik kuralı korunur).
    """
    satirlar = ["⚙️ <b>Hızlı ayarlar</b>", ""]
    butonlar: list[list[dict[str, Any]]] = []
    for anahtar in HIZLI_AYARLAR:
        a = ayar_getir(anahtar)
        if a is None:
            continue
        deger, _ = _deger_ve_kaynak(anahtar)
        if a["tip"] == "anahtar":
            acik = str(deger).lower() in ("1", "true", "evet", "acik")
            durum = "✅ Açık" if acik else "⛔ Kapalı"
            satirlar.append(f"• {a['etiket']}: {durum}")
            # Tek dokunuş: tersine çevir (riskli ayar → onaya gider)
            butonlar.append(
                [{"text": f"{a['etiket']} {'kapat' if acik else 'aç'}"[:20],
                  "callback_data": f"ay:t:{anahtar}"}]
            )
        else:
            satirlar.append(f"• {a['etiket']}: {deger}")
            butonlar.append(
                [
                    {"text": "➖", "callback_data": f"ay:d:-1:{anahtar}"},
                    {"text": f"{a['etiket']}"[:18], "callback_data": f"ay:s:{anahtar}"},
                    {"text": "➕", "callback_data": f"ay:d:1:{anahtar}"},
                ]
            )
    satirlar.append("")
    butonlar.append([{"text": "⚙️ Tüm ayarlar", "callback_data": "ay:tumu"}])
    butonlar.append(list(GERI_MENUSU))
    return "\n".join(satirlar), butonlar


def ekran_ayar_kok() -> tuple[str, list[list[dict[str, Any]]]]:
    """⚙️ Ayarlar = grupların site haritası (her grup TEK düğme + kaç ayar).

    DÜZELTME (2026-11-11): "Bildirim" ve "Sistem" gruplarının düğmesi başka
    ekranlara gidiyordu; `bildirim` grubunun ayarlarına panelden ULAŞILAMIYORDU.
    Artık her grubun kendi girişi var; ekstra ekranlar grubun İÇİNDE duruyor.
    """
    satirlar = ["⚙️ <b>Ayarlar</b>", "─────────────"]
    butonlar: list[list[dict[str, Any]]] = [
        [{"text": "⭐ Hızlı ayarlar", "callback_data": "ay:hizli"}]
    ]
    for grup in GRUPLAR:
        ayarlar = grup_ayarlari(grup)
        etiket = _grup_etiketleri()[grup]
        if grup == "temizlik":
            satirlar.append(f"│ {etiket}: görüntü amaçlı")
        elif grup == "sistem":
            satirlar.append(f"│ {etiket}: secret var/yok")
        else:
            satirlar.append(f"│ {etiket}: {len(ayarlar)} ayar")
        butonlar.append([{"text": etiket, "callback_data": f"ay:g:{grup}"}])
    satirlar.append("─────────────")
    butonlar.append([{"text": "🕘 Son değişiklikler", "callback_data": "ay:gecmis"}])
    butonlar.append(list(GERI_MENUSU))
    return "\n".join(satirlar), butonlar


def ekran_ayar_grup(grup: str) -> tuple[str, list[list[dict[str, Any]]]]:
    etiket = _grup_etiketleri().get(grup, grup)
    satirlar = [f"{etiket}", ""]
    butonlar: list[list[dict[str, Any]]] = []
    for a in grup_ayarlari(grup):
        deger, kaynak = _deger_ve_kaynak(str(a["anahtar"]))
        if a["tip"] == "sadece_goruntule" and a.get("secret"):
            tanimli = bool(os.environ.get(str(a["env_adi"]), ""))
            gosterim = "✅ tanımlı" if tanimli else "⛔ eksik"
        elif a["tip"] == "sadece_goruntule":
            gosterim = str(a.get("mevcut", BILINMIYOR))
        else:
            gosterim = f"{deger} ({kaynak})"
        satirlar.append(f"• {a['etiket']}: {gosterim}")
        butonlar.append([{"text": str(a["etiket"])[:20], "callback_data": f"ay:s:{a['anahtar']}"}])
    if grup == "temizlik":
        satirlar += ["", TEMIZLIK_UYARI]
    # Gruba bağlı ekranlar: bunlar artık grup İÇİNDEN erişilir (kökten değil),
    # böylece her grubun düğmesi kendi ayarlarını açar.
    if grup == "bildirim":
        butonlar.insert(0, [{"text": "🔔 Bildirim ekranı", "callback_data": "bildirim_goster"}])
    elif grup == "sistem":
        butonlar.insert(0, [{"text": "🖥 Sistem durumu", "callback_data": "sistem_goster"}])
    satirlar.append("")
    satirlar.append("Değiştirmek için ayar adına dokun:")
    butonlar.append(
        [
            {"text": "← Geri", "callback_data": "ay:kok"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ]
    )
    return "\n".join(satirlar), butonlar


def _secenek_dugmeleri(a: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Seçenek düğmeleri — callback_data İNDEKS taşır, değer taşımaz."""
    anahtar = str(a["anahtar"])
    satir: list[dict[str, str]] = []
    butonlar: list[list[dict[str, str]]] = []
    if a["tip"] == "anahtar":
        mevcut, _ = _deger_ve_kaynak(anahtar)
        for indeks, (etiket, deger) in enumerate((("Kapat", "0"), ("Aç", "1"))):
            isaret = "✓ " if str(mevcut) == deger else ""
            satir.append({"text": f"{isaret}{etiket}", "callback_data": f"ay:v:{anahtar}:{indeks}"})
        butonlar.append(satir)
        return butonlar
    # SERBEST GİRİŞ (2026-11-11 kullanıcı kararı): sayı ayarlarında hazır seçenek
    # dayatılmaz. Öneri varsa hızlı seçim olarak gösterilir + "✏️ Değer gir".
    if a["tip"] == "sayi":
        mevcut, _ = _deger_ve_kaynak(anahtar)
        # Not: düğme metni ≤20 karakter (mobilde kesilmesin); aralık ekranda yazılır.
        butonlar.append([{"text": "✏️ Değer gir", "callback_data": f"ay:gir:{anahtar}"}])
        for indeks, deger in enumerate(a.get("secenekler") or []):
            isaret = "✓ " if str(mevcut) == str(deger) else ""
            satir.append(
                {"text": f"{isaret}{deger}", "callback_data": f"ay:v:{anahtar}:{indeks}"}
            )
            if len(satir) == 3:
                butonlar.append(satir)
                satir = []
        if satir:
            butonlar.append(satir)
        return butonlar
    secenekler = a.get("secenekler") or []
    mevcut, _ = _deger_ve_kaynak(anahtar)
    for indeks, deger in enumerate(secenekler):
        isaret = "✓ " if str(mevcut) == str(deger) else ""
        satir.append({"text": f"{isaret}{deger}", "callback_data": f"ay:v:{anahtar}:{indeks}"})
        if len(satir) == 3:
            butonlar.append(satir)
            satir = []
    if satir:
        butonlar.append(satir)
    return butonlar


def ekran_ayar_detay(anahtar: str) -> tuple[str, list[list[dict[str, Any]]]]:
    a = ayar_getir(anahtar)
    if a is None:
        return ekran_ana()
    deger, kaynak = _deger_ve_kaynak(anahtar)
    satirlar = [f"⚙️ <b>{a['etiket']}</b>", f"Grup: {_grup_etiketleri().get(str(a['grup']), '?')}", ""]
    butonlar: list[list[dict[str, Any]]] = []
    if a["tip"] == "sadece_goruntule" and a.get("secret"):
        tanimli = bool(os.environ.get(str(a["env_adi"]), ""))
        satirlar.append(f"Durum: {'✅ tanımlı' if tanimli else '⛔ eksik'}")
        satirlar.append("Kaynak: GitHub Secrets")
        satirlar.append("")
        satirlar.append("🔒 Secret değeri güvenlik gereği ASLA gösterilmez.")
    elif a["tip"] == "sadece_goruntule":
        satirlar.append(f"Mevcut: {a.get('mevcut', BILINMIYOR)}")
        satirlar.append("")
        satirlar.append(TEMIZLIK_UYARI)
    else:
        satirlar.append(f"Mevcut: {deger} ({kaynak})")
        aciklama = a.get("aciklama")
        if aciklama:
            satirlar.append("")
            satirlar.append(str(aciklama))
        if str(a["grup"]) == "temizlik":
            # Kullanıcı kararı (2026-11-11): kilit kaldırıldı, ama silme riski
            # panelde AÇIKÇA yazılır ve değişiklik onay ekranından geçer.
            satirlar.append("")
            satirlar.append(TEMIZLIK_UYARI)
        if a["risk"] == "yuksek":
            satirlar.append("")
            satirlar.append("⚠️ Bu ayar RİSKLİ: seçtiğinizde onay istenecek.")
        butonlar.extend(_secenek_dugmeleri(a))
    satirlar.append("")
    # TODO 22: her ayarın "ne işe yarar?" rehberi tek dokunuş uzakta.
    butonlar.append([{"text": "❓ Ne işe yarar?", "callback_data": f"ay:nedir:{a['anahtar']}"}])
    butonlar.append(
        [
            {"text": "← Geri", "callback_data": f"ay:g:{a['grup']}"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ]
    )
    return "\n".join(satirlar), butonlar


def etki_onizlemesi(anahtar: str, deger: Any) -> str:
    """TODO 5 — riskli ayarın GERÇEK etkisini hesaplar.
    Yalnızca OKUMA yapar: hiçbir dosya silmez, yükleme/deneme yapmaz."""
    if anahtar == "force":
        degerler, _ = ayar_deposu.yukle(AYARLAR_STATE_YOLU)
        try:
            hedef = int(degerler.get("GUNLUK_HEDEF", "1"))
        except (TypeError, ValueError):
            hedef = 1
        return (
            "Zorla üretim, ön kontrolleri atlayıp hemen üretim+yükleme başlatır.\n"
            f"Günlük yükleme tavanı yok; normal hedef ~{hedef} yükleme.\n"
            f"{_kota_birim_ozeti()}"
        )
    if anahtar == "KOTA_DOLU_DAVRANIS":
        if str(deger) == "hata":
            return (
                "Kota dolunca koşu KIRMIZI TİK alır (exit 1).\n"
                "Self-repair otomasyonu tetiklenebilir (günde ~144 deneme + "
                "main'e otonom push riski)."
            )
        return "Kota dolunca koşu SESSİZCE durur (exit 0) — kırmızı tik yok."
    if anahtar in ("MIN_IZLENME_ESIGI", "IZLENME_KONTROL_DK"):
        return _silme_onizlemesi(anahtar, deger)
    return "Etki önizlemesi yok."


def _arsiv_kayitlari() -> list[dict[str, Any]]:
    """Okuma amaçlı arşiv kayıtları (yoksa boş liste — çökme yok)."""
    try:
        yol = Path("bobi_tv/archive/videos.json")
        if not yol.exists():
            return []
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [k for k in veri if isinstance(k, dict)] if isinstance(veri, list) else []


def _silme_onizlemesi(anahtar: str, deger: Any) -> str:
    """Kaç video silinir? Yalnızca OKUR — hiçbir şey silmez, API çağırmaz.

    Sınır: arşivde izlenme sayısı saklanmıyorsa gerçek sayı VERİLEMEZ; o durumda
    uydurma sayı yazılmaz, "bilinmiyor" denir (yalan söyleme yasağı).
    """
    degerler, _ = ayar_deposu.yukle(AYARLAR_STATE_YOLU)
    try:
        esik = int(deger if anahtar == "MIN_IZLENME_ESIGI" else degerler.get("MIN_IZLENME_ESIGI", 100))
        sure = int(deger if anahtar == "IZLENME_KONTROL_DK" else degerler.get("IZLENME_KONTROL_DK", 60))
    except (TypeError, ValueError):
        return "⚠️ Etki hesaplanamadı (değer sayı değil)."
    kayitlar = _arsiv_kayitlari()
    yayinda = [k for k in kayitlar if k.get("durum") == "yayinda"]
    izlenmeli = [k for k in yayinda if isinstance(k.get("izlenme"), (int, float))]
    basliklar = (
        f"Kural: yayından {sure} dk sonra <{esik} izlenme → SİLİNİR.\n"
        f"Arşivde yayında: {len(yayinda)} video (izlenme verisi olan: {len(izlenmeli)})."
    )
    if not izlenmeli:
        # Arşivde izlenme yok → CANLI sayım (1 kota birimi, 50 videoya kadar).
        # Sadece OKUMA: hiçbir video silinmez, hiçbir yükleme yapılmaz.
        canli, hata = _canli_izlenme_ozeti(esik, sure)
        if canli is not None:
            return f"{basliklar}\n\n{canli}"
        return (
            f"{basliklar}\n\n"
            "⛔ <b>Silinecek video sayısı BİLİNMİYOR</b>: arşivde izlenme sayısı "
            f"kaydedilmiyor. Canlı sayım da yapılamadı: {hata}\n"
            "Uydurma sayı yazmıyoruz: karar senin."
        )
    etkilenen = [k for k in izlenmeli if k.get("izlenme", 0) < esik]
    liste = "\n".join(
        f"• {str(k.get('baslik', k.get('video_id', '?')))[:38]} ({k.get('izlenme')} izlenme)"
        for k in etkilenen[:5]
    )
    return (
        f"{basliklar}\n\n"
        f"🗑️ <b>Bu ayarla {len(etkilenen)} video silinir.</b>"
        + (f"\n{liste}" if liste else "\n(silme listesi boş)")
    )


def _canli_izlenme_ozeti(esik: int, sure_dk: int) -> tuple[str | None, str]:
    """YouTube'dan izlenme sayılarını OKUR (1 kota birimi) — silme YAPMAZ.

    Kullanıcının "kaç video silinecek?" sorusuna gerçek cevap. Hata olursa
    (token yok, kota dolu, ağ) uydurma sayı yerine (None, sebep) döner.
    """
    if not os.environ.get("YOUTUBE_TOKEN", "").strip():
        return None, "YOUTUBE_TOKEN yok (bu ekran yalnız bot içinde çalışır)"
    try:
        import requests

        from modules.youtube_upload import (
            VIDEOS_URI,
            token_yenile,
            token_yukle,
        )

        erisim = token_yenile(token_yukle())
        kayitlar = _arsiv_kayitlari()
        idler = [str(k["video_id"]) for k in kayitlar
                 if k.get("durum") == "yayinda" and k.get("video_id")][:50]
        if not idler:
            return "Yayında kayıt yok — silinecek video da yok.", ""
        yanit = requests.get(
            f"{VIDEOS_URI}?part=statistics,snippet&id={','.join(idler)}",
            headers={"Authorization": f"Bearer {erisim}"},
            timeout=20,
        )
        if yanit.status_code != 200:
            return None, f"YouTube API {yanit.status_code}"
        satirlar = ["🗑️ <b>Bu ayarla silinecek (canlı sayım):</b>"]
        sayac = 0
        for oge in yanit.json().get("items", []):
            izlenme = int(oge.get("statistics", {}).get("viewCount", 0))
            if izlenme < esik:
                sayac += 1
                baslik = str(oge.get("snippet", {}).get("title", oge.get("id")))[:38]
                if sayac <= 5:
                    satirlar.append(f"• {baslik} ({izlenme} izlenme)")
        satirlar.insert(1, f"<b>{sayac}</b> video ({sure_dk} dk / {esik} izlenme kuralı)")
        return "\n".join(satirlar), ""
    except Exception as e:
        return None, str(e)[:80]


def ekran_giris(anahtar: str) -> tuple[str, list[list[dict[str, Any]]]]:
    """Serbest değer girişi ekranı — kullanıcı klavyeden sayı yazar.

    Seçenek dayatması yok (kullanıcı kararı 2026-11-11). Aralık ve BİRİM
    gösterilir; sınır dışı değer sonraki adımda reddedilir.
    """
    a = ayar_getir(anahtar)
    if a is None or a["tip"] != "sayi":
        return ekran_ana()
    mevcut, kaynak = _deger_ve_kaynak(anahtar)
    satirlar = [
        f"✏️ <b>{a['etiket']}</b> — değer gir",
        "",
        f"Mevcut: <b>{mevcut}</b> ({kaynak})",
        f"Aralık: {a.get('min')} – {a.get('max')}",
        "",
        "👇 Şimdi mesaj olarak sadece sayıyı yaz (örn. <code>60</code>).",
    ]
    aciklama = a.get("aciklama")
    if aciklama:
        satirlar += ["", str(aciklama)]
    butonlar = [
        [{"text": "← Vazgeç", "callback_data": f"ay:s:{anahtar}"}],
        [
            {"text": "← Geri", "callback_data": f"ay:g:{a['grup']}"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ],
    ]
    return "\n".join(satirlar), butonlar


def ekran_onay_deger(anahtar: str, deger: str) -> tuple[str, list[list[dict[str, Any]]]]:
    """Serbest girilen RİSKLİ değer için onay ekranı — YAZMAZ, yalnız gösterir.

    Canlı etki önizlemesi: "bu eşikle şu an N video silinir" (gerçek arşiv okunur,
    hiçbir şey silinmez). Kullanıcı onaylarsa değer uygulanır.
    """
    a = ayar_getir(anahtar)
    if a is None or not degistirilebilir_mi(a):
        return ekran_ana()
    satirlar = [
        "⚠️ <b>ONAY GEREKİYOR</b>",
        "",
        f"{a['etiket']} → <b>{deger}</b>",
        "",
        etki_onizlemesi(anahtar, deger),
        "",
        "Değişiklik yalnızca onayınızdan sonra uygulanır. Geri alınamaz.",
    ]
    butonlar = [
        # TODO 25: onay riskli aksiyondur → İMZALI + süreli callback.
        [{"text": "✅ Onayla", "callback_data": imzali_ay_callback("ay:onayd", anahtar)}],
        [{"text": "← Vazgeç", "callback_data": f"ay:s:{anahtar}"}],
        [
            {"text": "← Geri", "callback_data": f"ay:g:{a['grup']}"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ],
    ]
    return "\n".join(satirlar), butonlar


def ekran_onay(anahtar: str, indeks: int) -> tuple[str, list[list[dict[str, Any]]]]:
    """Riskli ayar için onay ekranı — DURUM YAZMAZ (yalnızca gösterir)."""
    a = ayar_getir(anahtar)
    if a is None or not degistirilebilir_mi(a) or a["risk"] != "yuksek":
        return ekran_ana()
    deger, _ = _secenek_coz(a, indeks)
    if deger is None:
        return ekran_ana()
    satirlar = [
        "⚠️ <b>ONAY GEREKİYOR</b>",
        "",
        f"{a['etiket']} → {deger}",
        "",
        etki_onizlemesi(anahtar, deger),
        "",
        "Değişiklik yalnızca onayınızdan sonra uygulanır.",
    ]
    butonlar = [
        # TODO 25: onay riskli aksiyondur → İMZALI + süreli callback.
        [{"text": "✅ Onayla", "callback_data": imzali_ay_callback("ay:onay", anahtar, indeks)}],
        [{"text": "← Vazgeç", "callback_data": f"ay:iptal:{anahtar}"}],
        [
            {"text": "← Geri", "callback_data": f"ay:s:{anahtar}"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ],
    ]
    return "\n".join(satirlar), butonlar


def ekran_ayar_test(anahtar: str) -> tuple[str, list[list[dict[str, Any]]]]:
    """TODO 5 — dry-run ön izleme: HİÇBİR YAZMA YAPMAZ."""
    a = ayar_getir(anahtar)
    if a is None:
        return ekran_ana()
    deger, kaynak = _deger_ve_kaynak(anahtar)
    satirlar = [
        f"🧪 <b>Dry-run ön izleme</b> — {a['etiket']}",
        "",
        f"Mevcut: {deger} ({kaynak})",
        "",
        etki_onizlemesi(anahtar, a["varsayilan"] if a["tip"] == "anahtar" else deger),
        "",
        "Bu ekran hiçbir dosyaya yazmadı; ayar değişmedi.",
    ]
    butonlar = [
        [{"text": "← Geri", "callback_data": f"ay:s:{anahtar}"}],
        [{"text": "🏠 Menü", "callback_data": "menu_main"}],
    ]
    return "\n".join(satirlar), butonlar


def _gecmis_kaynak_metni(kayit: dict[str, Any]) -> str:
    try:
        zaman = datetime.fromisoformat(str(kayit.get("zaman")))
        if zaman.tzinfo is None:
            zaman = zaman.replace(tzinfo=UTC)
        dk = int((datetime.now(UTC) - zaman).total_seconds() / 60)
        if dk < 1:
            return "şimdi"
        if dk < 60:
            return f"{dk} dk önce"
        return f"{dk // 60} saat önce"
    except Exception:
        return ""


def ekran_gecmis() -> tuple[str, list[list[dict[str, Any]]]]:
    kayitlar = ayar_deposu.gecmisi_oku(10, GECMIS_YOLU)
    satirlar = ["🕘 <b>Son değişiklikler</b>", ""]
    if not kayitlar:
        satirlar.append("Henüz değişiklik yok.")
    else:
        for k in kayitlar:
            kaynak_metin = _gecmis_kaynak_metni(k)
            zaman_etiketi = f" · {kaynak_metin}" if kaynak_metin else ""
            satirlar.append(
                f"• {k.get('anahtar', '?')}: {k.get('eski', '?')} → {k.get('yeni', '?')}{zaman_etiketi}"
            )
    butonlar = [
        [{"text": "🔄 Yenile", "callback_data": "ay:gecmis"}],
        [{"text": "← Geri", "callback_data": "ay:kok"}, {"text": "🏠 Menü", "callback_data": "menu_main"}],
    ]
    return "\n".join(satirlar), butonlar


def ekran_sistem() -> tuple[str, list[list[dict[str, Any]]]]:
    """TODO 7 — secret durumu: yalnız ✅ tanımlı / ⛔ eksik; değer ASLA yazdırılmaz."""
    satirlar = ["🔑 <b>Sistem durumu</b>", ""]
    for a in grup_ayarlari("sistem"):
        tanimli = bool(os.environ.get(str(a["env_adi"]), ""))
        satirlar.append(f"• {a['etiket']}: {'✅ tanımlı' if tanimli else '⛔ eksik'} (GitHub Secrets)")
    satirlar += [
        "",
        f"🎬 Son üretim koşusu: {_son_kosu_ozeti()}",
        f"📡 Bot poller: {_poller_ozeti()}",
        f"🧭 Tetikleyici: {_tetikleyici_sagligi()}",
        f"🚫 {_kota_birim_ozeti()}",
        "📐 Günlük yükleme tavanı: YOK (kota kaldırıldı)",
        f"📱 Mini App: {'✅ yayında' if MINI_APP_URL.startswith('https://') else '⛔ adres yok'}",
    ]
    butonlar = [
        [{"text": "🔄 Yenile", "callback_data": "sistem_goster"}],
        [
            {"text": "🔔 Bildirimler", "callback_data": "bildirim_goster"},
            {"text": "🧹 Temizle", "callback_data": "panelleri_temizle"},
        ],
        [
            {"text": "← Geri", "callback_data": "ay:kok"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ],
    ]
    return "\n".join(satirlar), butonlar


def ekran_ayar_nedir(anahtar: str) -> tuple[str, list[list[dict[str, Any]]]]:
    """❓ "Ne işe yarar?" ekranı (TODO 22) — ayarın etkisi ve ETKİSİZLİĞİ.

    Açıklama `modules/rehber.py`den gelir; rehberi olmayan ayarda uydurma metin
    yazılmaz, "bilinmiyor" denir.
    """
    a = ayar_getir(anahtar)
    if a is None:
        return ekran_ana()
    metin = rehber.detay_metni(anahtar, str(a.get("etiket") or anahtar))
    butonlar = [
        [
            {"text": "⚙️ Ayarı aç", "callback_data": f"ay:d:{anahtar}"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ],
        [
            {"text": "← Geri", "callback_data": f"ay:g:{a['grup']}"},
            {"text": "🏠 Menü", "callback_data": "menu_main"},
        ],
    ]
    return metin, butonlar


def ekran_sistem_kok() -> tuple[str, list[list[dict[str, Any]]]]:
    """🛠 Sistem = sistemle ilgili TÜM alt ekranların tek kapısı.

    2026-11-11: bu ekranlar (sistem durumu / bildirim / denetim / mini app)
    yalnız gizli metin komutlarından erişilebiliyordu; panelde kapı yoktu.
    """
    ayirici = "─────────────"
    metin = (
        "🛠 <b>Sistem</b>\n"
        f"{ayirici}\n"
        f"│ 🕐 Son koşu: {_son_kosu_ozeti()}\n"
        f"│ 📡 Bot: {_poller_ozeti()}\n"
        f"{ayirici}\n"
        "<i>Hepsi tek panelde: aşağıdan seç.</i>"
    )
    return metin, [
        [
            {"text": "🖥 Durum", "callback_data": "status_now"},
            {"text": "⚙️ Ayarlar", "callback_data": "ay:kok"},
        ],
        [
            {"text": "🔔 Bildirim", "callback_data": "bildirim_goster"},
            {"text": "📋 Denetim", "callback_data": "denetim_goster"},
        ],
        [
            {"text": "📱 Mini App", "callback_data": "mini_app_goster"},
            {"text": "❓ Yardım", "callback_data": "yardim_goster"},
        ],
        list(GERI_MENUSU),
    ]


def ekran_mini_app() -> tuple[str, list[list[dict[str, Any]]]]:
    """📱 Mini App ekranı (TODO 31) — adres + veri tazeliği + salt okunur notu.

    Adres bir DÜĞME değil metin olarak verilir: Telegram'da web_app düğmesi
    yalnız HTTPS + BotFather'da kayıtlı domain ile çalışır; kayıt yapılmadan
    düğme kullanıcıya hata gösterir. Bu yüzden önce bilgi, sonra kayıt adımı.
    """
    satirlar = ["📱 <b>Mini App</b>", ""]
    satirlar.append(f"🔗 <code>{MINI_APP_URL}</code>")
    satirlar.append("")
    # Veri tazeliği — dosya yoksa uydurma yok.
    try:
        veri = json.loads(
            Path("webapp/veri/mini_app_ozet.json").read_text(encoding="utf-8")
        )
        guncelleme = str(veri.get("guncelleme", ""))[:16].replace("T", " ")
        b = veri.get("bugun") or {}
        satirlar.append(f"🕐 Veri: {guncelleme or BILINMIYOR}")
        satirlar.append(
            f"🎥 Bugün: {b.get('uretilen') if b.get('uretilen') is not None else BILINMIYOR} üretildi · "
            f"{b.get('yayinda') if b.get('yayinda') is not None else BILINMIYOR} yayında"
        )
    except (OSError, ValueError):
        satirlar.append(f"🕐 Veri: {BILINMIYOR} (özet dosyası okunamadı)")
    satirlar += [
        "",
        "🔐 <b>Onaylı yazma:</b> Mini App yalnız istek gönderir; üretim/boşaltma",
        "bu panelin onay ekranından geçer ve denetim kaydına yazılır.",
    ]
    satirlar += [
        "",
        "<i>Yazma düğmeleri yalnız Telegram içinde çalışır (BotFather → Menu "
        "Button'a bu adres girilmeli). Çalışmazsa aynı işlemleri bu panelden yap.</i>",
    ]
    butonlar = [
        # Telegram'ın izin verdiği en güvenli açılış: web_app düğmesi.
        [{"text": "📱 Mini App'i aç", "web_app": {"url": MINI_APP_URL}}],
        [
            {"text": "🔄 Yenile", "callback_data": "mini_app_goster"},
            {"text": "🎬 Üret", "callback_data": "uret_baslat"},
        ],
        list(GERI_MENUSU),
    ]
    return "\n".join(satirlar), butonlar


def ekran_denetim() -> tuple[str, list[list[dict[str, Any]]]]:
    """📋 Denetim kaydı (TODO 27) — geri alınamaz işlemlerin izi."""
    butonlar = [
        [{"text": "🔄 Yenile", "callback_data": "denetim_goster"}],
        list(GERI_MENUSU),
    ]
    return denetim.panel_metni(), butonlar


def ekran_sistem_nedir() -> tuple[str, list[list[dict[str, Any]]]]:
    """❓ "Bu sistem ne işe yarıyor?" — uçtan uca akış + dürüst sınırlar."""
    butonlar = [
        [
            {"text": "📊 Durum", "callback_data": "status_now"},
            {"text": "📦 Kuyruk", "callback_data": "kuyruk_liste"},
        ],
        list(GERI_MENUSU),
    ]
    return rehber.sistem_metni(), butonlar


def _son_render_kosusu() -> tuple[dict[str, Any] | None, str]:
    """Render testi (yukleme_atla) koşusunu GitHub'dan okur — 60 sn önbellekli.

    Döner: (koşu sözlüğü veya None, hata metni). Hata uydurulmaz, sebep yazılır.
    """
    veri = _github_get_onbellekli("actions/workflows/hourly_production.yml/runs?per_page=10")
    if veri is None:
        return None, "GitHub okunamadı (token yok veya API hatası)"
    kosular = veri.get("workflow_runs") or []
    if not kosular:
        return None, "koşu kaydı yok"
    # Önce yerel tetikleme kaydındaki koşuyu bul (varsa en doğrusu), yoksa en yeni.
    yerel = render_karti.durum_oku()
    istenen = yerel.get("kosu_id")
    if istenen:
        for k in kosular:
            if str(k.get("id")) == str(istenen):
                return k, ""
    for k in kosular:
        if "yukleme_atla" in json.dumps(k)[:2000] or "render" in str(k.get("display_title", "")).lower():
            return k, ""
    return kosular[0], ""


def ekran_render_kart() -> tuple[str, list[list[dict[str, Any]]]]:
    """🧪 Render testi CANLI kart (TODO 21) — durum/süre/adım, yükleme YOK.

    Uydurma yüzde yok: adım bilgisi gelmezse "bilinmiyor" yazılır. Koşu
    bitmişse yenile düğmesi kalır (kullanıcı sonucu tekrar görebilir).
    """
    kosu, hata = _son_render_kosusu()
    metin = render_karti.kart_metni(kosu, hata=hata)
    butonlar = [
        [
            {"text": "🔄 Yenile", "callback_data": "render_kart"},
            {"text": "▶️ Testi başlat", "callback_data": "uret_render_test"},
        ],
        list(GERI_MENUSU),
    ]
    return metin, butonlar


def ekran_kuyruk() -> tuple[str, list[list[dict[str, Any]]]]:
    """📦 Stok (kuyruk) ekranı (TODO 20) — sebep dağılımı, yaş, deneme sayısı.

    Metin `modules/kuyruk_yonetimi.panel_metni`den gelir; sayı uydurulmaz,
    bozuk kayıt silinmez, kuyruk boşsa bunu açıkça söyler.
    """
    from modules.kuyruk_yonetimi import ozet, panel_metni

    satirlar = [panel_metni(), ""]
    o = ozet()
    butonlar: list[list[dict[str, Any]]] = []
    if o["toplam"]:
        # Riskli işlem (atma) önce onay ekranından geçer — tek adımda silme YOK.
        butonlar.append(
            [
                {"text": "🗑️ Hepsini at", "callback_data": "kuyruk_at_onay"},
                {"text": "🔄 Yenile", "callback_data": "kuyruk_liste"},
            ]
        )
    else:
        # Kuyruk boşken de geri alınabilir: çöp kutusu boşsa dürüst mesaj döner.
        butonlar.append([{"text": "↩️ Geri al", "callback_data": "kuyruk_geri_al"}])
    butonlar.append(list(GERI_MENUSU))
    return "\n".join(satirlar).rstrip(), butonlar


def ekran_kuyruk_at_onay() -> tuple[str, list[list[dict[str, Any]]]]:
    """Kuyruğu boşaltma ONAY ekranı — kaç kayıt, geri alınabilir mi."""
    from modules.kuyruk_yonetimi import onay_metni

    butonlar = [
        [
            renkli_buton("✅ Onayla", "kuyruk_at_uygula", "onay"),
            renkli_buton("✖️ Vazgeç", "kuyruk_liste", "vazgec"),
        ],
        list(GERI_MENUSU),
    ]
    return onay_metni(), butonlar


def ekran_kuyruk_at_uygula() -> tuple[str, list[list[dict[str, Any]]]]:
    """Onaylanan atma işlemini UYGULAR (taşır) ve sonucu dürüstçe yazar."""
    from modules.kuyruk_yonetimi import toplu_at

    sonuc = toplu_at(None)
    # TODO 27: geri alınabilir ama iz bırakır (kaç kayıt, ne zaman).
    denetim.kaydet(
        "stok_at",
        "ok" if sonuc["atilan"] else "bos",
        ayrinti={"atilan": sonuc["atilan"], "basarisiz": sonuc["basarisiz"]},
    )
    if sonuc["atilan"] == 0:
        metin = "ℹ️ <b>Atılacak kayıt yok</b>\n\nKuyruk zaten boş."
    else:
        metin = (
            f"🗑️ <b>{sonuc['atilan']} kayıt stoktan atıldı</b>\n\n"
            "SİLİNMEDİ: <code>archive/atilan/</code> altına taşındı.\n"
            "Yanlış tıkladıysan '↩️ Geri al' ile döndürebilirsin."
        )
        if sonuc["basarisiz"]:
            metin += f"\n\n⚠️ {sonuc['basarisiz']} kayıt taşınamadı (YAPILMADI)."
    butonlar = [
        [
            {"text": "↩️ Geri al", "callback_data": "kuyruk_geri_al"},
            {"text": "📦 Kuyruk", "callback_data": "kuyruk_liste"},
        ],
        list(GERI_MENUSU),
    ]
    return metin, butonlar


def ekran_kuyruk_geri_al() -> tuple[str, list[list[dict[str, Any]]]]:
    """Son atılan kaydı kuyruğa geri koyar (yanlış tıklama telafisi)."""
    from modules.kuyruk_yonetimi import geri_al

    sonuc = geri_al()
    if sonuc["geri_alinan"]:
        metin = f"↩️ <b>{sonuc['geri_alinan']} kayıt geri alındı</b>\n\nStok yeniden görünüyor."
    else:
        metin = f"ℹ️ <b>Geri alınacak kayıt yok</b>\n\nSebep: {sonuc['sebep'] or BILINMIYOR}."
    butonlar = [
        [{"text": "📦 Kuyruk", "callback_data": "kuyruk_liste"}],
        list(GERI_MENUSU),
    ]
    return metin, butonlar


def ekran_durum() -> tuple[str, list[list[dict[str, Any]]]]:
    """🖥 Canlı sistem durumu (durum düğmesi / alt klavye "Durum")."""
    return get_status_text(), [
        [{"text": "🔄 Yenile", "callback_data": "status_now"}],
        [
            {"text": "📈 Rapor", "callback_data": "rapor_goster"},
            {"text": "🛠 Sistem", "callback_data": "sistem_kok"},
        ],
        list(GERI_MENUSU),
    ]


def ekran_kanal_sagligi() -> tuple[str, list[list[dict[str, Any]]]]:
    """🩺 Kanal sağlığı — kadans/silme değişikliğinin işe yarayıp yaramadığını ölçer.

    Kullanıcının sorusu: "kanal istatistikleri düştü, algoritma bizi biçti".
    Bu ekran DUYGU değil ÖLÇÜM gösterir; veri yoksa "veri yetersiz" der.
    """
    from modules.kanal_sagligi import ASGARI_ORNEK, saglik_ozeti

    ozet = saglik_ozeti(7)
    ayirici = "─────────────"
    ornek = ozet.get("izlenme_ornek") or 0

    def _sayi(deger: Any, birim: str = "") -> str:
        return f"<b>{deger}{birim}</b>" if deger is not None else "<b>—</b>"

    satirlar = [
        "🩺 <b>Kanal Sağlığı</b>  ·  <i>son 7 gün</i>",
        ayirici,
        "📊 <b>Dağıtım</b>",
        f"│ 🎥 Üretilen: {_sayi(ozet.get('uretilen'))}   "
        f"🗑 Silinen: {_sayi(ozet.get('silinen'))}",
        f"│ 👁 Ortalama izlenme: {_sayi(ozet.get('ortalama_izlenme'))}   "
        f"📈 En yüksek: {_sayi(ozet.get('en_yuksek_izlenme'))}",
        f"│ 🚀 Akışa giren (100+): {_sayi(ozet.get('akisa_giren'))} "
        f"({_sayi(ozet.get('akisa_girme_orani'), '%')})",
        ayirici,
        "🎯 <b>İçerik</b>",
        f"│ ⭐ Kalite ortalaması: {_sayi(ozet.get('kalite_ortalama'))} "
        f"({ozet.get('kalite_ornek') or 0} senaryo)",
        f"│ 🪝 Kanca: {_kanca_ozeti(ozet)}",
        *(["│ " + _arena_sure_ozeti()] if _arena_sure_ozeti() else []),
        ayirici,
        f"📐 Kadans: <b>{_kadans_etiketi()}</b> · 🗑 Silme eşiği: "
        f"<b>{_izlenme_kurali_ozeti()}</b>",
    ]
    if ornek < ASGARI_ORNEK:
        satirlar.append(
            f"<i>Yorum için en az {ASGARI_ORNEK} video gerekiyor ({ornek} var) — "
            "sayı uydurulmaz.</i>"
        )
    else:
        satirlar.append(f"<i>{ozet.get('yorum')}</i>")

    return "\n".join(satirlar), [
        [{"text": "🔄 Yenile", "callback_data": "kanal_sagligi"}],
        [
            {"text": "📈 Rapor", "callback_data": "rapor_goster"},
            {"text": "🏆 Performans", "callback_data": "performans"},
        ],
        list(GERI_MENUSU),
    ]


def _arena_sure_ozeti() -> str:
    """Arena'nın GERÇEK yanıt süresi — ölçülmüş, uydurulmuş değil.

    Kullanıcı isteği (2026-11-11): "Arena bazen uzun düşünüyor; süreci anlık
    gösterelim, süreyi varsayımsal değil gerçek gösterelim."
    Kaynak: `bobi_tv/state/arena_sure.json` (arena_api her yanıtta yazar).
    """
    with suppress(Exception):
        from modules.arena_api import ARENA_SURE_YOLU

        veri = json.loads(ARENA_SURE_YOLU.read_text(encoding="utf-8"))
        son = veri.get("son") or {}
        if not son:
            return ""
        sn = float(son.get("saniye") or 0)
        ek = f" · Arena: {son['arena_dusunme']}" if son.get("arena_dusunme") else ""
        return f"🌐 Arena: son yanıt <b>{sn:.0f} sn</b> · ort. <b>{veri.get('ortalama')} sn</b>{ek}"
    return ""


def _kanca_ozeti(ozet: dict[str, Any]) -> str:
    """Kanca formu ölçümü tek satır (A1): hangi form daha çok izlenme getirdi?

    Veri yoksa "ölçüm sürüyor" der — uydurma yok.
    """
    kanca = ozet.get("kanca") or {}
    form_verisi = kanca.get("form_verisi") or {}
    if not form_verisi:
        return "<i>ölçüm sürüyor (yeni kancalı videolar bekleniyor)</i>"
    parcalar = [
        f"{form} {veri['ortalama']} ({veri['video']})"
        for form, veri in sorted(form_verisi.items(), key=lambda kv: -kv[1]["ortalama"])[:3]
    ]
    en_iyi = kanca.get("en_iyi_form")
    if en_iyi:
        return f"<b>{en_iyi}</b> önde · " + " · ".join(parcalar)
    return " · ".join(parcalar) + " <i>(kazanan için ≥2 video/form)</i>"


def _izlenme_kurali_ozeti() -> str:
    """Silme kuralını TEK kaynaktan okur (katalog/main_pipeline ile aynı)."""
    with suppress(Exception):
        from modules.ayar_katalogu import ayar_getir

        a = ayar_getir("IZLENME_KONTROL_DK") or {}
        sure = int(a.get("varsayilan") or 360)
        esik = int((ayar_getir("MIN_IZLENME_ESIGI") or {}).get("varsayilan") or 100)
        return f"{sure // 60} saatte {esik} izlenme"
    return "bilinmiyor"


def ekran_rapor() -> tuple[str, list[list[dict[str, Any]]]]:
    """📈 Rapor = SAYISAL ÖZET + site haritası.

    2026-11-11 tasarım düzeltmesi (kullanıcı: "her şey elimin altında"):
    - 3 ayrı metin bloğu üst üste yığılmıştı (İstatistik + Kalite + Yükleme),
      ekranı kaydırmadan hiçbir şey görünmüyordu → artık TEK özet kart.
    - Rapor altındaki hiçbir ekrana (7 gün / performans / kuyruk / sistem)
      gezinme yolu YOKTU; metinlerden "başka ekran" diye bahsetmek
      düğmesiz ölü yönergedir → hepsi düğme oldu.
    """
    from modules.kalite_log import kalite_istatistik

    bugun = datetime.now(UTC).strftime("%Y-%m-%d")
    ist = kalite_istatistik(bugun)
    uretilen, yayinda = _bugun_arsiv_ozeti()
    kuyruk = Path("bobi_tv/queue")
    kuyruk_sayisi = len(list(kuyruk.glob("*.json"))) if kuyruk.exists() else 0
    ayirici = "─────────────"

    if ist.get("toplam"):
        gecen = int(ist.get("gecen", 0))
        kalan = int(ist.get("kalan", 0))
        oran = round(gecen / ist["toplam"] * 100)
        kalite_satiri = (
            f"│ 🎯 Ortalama: <b>{ist.get('ortalama_puan', 0)}/100</b>   "
            f"✅ Geçen: <b>{gecen}</b>   ❌ Kalan: <b>{kalan}</b>"
        )
        kalite_alt = (
            f"│ 📉 Min: {ist.get('min_puan', '—')}   "
            f"📈 Max: {ist.get('max_puan', '—')}   📊 Geçme: %{oran}"
        )
    else:
        kalite_satiri = "│ 🎯 Kalite: <b>bugün için veri yok</b> (üretim henüz koşmadı)"
        kalite_alt = "│ 📉 Min: —   📈 Max: —   📊 Geçme: —"

    seri = _son_7gun_seri()
    trend = (
        f"│ 📈 7 gün: <code>{_sparkline(seri)}</code> ({int(sum(seri))} video)"
        if seri
        else "│ 📈 7 gün: <b>veri yok</b>"
    )

    metin = (
        f"📈 <b>Rapor</b>  ·  <i>{bugun}</i>\n"
        f"{ayirici}\n"
        "🎬 <b>Üretim</b>\n"
        f"│ 🎥 Üretilen: <b>{uretilen}</b>   🚀 Yayında: <b>{yayinda}</b>   📦 Stok: <b>{kuyruk_sayisi}</b>\n"
        f"{ayirici}\n"
        "🎯 <b>Kalite</b>\n"
        f"{kalite_satiri}\n"
        f"{kalite_alt}\n"
        f"{ayirici}\n"
        "📊 <b>Trend</b>\n"
        f"{trend}\n"
        f"{ayirici}\n"
        "<i>Yükleme tavanı: YOK — üretilen her video yüklenir.</i>"
    )
    butonlar = [
        [
            {"text": "🩺 Kanal sağlığı", "callback_data": "kanal_sagligi"},
            {"text": "🗓 7 gün", "callback_data": "rapor_7gun"},
        ],
        [
            {"text": "🏆 Performans", "callback_data": "performans"},
        ],
        [
            {"text": "📦 Stok", "callback_data": "kuyruk_liste"},
            {"text": "🛠 Sistem", "callback_data": "sistem_kok"},
        ],
        [
            {"text": "🖥 Render", "callback_data": "render_kart"},
            {"text": "📋 Denetim", "callback_data": "denetim_goster"},
        ],
        [{"text": "🔄 Yenile", "callback_data": "rapor_goster"}],
        list(GERI_MENUSU),
    ]
    return metin, butonlar


def ekran_uret() -> tuple[str, list[list[dict[str, Any]]]]:
    """🎬 Üretim = tek ekranda üretimle ilgili HER ŞEY (başlat / test / stok)."""
    kuyruk = Path("bobi_tv/queue")
    stok = len(list(kuyruk.glob("*.json"))) if kuyruk.exists() else 0
    uretilen, yayinda = _bugun_arsiv_ozeti()
    ayirici = "─────────────"
    metin = (
        "🎬 <b>Üretim</b>\n"
        f"{ayirici}\n"
        f"│ 🎥 Bugün üretilen: <b>{uretilen}</b>   🚀 Yayında: <b>{yayinda}</b>\n"
        f"│ 📦 Stok (sırada bekleyen): <b>{stok}</b>\n"
        f"│ 📐 Günlük tavan: <b>YOK</b> — üretilen her video yüklenir\n"
        f"{ayirici}\n"
        "▶️ <b>Üretimi başlat</b> — pipeline'ı workflow ile koşturur.\n"
        "🧪 <b>Render testi</b> — YouTube'a YÜKLEME YAPMADAN zinciri dener."
    )
    butonlar: list[list[dict[str, Any]]] = [
        [{"text": "▶️ Üretimi başlat", "callback_data": "uret_baslat"}],
    ]
    # TODO 26: son tetikleme 10 dk içindeyse İPTAL düğmesi görünür.
    kalan = iptal_kalan_sn()
    if kalan > 0:
        butonlar.insert(
            0,
            [
                renkli_buton(
                    f"🛑 İptal ({max(1, kalan // 60)} dk)",
                    "uret_iptal",
                    "riskli",
                )
            ],
        )
    butonlar += [
        [
            {"text": "🧪 Render testi", "callback_data": "uret_render_test"},
            {"text": "📈 Test kartı", "callback_data": "render_kart"},
        ],
        [
            {"text": "📦 Stok", "callback_data": "kuyruk_liste"},
            {"text": "🛠 Sistem", "callback_data": "sistem_kok"},
        ],
        list(GERI_MENUSU),
    ]
    return metin, butonlar


def ekran_metin_dugme(metin: str) -> tuple[str, list[list[dict[str, Any]]]]:
    """Basit sonuç ekranları (tetikleme cevabı vb.)."""
    return metin, [
        [{"text": "🔄 Yenile", "callback_data": "uret_menu"}],
        [{"text": "← Geri", "callback_data": "menu_main"}, {"text": "🏠 Menü", "callback_data": "menu_main"}],
    ]


# ---------------------------------------------------------------------------
# TODO 5/8 — ayar uygulama + bekleyen kuyruk
# ---------------------------------------------------------------------------


def _secenek_coz(a: dict[str, Any], indeks: int | str) -> tuple[Any | None, str]:
    """callback_data'daki İNDEKSİ katalogdaki değere çevirir.
    İndeks aralık dışıysa (None, sebep) — uydurma payload işe yaramaz."""
    try:
        i = int(indeks)
    except (TypeError, ValueError):
        return None, "indeks sayı değil"
    if a["tip"] == "anahtar":
        if i not in (0, 1):
            return None, "geçersiz indeks"
        return ("0" if i == 0 else "1"), ""
    secenekler = a.get("secenekler") or []
    if i < 0 or i >= len(secenekler):
        return None, "geçersiz indeks"
    # sayi tipinde öneri listesi varsa o değer; yoksa "ay:gir" akışı kullanılır.
    if a["tip"] == "sayi":
        secilen = secenekler[i]
        return _sayi_dogrula(a, secilen)
    return secenekler[i], ""


def _sayi_dogrula(a: dict[str, Any], ham: Any) -> tuple[str | None, str]:
    """Klavyeden/öneriden gelen değeri doğrular — aralık dışı REDDEDİLİR.

    Serbest giriş = sınırsız DEĞİL: min/max aralığı korunur (katalogda tanımlı).
    Döner: (geçerli_değer | None, sebep)
    """
    try:
        deger = int(str(ham).strip())
    except (TypeError, ValueError):
        return None, "sayı değil"
    mn, mx = a.get("min"), a.get("max")
    if mn is not None and deger < int(mn):
        return None, f"en az {mn} olmalı"
    if mx is not None and deger > int(mx):
        return None, f"en fazla {mx} olabilir"
    return str(deger), ""


def ayar_uygula(anahtar: str, deger: Any, kullanici_id: int | None) -> tuple[bool, str]:
    """Ayarı state'e yazar, geçmişe ekler ve AYRI bir commit ile push eder (TODO 8).

    Push başarısızsa: bekleyen kuyruğa yazılır + panel uyarısı döner.
    Başarısızlık SESSİZCE YUTULMAZ."""
    a = ayar_getir(anahtar)
    if a is None or not degistirilebilir_mi(a):
        return False, "ayar değiştirilemez veya bilinmiyor"
    eski = ayar_deposu.state_ham_ayarlari(AYARLAR_STATE_YOLU).get(anahtar, a.get("varsayilan"))
    uygulanan, uyarilar = ayar_deposu.kaydet({anahtar: deger}, AYARLAR_STATE_YOLU)
    if anahtar not in uygulanan:
        return False, "; ".join(uyarilar) or "değişiklik uygulanamadı"
    ayar_deposu.gecmise_ekle(kullanici_id, anahtar, eski, uygulanan[anahtar], "telegram", GECMIS_YOLU)
    ok, sebep = ayar_deposu.commit_ve_yukle(
        [str(AYARLAR_STATE_YOLU), str(GECMIS_YOLU)],
        f"⚙️ ayar: {anahtar} → {uygulanan[anahtar]} (telegram) [skip ci]",
    )
    # TODO 27: ayar değişikliği geri alınabilir ama İZLENEBİLİR olmalı.
    denetim.kaydet(
        "ayar_degistir",
        "ok" if ok else "beklemede",
        kullanici_id=kullanici_id,
        ayrinti={"anahtar": anahtar, "eski": eski, "yeni": uygulanan[anahtar], "sebep": sebep},
    )
    if ok:
        return True, ""
    ayar_deposu.bekleyene_yaz({anahtar: uygulanan[anahtar]}, sebep, kullanici_id, BEKLEYEN_YOLU)
    return True, f"⚠️ kaydedilemedi, tekrar denenecek ({sebep})"


def bekleyen_ayarlari_yeniden_dene() -> str:
    """Önceki koşudan push edilememiş ayar değişikliğini tekrar dener (TODO 8)."""
    bekleyen = ayar_deposu.bekleyenleri_al(BEKLEYEN_YOLU)
    if not bekleyen:
        return ""
    degisiklikler = bekleyen.get("degisiklikler") or {}
    if not degisiklikler:
        ayar_deposu.bekleyenleri_temizle(BEKLEYEN_YOLU)
        return "boş bekleyen kayıt temizlendi"
    uygulanan, uyarilar = ayar_deposu.kaydet(degisiklikler, AYARLAR_STATE_YOLU)
    if not uygulanan:
        return f"bekleyen ayar uygulanamadı: {'; '.join(uyarilar) or 'bilinmeyen'}"
    ok, sebep = ayar_deposu.commit_ve_yukle(
        [str(AYARLAR_STATE_YOLU), str(GECMIS_YOLU)],
        "⚙️ ayar: bekleyen değişiklik tamamlandı [skip ci]",
    )
    if ok:
        ayar_deposu.bekleyenleri_temizle(BEKLEYEN_YOLU)
        return "bekleyen ayar değişikliği push edildi"
    return f"bekleyen ayar hâlâ push edilemedi: {sebep}"


# ---------------------------------------------------------------------------
# Callback yönlendirme (TODO 3) — bilinmeyen payload çökmeden menüye döner
# ---------------------------------------------------------------------------


def _bilinmeyen_komut(callback_id: str) -> str:
    answer_callback(callback_id, "Bilinmeyen komut")
    panel_goster(*ekran_ana())
    return "bilinmeyen komut"


def _ekran_goster(metin_dugmeler: tuple[str, list[list[dict[str, Any]]]]) -> None:
    """Ekranı panele basar; "← Geri" düğmesini BİR ÜST ekrana yönlendirir."""
    metin, butonlar = metin_dugmeler
    hedef = ekran_ust(_SON_CALLBACK)
    for satir in butonlar:
        for b in satir:
            if b.get("callback_data") == "geri":
                b["callback_data"] = hedef
    panel_goster(metin, butonlar)


def handle_callback(callback_data: str, callback_id: str, kullanici_id: int | None = None) -> str:
    try:
        _handle_callback_icerde(callback_data, callback_id, kullanici_id)
    except Exception as e:
        # Çökme YOK: hatayı bildir, paneli ana menüye döndür.
        print(f"::error::Panel hatası ({callback_data}): {e}")
        answer_callback(callback_id, "Bir hata oluştu")
        panel_goster(*ekran_ana())
        return "hata"
    return ""


def _handle_callback_icerde(callback_data: str, callback_id: str, kullanici_id: int | None) -> None:
    # TODO 25 — İMZALI CALLBACK KAPISI: riskli aksiyonlar imza + süre ister.
    # Bayat (eski panelden kalmış) veya taklit edilmiş buton ÇALIŞMAZ.
    if imza_gerekli(callback_data):
        gecerli, sonuc = imza_dogrula(callback_data)
        if not gecerli:
            mesaj = (
                "Bu düğme eskidi, menüyü yenile"
                if sonuc == "süresi geçti"
                else f"⛔ Düğme doğrulanamadı ({sonuc})"
            )
            answer_callback(callback_id, mesaj, show_alert=True)
            _ekran_goster(ekran_ana())
            return
        # Doğrulandı: imzayı ayır, PAYLOAD'u koru (ay:onay:<anahtar>:<indeks>)
        parcalar_imzali = callback_data.split(":")
        payload = ":".join(parcalar_imzali[:-2])
        callback_data = payload if payload.startswith("ay:onay") else sonuc

    global _SON_CALLBACK
    _SON_CALLBACK = callback_data
    if callback_data == "menu_main":
        _SON_CALLBACK = "menu_main"
        answer_callback(callback_id)
        _ekran_goster(ekran_ana())
        return
    if callback_data == "kanal_sagligi":
        answer_callback(callback_id, "Kanal sağlığı ölçülüyor...")
        _ekran_goster(ekran_kanal_sagligi())
        return
    if callback_data == "sistem_kok":
        answer_callback(callback_id)
        _ekran_goster(ekran_sistem_kok())
        return
    if callback_data == "geri":
        # Eski panellerden gelen "geri": bir üst ekranı yeniden çizer.
        hedef = ekran_ust(_SON_CALLBACK)
        answer_callback(callback_id)
        _ekran_goster(_EKRAN_URETICILER.get(hedef, ekran_ana)())
        return
    if callback_data == "mini_app_goster":
        answer_callback(callback_id)
        _ekran_goster(ekran_mini_app())
        return
    if callback_data == "denetim_goster":
        answer_callback(callback_id)
        _ekran_goster(ekran_denetim())
        return
    if callback_data == "sistem_nedir":
        answer_callback(callback_id)
        _ekran_goster(ekran_sistem_nedir())
        return
    if callback_data == "render_kart":
        answer_callback(callback_id)
        _ekran_goster(ekran_render_kart())
        return
    if callback_data == "kuyruk_liste":
        answer_callback(callback_id)
        _ekran_goster(ekran_kuyruk())
        return
    if callback_data == "kuyruk_at_onay":
        # TODO 13 kuralı: riskli işlem önce ONAY ekranından geçer.
        answer_callback(callback_id)
        _ekran_goster(ekran_kuyruk_at_onay())
        return
    if callback_data == "kuyruk_at_uygula":
        answer_callback(callback_id, "Kuyruk boşaltılıyor...")
        _ekran_goster(ekran_kuyruk_at_uygula())
        return
    if callback_data == "kuyruk_geri_al":
        answer_callback(callback_id, "Geri alınıyor...")
        _ekran_goster(ekran_kuyruk_geri_al())
        return
    if callback_data == "rapor_goster":
        answer_callback(callback_id, "Rapor yükleniyor...")
        _ekran_goster(ekran_rapor())
        return
    if callback_data == "uret_menu":
        answer_callback(callback_id)
        _ekran_goster(ekran_uret())
        return
    if callback_data == "uret_baslat":
        # TODO 13: onaysız tetikleme YOK — önce onay ekranı.
        answer_callback(callback_id)
        _ekran_goster(ekran_uret_onay())
        return
    if callback_data == "uret_onay":
        answer_callback(callback_id, "Üretim tetikleniyor...")
        _ekran_goster(ekran_metin_dugme(trigger_production_kontrollu()))
        return
    if callback_data == "uret_iptal":
        ok, mesaj = uretim_iptal_et()
        answer_callback(callback_id, "İptal edildi" if ok else "Pencere kapalı")
        _ekran_goster(ekran_metin_dugme(mesaj))
        return
    if callback_data == "uret_render_test":
        answer_callback(callback_id, "Render testi başlatılıyor...")
        _ekran_goster(ekran_metin_dugme(render_testi_tetikle()))
        return
    if callback_data == "ay:kok":
        answer_callback(callback_id)
        _ekran_goster(ekran_ayar_kok())
        return
    if callback_data == "ay:gecmis":
        answer_callback(callback_id, "Geçmiş yükleniyor...")
        _ekran_goster(ekran_gecmis())
        return
    if callback_data == "sistem_goster":
        answer_callback(callback_id, "Sistem durumu yükleniyor...")
        _ekran_goster(ekran_sistem())
        return
    if callback_data == "rapor_7gun":
        answer_callback(callback_id)
        _ekran_goster(ekran_7gun())
        return
    if callback_data == "performans":
        answer_callback(callback_id, "İzlenmeler okunuyor...")
        _ekran_goster(ekran_performans())
        return
    if callback_data == "bildirim_goster":
        answer_callback(callback_id)
        _ekran_goster(ekran_bildirim())
        return
    if callback_data == "bildirim_sustur1":
        from modules.bildirim import sustur

        bitis = sustur(1)
        answer_callback(callback_id, f"1 saat susturuldu ({bitis}'e kadar)")
        _ekran_goster(ekran_bildirim())
        return
    if callback_data == "bildirim_sustur24":
        from modules.bildirim import sustur

        bitis = sustur(24)
        answer_callback(callback_id, f"1 gün susturuldu ({bitis}'e kadar)")
        _ekran_goster(ekran_bildirim())
        return
    if callback_data == "bildirim_ac":
        from modules.bildirim import susturu_kaldir

        susturu_kaldir()
        answer_callback(callback_id, "Bildirimler açıldı")
        _ekran_goster(ekran_bildirim())
        return
    if callback_data == "bildirim_ozet":
        from modules.bildirim import gunluk_ozet_gonder

        sonuc = gunluk_ozet_gonder()
        answer_callback(callback_id, "Özet gönderildi" if sonuc["gonderildi"] else "Gönderilemedi")
        _ekran_goster(ekran_bildirim())
        return
    if callback_data == "panelleri_temizle":
        # Poller gecikince biriken panelleri ekrandan siler (geçmiş birikim temizliği).
        silinen = eski_panelleri_sil()
        answer_callback(
            callback_id,
            f"{silinen} mesaj silindi" if silinen else "Silinecek eski panel bulunamadı",
        )
        _ekran_goster(ekran_sistem())
        return
    if callback_data == "ay:hizli":
        answer_callback(callback_id)
        _ekran_goster(ekran_hizli_ayarlar())
        return
    if callback_data == "ay:tumu":
        answer_callback(callback_id)
        _ekran_goster(ekran_ayar_kok())
        return
    _p = callback_data.split(":")
    if len(_p) == 3 and _p[0] == "ay" and _p[1] == "t":
        _hizli_toggle(_p[2], callback_id)
        return
    if len(_p) == 4 and _p[0] == "ay" and _p[1] == "d":
        _hizli_stepper(_p[3], int(_p[2]), callback_id)
        return
    parcalar = callback_data.split(":")
    if len(parcalar) == 3 and parcalar[0] == "ay" and parcalar[1] == "g":
        grup = parcalar[2]
        if grup not in GRUPLAR:
            _bilinmeyen_komut(callback_id)
            return
        answer_callback(callback_id)
        _ekran_goster(ekran_ayar_grup(grup))
        return
    if len(parcalar) == 3 and parcalar[0] == "ay" and parcalar[1] == "nedir":
        # TODO 22: "ne işe yarar?" — salt okuma ekranı.
        anahtar = parcalar[2]
        if ayar_getir(anahtar) is None:
            _bilinmeyen_komut(callback_id)
            return
        answer_callback(callback_id)
        _ekran_goster(ekran_ayar_nedir(anahtar))
        return
    if len(parcalar) == 3 and parcalar[0] == "ay" and parcalar[1] == "s":
        anahtar = parcalar[2]
        a = ayar_getir(anahtar)
        if a is None:
            _bilinmeyen_komut(callback_id)
            return
        answer_callback(callback_id)
        _ekran_goster(ekran_ayar_detay(anahtar))
        return
    if len(parcalar) == 3 and parcalar[0] == "ay" and parcalar[1] == "onayd":
        anahtar = parcalar[2]
        beklemede = _bekleyen_giris_oku() or ""
        if not beklemede.startswith(f"{anahtar}#"):
            _bilinmeyen_komut(callback_id)
            return
        onaylanan = beklemede.split("#", 1)[1]
        _bekleyen_giris_yaz(None)
        answer_callback(callback_id, "Uygulanıyor...")
        ok, durum = ayar_uygula(anahtar, onaylanan, None)
        metin, dugmeler = ekran_ayar_detay(anahtar)
        if ok:
            panel_goster(f"{metin}\n\n✅ <b>Kaydedildi:</b> {onaylanan}", dugmeler)
        else:
            panel_goster(f"{metin}\n\n❌ <b>Uygulanamadı:</b> {durum}", dugmeler)
        return
    if len(parcalar) == 3 and parcalar[0] == "ay" and parcalar[1] == "gir":
        anahtar = parcalar[2]
        a = ayar_getir(anahtar)
        if a is None or a["tip"] != "sayi" or not degistirilebilir_mi(a):
            _bilinmeyen_komut(callback_id)
            return
        _bekleyen_giris_yaz(anahtar)
        answer_callback(callback_id, "Sayıyı yazın")
        _ekran_goster(ekran_giris(anahtar))
        return
    if len(parcalar) == 3 and parcalar[0] == "ay" and parcalar[1] == "test":
        anahtar = parcalar[2]
        if ayar_getir(anahtar) is None:
            _bilinmeyen_komut(callback_id)
            return
        answer_callback(callback_id, "Dry-run: hiçbir şey yazılmıyor...")
        _ekran_goster(ekran_ayar_test(anahtar))
        return
    if len(parcalar) == 3 and parcalar[0] == "ay" and parcalar[1] == "iptal":
        anahtar = parcalar[2]
        if ayar_getir(anahtar) is None:
            _bilinmeyen_komut(callback_id)
            return
        # Vazgeç: HİÇBİR YAZMA YOK — state bit bit aynı kalır.
        answer_callback(callback_id, "Vazgeçildi — değişiklik yapılmadı")
        _ekran_goster(ekran_ayar_detay(anahtar))
        return
    if len(parcalar) == 4 and parcalar[0] == "ay" and parcalar[1] in ("v", "onay"):
        _, eylem, anahtar, indeks_metin = parcalar
        a = ayar_getir(anahtar)
        if a is None or not degistirilebilir_mi(a):
            _bilinmeyen_komut(callback_id)
            return
        deger, sebep = _secenek_coz(a, indeks_metin)
        if deger is None:
            _bilinmeyen_komut(callback_id)
            return
        if eylem == "v" and a["risk"] == "yuksek":
            # Riskli ayar tek dokunuşla DEĞİŞMEZ — onay ekranı (yazma yok).
            answer_callback(callback_id, "Onay gerekiyor")
            _ekran_goster(ekran_onay(anahtar, int(indeks_metin)))
            return
        if eylem == "onay" and a["risk"] == "yuksek":
            answer_callback(callback_id, "Uygulanıyor...")
            ok, durum = ayar_uygula(anahtar, deger, kullanici_id)
            if not ok:
                _ekran_goster(ekran_metin_dugme(f"❌ Uygulanamadı: {durum}"))
                return
            metin, dugmeler = ekran_ayar_detay(anahtar)
            if durum:
                metin += f"\n\n{durum}"
            panel_goster(metin, dugmeler)
            return
        # riskli olmayan doğrudan uygulama
        answer_callback(callback_id, "Uygulanıyor...")
        ok, durum = ayar_uygula(anahtar, deger, kullanici_id)
        if not ok:
            _ekran_goster(ekran_metin_dugme(f"❌ Uygulanamadı: {durum}"))
            return
        metin, dugmeler = ekran_ayar_detay(anahtar)
        if durum:
            metin += f"\n\n{durum}"
        panel_goster(metin, dugmeler)
        return
    # Eski düğmeler (panel mesajı eski kalanlar için) — ekran olarak gösterilir
    eski_ekranlar: dict[str, str] = {
        "status_now": "status",
        "trigger_now": "trigger",
        "stats_today": "stats",
        "quality_today": "quality",
        "quota_status": "quota",
        "help_show": "help",
    }
    if callback_data in eski_ekranlar:
        ekran = eski_ekranlar[callback_data]
        metinler: dict[str, str] = {
            "status": get_status_text(),
            "stats": get_stats_text(),
            "quality": get_quality_text(),
            "quota": get_quota_text(),
            "help": get_help_text(),
            "trigger": trigger_production(),
        }
        answer_callback(callback_id, "Yükleniyor...")
        panel_goster(
            metinler[ekran],
            [
                [{"text": "🔄 Yenile", "callback_data": callback_data}],
                [{"text": "🏠 Menü", "callback_data": "menu_main"}],
            ],
        )
        return
    _bilinmeyen_komut(callback_id)


MENU_KOMUTLARI = {"/start", "/menu", "menü", "menu"}


def handle_message(text: str) -> str:
    """Metin komutlarını işler.

    - /start ve /menu: paneli GÖSTERİR. Kayıtlı panel varsa AYNI mesaj düzenlenir.
      Yeni panel yalnızca kayıt yok / >48 saat / mesaj silinmiş (edit 404) ise açılır.
    - Diğer tanınan komutlar reply_markup OLMAYAN düz mesajla cevap verir.
    - Tanınmayan metne cevap VERİLMEZ: klavye açıkken her tuş vuruşu spam üretmesin.

    NOT (2026-11-11 düzeltmesi): /start "her seferinde yeni panel" davranışı
    KALDIRILDI. Poller saatlerce çalışmadığında Telegram update'leri kuyruklar;
    kuyruk boşalınca N adet /start art arda işleniyor ve ekrana N panel düşüyordu
    (kanıt: 2026-11-11 koşusu — 5 × "/start" tek koşuda, ekranda üst üste paneller).
    Panel sıfırlama artık yalnızca kayıt geçersizse olur.
    """
    ham_metin = text.strip()
    text = ham_metin.lower()

    # SERBEST DEĞER GİRİŞİ (2026-11-11): panelde "✏️ Değer gir" seçildiyse
    # kullanıcının yazdığı sayı o ayara uygulanır. Komut/menü öncelikli DEĞİL:
    # kullanıcı beklerken yazdığı her şey değer sayılır, '/' ile başlamadıkça.
    bekleyen = _bekleyen_giris_oku()
    if bekleyen and not ham_metin.startswith("/"):
        a = ayar_getir(bekleyen)
        if a is not None:
            deger, sebep = _sayi_dogrula(a, ham_metin)
            if deger is None:
                # Sınır dışı → REDDET, ekranı tekrar göster (kaydetme YOK).
                metin, dugmeler = ekran_giris(bekleyen)
                panel_goster(f"{metin}\n\n❌ <b>Geçersiz:</b> {sebep}", dugmeler)
                return ""
            _bekleyen_giris_yaz(None)
            if a["risk"] == "yuksek":
                # Riskli ayar (video silebilir): ONAY ekranı — değeri beklemede tut.
                _bekleyen_giris_yaz(f"{bekleyen}#{deger}")
                panel_goster(*ekran_onay_deger(bekleyen, deger))
                return ""
            ok, durum = ayar_uygula(bekleyen, deger, None)
            metin, dugmeler = ekran_ayar_detay(bekleyen)
            if ok:
                ek = f"\n{durum}" if durum else ""
                panel_goster(f"{metin}\n\n✅ <b>Kaydedildi:</b> {deger}{ek}", dugmeler)
            else:
                panel_goster(f"{metin}\n\n❌ <b>Uygulanamadı:</b> {durum}", dugmeler)
            return ""

    if text in MENU_KOMUTLARI:
        # Kullanıcı isteği (2026-11-11): bot açılınca menüler GÖRÜNÜR olsun.
        klavye_gonder()
        menyu_gonder()
        return ""
    # ALT KLAVYE düğmeleri → aynı panelde ilgili ekran (yeni mesaj YOK).
    _duz = _duz_metin(ham_metin)
    if _duz in REPLY_ESLEME:
        hedef = REPLY_ESLEME[_duz]
        if hedef == "ay:kok":
            panel_goster(*ekran_ayar_kok())
        elif hedef == "kuyruk_liste":
            panel_goster(*ekran_kuyruk())
        elif hedef == "yardim_goster":
            panel_goster(*ekran_yardim())
        elif hedef == "uret_menu":
            panel_goster(*ekran_uret())
        elif hedef == "status_now":
            panel_goster(
                get_status_text(),
                [[{"text": "🔄 Yenile", "callback_data": "status_now"}], list(GERI_MENUSU)],
            )
        else:
            panel_goster(*ekran_rapor())
        return ""
    # TODO 13 — TEK PANEL KURALI: metin komutları YENİ MESAJ ATMAZ.
    # Eskiden /status, /stats, /help, /trigger doğrudan send_message çağırıp
    # panelin dışında paralel mesaj üretiyordu (ekranda iki panel birden).
    # Artık hepsi AYNI paneli ilgili ekrana yönlendirir.
    if text in ["/status", "durum", "status"]:
        panel_goster(*ekran_rapor())
        return ""
    if text in ["/trigger", "üret", "uret", "produce"]:
        # Onaysız tetikleme YOK: onay ekranı açılır (cooldown dahil).
        panel_goster(*ekran_uret_onay())
        return ""
    if text in ["/stats", "istatistik", "stats"]:
        panel_goster(*ekran_rapor())
        return ""
    if text in ["/mini", "/app", "mini", "miniapp"]:
        # TODO 31: Mini App bilgisi panelin İÇİNDE (yeni mesaj yok, tek panel).
        panel_goster(*ekran_mini_app())
        return ""
    if text in ["/help", "yardım", "yardim", "help"]:
        panel_goster(*ekran_yardim())
        return ""
    print(f"[Telegram Bot] Tanınmayan metin yok sayıldı (cevap verilmedi): {text[:40]!r}")
    return ""


# NOT: run_bot() uzun polling döngüsü GÜVENLİK TUZAĞIYDIR (workflow poller ile çakışır).
# Tek tüketim noktası: telegram_bot.yml workflow poller'ıdır. Yerelde çalıştırmak yerine
# `python -c "from modules.telegram_bot import process_update; ..."` kullanın.


_EKRAN_URETICILER: dict[str, Any] = {
    "menu_main": ekran_ana,
    "rapor_goster": ekran_rapor,
    "kanal_sagligi": ekran_kanal_sagligi,
    "uret_menu": ekran_uret,
    "status_now": ekran_durum,
    "sistem_kok": ekran_sistem_kok,
    "rapor_7gun": ekran_7gun,
    "performans": ekran_performans,
    "kuyruk_liste": ekran_kuyruk,
    "render_kart": ekran_render_kart,
    "denetim_goster": ekran_denetim,
    "bildirim_goster": ekran_bildirim,
    "mini_app_goster": ekran_mini_app,
    "sistem_goster": ekran_sistem,
    "ay:kok": ekran_ayar_kok,
    "ay:hizli": ekran_hizli_ayarlar,
    "ay:gecmis": ekran_gecmis,
    "yardim_goster": ekran_yardim,
}
