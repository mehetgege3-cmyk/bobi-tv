"""TODO 3/4/5/7/12 — Hiyerarşik ayarlar menüsü + tek mesaj kuralı + onay + secret sınırı.

Kapsam: 4 düğmeli ana menü, callback_data şeması (kimlik taşır, değer taşımaz),
derinlik ≤3, düğme metni ≤20 karakter, callback ≤64 byte, bilinmeyen payload
çökmeden menüye döner, edit-in-place (10 etkileşim → 1 sendMessage + 9
editMessageText), 48 saat istisnası, riskli ayar onayı + dry-run, secret
desen taraması (0 eşleşme), push başarısızlığında bekleyen kuyruk + panel
uyarısı, render testi dispatch payload'ı, kota panelinin dürüst 'bilinmiyor'ı.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

# Repo kökünü import yoluna ekle (tests/ altından çalıştırılırken)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.ayar_deposu as ad  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402
from modules.ayar_katalogu import ayar_getir, tumu  # noqa: E402


@pytest.fixture(autouse=True)
def _panel_ortami(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Panel ortamı: izole state yolları + güvenli varsayılanlar.
    commit_ve_yukle varsayılan olarak başarılı taklit edilir; push başarısızlığı
    test eden testler kendi taklidini kurar."""
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(tb, "AYARLAR_STATE_YOLU", tmp_path / "ayarlar.json")
    monkeypatch.setattr(tb, "GECMIS_YOLU", tmp_path / "ayar_gecmisi.jsonl")
    monkeypatch.setattr(tb, "BEKLEYEN_YOLU", tmp_path / "ayarlar_bekleyen.json")
    monkeypatch.setattr(tb, "KOTA_YOLU", tmp_path / "youtube_quota.json")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(ad, "commit_ve_yukle", lambda dosyalar, mesaj, repo_kok=None: (True, ""))


def _telegram_yakalayici(
    ozel: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[tuple[str, dict[str, Any]]], Callable[[str, dict[str, Any] | None, float | None], Any]]:
    """requests.post yakalar; (yöntem, payload) listesi döndürür.
    ozel: yöntem → yanıt gövdesi (örn. editMessageText hata simülasyonu)."""
    cagrilar: list[tuple[str, dict[str, Any]]] = []
    ozel_yanitlar = ozel or {}

    def sahte_post(url: str, json: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
        yontem = str(url).rsplit("/", 1)[-1]
        cagrilar.append((yontem, json or {}))

        class R:
            status_code = 200

            def json(self) -> dict[str, Any]:
                if yontem in ozel_yanitlar:
                    return ozel_yanitlar[yontem]
                return {"ok": True, "result": {"message_id": 777}}

        return R()

    return cagrilar, sahte_post


def _takip_et(
    monkeypatch: pytest.MonkeyPatch, ozel: dict[str, dict[str, Any]] | None = None
) -> list[tuple[str, dict[str, Any]]]:
    cagrilar, sahte_post = _telegram_yakalayici(ozel)
    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    return cagrilar


def _son_panel_metni(cagrilar: list[tuple[str, dict[str, Any]]]) -> str:
    """En son sendMessage/editMessageText payload'ının metni."""
    for yontem, payload in reversed(cagrilar):
        if yontem in ("sendMessage", "editMessageText"):
            return str(payload.get("text", ""))
    return ""


# ---------------------------------------------------------------------------
# TODO 3 — menü hiyerarşisi ve callback_data şeması
# ---------------------------------------------------------------------------


def _tum_ekranlari_topla() -> list[tuple[str, tuple[str, list[list[dict[str, Any]]]]]]:
    """Şema sözleşmesi: her callback_data → ekran üretici."""
    ekranlar: list[tuple[str, tuple[str, list[list[dict[str, Any]]]]]] = [("menu_main", tb.ekran_ana())]
    ekranlar.append(("rapor_goster", tb.ekran_rapor()))
    ekranlar.append(("uret_menu", tb.ekran_uret()))
    ekranlar.append(("ay:kok", tb.ekran_ayar_kok()))
    ekranlar.append(("ay:gecmis", tb.ekran_gecmis()))
    ekranlar.append(("sistem_goster", tb.ekran_sistem()))
    ekranlar.append(("ay:g:tetikleme", tb.ekran_ayar_grup("tetikleme")))
    ekranlar.append(("ay:g:uretim_kota", tb.ekran_ayar_grup("uretim_kota")))
    ekranlar.append(("ay:g:temizlik", tb.ekran_ayar_grup("temizlik")))
    ekranlar.append(("ay:g:sistem", tb.ekran_ayar_grup("sistem")))
    for a in tumu():
        anahtar = str(a["anahtar"])
        ekranlar.append((f"ay:s:{anahtar}", tb.ekran_ayar_detay(anahtar)))
        ekranlar.append((f"ay:test:{anahtar}", tb.ekran_ayar_test(anahtar)))
    # TODO 25: onay callback'i imzalıdır; ekran karşılaştırması aksiyon
    # adı üzerinden yapılır (imza/zaman değişkendir).
    ekranlar.append(("ay:onay:force:1", tb.ekran_onay("force", 1)))
    ekranlar.append(("ay:onay:KOTA_DOLU_DAVRANIS:1", tb.ekran_onay("KOTA_DOLU_DAVRANIS", 1)))
    return ekranlar


def test_ana_menu_tam_dort_dugme() -> None:
    metin, butonlar = tb.ekran_ana()
    duz = [d["callback_data"] for satir in butonlar for d in satir]
    assert len(duz) == 4, f"ana menüde tam 4 düğme olmalı, gelen: {duz}"
    assert sorted(duz) == ["ay:kok", "rapor_goster", "status_now", "uret_menu"]
    # TODO 14: ana ekran artık canlı durum kartı; başlık "🎬 BOBİ TV".
    assert "BOBİ TV" in metin


def test_buton_metinleri_20_karakter_siniri() -> None:
    for ad_, (_metin, butonlar) in _tum_ekranlari_topla():
        for satir in butonlar:
            for dugme in satir:
                uzunluk = len(str(dugme["text"]))
                assert uzunluk <= 20, f"{ad_}: düğme metni >20: {dugme['text']!r} ({uzunluk})"


def test_callback_data_64_byte_siniri() -> None:
    for ad_, (_metin, butonlar) in _tum_ekranlari_topla():
        for satir in butonlar:
            for dugme in satir:
                bayt = len(str(dugme["callback_data"]).encode("utf-8"))
                assert bayt <= 64, f"{ad_}: callback_data >64 byte: {dugme['callback_data']!r}"


def test_menu_derinligi_en_fazla_3() -> None:
    """Callback şemasındaki her yol ana menüden ≤3 derinliktedir."""
    assert tb.CALLBACK_DERINLIK["menu_main"] == 0
    assert tb.CALLBACK_DERINLIK["ay:kok"] == 1
    assert tb.CALLBACK_DERINLIK["ay:g"] == 2
    assert tb.CALLBACK_DERINLIK["ay:s"] == 3
    assert max(tb.CALLBACK_DERINLIK.values()) <= 3


def test_her_alt_ekranda_menu_yolu_var() -> None:
    for ad_, (_metin, butonlar) in _tum_ekranlari_topla():
        if ad_ == "menu_main":
            continue
        callbacklar = [d["callback_data"] for satir in butonlar for d in satir]
        assert "menu_main" in callbacklar, f"{ad_}: 🏠 Menü yolu eksik"
        assert any(cb != "menu_main" for cb in callbacklar), f"{ad_}: ekran boş"


def test_bilinmeyen_callback_cokmeden_menuye_doner(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ay:s:gmax:9999` benzeri uydurma payload — çökme YOK, 'Bilinmeyen komut' + menü."""
    cagrilar = _takip_et(monkeypatch)
    sonuc = tb.handle_callback("ay:s:gmax:9999", "cbx")
    assert sonuc == ""
    cevaplar = [p for y, p in cagrilar if y == "answerCallbackQuery"]
    assert any("Bilinmeyen komut" in str(p.get("text", "")) for p in cevaplar)
    son = cagrilar[-1]
    assert son[0] in ("sendMessage", "editMessageText"), "menüye dönülmeli (panel yeniden)"
    assert "BOBİ TV" in str(son[1].get("text", ""))


def test_gecersiz_indeksli_uydurma_payload_uygulanmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ay:v:GUNLUK_HEDEF:99` — indeks katalog aralığı dışında → uygulanmaz, state yok.

    NOT (2026-11-11): GUNLUK_MAKS kaldırıldı ("kotayı kaldır" kararı); aynı
    test sayı tipi kalan GUNLUK_HEDEF ile yürütülüyor.
    """
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback("ay:v:GUNLUK_HEDEF:99", "cbz")
    assert not tb.AYARLAR_STATE_YOLU.exists(), "uydurma indeks state'e yazılamaz"
    assert "BOBİ TV" in _son_panel_metni(cagrilar)


def test_indeks_sunucuda_katalogdan_cozulur() -> None:
    """Şema sözleşmesi: callback_data İNDEKS taşır; değer yalnız sunucuda çözülür."""
    a = ayar_getir("GUNLUK_HEDEF")
    assert a is not None
    deger, _ = tb._secenek_coz(a, 2)
    # GUNLUK_HEDEF secenekleri ["1","2","4"] → indeks 2 = "4"
    assert deger == a["secenekler"][2], "indeks → katalog sırasındaki değer"
    deger_oob, sebep = tb._secenek_coz(a, 42)
    assert deger_oob is None and sebep
    yukleme_atla = ayar_getir("YUKLEME_ATLA")
    assert yukleme_atla is not None
    toggle, _ = tb._secenek_coz(yukleme_atla, 1)
    assert toggle == "1"


# ---------------------------------------------------------------------------
# TODO 4 — TEK MESAJ KURALI (edit-in-place)
# ---------------------------------------------------------------------------


def test_10_etkilesim_tek_mesaj_kurali(monkeypatch: pytest.MonkeyPatch) -> None:
    """/start + 9 ardışık tıklama → tam olarak 1 sendMessage + 9 editMessageText.
    Panel etkileşimi istisnasız AYNI mesajı düzenler (TODO 4)."""
    cagrilar = _takip_et(monkeypatch)
    tb.handle_message("/start")  # 1 sendMessage (panel burada doğar)
    tiklamalar = [
        "ay:kok",
        "ay:g:uretim_kota",
        "ay:s:GUNLUK_HEDEF",
        "menu_main",
        "rapor_goster",
        "ay:kok",
        "ay:g:tetikleme",
        "ay:s:MOD",
        "ay:gecmis",
    ]
    for i, cb in enumerate(tiklamalar):
        tb.handle_callback(cb, f"cb{i}")
    # Alt klavye taşıyıcısı hariç (2026-11-11 spec değişikliği).
    sends = sum(
        1 for y, p in cagrilar
        if y == "sendMessage" and "keyboard" not in (p.get("reply_markup") or {})
    )
    edits = sum(1 for y, _ in cagrilar if y == "editMessageText")
    assert sends == 1, f"10 etkileşimde tam 1 sendMessage olmalı, gelen: {sends}"
    assert edits == 9, f"9 tıklama tam 9 editMessageText olmalı, gelen: {edits}"


def test_start_yeni_panel_mesaji_acar(monkeypatch: pytest.MonkeyPatch) -> None:
    """/start artık YENİ panel AÇMAZ — kayıtlı panel varsa onu düzenler.

    2026-11-11 düzeltmesi: kuyrukta biriken N adet /start art arda işlenince
    ekrana N panel düşüyordu (kanıt: 5 × "/start" tek koşuda). Sözleşme artık:
    2 × /start → 1 sendMessage + 1 editMessageText (ilk çağrı paneli doğurur).
    """
    cagrilar = _takip_et(monkeypatch)
    tb.handle_message("/start")
    tb.handle_message("/start")
    # SPEC DEĞİŞTİ (2026-11-11, kullanıcı: "bot açılınca menüler açık görünsün"):
    # ilk /start'ta KALICI ALT KLAVYE için 1 taşıyıcı sendMessage gönderilir
    # (Telegram'da kalıcı klavye yalnız sendMessage ile kurulur). Panel sayısı
    # kuralı korunur: panel 1 kez doğar, ikinci /start onu DÜZENLER.
    panel_sends = [
        y for y, p in cagrilar
        if y == "sendMessage" and "reply_markup" in p and "inline_keyboard" in p["reply_markup"]
    ]
    edits = sum(1 for y, _ in cagrilar if y == "editMessageText")
    assert len(panel_sends) == 1, f"2 /start → tek panel olmalı, panel sendMessage: {len(panel_sends)}"
    assert edits == 1, f"ikinci /start paneli düzenlemeli, editMessageText: {edits}"
    # Klavye taşıyıcısı BİR KEZ gönderilir (ikinci /start'ta tekrar etmez).
    klavye = [
        y for y, p in cagrilar
        if y == "sendMessage" and "keyboard" in (p.get("reply_markup") or {})
    ]
    assert len(klavye) == 1, f"alt klavye yalnız bir kez kurulmalı, gelen: {len(klavye)}"


def test_menu_metni_ayni_mesaji_duzenler(monkeypatch: pytest.MonkeyPatch) -> None:
    """/start dışındaki menü komutları spam üretmez: panel varsa düzenlenir."""
    cagrilar = _takip_et(monkeypatch)
    tb.handle_message("/start")
    tb.handle_message("menu")
    tb.handle_message("menü")
    # Alt klavye taşıyıcısı hariç: panel mesajları sayılır (spec değişikliği
    # 2026-11-11 — kalıcı klavye ilk /start'ta bir kez gönderilir).
    sends = sum(
        1 for y, p in cagrilar
        if y == "sendMessage" and "keyboard" not in (p.get("reply_markup") or {})
    )
    edits = sum(1 for y, _ in cagrilar if y == "editMessageText")
    assert sends == 1
    assert edits == 2


def test_48_saatt_eski_panel_yeni_mesaj_istirisasi(monkeypatch: pytest.MonkeyPatch) -> None:
    """TODO 4 istisnası a: panel >48 saat → edit yerine yeni mesaj."""
    _takip_et(monkeypatch)
    tb.handle_message("/start")
    # panel zamanını 3 gün öncesine al:
    veri = json.loads(tb.MENU_STATE_YOLU.read_text(encoding="utf-8"))
    eski_zaman = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    veri["zaman"] = eski_zaman
    tb.MENU_STATE_YOLU.write_text(json.dumps(veri), encoding="utf-8")
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback("rapor_goster", "cb1")
    sends = sum(1 for y, _ in cagrilar if y == "sendMessage")
    edits = sum(1 for y, _ in cagrilar if y == "editMessageText")
    assert sends == 1 and edits == 0, "48 saatten eski panel düzenlenmez, taze panel açılır"


def test_message_not_modified_sessizce_yutulur(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aynı ekranı tekrar çizmek 'message is not modified' döndürür — bu HATA
    sayılmaz, sessizce yutulur, yeni mesaj GÖNDERİLMEZ."""
    ozel = {"editMessageText": {"ok": False, "description": "Bad Request: message is not modified"}}
    _takip_et(monkeypatch)
    tb.handle_message("/start")
    cagrilar = _takip_et(monkeypatch, ozel)
    tb.handle_callback("ay:kok", "cb1")
    tb.handle_callback("ay:kok", "cb2")
    sends = sum(1 for y, _ in cagrilar if y == "sendMessage")
    assert sends == 0, "'not modified' durumunda yeni mesaj gönderilmemeli"
    edits = sum(1 for y, _ in cagrilar if y == "editMessageText")
    assert edits == 2, "her tıklama yine de düzenleme yolunu denemeli"


def test_panel_hatasinda_cokme_yok_menuye_donus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ekran üretiminde beklenmedik istisna → bot çökmez, ana menüye döner."""
    cagrilar = _takip_et(monkeypatch)

    def patlayan(grup: str) -> tuple[str, list[list[dict[str, Any]]]]:
        raise RuntimeError("ekran üretimi patladı")

    monkeypatch.setattr(tb, "ekran_ayar_grup", patlayan)
    sonuc = tb.handle_callback("ay:g:uretim_kota", "cberr")
    assert sonuc == "hata"
    assert "BOBİ TV" in _son_panel_metni(cagrilar)


# ---------------------------------------------------------------------------
# TODO 5 — riskli ayarlar: onay + dry-run
# ---------------------------------------------------------------------------


def test_riskli_ayar_onaysiz_uygulanmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    """KOTA_DOLU_DAVRANIS riskli → seçim anında YAZMAZ, onay ekranı gösterir."""
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback("ay:v:KOTA_DOLU_DAVRANIS:1", "cb1")
    assert not tb.AYARLAR_STATE_YOLU.exists(), "riskli ayar onaydan önce yazılamaz"
    metin = _son_panel_metni(cagrilar)
    assert "ONAY GEREKİYOR" in metin
    dugmeler = [
        d
        for y, p in cagrilar
        if y in ("sendMessage", "editMessageText")
        for d in (p.get("reply_markup") or {}).get("inline_keyboard", [])
    ]
    flat = [d for satir in dugmeler for d in satir]
    onayla = [d["callback_data"] for d in flat if "Onayla" in str(d["text"])]
    vazgec = [d["callback_data"] for d in flat if "Vazgeç" in str(d["text"])]
    # TODO 25: onay butonu artık İMZALI + süreli (payload imzaya dahil).
    assert len(onayla) == 1
    assert onayla[0].startswith("ay:onay:KOTA_DOLU_DAVRANIS:1:")
    assert tb.imza_dogrula(onayla[0])[0] is True, "onay imzası geçersiz"
    assert vazgec == ["ay:iptal:KOTA_DOLU_DAVRANIS"]


def test_force_onay_ekrani_gercek_etkiyi_hesaplar(monkeypatch: pytest.MonkeyPatch) -> None:
    """force onay ekranı kota matematiğini gösterir — uydurma sayı yok."""
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback("ay:v:force:1", "cb1")
    metin = _son_panel_metni(cagrilar)
    # SPEC DEĞİŞTİ (2026-11-11, kullanıcı: "kotayı kaldır"): onay metni artık
    # "günlük sınırı aşar" demez; tavan olmadığı için "tavan 6" beklentisi de
    # kaldırıldı. Etki yine GERÇEK hedeften hesaplanır (uydurma sayı yok).
    assert "Zorla üretim" in metin
    assert "~1 yükleme" in metin, "etki: GUNLUK_HEDEF varsayılanı 1"
    assert "yükleme tavanı yok" in metin.lower()
    assert "tavan 6" not in metin
    assert not tb.AYARLAR_STATE_YOLU.exists(), "onay ekranı HİÇBİR YAZMA yapmaz"


def test_onay_sonrasi_uygulanir_ve_gecmise_yazar(monkeypatch: pytest.MonkeyPatch) -> None:
    cagrilar = _takip_et(monkeypatch)
    # TODO 25: imzalı onay callback'i (elle yazılan imzasız veri reddedilir).
    tb.handle_callback(tb.imzali_ay_callback("ay:onay", "KOTA_DOLU_DAVRANIS", 1), "cb1")
    ham = ad.state_ham_ayarlari(tb.AYARLAR_STATE_YOLU)
    assert ham.get("KOTA_DOLU_DAVRANIS") == "hata"
    kayitlar = ad.gecmisi_oku(10, tb.GECMIS_YOLU)
    assert len(kayitlar) == 1
    assert kayitlar[0]["anahtar"] == "KOTA_DOLU_DAVRANIS"
    assert kayitlar[0]["eski"] == "sessiz_dur" and kayitlar[0]["yeni"] == "hata"
    assert kayitlar[0]["kaynak"] == "telegram"
    metin = _son_panel_metni(cagrilar)
    assert "hata (state)" in metin, "detay ekranı yeni değeri + kaynağı göstermeli"


def test_vazgec_state_bit_bit_ayni_birakir(monkeypatch: pytest.MonkeyPatch) -> None:
    """'← Vazgeç' → state bit bit aynı (onay ekranı hiçbir şey yazmadı)."""
    _takip_et(monkeypatch)
    ad.kaydet({"GUNLUK_HEDEF": "2", "MOD": "normal"}, tb.AYARLAR_STATE_YOLU)
    onceki = tb.AYARLAR_STATE_YOLU.read_bytes()
    tb.handle_callback("ay:v:force:1", "cb0")  # onay ekranı
    tb.handle_callback("ay:iptal:force", "cb1")  # vazgeç
    sonraki = tb.AYARLAR_STATE_YOLU.read_bytes()
    assert onceki == sonraki, "Vazgeç state'i bit bit aynı bırakmalı"
    ham = ad.state_ham_ayarlari(tb.AYARLAR_STATE_YOLU)
    assert ham.get("force", "0") == "0" and "force" not in ham


def test_dry_run_hicbir_yazma_yapmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    """TODO 5 dry-run: 'ay:test' ekranı hiçbir dosyaya yazmaz, yükleme/deneme yapmaz."""
    cagrilar = _takip_et(monkeypatch)

    def yazmamali(*args: object, **kwargs: object) -> None:
        raise AssertionError("dry-run ekranı kaydet() çağırmamalıydı")

    def commitmamali(*args: object, **kwargs: object) -> None:
        raise AssertionError("dry-run ekranı commit çağırmamalıydı")

    monkeypatch.setattr(ad, "kaydet", yazmamali)
    monkeypatch.setattr(ad, "commit_ve_yukle", commitmamali)
    tb.handle_callback("ay:test:force", "cb1")
    tb.handle_callback("ay:test:GUNLUK_HEDEF", "cb2")
    metin = _son_panel_metni(cagrilar)
    assert "hiçbir dosyaya yazmadı" in metin
    assert not tb.AYARLAR_STATE_YOLU.exists()
    assert not tb.BEKLEYEN_YOLU.exists()


# ---------------------------------------------------------------------------
# TODO 11 — temizlik grubu: değiştirilemez + dürüst uyarı
# ---------------------------------------------------------------------------


def test_temizlik_ayari_degistirme_yolu_URETIR() -> None:
    """2026-11-11 kararı: temizlik ayarları kilitli DEĞİL — kullanıcı girer.

    Önceki spec değiştirme düğmesini YASAKLIYORDU; kullanıcı bunu "muhafazakâr
    dayatma" olarak reddetti. Artık düğme VAR, ama riskli ayar olduğu için
    değişiklik ONAY ekranından geçer (ay:onay:...).
    """
    for anahtar in ("OTOMATIK_SIL_AKTIF", "MIN_IZLENME_ESIGI", "IZLENME_KONTROL_DK"):
        _metin, butonlar = tb.ekran_ayar_detay(anahtar)
        callbacklar = [d["callback_data"] for satir in butonlar for d in satir]
        giris = [cb for cb in callbacklar
                 if cb.startswith(("ay:v:", "ay:onay:", "ay:gir:"))]
        assert giris, f"{anahtar}: değiştirme yolu ÜRETİLMELİ (kilit kaldırıldı)"


def test_temizlik_uyari_metni_panelde_gosterilir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Panel, videonun GERÇEKTEN silineceğini söylemeli (yalan yasak)."""
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback("ay:s:MIN_IZLENME_ESIGI", "cb1")
    metin = _son_panel_metni(cagrilar)
    assert "SİLER" in metin, "silme uyarısı panelde olmalı"
    assert "100" in metin, "mevcut değer (100) gösterilir"


def test_temizlik_yazmaya_calisirsa_reddedilir(monkeypatch: pytest.MonkeyPatch) -> None:
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback(tb.imzali_ay_callback("ay:onay", "MIN_IZLENME_ESIGI", 0), "cb1")
    assert not tb.AYARLAR_STATE_YOLU.exists()
    assert "BOBİ TV" in _son_panel_metni(cagrilar)


# ---------------------------------------------------------------------------
# TODO 7 — secret sınırı: desen taraması 0 eşleşme
# ---------------------------------------------------------------------------

SECRET_DESENLER: tuple[re.Pattern[str], ...] = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza"),
    re.compile(r"ya29\."),
    re.compile(r"Bearer "),
    re.compile(r"[A-Za-z0-9+/]{40,}"),  # 40+ karakterlik base64 blok
)


def _butun_panel_ciktilarini_uret() -> list[str]:
    ciktilar: list[str] = []
    for _ad, (metin, butonlar) in _tum_ekranlari_topla():
        ciktilar.append(metin)
        for satir in butonlar:
            for dugme in satir:
                ciktilar.append(str(dugme["text"]))
                ciktilar.append(str(dugme["callback_data"]))
    return ciktilar


def test_panel_ciktilarinda_secret_deseni_sifir_eslesme(monkeypatch: pytest.MonkeyPatch) -> None:
    """TODO 7 — TÜM panel ekranlarında ghp_ / github_pat_ / AIza / ya29. /
    Bearer  / 40+ base64 blok → 0 eşleşme (secret tanımlı VE eksik durumlarında)."""
    for gh_durum in (True, False):
        if gh_durum:
            monkeypatch.setenv("GH_TOKEN", "fake-token")
            monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
        else:
            monkeypatch.delenv("GH_TOKEN", raising=False)
            monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        for cikti in _butun_panel_ciktilarini_uret():
            for desen in SECRET_DESENLER:
                eslesme = desen.search(cikti)
                assert eslesme is None, f"secret deseni sızdı: {desen.pattern} → {cikti[:80]!r}"


def test_sistem_ekrani_sadece_var_yok_gosterir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret tanımlıysa ✅, değilse ⛔ — değer asla metinde yok."""
    metin, _ = tb.ekran_sistem()
    assert "⛔ eksik" in metin
    assert "fake:token" not in metin and "fake-token" not in metin
    monkeypatch.setenv("GH_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    metin2, _ = tb.ekran_sistem()
    assert "✅ tanımlı" in metin2
    assert "fake-token" not in metin2 and "fake:token" not in metin2
    assert "GitHub Secrets" in metin2


def test_secret_detay_ekrani_deger_gostemez() -> None:
    metin, butonlar = tb.ekran_ayar_detay("YOUTUBE_TOKEN")
    assert "ASLA gösterilmez" in metin
    callbacklar = [d["callback_data"] for satir in butonlar for d in satir]
    assert not [cb for cb in callbacklar if cb.startswith(("ay:v:", "ay:onay:"))]


# ---------------------------------------------------------------------------
# TODO 8 — push başarısızlığı yutulmaz: bekleyen kuyruk + panel uyarısı
# ---------------------------------------------------------------------------


def test_push_basarisizsa_bekleyen_kuyruk_ve_panel_uyarisi(monkeypatch: pytest.MonkeyPatch) -> None:
    cagrilar = _takip_et(monkeypatch)

    def basarisiz(dosyalar: list[str], mesaj: str, repo_kok: Path | None = None) -> tuple[bool, str]:
        return False, "git push başarısız: simülasyon"

    monkeypatch.setattr(ad, "commit_ve_yukle", basarisiz)
    tb.handle_callback("ay:v:GUNLUK_HEDEF:2", "cb1")  # değer "4", riskli değil → uygula
    bekleyen = ad.bekleyenleri_al(tb.BEKLEYEN_YOLU)
    assert bekleyen is not None, "push başarısız → bekleyen kuyruğa yazılmalı"
    assert bekleyen["degisiklikler"] == {"GUNLUK_HEDEF": "4"}
    ham = ad.state_ham_ayarlari(tb.AYARLAR_STATE_YOLU)
    assert ham.get("GUNLUK_HEDEF") == "4", "yerel state yine de güncel olmalı"
    metin = _son_panel_metni(cagrilar)
    assert "kaydedilemedi" in metin and "tekrar denenecek" in metin


def test_push_basarisizligi_sonraki_kosuda_yeniden_denir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bekleyen kuyruk: ilk denemede geçmiş zaten yazıldı; yeniden deneme
    geçmişi TEKRAR yazmaz (çift kayıt olmaz) ama state'i tamamlar."""
    ad.bekleyene_yaz({"GUNLUK_HEDEF": "4"}, "geçen koşu push hatası", 7, tb.BEKLEYEN_YOLU)
    durum = tb.bekleyen_ayarlari_yeniden_dene()
    assert "push edildi" in durum
    ham = ad.state_ham_ayarlari(tb.AYARLAR_STATE_YOLU)
    assert ham.get("GUNLUK_HEDEF") == "4"
    assert ad.bekleyenleri_al(tb.BEKLEYEN_YOLU) is None, "başarılı denemeden sonra kuyruk temizlenmeli"
    assert ad.gecmisi_oku(10, tb.GECMIS_YOLU) == [], "yeniden deneme geçmişi kopyalamaz"


def test_bekleyen_hala_basarısızsa_kuyruk_kalir(monkeypatch: pytest.MonkeyPatch) -> None:
    ad.bekleyene_yaz({"MOD": "normal"}, "geçen koşu push hatası", 7, tb.BEKLEYEN_YOLU)

    def basarisiz(dosyalar: list[str], mesaj: str, repo_kok: Path | None = None) -> tuple[bool, str]:
        return False, "git push başarısız: hâlâ"

    monkeypatch.setattr(ad, "commit_ve_yukle", basarisiz)
    durum = tb.bekleyen_ayarlari_yeniden_dene()
    assert "hâlâ push edilemedi" in durum
    assert ad.bekleyenleri_al(tb.BEKLEYEN_YOLU) is not None, "kuyruk temizlenmemeli"


def test_kaynak_etiketi_duruma_gore_degisir(tmp_path) -> None:
    """Kaynak etiketi katmanı doğru göstermeli: (varsayılan) vs (state).

    NOT (2026-11-11): sabit "6" beklentisi GUNLUK_MAKS döneminden kalmaydı;
    GUNLUK_HEDEF varsayılanı "1". Sabit sayı yerine katalog varsayılanı
    kullanılıyor ki katalog değişince test yanlış kırılmasın.
    """
    varsayilan = ayar_getir("GUNLUK_HEDEF")["varsayilan"]
    metin = tb.ekran_ayar_detay("GUNLUK_HEDEF")[0]
    assert f"{varsayilan} (varsayılan)" in metin
    ad.kaydet({"GUNLUK_HEDEF": "5"}, tb.AYARLAR_STATE_YOLU)
    metin2, _ = tb.ekran_ayar_detay("GUNLUK_HEDEF")
    assert "5 (state)" in metin2


# ---------------------------------------------------------------------------
# TODO 12 — yüklemsiz test düğmesi
# ---------------------------------------------------------------------------


def test_render_testi_dispatch_payload_dogru(monkeypatch: pytest.MonkeyPatch) -> None:
    """repository_dispatch payload: event_type=bobi-tv-produce, yukleme_atla=1,
    force=true — URL dispatches uç noktası olmalı, token yalnız header'da."""
    yakalanan: dict[str, Any] = {}

    class SahteYanit:
        status_code = 204
        text = ""

    def sahte_post(
        url: str,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> SahteYanit:
        yakalanan["url"] = url
        yakalanan["json"] = json or {}
        yakalanan["headers"] = headers or {}
        return SahteYanit()

    monkeypatch.setenv("GH_TOKEN", "fake-pat")
    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    mesaj = tb.render_testi_tetikle()
    assert yakalanan["url"].endswith("/repos/mehetgege3-cmyk/bobi-tv/dispatches")
    govde = yakalanan["json"]
    assert govde["event_type"] == "bobi-tv-produce"
    assert govde["client_payload"]["yukleme_atla"] == "1"
    assert govde["client_payload"]["force"] == "true"
    assert "fake-pat" in yakalanan["headers"]["Authorization"], "token header'da, argv'de değil"
    assert "yükleme yapılmadı" in mesaj


def test_render_testi_token_yoksa_durstur_hata_verir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    mesaj = tb.render_testi_tetikle()
    assert mesaj.startswith("❌")
    assert "tetiklendi" not in mesaj and "başlatıldı" not in mesaj


def test_render_testi_dugmesi_uret_ekraninda() -> None:
    metin, butonlar = tb.ekran_uret()
    callbacklar = [d["callback_data"] for satir in butonlar for d in satir]
    assert "uret_render_test" in callbacklar
    assert "YÜKLEME YAPMADAN" in metin or "YÜKLEME YAPILMAZ" in metin


# ---------------------------------------------------------------------------
# TODO 10 (panel yüzü) — kota durumu dürüst 'bilinmiyor'
# ---------------------------------------------------------------------------


def test_kota_paneli_dosya_yokken_bilinmiyor_der() -> None:
    ozet = tb._kota_birim_ozeti()
    assert "bilinmiyor" in ozet
    assert not re.search(r"\d{3,}", ozet), "dosya yokken sayı UYDURULMAZ"


def test_kota_paneli_birim_kaydi_yokken_bilinmiyor_der() -> None:
    tb.KOTA_YOLU.write_text(
        json.dumps({"doldu": True, "kalan_saat": 24, "video_sayisi": 0}), encoding="utf-8"
    )
    ozet = tb._kota_birim_ozeti()
    assert "bilinmiyor" in ozet, "birim kaydı yoksa uydurma hesap yapma"


def test_kota_paneli_birim_bilgisiyle_yukleme_hesaplar() -> None:
    tb.KOTA_YOLU.write_text(json.dumps({"kalan_birim": 5200, "toplam_birim": 10000}), encoding="utf-8")
    ozet = tb._kota_birim_ozeti()
    assert "4800/10000 birim" in ozet
    assert "~3 yükleme kaldı" in ozet, "5200 // 1600 = 3"


def test_rapor_ekrani_uc_bolumu_birlestirir(monkeypatch: pytest.MonkeyPatch) -> None:
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback("rapor_goster", "cb1")
    metin = _son_panel_metni(cagrilar)
    # SPEC DEĞİŞTİ (2026-11-11): raporun 3. bölümü artık "Kota" değil
    # "Yükleme" — tavan kaldırıldı, bölüm sayıyı korur ("tavan YOK" yazar).
    assert "İstatistik" in metin and "Kalite Raporu" in metin and "Yükleme" in metin
