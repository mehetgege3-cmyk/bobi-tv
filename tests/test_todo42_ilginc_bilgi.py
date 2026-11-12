"""İlginç bilgi içerik hattı — 8 kategori, 12 kural, doğruluk, etkileşim, paket.

KULLANICI TALEBİ (2026-11-11): "Bu kategorileri, formatı ve konuların hepsini
çöpe at. Hiçbir kullanıcı bu saçmalıklara zaman ayırmaz."

Yeni sözleşme:
  • 8 kategori, her paylaşımda rastgele biri (son 4 videoda tekrar yok)
  • Zorunlu format: 🧠 Günün Merak Uyandıran Sorusu / 🔍 Cevabı Biliyor
    Muydun? (200-300 kelime) / 💡 Şaşırtıcı Sonuç
  • 12 içerik kuralı, her biri ayrı denetim fonksiyonu
  • Uydurma bilgi yok: kaynak zorunlu, tehlikeli iddia reddedilir,
    çürütülmüş bilgi "gerçek" diye sunulamaz
  • Eski VS/iki karakter düellosu ve "😱 Şoke Etti" kalıbı YOK
  • Arena çökerse doğrulanmış banka; o da yoksa üretim DURUR (uydurmaz)
"""

from __future__ import annotations

import pytest

from modules.ilginc_bilgi import (
    dogruluk,
    etkilesim,
    kategoriler,
    kurallar,
    uretici,
    yedek_bilgiler,
)

# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def ornek_metin(cevap_ek: str = "", soru: str = "Ahtapotların kaç kalbi var?") -> str:
    cevap = (
        "Çoğumuz hayvanların tek kalbi olduğunu düşünürüz, oysa ahtapotlarda işler "
        "bambaşka. Ahtapotların tam üç kalbi vardır ve her biri farklı bir iş yapar. "
        "İki kalp solungaçlara kan pompalar, üçüncüsü vücuda temiz kan taşır. İşin "
        "ilginç yanı, bu kalplerden biri yüzerken durur. Yani ahtapot yüzdüğü sürece "
        "üçüncü kalbi çalışmaz ve hayvan bu yüzden deniz tabanında sürünmeyi seçer. "
        "Bir düşün: sabah kahveni içerken, denizin altında senden tamamen farklı bir "
        "dolaşım sistemiyle yaşayan bir canlı olduğunu hayal et. Kanı da sıra dışıdır: "
        "oksijen taşıyan pigment demir değil bakır kullanır, bu yüzden kanı mavidir. "
        "Bakır temelli kan oksijeni soğuk sularda daha verimli taşır; bu da ahtapotun "
        "neden derin denizlerde rahat yaşadığını açıklar. Kollarında sinir hücresi "
        "kümeleri vardır; yani kolları neredeyse kendi başına karar verebilir. Bir "
        "ahtapotun kolu koptuğunda bir süre hareket etmeye devam eder. Dokunaçlarındaki "
        "vantuzlar tat alır, bu yüzden hayvan adeta dokunarak tadar. Laboratuvarda "
        "kavanoz kapağını açmayı öğrenen bireyler kaydedilmiştir. Bu yüzden bilim "
        "insanları ahtapotu sıra dışı zekâlardan biri sayar. Sinir sisteminin üçte "
        "ikisi kollarında dağılmış durumdadır ve bu dağılım onu benzersiz kılar. "
        "Ahtapotlar dünyanın hemen her okyanusunda yaşar; kutup sularından tropik "
        "mercan resiflerine kadar geniş bir alana yayılmışlardır. En küçük türler bir "
        "buğday tanesi kadar, en büyükleri ise bir insandan daha uzun kollarıyla "
        "tanınır. Kısa ömürlüdürler; pek çoğu bir yıl kadar yaşar ve çiftleşmeden sonra "
        "hayatları sona erer. Yumurtadan çıkan yavrular başlangıçta planktonla beslenir, "
        "büyüdükçe yengeç ve deniz kabuğu gibi sert kabuklu canlılara yönelir. "
        "Renk değiştirerek saklanmaları yalnız kamuflaj değildir; duygusal durumlarını "
        "de yansıttığı düşünülüyor. Bu yüzden bir akvaryumda oturup kahveni yudumlarken "
        "onun saniyeler içinde renk değiştirmesini izlemek, doğanın en tuhaf "
        "gösterilerinden biridir." + cevap_ek
    )
    return (
        f"{kurallar.BASLIK_SORU}\n{soru}\n\n"
        f"{kurallar.BASLIK_CEVAP}\n{cevap}\n\n"
        f"{kurallar.BASLIK_SONUC}\nÜç kalbi olan bir canlı yüzerken birini kapatıyor. 🐙"
    )


# ---------------------------------------------------------------------------
# 1) Kategoriler
# ---------------------------------------------------------------------------


def test_sekiz_kategori_var():
    assert len(kategoriler.ANAHTARLAR) == 8
    adlar = {kategoriler.kategori_adi(k) for k in kategoriler.ANAHTARLAR}
    assert "Bilim ve Teknoloji" in adlar
    assert "Hayvanlar ve Canlılar" in adlar
    assert "Günlük Yaşam ve İlginç Olaylar" in adlar


def test_her_kategorinin_ayri_renk_paleti_var():
    """Her video farklı görünsün kuralı: paletler birbirinden ayrışmalı."""
    paletler = {kategoriler.renk_paleti(k) for k in kategoriler.ANAHTARLAR}
    assert len(paletler) == 8


def test_kategori_son_sekiz_videoda_tekrar_etmez():
    son = [
        "hayvanlar",
        "doga_evren",
        "tarih_medeniyet",
        "bilim_teknoloji",
        "insan_vucudu",
        "yiyecekler",
        "kulturler",
    ]
    for video_no in range(1, 30):
        secilen = kategoriler.siradaki_kategori(son, video_no=video_no)
        assert secilen not in son
        assert secilen == "gunluk_yasam"  # kalan tek aday


def test_kategori_secimi_deterministik():
    a = kategoriler.siradaki_kategori([], video_no=7)
    b = kategoriler.siradaki_kategori([], video_no=7)
    assert a == b


# ---------------------------------------------------------------------------
# 2) Zorunlu format
# ---------------------------------------------------------------------------


def test_zorunlu_uc_baslik_denetlenir():
    tam = f"{kurallar.BASLIK_SORU}\nsoru\n\n{kurallar.BASLIK_CEVAP}\ncevap\n\n{kurallar.BASLIK_SONUC}\nsonuç"
    assert kurallar.format_dogrula(tam) == []

    eksik = kurallar.format_dogrula(f"{kurallar.BASLIK_SORU}\nsoru\n{kurallar.BASLIK_SONUC}\nsonuç")
    assert eksik and "başlık eksik" in eksik[0].ayrinti


def test_baslik_sirasi_yanlissa_reddedilir():
    ihlaller = kurallar.format_dogrula(
        f"{kurallar.BASLIK_CEVAP}\nx\n{kurallar.BASLIK_SORU}\ny\n{kurallar.BASLIK_SONUC}\nz"
    )
    assert any("sırada" in i.ayrinti for i in ihlaller)


def test_eski_sok_kalibi_yok():
    """Eski '😱 Şoke Etti #shorts' kalıbı yeni formatta bulunmamalı."""
    for b in yedek_bilgiler.YEDEK_BILGILER:
        text = yedek_bilgiler.tam_metin(b).lower()
        assert "şoke etti" not in text
        assert "yok artık" not in text


# ---------------------------------------------------------------------------
# 3) 12 kural — tek tek
# ---------------------------------------------------------------------------


def test_tum_kurallar_gecerli_metinde_temiz():
    rapor = kurallar.denetle(ornek_metin(), kaynak="National Geographic", kategori="hayvanlar")
    assert rapor.yayinlanabilir, rapor.ozet()
    assert rapor.skor >= 90


def test_k1_soru_yoksa_kritik():
    metin = ornek_metin().replace(kurallar.BASLIK_SORU, "Giriş")
    rapor = kurallar.denetle(metin, kaynak="Britannica")
    assert any(i.kod == "R1" and i.agirlik == 3 for i in rapor.ihlaller)


def test_k1_soru_isareti_yoksa_uyari():
    rapor = kurallar.denetle(
        ornek_metin(soru="Ahtapotların kaç kalbi olduğunu düşün"),
        kaynak="Britannica",
    )
    assert any(i.kod == "R1" for i in rapor.ihlaller)


def test_k2_cevap_ilk_cumlede_sizarsa_uyari():
    rapor = kurallar.denetle(
        ornek_metin(cevap_ek="", soru="Ahtapotların 3 kalbi mi var?").replace(
            "Çoğumuz hayvanların tek kalbi olduğunu düşünürüz, oysa ahtapotlarda işler bambaşka.",
            "Ahtapotların 3 kalbi var ve bu çok ilginç.",
        ),
        kaynak="Britannica",
    )
    assert any(i.kod == "R2" for i in rapor.ihlaller)


def test_k3_resmi_dil_uyarisi():
    rapor = kurallar.denetle(
        ornek_metin() + " Bu bağlamda hususunda mütalaa edilmiştir.", kaynak="Britannica"
    )
    assert any(i.kod == "R3" for i in rapor.ihlaller)


def test_k8_kelime_siniri_altinda_kritik():
    kisa = (
        f"{kurallar.BASLIK_SORU}\nSoru var mı?\n\n"
        f"{kurallar.BASLIK_CEVAP}\nÇok kısa bir cevap burada.\n\n"
        f"{kurallar.BASLIK_SONUC}\nSon."
    )
    rapor = kurallar.denetle(kisa, kaynak="Britannica")
    assert any(i.kod == "R8" and i.agirlik == 3 for i in rapor.ihlaller)


def test_k8_300_kelime_uzerinde_uyari():
    rapor = kurallar.denetle(ornek_metin(cevap_ek=" Kelime " * 120), kaynak="Britannica")
    assert any(i.kod == "R8" for i in rapor.ihlaller)


def test_k9_gunluk_hayat_ornegi_yoksa_uyari():
    metin = ornek_metin().replace("Bir düşün:", "Ayrıca:").replace("kahveni", "suyu")
    for iz in kurallar.GUNLUK_IZLER:
        metin = metin.replace(iz, "zzz").replace(iz.capitalize(), "Zzz")
    rapor = kurallar.denetle(metin, kaynak="Britannica")
    assert any(i.kod == "R9" for i in rapor.ihlaller)


def test_k10_uzun_cumle_uyarisi():
    uzun = " ".join(["bu"] * 40) + " cümle."
    # Metni R8 ihlali olmayacak uzunlukta tut (yalnız R10 test ediliyor)
    metin = ornek_metin(cevap_ek=" ").replace("Bir düşün:", uzun + " Bir düşün:")
    metin = metin.replace(
        "Kollarında sinir hücresi kümeleri vardır; yani kolları neredeyse kendi başına karar verebilir. ", ""
    )
    metin = metin.replace("Laboratuvarda kavanoz kapağını açmayı öğrenen bireyler kaydedilmiştir. ", "")
    rapor = kurallar.denetle(metin, kaynak="Britannica")
    assert any(i.kod == "R10" for i in rapor.ihlaller)


def test_k12_ingilizce_kelime_kritik():
    rapor = kurallar.denetle(
        ornek_metin(cevap_ek=" This is the answer about the animal."), kaynak="Britannica"
    )
    assert any(i.kod == "R12" and i.agirlik == 3 for i in rapor.ihlaller)


def test_k11_emoji_cok_fazlaysa_uyari():
    rapor = kurallar.denetle(ornek_metin(cevap_ek=" 🐙" * 20), kaynak="Britannica")
    assert any(i.kod == "R11" for i in rapor.ihlaller)


def test_k6_onceki_videoyla_tekrar_kritik():
    ayni = ornek_metin()
    rapor = kurallar.denetle(ayni, kaynak="Britannica", onceki_metinler=[ayni])
    assert any(i.kod == "R6" and i.agirlik == 3 for i in rapor.ihlaller)


def test_k7_ayni_kategori_ust_uste_uyari():
    rapor = kurallar.denetle(
        ornek_metin(),
        kaynak="Britannica",
        kategori="hayvanlar",
        son_kategoriler=["hayvanlar"],
    )
    assert any(i.kod == "R7" for i in rapor.ihlaller)


# ---------------------------------------------------------------------------
# 4) Doğruluk — "uydurma bilgi yok"
# ---------------------------------------------------------------------------


def test_kaynak_bos_ise_reddedilir():
    sonuc = dogruluk.dogrula(ornek_metin(), kaynak="")
    assert sonuc.gecti is False and "kaynak" in sonuc.ret_sebebi


def test_belirsiz_kaynak_reddedilir():
    sonuc = dogruluk.dogrula(ornek_metin(), kaynak="internette okudum")
    assert sonuc.gecti is False


def test_tehlikeli_saglik_iddiasi_reddedilir():
    sonuc = dogruluk.dogrula(
        ornek_metin() + " Bu bitki kanseri yener ve tedavi eder.",
        kaynak="Britannica",
    )
    assert sonuc.gecti is False and "tehlikeli iddia" in sonuc.ret_sebebi


def test_tehlikeli_finans_iddiasi_reddedilir():
    sonuc = dogruluk.dogrula(ornek_metin() + " Bu yöntem garanti kazanç sağlar.", kaynak="Britannica")
    assert sonuc.gecti is False


@pytest.mark.parametrize(
    "metin,kalip",
    [
        ("Beynimizin sadece %10'unu kullanıyoruz, gerisi boş.", "beyin_yuzde10"),
        ("Dilin farklı bölgeleri farklı tatları alır.", "dil_bolgeleri"),
        ("Sakız yutarsan 7 yıl sindirilmez.", "sakiz_7_yil"),
    ],
)
def test_curutulmus_bilgi_gercek_gibi_sunulamaz(metin, kalip):
    assert dogruluk.curutulmus_bilgi_mi(metin) == kalip
    sonuc = dogruluk.dogrula(metin * 3, kaynak="Britannica")
    assert sonuc.gecti is False and "çürütülmüş" in sonuc.ret_sebebi


def test_curuten_icerik_serbest():
    """T1 taktiği: yaygın yanlış inanışı ÇÜRÜTEN içerik yapılabilir."""
    metin = ornek_metin(
        cevap_ek=" Herkes beyninin %10'unu kullandığını sanır, oysa görüntüleme "
        "çalışmaları beynin tamamının aktif olduğunu gösteriyor."
    )
    sonuc = dogruluk.dogrula(metin, kaynak="Scientific American", curutme_icerigi=True)
    assert sonuc.gecti is True


def test_asiri_kesinlik_ifadesi_sinirli():
    metin = ornek_metin(cevap_ek=" Bu asla değişmez, her zaman böyledir, kesinlikle kanıtlanmıştır.")
    sonuc = dogruluk.dogrula(metin, kaynak="Britannica")
    assert sonuc.gecti is False and "abartılı" in sonuc.ret_sebebi


def test_arena_dogruluk_talimati_kurallari_icerir():
    talimat = dogruluk.arena_dogruluk_talimati()
    assert "kaynağı adlandırılabilir" in talimat
    assert "tedavi eder" in talimat
    assert "Sağlık, para ve güvenlik" in talimat


# ---------------------------------------------------------------------------
# 5) Etkileşim taktikleri — rotasyon ve YASAKLAR
# ---------------------------------------------------------------------------


def test_rotasyon_on_videoda_dagilir():
    """Rotasyon tablosu 10 videoda 5 taktiği dengeli dağıtır."""
    # `onceki_taktikler=[]` şart: canlı üretim state'i (bobi_tv/state/etkilesim_gecmisi.json)
    # repoda duruyor ve "art arda gelme" koruması rotasyonu eziyordu → test makine
    # durumuna bağlı kalıp canlı koşudan sonra kırılıyordu.
    kodlar = [
        etkilesim.taktik_sec(i, "hayvanlar", 0, onceki_taktikler=[]).kod
        for i in range(21, 31)
    ]
    beklenen = {etkilesim.ROTASYON_10[i % 10] for i in range(21, 31)}
    assert set(kodlar) == beklenen
    assert len(set(kodlar)) == 5


def test_rotasyon_uzun_vadede_kilitlenmez():
    """State'li canlı akışta her taktik düzenli gelir (T1'e kilitlenme hatası)."""
    import tempfile
    from pathlib import Path

    yol = Path(tempfile.mkdtemp()) / "e.json"
    kodlar = []
    for i in range(1, 41):
        secim = etkilesim.taktik_sec(i, "hayvanlar", 100, yol)
        kodlar.append(secim.kod)
        etkilesim.kaydet(i, secim.kod, "hayvanlar", "", yol)
    sayac = {k: kodlar.count(k) for k in set(kodlar)}
    for taktik in ("T1", "T2", "T4", "T5", "T6"):
        assert sayac.get(taktik, 0) >= 6, sayac
    assert "T3" in kodlar  # 20'de bir sürçme
    assert kodlar.count("T3") == 2


def test_ayni_taktik_art_arda_gelmez():
    secim = etkilesim.taktik_sec(2, "hayvanlar", 0, onceki_taktikler=["T5", "T1"])
    assert secim.kod not in ("T5", "T1")


@pytest.mark.parametrize("kategori", ["saglik_sorunu", "beslenme", "para", "guvenlik", "insan_vucudu"])
def test_hassas_kategoride_surcme_ve_ters_psikoloji_yasak(kategori):
    for video_no in range(1, 60):
        secim = etkilesim.taktik_sec(video_no, kategori, yayin_sayisi=100)
        assert secim.kod not in ("T3", "T4"), f"video {video_no}: {secim.kod}"


def test_t3_yetkinlik_kanitlanmadan_yasak():
    secim = etkilesim.taktik_sec(20, "hayvanlar", yayin_sayisi=5)
    assert secim.kod != "T3"
    assert any("yetkinlik" in u for u in secim.uyarilar)


def test_t3_yetkinlik_varsa_20de_bir_uygulanir():
    secim = etkilesim.taktik_sec(20, "hayvanlar", yayin_sayisi=50, onceki_taktikler=["T1", "T2"])
    assert secim.kod == "T3"
    assert "T3 AKTİF" in " ".join(secim.uyarilar)


def test_t3_surcme_duzeltilmeden_birakilamaz():
    gecti, sebep = etkilesim.t3_duzeltme_dogrula("1800'lerde olmuştu. Neyse devam edelim.", duzeltme_sn=1.5)
    assert gecti is False and "düzeltme izi yok" in sebep

    gecti, _ = etkilesim.t3_duzeltme_dogrula(
        "1800'lerde... pardon, 1700'lerin sonunda olmuştu.", duzeltme_sn=2.0
    )
    assert gecti is True


def test_t3_gec_duzeltme_reddedilir():
    gecti, sebep = etkilesim.t3_duzeltme_dogrula("pardon, doğrusu şu", duzeltme_sn=9.0)
    assert gecti is False and "çok geç" in sebep


def test_taktik_her_zaman_talimat_tasir():
    for kod in etkilesim.TAKTIKLER:
        assert etkilesim.TALIMATLAR[kod]


# ---------------------------------------------------------------------------
# 6) Üretici — Arena yok → banka, paket sözleşmesi
# ---------------------------------------------------------------------------


def test_arena_yoksa_banka_kullanilir_ve_uretim_durmaz(tmp_path):
    sonuc = uretici.uret(1, arena_fn=lambda p: None, state_yolu=tmp_path / "s.json")
    assert sonuc["kaynak_turu"] == "yedek"
    assert sonuc["rapor"].yayinlanabilir
    assert sonuc["paket"]["senaryo"]["icerik_kaynagi"] == "yedek"


def test_arena_bos_ve_banka_bitince_uretim_durur(tmp_path, monkeypatch):
    """Uydurmak yerine durmak doğru davranış."""
    monkeypatch.setattr(yedek_bilgiler, "bilgi_sec", lambda kategori, kullanilan=None: None)
    with pytest.raises(RuntimeError, match="uydurma bilgi"):
        uretici.uret(1, arena_fn=lambda p: None, state_yolu=tmp_path / "s.json")


def test_paket_video_hatti_sozlesmesine_uyar(tmp_path):
    sonuc = uretici.uret(2, arena_fn=lambda p: None, state_yolu=tmp_path / "s.json")
    paket = sonuc["paket"]
    senaryo = paket["senaryo"]

    # Zorunlu alanlar
    for alan in ("video_no", "dosya_adi", "baslik", "senaryo", "hash"):
        assert alan in paket
    for alan in ("diyaloglar", "karakterler", "toplam_sure", "semaversiyonu"):
        assert alan in senaryo

    # TTS/video hattının beklediği diyalog alanları
    for d in senaryo["diyaloglar"]:
        for alan in ("karakter", "metin", "cinsiyet", "ses", "duraklamams", "rol"):
            assert alan in d

    # Tek anlatıcı (VS düellosu bitti)
    assert {d["karakter"] for d in senaryo["diyaloglar"]} == {"BOBİ"}
    assert len(senaryo["karakterler"]) == 1


def test_paket_200_300_kelime_ve_180_sn_altinda(tmp_path):
    sonuc = uretici.uret(3, arena_fn=lambda p: None, state_yolu=tmp_path / "s.json")
    senaryo = sonuc["paket"]["senaryo"]
    assert 200 <= senaryo["kelime_sayisi"] <= 300
    # 180 sn YouTube tavanı
    assert senaryo["toplam_sure"] < 180


def test_paket_dogru_bilgi_tasir_yorum_cevabi_icin(tmp_path):
    """Yorum cevaplama hattı 'dogru_bilgi' alanını bekler."""
    sonuc = uretici.uret(4, arena_fn=lambda p: None, state_yolu=tmp_path / "s.json")
    senaryo = sonuc["paket"]["senaryo"]
    assert senaryo["dogru_bilgi"].strip()
    assert senaryo["soru"].strip()
    assert senaryo["kaynak"].strip()
    assert senaryo["taktik"] in etkilesim.TAKTIKLER


def test_paket_baslik_eski_sablonu_tasimaz(tmp_path):
    sonuc = uretici.uret(5, arena_fn=lambda p: None, state_yolu=tmp_path / "s.json")
    baslik = sonuc["paket"]["baslik"].lower()
    assert "#shorts" in baslik
    assert "şoke etti" not in baslik
    assert "vs" not in baslik.split()


def test_diyalog_metni_bolum_basligini_seslendirmez(tmp_path):
    """🧠/🔍/💡 başlıkları EKRANDA görünür, sesli OKUNMAZ."""
    sonuc = uretici.uret(6, arena_fn=lambda p: None, state_yolu=tmp_path / "s.json")
    for d in sonuc["paket"]["senaryo"]["diyaloglar"]:
        assert not d["metin"].startswith(kurallar.BASLIK_SORU)
        assert not d["metin"].startswith(kurallar.BASLIK_CEVAP)
        assert not d["metin"].startswith(kurallar.BASLIK_SONUC)
        assert d["ekran_basligi"] in kurallar.ZORUNLU_BASLIKLAR


def test_arena_json_cevabi_isleme(tmp_path):
    import json as _json

    kart = {
        "soru": "Denizanaları neden yanmaz?",
        "cevap": ornek_metin().split(kurallar.BASLIK_CEVAP)[1].split(kurallar.BASLIK_SONUC)[0].strip(),
        "sonuc": "Denizanası aslında bir hayvan kolonisi. 🌊",
        "baslik": "Denizanası Sırrı 🐚",
        "kaynak": "Britannica — jellyfish",
        "sayilar": ["3"],
        "dogru_bilgi": "Denizanaları kolonilerden oluşur.",
        "kapak_baslik": "BALIK DEĞİL, KOLONİ",
    }
    sonuc = uretici.uret(
        7,
        arena_fn=lambda p: _json.dumps(kart, ensure_ascii=False),
        state_yolu=tmp_path / "s.json",
        zorla_kategori="doga_evren",
    )
    assert sonuc["kaynak_turu"] == "arena"
    assert sonuc["kategori"] == "doga_evren"
    assert "Denizanası" in sonuc["paket"]["baslik"]


def test_kategori_gecmisi_tekrari_engeller(tmp_path):
    yol = tmp_path / "s.json"
    kategoriler_gorulen = []
    # Bankada 3 doğrulanmış bilgi var; 3 üretimden sonra bilinçli olarak durur
    # (uydurmak yerine durmak doğru davranış).
    from modules.ilginc_bilgi import kategoriler

    for no in range(1, 4):
        sonuc = uretici.uret(
            no, arena_fn=lambda p: None, state_yolu=yol, zorla_kategori=kategoriler.ANAHTARLAR[no % 8]
        )
        kategoriler_gorulen.append(sonuc["kategori"])
    # Banka tükendiğinde üretim DURUR (uydurma yok) — ayrı testte doğrulanır.
    for i in range(len(kategoriler_gorulen)):
        assert kategoriler_gorulen[i] not in kategoriler_gorulen[i - 8 : i] if i else True


def test_yedek_banka_bilgileri_kaliteli():
    for b in yedek_bilgiler.YEDEK_BILGILER:
        metin = yedek_bilgiler.tam_metin(b)
        rapor = kurallar.denetle(metin, kaynak=b["kaynak"], kategori=b["kategori"], sayilar=b["sayilar"])
        assert rapor.yayinlanabilir, f"{b['anahtar']}: {rapor.ozet()}"
        assert 200 <= kurallar.kelime_say(kurallar.bolumleri_ayir(metin)[kurallar.BASLIK_CEVAP]) <= 300


def test_canli_hat_anahtari_eski_formata_doner(monkeypatch):
    """ILGINC_BILGI_AKTIF=0 → eski hat (geri dönüş sigortası)."""
    import modules.arena_uretici as au

    monkeypatch.setenv("ILGINC_BILGI_AKTIF", "0")
    assert au.ilginc_bilgi_aktif() is False
    monkeypatch.setenv("ILGINC_BILGI_AKTIF", "1")
    assert au.ilginc_bilgi_aktif() is True


def test_kapak_basligi_kelime_ortasinda_kesmez():
    kisa = uretici.kapak_basligi("Ahtapotların Üç Kalbi Var — Biri Yüzerken Duruyor!", 34)
    assert len(kisa) <= 34
    assert kisa.endswith("…")
    # Son kelime yarım kalmamalı: kesilen kısımda 'Bir' gibi kırıntı olmasın
    kesilen = kisa[:-1].split()
    assert not kesilen or kesilen[-1] != "Bir"


# ---------------------------------------------------------------------------
# 8) Yedek banka 8 kategoriyi de kapsar (Arena çökse bile kanal durmaz)
# ---------------------------------------------------------------------------


def test_yedek_banka_sekiz_kategorinin_hepsini_kapsar():
    banka_kategorileri = {b["kategori"] for b in yedek_bilgiler.YEDEK_BILGILER}
    assert banka_kategorileri == set(kategoriler.ANAHTARLAR), (
        f"eksik kategoriler: {set(kategoriler.ANAHTARLAR) - banka_kategorileri}"
    )


def test_yedek_banka_her_kategoride_secim_yapar():
    for kategori in kategoriler.ANAHTARLAR:
        bilgi = yedek_bilgiler.bilgi_sec(kategori, [])
        assert bilgi is not None and bilgi["kategori"] == kategori


def test_yedek_banka_kullanilanlari_tekrar_vermez():
    ilk = yedek_bilgiler.bilgi_sec("hayvanlar", [])
    ikinci = yedek_bilgiler.bilgi_sec("hayvanlar", [ilk["anahtar"]])
    assert ikinci is not None and ikinci["anahtar"] != ilk["anahtar"]
    hepsi = [b["anahtar"] for b in yedek_bilgiler.YEDEK_BILGILER]
    # Havuz boşalınca üretim DURMAZ (tam otonomi): en eski kayıt yeniden gelir
    dongu = yedek_bilgiler.bilgi_sec("hayvanlar", hepsi)
    assert dongu is not None and dongu["anahtar"] in hepsi
    assert dongu["anahtar"] == hepsi[0]  # en uzun süre önce kullanılan


def test_arena_coktugunde_sekiz_video_uretilir(tmp_path):
    """Arena hiç yokken banka 8 ayrı kategoride video üretmeye yetmeli."""
    yol = tmp_path / "s.json"
    uretilen = []
    for no in range(1, 9):
        sonuc = uretici.uret(
            no, arena_fn=lambda p: None, state_yolu=yol,
            zorla_kategori=kategoriler.ANAHTARLAR[no - 1],
        )
        assert sonuc["rapor"].yayinlanabilir, sonuc["rapor"].ozet()
        assert 200 <= sonuc["paket"]["senaryo"]["kelime_sayisi"] <= 300
        uretilen.append(sonuc["kategori"])
    assert sorted(uretilen) == sorted(kategoriler.ANAHTARLAR)


# ---------------------------------------------------------------------------
# 9) Canlı koşu bulguları (run 43111414945)
# ---------------------------------------------------------------------------


def test_arena_sablon_yankisi_reddedilir():
    """Arena, prompt'un JSON şablonunu cevap diye yankılıyordu → içerik boştu."""
    yanki = '..", "kaynak": "...", "sayilar": ["..."], "dogru_bilgi": "...", "kapak_baslik": "..."'
    assert uretici.sablon_yankisi_mi(yanki) is True
    assert uretici._json_ayikla(yanki) is None
    assert uretici._duz_metinden_kart(yanki) is None

    gercek = '{"soru":"Ahtapotların kaç kalbi var?","cevap":"Çoğumuz tek kalp sanırız, oysa üç kalbi var."}'
    assert uretici.sablon_yankisi_mi(gercek) is False


def test_arena_promptu_sablonu_sonda_tekrarlamaz():
    """Şablon prompt'un sonunda olursa model onu yankılıyor."""
    taktik = etkilesim.taktik_sec(3, "hayvanlar", 0)
    prompt = uretici.arena_promptu("hayvanlar", taktik, [])
    assert prompt.rstrip().endswith("sadece metin yaz.")
    assert "yankılama" in prompt


def test_yeni_hat_render_zincirini_tetikler(monkeypatch, tmp_path):
    """Yeni hat yalnız senaryo üretiyordu; ses/render/kapak çağrılmalı."""
    import modules.arena_uretici as au
    import modules.tts_engine as tts
    import modules.video_render as vr
    from modules.ilginc_bilgi import uretici as uretici_mod

    cagrilar = {}

    def sahte_seslendir(paket):
        cagrilar["tts"] = True
        paket["ses_dosyalari"] = []
        return paket

    def sahte_render(paket):
        cagrilar["render"] = True
        yol = tmp_path / "v.mp4"
        yol.write_bytes(b"x" * 30000)
        return str(yol)

    monkeypatch.setattr(tts, "senaryo_seslendir", sahte_seslendir)
    monkeypatch.setattr(vr, "video_render", sahte_render)
    monkeypatch.setattr(vr, "video_kalite_kontrol", lambda p: {"sure": 95.0})
    monkeypatch.setattr(
        uretici_mod, "uret",
        lambda no: {
            "paket": {"senaryo": {"kelime_sayisi": 220}, "dosya_adi": "t"},
            "rapor": type("R", (), {"skor": 100})(),
            "kategori": "hayvanlar", "taktik": "T1", "kaynak_turu": "arena", "uyarilar": [],
        },
    )
    import modules.kapak_uret as ku

    monkeypatch.setattr(ku, "kapak_uret", lambda p: cagrilar.setdefault("kapak", True))

    paket = au.arena_tam_uretim(1)
    assert cagrilar.get("tts") and cagrilar.get("render")
    assert paket["final_video"].endswith("v.mp4")


def test_yanki_ardindaki_gercek_cevap_kullanilir():
    """CANLI KANIT (43138461248): Arena 3193 karakter döndü — başta bizim JSON
    şablonumuzun yankısı, gerçek cevap HEMEN ARDINDAN. Yankıyı görüp tümden
    reddetmek içeriği çöpe atıyordu."""
    taktik = etkilesim.taktik_sec(1, "insan_vucudu", 0, onceki_taktikler=[])
    prompt = uretici.arena_promptu("insan_vucudu", taktik, [])
    yanki = (
        'dur): {"soru":"...","cevap":"...","sonuc":"...","baslik":"...","kaynak":"...",'
        '"sayilar":["..."],"dogru_bilgi":"...","kapak_baslik":"..."}\n\n' + prompt[120:1400] + "\n\n"
    )
    gercek = (
        '{"soru":"Beynimiz uyurken çöplerini nasıl atıyor?",'
        '"cevap":"Uykuyu sadece dinlenme sanırız, oysa beyin gece boyunca temizlik yapıyor.",'
        '"sonuc":"İyi uyku beynin çöp kamyonu.","baslik":"Uykuda beyin temizliği",'
        '"kaynak":"Nature","sayilar":["1"],"dogru_bilgi":"Uyku beyni temizler.",'
        '"kapak_baslik":"BEYİN ÇÖP TOPLAR"}'
    )
    kart = uretici.arena_bilgi_uret(
        "insan_vucudu", taktik, [], arena_fn=lambda _p: yanki + gercek
    )
    assert kart is not None
    assert kart["soru"].startswith("Beynimiz uyurken")
    assert "BOBİ TV" not in kart["cevap"]
    assert kart["kapak_baslik"] == "BEYİN ÇÖP TOPLAR"


def test_arena_cevabindan_prompt_yankisi_kesilir():
    """arena_api._cevabi_ayikla, cevabın başındaki prompt yankısını atmalı."""
    from modules.arena_api import _cevabi_ayikla

    prompt = "SADECE şu JSON ile cevap ver (şablonu tekrar yazma, doldur): {...}\n\nKATEGORİ: Tarih"
    ilk = prompt.splitlines()[0][:55]
    body = (
        "Arena sohbeti\n" + prompt + "\n\nEski mesaj yankısı: " + ilk + "\n\n"
        "Gercek cevap burada.\nWas this task successful?\n"
    )
    cevap = _cevabi_ayikla(body, prompt, ilk)
    assert "SADECE şu JSON" not in cevap
    assert "Gercek cevap" in cevap


def test_prompt_yankisi_cevap_sayilmaz():
    """CANLI KANIT (43139582417): 3166 karakterlik 'cevap' bizim prompt'umuzdu.

    Arena prompt'u yankılıyor, gerçek cevap hiç gelmiyor; eski kod bunu
    'cevap oturdu' diye kabul edip çöp içerik üretiyordu.
    """
    from modules import arena_api
    from modules.ilginc_bilgi import etkilesim as etk

    taktik = etk.taktik_sec(2, "gunluk_yasam", 0, onceki_taktikler=[])
    prompt = uretici.arena_promptu("gunluk_yasam", taktik, [])
    body = "Arena sohbeti\n" + prompt + "\nWas this task successful?\n"
    cevap = arena_api._cevabi_ayikla(body, prompt, prompt.splitlines()[0][:55])
    cevap = arena_api._prompt_kuyrugunu_at(cevap, prompt)
    assert "YAZIM KURALLARI" not in cevap
    assert cevap.strip() == ""  # gerçek cevap yok → boş
    kart = uretici.arena_bilgi_uret(
        "gunluk_yasam", taktik, [], arena_fn=lambda _p: prompt
    )
    assert kart is None  # banka devreye girer, çöp içerik üretilmez


def test_sorusuz_metin_kart_olmaz():
    """'?' olmayan metin R1'i kırar; uydurma soru yazmak yerine reddedilir."""
    import modules.ilginc_bilgi.uretici as u

    metin = (
        "Fermuar 1851'de icat edildi ama yıllarca kimse kullanmadı. "
        "İlk sürümler pahalıydı ve sıkışıyordu. Bugün her kıyafette var."
    )
    assert u._duz_metinden_kart(metin) is None


def test_arena_onay_modalini_kapatir():
    """ARENA_CONSENT_BUTTON_LABELS sabiti hiç kullanılmıyordu → modal açıkken
    cevap hiç gelmiyordu (koşu 43140690378: 4,5 dk bekleme, dönen metin modal)."""
    import inspect

    from modules import arena_api

    kaynak = inspect.getsource(arena_api._arena_riza_modalini_kapat)
    assert "ARENA_CONSENT_BUTTON_LABELS" in kaynak
    assert "Agree" in arena_api.ARENA_CONSENT_BUTTON_LABELS
    # _arena_sorgusu_yap hem açılışta hem döngüde kapatmayı denemeli
    sorgu = inspect.getsource(arena_api._arena_sorgusu_yap)
    assert sorgu.count("_arena_riza_modalini_kapat") >= 2


def test_oturum_dolunca_tarayici_acilmaz():
    """Çerez süresi dolduğunda her çağrıda Playwright açılıp boşa beklenmemeli."""
    from modules import arena_api

    arena_api.oturum_bayragini_sifirla()
    try:
        arena_api._oturum_doldu_isaretle()
        assert arena_api.oturum_doldu_mu() is True
        # kapak yolu erken çıkmalı (Playwright hiç çağrılmadan None)
        assert arena_api.arena_kapak_onerisi_kisa({"baslik": "x"}) is None
        # kısa cevap yolu da erken çıkmalı
        assert arena_api.arena_kisa_cevap_al("test") is None
    finally:
        arena_api.oturum_bayragini_sifirla()
    assert arena_api.oturum_doldu_mu() is False


def test_banka_tukenince_uretim_durmaz(tmp_path):
    """CANLI HATA (43148464044): banka tükenince '0 yayınlandı' oldu.

    Tam otonomi kuralı: Arena yok + banka bitti → en eski kayıt yeniden kullanılır,
    üretim ASLA durmaz.
    """
    import modules.ilginc_bilgi.uretici as u

    yol = tmp_path / "s.json"
    uretilen = []
    for no in range(1, 40):
        paket = u.uret(no, state_yolu=yol, arena_fn=lambda _p: None)
        uretilen.append(paket["paket"]["senaryo"]["baslik"])
    assert len(uretilen) == 39
    assert all(uretilen)


def test_banka_16_kayit_ve_her_kategoride_2():
    """Arena çerezi dolu olduğu sürece banka TEK içerik kaynağı: 16 tur dayanmalı."""
    from collections import Counter

    kayitlar = yedek_bilgiler.YEDEK_BILGILER
    assert len(kayitlar) >= 16
    sayim = Counter(b["kategori"] for b in kayitlar)
    for kategori in kategoriler.ANAHTARLAR:
        assert sayim[kategori] >= 2, sayim
    assert len({b["anahtar"] for b in kayitlar}) == len(kayitlar)


def test_banka_kayitlari_kalite_kapisindan_gecer():
    """Her yedek kayıt 200-300 kelime + 12 kural: skor 100 olmalı."""
    for bilgi in yedek_bilgiler.YEDEK_BILGILER:
        assert bilgi["soru"].strip().endswith("?"), bilgi["anahtar"]
        rapor = kurallar.denetle(
            yedek_bilgiler.tam_metin(bilgi),
            kaynak=bilgi["kaynak"],
            sayilar=bilgi["sayilar"],
            kategori=bilgi["kategori"],
        )
        assert rapor.skor == 100, (bilgi["anahtar"], rapor.ozet()[:120])


# ---------------------------------------------------------------------------
# Arena çerezi kendini besleme (kullanıcı isteği: "Yap")
# ---------------------------------------------------------------------------


def _sahte_cerezler():
    import base64
    import json

    govde = base64.b64encode(
        json.dumps(
            {
                "access_token": "a" * 40,
                "refresh_token": "r" * 40,
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": "u1", "email": "x@y.z"},
            }
        ).encode()
    ).decode()
    return [
        {"name": "arena-auth-prod-v1.0", "value": govde},
        {"name": "arena_build_bucket", "value": "stable"},
        {"name": "baska_cerez", "value": "yok"},
    ]


def test_cerez_paketi_uretim_biciminde_ve_dogrulanir():
    """Yazılacak çerez, üretim hattının okuyucusundan geçmeli (round-trip)."""
    from modules import arena_cerez

    metin = arena_cerez.secret_paketi_olustur(_sahte_cerezler())
    assert metin and "arena-auth-prod-v1" in metin
    assert "baska_cerez" not in metin  # alakasız çerezler yazılmaz
    assert arena_cerez.secret_dogrula(metin) is True
    assert arena_cerez.secret_dogrula("bozuk-json") is False


def test_oturum_sagliksizsa_secret_yazilmaz(monkeypatch, tmp_path):
    """Login modalı görüldüyse ölü çerez yazılmaz — çalışan çerez korunur."""
    from modules import arena_cerez

    cagrildi = {"n": 0}

    def sahte_yaz(metin, repo=None):
        cagrildi["n"] += 1
        return True, "yazıldı"

    monkeypatch.setattr(arena_cerez, "secret_yaz", sahte_yaz)
    kayit = arena_cerez.oturumdan_guncelle(
        _sahte_cerezler(), oturum_saglikli=False
    )
    assert cagrildi["n"] == 0
    assert kayit["guncellendi"] is False


def test_secret_yazma_pat_yoksa_sessiz_gecer(monkeypatch):
    """PAT yoksa üretim düşmez; sadece yazma atlanır."""
    from modules import arena_cerez

    monkeypatch.delenv("GH_PAT", raising=False)
    monkeypatch.delenv("GH_SECRET_PAT", raising=False)
    metin = arena_cerez.secret_paketi_olustur(_sahte_cerezler())
    basari, mesaj = arena_cerez.secret_yaz(metin)
    assert basari is False and "korunuyor" in mesaj
