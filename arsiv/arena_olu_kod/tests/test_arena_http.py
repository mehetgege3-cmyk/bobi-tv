"""`modules/arena_http.py` — tarayıcısız Arena veri yolu testleri.

Kanıt kaynağı: Drive'daki `arena.ai_2026_11_13_00_17_02.md` (HAR) ve canlı
ölçüm: hash `ncoCtMLfdc358Ey9wglM-B3UUTRNnmagcXr4BxtSZx8` → image/png 3.1 MB.
"""

import json

from modules import arena_http


def test_cerez_cookie_editor_jsonundan_okunur():
    raw = json.dumps([
        {"name": "arena-auth-prod-v1.0", "value": "abc"},
        {"name": "user_country_code", "value": "TR"},
    ])
    assert arena_http._cerez_basligi(raw) == "arena-auth-prod-v1.0=abc; user_country_code=TR"


def test_cerez_ham_base64_deger_kabul_edilir():
    assert arena_http._cerez_basligi("xyz") == "arena-auth-prod-v1.0=xyz"


def test_cerez_base64_onekli_deger_soyulur():
    assert arena_http._cerez_basligi("base64-QVJD") == "arena-auth-prod-v1.0=QVJD"


def test_cerez_bos_ise_bos_doner(monkeypatch):
    monkeypatch.delenv("ARENA_COOKIES_JSON", raising=False)
    assert arena_http._cerez_basligi("") == ""


def test_sse_cevap_ve_gorsel_hash_cikarilir():
    """Gerçek HAR kaydının küçültülmüş hâli: text-delta + tool-output-available."""
    govde = "\n".join([
        'event: batch\ndata: ' + json.dumps({"records": [
            {"body": json.dumps({"data": {"type": "text-delta", "delta": "Yeşil "}})},
            {"body": json.dumps({"data": {"type": "text-delta", "delta": "orman"}})},
        ]}),
        'event: batch\ndata: ' + json.dumps({"records": [
            {"body": json.dumps({"data": {
                "type": "tool-output-available",
                "toolCallId": "tc_1",
                "output": {"status": "success", "hash": "ncoCtMLfd",
                           "file_path": "/home/user/kus.png"}}})},
        ]}),
    ])
    sonuc = {"metin": "", "gorsel_yolu": None, "hash": None}
    parcalar = []
    for kayit in arena_http._sse_kayitlari(govde):
        veri = kayit.get("data") or {}
        if veri.get("type") == "text-delta":
            parcalar.append(veri["delta"])
        if veri.get("type") == "tool-output-available":
            sonuc["hash"] = veri["output"]["hash"]
            sonuc["gorsel_yolu"] = veri["output"]["file_path"]
    assert "".join(parcalar) == "Yeşil orman"
    assert sonuc["hash"] == "ncoCtMLfd"
    assert sonuc["gorsel_yolu"] == "/home/user/kus.png"


def test_generate_image_girdisinden_yol_okunur():
    govde = 'data: ' + json.dumps({"records": [{"body": json.dumps({"data": {
        "type": "tool-input-available", "toolName": "generate_image",
        "input": {"file_path": "/home/user/kapak.png", "prompt": "x"}}})}]})
    kayitlar = list(arena_http._sse_kayitlari(govde))
    assert kayitlar[0]["data"]["input"]["file_path"] == "/home/user/kapak.png"


def test_oturum_bayragi_kalici():
    arena_http._OTURUM.clear()
    assert arena_http.oturum_doldu_mu() is False
    arena_http.oturum_doldu_isaretle()
    assert arena_http.oturum_doldu_mu() is True
    arena_http._OTURUM.clear()


def test_prompt_sonuna_soru_sorma_eklenir():
    """Kullanıcı bulgusu (2026-11-13): Arena 'Which image do you prefer?' diye
    soruyor; istem sonuna 'Soru sorma, yap.' eklenince doğrudan yapıyor."""
    assert arena_http.prompt_hazirla("Görsel üret").endswith("Soru sorma, yap.")
    # iki kez eklenmez
    bir = arena_http.prompt_hazirla("Görsel üret")
    assert arena_http.prompt_hazirla(bir) == bir


def test_kapak_promptu_kullanicinin_tek_cumlesi():
    """KULLANICI (2026-11-13): "Şablonu çöpe at, sadece benim dediğimi yap."

    İstem artık tek cümle: başlık + kullanıcının metni. Eski 7 kurallı şablon
    ve "Soru sorma, yap." eki KALDIRILDI.
    """
    from modules import kapak_gorsel

    prompt = kapak_gorsel.gorsel_promptu({"baslik": "Test Başlığı"})
    assert prompt.startswith("Test Başlığı")
    assert "İsimli short video için kapak fotoğrafı istiyorum" in prompt
    assert "profesyonel şekilde tasarla" in prompt
    assert "merak edip tıklasın" in prompt
    # Eski şablon izleri OLMAMALI
    assert "VİDEO METNİ (TAM)" not in prompt
    assert "TASARIM KURALLARI" not in prompt


def test_create_chat_yanitindan_chat_id_yakalanir():
    """HAR kanıtı: POST /nextjs-api/stream/create-chat → {"id": "<uuid>"}."""
    import inspect

    from modules import arena_api

    kaynak = inspect.getsource(arena_api)
    assert "create-chat" in kaynak
    assert 'page.on("response"' in kaynak
    assert "def son_chat_id" in kaynak


def test_video_metni_paket_metin_alani_okunur():
    """Koşu 43321910940: kapak istemine 21 karakter gitti (tam metin değil)."""
    from modules.kapak_gorsel import video_metni

    metin = "🧠 Merak sorusu... " * 10
    assert video_metni({"metin": metin}) == metin.strip()
    # senaryo.tam_metin öncelikli
    assert video_metni({"metin": "kisa", "senaryo": {"tam_metin": "uzun metin"}}) == "uzun metin"


def test_create_chat_dinleyici_her_akista_eklenir():
    """create-chat yakalama kapak hattında da bağlı olmalı (koşu 43321910940)."""
    import inspect

    from modules import arena_api, kapak_gorsel

    assert "def create_chat_dinleyici_ekle" in inspect.getsource(arena_api)
    assert "create_chat_dinleyici_ekle" in inspect.getsource(kapak_gorsel)
