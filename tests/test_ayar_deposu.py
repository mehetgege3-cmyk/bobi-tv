"""TODO 2/6/8 — Ayar deposu testleri: atomiklik, tolerans, geçmiş, bekleyen kuyruk.

Kapsam: bozuk JSON kurtarması (EZME yok), atomik yazma, aralık dışı red,
state>env>varsayılan önceliği, değişiklik geçmişi şeması ve 200 satır rotasyonu,
gerçek git havuzlarıyla push başarısı/başarısızlığı ve bekleyen kuyruğun
yeniden denenmesi, ayarların offset ile AYRI commit edilmesi.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import modules.ayar_deposu as ad  # noqa: E402

REPO_KOK = Path(__file__).resolve().parent.parent
BOT_WORKFLOW = REPO_KOK / ".github" / "workflows" / "telegram_bot.yml"


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def _gecici_git_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Taze git havuzu: ayar dosyası ilk commit'te olsun; push edilebilir
    bare remote sonradan eklenir (gerçek push yolu test edilir)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(["init", "-q"], repo).returncode == 0
    _git(["config", "user.email", "test@test"], repo)
    _git(["config", "user.name", "test"], repo)
    state = repo / "bobi_tv" / "state"
    state.mkdir(parents=True)
    (state / "ayarlar.json").write_text("{}\n", encoding="utf-8")
    assert _git(["add", "-f", "bobi_tv/state/ayarlar.json"], repo).returncode == 0
    assert _git(["commit", "-q", "-m", "init"], repo).returncode == 0
    bare = tmp_path / "remote.git"
    assert _git(["init", "--bare", "-q", str(bare)], tmp_path).returncode == 0
    return repo, bare


# ---------- TODO 2: toleranslı yükleme ----------


def test_yokluk_varsayilanlari_uyarisiz_dondurur(tmp_path: Path) -> None:
    degerler, uyarilar = ad.yukle(tmp_path / "yok.json")
    assert uyarilar == []
    assert degerler["GUNLUK_MAKS"] == "6"
    assert degerler["KOTA_DOLU_DAVRANIS"] == "sessiz_dur"
    assert degerler["MOD"] == "isindirma_saatlik"


def test_bozuk_json_cokmez_vey_ezmez_yedekler(tmp_path: Path) -> None:
    """C4 dersi: bozuk JSON üzerinde `ayarlar={}` EZME YOK — dosya `.bozuk`
    olarak saklanır, varsayılanlara dönülür, panel için uyarı üretilir."""
    yol = tmp_path / "ayarlar.json"
    bozuk_icerik = '{"sur": 1, "guncelleme": "...", "ayarlar": {"GUNLUK_MA'
    yol.write_text(bozuk_icerik, encoding="utf-8")
    degerler, uyarilar = ad.yukle(yol)
    assert degerler["GUNLUK_MAKS"] == "6", "varsayılana dönmeli"
    assert any("bozuk" in u for u in uyarilar)
    yedek = Path(str(yol) + ".bozuk")
    assert yedek.exists(), "bozuk dosya saklanmalı (EZME yok)"
    assert yedek.read_text(encoding="utf-8") == bozuk_icerik, "yedek bit bit aynı olmalı"


def test_kok_dict_degilse_de_tolerans(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    yol.write_text("[1, 2, 3]\n", encoding="utf-8")
    degerler, uyarilar = ad.yukle(yol)
    assert degerler["GUNLUK_MAKS"] == "6"
    assert uyarilar, "kök liste uyarı üretmeli"


def test_sema_surumu_farkliyse_uyar_ve_varsayilan(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    yol.write_text(
        json.dumps({"sur": 99, "guncelleme": "x", "ayarlar": {"GUNLUK_MAKS": "2"}}),
        encoding="utf-8",
    )
    degerler, uyarilar = ad.yukle(yol)
    assert degerler["GUNLUK_MAKS"] == "6", "farklı şema sürümü → varsayılan"
    assert any("şema sürümü" in u for u in uyarilar)


def test_aralik_disi_deger_reddedilir_varsayilan_doner(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    yol.write_text(
        json.dumps({"sur": 1, "guncelleme": "x", "ayarlar": {"GUNLUK_MAKS": "24", "MOD": "yok_boyle"}}),
        encoding="utf-8",
    )
    degerler, uyarilar = ad.yukle(yol)
    assert degerler["GUNLUK_MAKS"] == "6", "24 katalog seçeneği değil → varsayılan 6"
    assert degerler["MOD"] == "isindirma_saatlik"
    assert any("aralık dışı" in u for u in uyarilar)


def test_bilinmeyen_anahtar_yok_sayilir(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    yol.write_text(
        json.dumps({"sur": 1, "guncelleme": "x", "ayarlar": {"SAHTE_ANAHTAR": 1}}),
        encoding="utf-8",
    )
    degerler, uyarilar = ad.yukle(yol)
    assert "SAHTE_ANAHTAR" not in degerler
    assert any("bilinmeyen" in u for u in uyarilar)


def test_state_env_varsayilan_onceligi(tmp_path: Path) -> None:
    """Öncelik: state > env > katalog varsayılanı."""
    yol = tmp_path / "ayarlar.json"
    yol.write_text(
        json.dumps({"sur": 1, "guncelleme": "x", "ayarlar": {"GUNLUK_HEDEF": "2"}}),
        encoding="utf-8",
    )
    env = {"GUNLUK_HEDEF": "4", "GUNLUK_MAKS": "5", "MOD": "normal"}
    degerler, _ = ad.yukle(yol, env=env)
    assert degerler["GUNLUK_HEDEF"] == "2", "state env'i yener"
    assert degerler["GUNLUK_MAKS"] == "5", "env state'te yoksa devreye girer"
    assert degerler["MOD"] == "normal"


def test_temizlik_ayarlari_artik_degistirilebilir(tmp_path: Path) -> None:
    """2026-11-11 kararı: temizlik ayarları KİLİTLİ DEĞİL — kullanıcı istediği
    eşiği girer (1 saatte 100 izlenme kuralı). Sınırlar (min/max) korunur."""
    yol = tmp_path / "ayarlar.json"
    uygulanan, uyarilar = ad.kaydet({"MIN_IZLENME_ESIGI": 50, "GUNLUK_HEDEF": "2"}, yol)
    assert "MIN_IZLENME_ESIGI" in uygulanan
    assert "GUNLUK_HEDEF" in uygulanan
    ham = ad.state_ham_ayarlari(yol)
    assert str(ham["MIN_IZLENME_ESIGI"]) == "50"


def test_temizlik_ayari_sinir_disi_reddedilir(tmp_path: Path) -> None:
    """Serbest giriş = sınırsız değil: 0-100000 dışı reddedilir, varsayılan kalır."""
    yol = tmp_path / "ayarlar.json"
    uygulanan, uyarilar = ad.kaydet({"MIN_IZLENME_ESIGI": 999999}, yol)
    assert "MIN_IZLENME_ESIGI" not in uygulanan
    assert uyarilar, "sınır dışı değer sessizce kabul edilmemeli"


# ---------- TODO 2: atomik yazma ----------


def test_atomik_yazma_yarida_kesilse_eski_dosya_bozulmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yol = tmp_path / "ayarlar.json"
    ad.kaydet({"GUNLUK_HEDEF": "2"}, yol)
    guvenli = yol.read_text(encoding="utf-8")

    def patlayan_replace(a: str, b: str) -> None:
        raise OSError("disk doldu (simülasyon)")

    monkeypatch.setattr("os.replace", patlayan_replace)
    with pytest.raises(OSError):
        ad.kaydet({"GUNLUK_HEDEF": "4"}, yol)
    monkeypatch.undo()

    assert yol.read_text(encoding="utf-8") == guvenli, "yarıda kesilen yazma eski dosyayı bozmamalı"
    assert Path(str(yol) + ".tmp").exists(), "yarım kalan tmp izi görülebilir"
    degerler, _ = ad.yukle(yol)
    assert degerler["GUNLUK_HEDEF"] == "2"


def test_kaydet_atomik_sonuc_gecerli_json(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    uygulanan, uyarilar = ad.kaydet({"KOTA_REZERV": 750}, yol)
    assert uygulanan == {"KOTA_REZERV": "750"}
    assert uyarilar == []
    veri = json.loads(yol.read_text(encoding="utf-8"))
    assert veri["sur"] == ad.SEMA_SURUMU
    assert "guncelleme" in veri and "ayarlar" in veri
    assert veri["ayarlar"]["KOTA_REZERV"] == "750"


def test_kaydet_sayi_aralik_disini_duser(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    uygulanan, uyarilar = ad.kaydet({"KOTA_REZERV": 9999}, yol)
    assert "KOTA_REZERV" not in uygulanan
    assert any("aralık dışı" in u for u in uyarilar)


# ---------- TODO 6: değişiklik geçmişi ----------


def test_degisiklik_gecmise_yazilir_sema_tam(tmp_path: Path) -> None:
    yol = tmp_path / "ayar_gecmisi.jsonl"
    ad.gecmise_ekle(42, "GUNLUK_MAKS", "24", "6", "telegram", yol)
    ad.gecmise_ekle(42, "MOD", "normal", "isindirma_saatlik", "telegram", yol)
    kayitlar = ad.gecmisi_oku(10, yol)
    assert len(kayitlar) == 2
    son = kayitlar[-1]
    for alan in ("zaman", "kullanici_id", "anahtar", "eski", "yeni", "kaynak"):
        assert alan in son, f"geçmiş satırında {alan} eksik"
    assert son["anahtar"] == "MOD" and son["eski"] == "normal"
    assert son["kullanici_id"] == 42


def test_degistirilebilir_gecmise_yazilir_secret_yazilmaz(tmp_path: Path) -> None:
    """2026-11-11: MIN_IZLENME_ESIGI değiştirilebilir oldu → geçmişe YAZILIR.
    Secret (YOUTUBE_TOKEN) hiçbir koşulda geçmişe yazılmaz."""
    yol = tmp_path / "ayar_gecmisi.jsonl"
    ad.gecmise_ekle(42, "MIN_IZLENME_ESIGI", "100", "50", "telegram", yol)
    ad.gecmise_ekle(42, "YOUTUBE_TOKEN", None, "sifre", "telegram", yol)
    kayitlar = ad.gecmisi_oku(10, yol)
    assert len(kayitlar) == 1
    assert kayitlar[0]["anahtar"] == "MIN_IZLENME_ESIGI"
    assert "sifre" not in yol.read_text(encoding="utf-8")


def test_gecmis_200_satir_rotasyonu(tmp_path: Path) -> None:
    """Sınır: mevcut dosya son 200 satırda kalır; taşma `.1.jsonl`e döner
    (logrotate semantiği — her rotasyonda yedek yenilenir)."""
    yol = tmp_path / "ayar_gecmisi.jsonl"
    yedek = ad.gecmis_yedek_yolu(yol)
    zamanlar: list[str] = []
    for _i in range(205):
        ad.gecmise_ekle(1, "GUNLUK_HEDEF", "1", "1", "telegram", yol)
        zamanlar.append(ad.gecmisi_oku(1, yol)[0]["zaman"])
    mevcut_satirlar = yol.read_text(encoding="utf-8").splitlines()
    assert len(mevcut_satirlar) == ad.GECMIS_SINIRI == 200
    assert yedek.exists(), "taşan satırlar .1.jsonl'e gitmeli"
    tasinan = yedek.read_text(encoding="utf-8").splitlines()
    assert 1 <= len(tasinan) <= 5, f"taşma satır sayısı: {len(tasinan)}"
    # kronoloji korunur: yedek en eskileri, mevcut en yenileri tutar
    assert json.loads(tasinan[0])["zaman"] <= json.loads(mevcut_satirlar[0])["zaman"]
    # son 200 kayıt KAYIP DEĞİL: en son yazılan kayıt mevcut dosyanın sonunda
    assert json.loads(mevcut_satirlar[-1])["zaman"] == zamanlar[-1]


# ---------- TODO 8: push başarısızlığı yutulmaz + bekleyen kuyruk ----------


def test_push_basarisizligi_yutulmaz_sebep_doner(tmp_path: Path) -> None:
    """Remote yok → push FİİLEN başarısız; fonksiyon False + sebep döndürür,
    `|| echo` gibi sessizce yutmaz."""
    repo, _ = _gecici_git_repo(tmp_path)
    (repo / "bobi_tv" / "state" / "ayarlar.json").write_text(
        json.dumps({"sur": 1, "guncelleme": "x", "ayarlar": {"GUNLUK_HEDEF": "4"}}),
        encoding="utf-8",
    )
    ok, sebep = ad.commit_ve_yukle(["bobi_tv/state/ayarlar.json"], "test", repo_kok=repo)
    assert ok is False
    assert "push" in sebep.lower(), f"sebep push hatasını belli etmeli: {sebep}"


def test_push_basarisizligi_bekleyen_kuyruga_girer_state_bozulmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_yolu = tmp_path / "ayarlar.json"
    bekleyen_yolu = tmp_path / "ayarlar_bekleyen.json"
    uygulanan, _ = ad.kaydet({"GUNLUK_HEDEF": "2"}, state_yolu)
    assert uygulanan == {"GUNLUK_HEDEF": "2"}
    onceki_dosya = state_yolu.read_text(encoding="utf-8")

    def basarisiz_push(dosyalar: list[str], mesaj: str, repo_kok: Path | None = None) -> tuple[bool, str]:
        return False, "git push başarısız: simülasyon"

    monkeypatch.setattr(ad, "commit_ve_yukle", basarisiz_push)
    ok, durum = ad.commit_ve_yukle(["x"], "m")
    assert ok is False and "push" in durum
    ad.bekleyene_yaz({"GUNLUK_HEDEF": "2"}, durum, 7, bekleyen_yolu)
    bekleyen = ad.bekleyenleri_al(bekleyen_yolu)
    assert bekleyen is not None
    assert bekleyen["degisiklikler"] == {"GUNLUK_HEDEF": "2"}
    assert bekleyen["kullanici_id"] == 7
    assert state_yolu.read_text(encoding="utf-8") == onceki_dosya, "yerel state bozulmamalı"


def test_bekleyen_sonraki_kosuda_denir_ve_kuyruk_temizlenir(tmp_path: Path) -> None:
    """Gerçek git havuzu: remote eklenince bekleyen değişiklik FİİLEN push edilir."""
    repo, bare = _gecici_git_repo(tmp_path)
    _git(["remote", "add", "origin", str(bare)], repo)
    bekleyen_yolu = repo / "bobi_tv" / "state" / "ayarlar_bekleyen.json"
    ad.bekleyene_yaz({"GUNLUK_HEDEF": "4"}, "ilk deneme başarısız", 7, bekleyen_yolu)
    bekleyen = ad.bekleyenleri_al(bekleyen_yolu)
    assert bekleyen is not None
    # sonraki koşu: state'i güncelle + push (artık remote var)
    ad.kaydet(bekleyen["degisiklikler"], repo / "bobi_tv" / "state" / "ayarlar.json")
    ok, sebep = ad.commit_ve_yukle(
        ["bobi_tv/state/ayarlar.json", "bobi_tv/state/ayarlar_bekleyen.json"],
        "bekleyen tamamlandı",
        repo_kok=repo,
    )
    assert ok is True, sebep
    ad.bekleyenleri_temizle(bekleyen_yolu)
    assert ad.bekleyenleri_al(bekleyen_yolu) is None
    log = _git(["log", "--oneline"], repo).stdout
    assert "bekleyen tamamlandı" in log, "ikinci koşu gerçek commit yaptı"


def test_push_basarili_ayri_commit_olusur(tmp_path: Path) -> None:
    repo, bare = _gecici_git_repo(tmp_path)
    _git(["remote", "add", "origin", str(bare)], repo)
    (repo / "bobi_tv" / "state" / "ayarlar.json").write_text(
        json.dumps({"sur": 1, "guncelleme": "x", "ayarlar": {"GUNLUK_HEDEF": "4"}}),
        encoding="utf-8",
    )
    ok, sebep = ad.commit_ve_yukle(["bobi_tv/state/ayarlar.json"], "⚙️ ayar testi", repo_kok=repo)
    assert ok is True, sebep
    log = _git(["log", "--oneline"], repo).stdout.splitlines()
    assert log[0].endswith("⚙️ ayar testi")


def test_offset_ve_ayalar_ayri_committeste_karsimaz() -> None:
    """TODO 8: telegram_bot.yml offset commit'i ayar dosyalarını STAGE ETMEZ;
    ayarlar bot tarafından kendi commit'inde (commit_ve_yukle) taşınır.
    (P2 '|| echo' yasağının testi commit 4'teki workflow düzeltmesiyle gelir.)"""
    yazi = BOT_WORKFLOW.read_text(encoding="utf-8")
    state_commit = yazi.split("State dosyasını commit et")[1]
    assert "ayarlar.json" not in state_commit, "offset commit ayarlar.json'ı almamalı"
    assert "ayar_gecmisi" not in state_commit, "offset commit geçmişi de almamalı"


# ---------- TODO 9: env köprüsü ----------


def test_env_satirlari_secretlari_icermez() -> None:
    satirlar = ad.env_satirlari()
    metin = "\n".join(satirlar)
    for yasak in (
        "YOUTUBE_TOKEN=",
        "YOUTUBE_CLIENT_SECRET=",
        "ARENA_COOKIES_JSON=",
        "PEXELS_API_KEY=",
        "GH_TOKEN=",
        "TELEGRAM_BOT_TOKEN=",
    ):
        assert yasak not in metin, f"köprü secret yazdı: {yasak}"
    assert "GUNLUK_MAKS=6" in satirlar
    assert "KOTA_DOLU_DAVRANIS=sessiz_dur" in satirlar
    assert "MOD=isindirma_saatlik" in satirlar


def test_env_satirlari_state_degerini_tasir(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    ad.kaydet({"GUNLUK_HEDEF": "4", "KOTA_DOLU_DAVRANIS": "hata"}, yol)
    satirlar = ad.env_satirlari(degerler=ad.yukle(yol)[0])
    assert "GUNLUK_HEDEF=4" in satirlar
    assert "KOTA_DOLU_DAVRANIS=hata" in satirlar
    assert "GUNLUK_MAKS=6" in satirlar, "state'te olmayan ayar varsayılanla geçer"


def test_env_satirlari_temizlik_ayarlarini_gecirir() -> None:
    """2026-11-11: temizlik ayarları etkili ve değiştirilebilir → env'e geçer.
    Kullanıcı 1 saatte 100 izlenme kuralını panelden ayarlayabilsin.
    Secret'lar köprüden ASLA geçmez."""
    metin = "\n".join(ad.env_satirlari())
    for anahtar in ("OTOMATIK_SIL_AKTIF=", "MIN_IZLENME_ESIGI=", "IZLENME_KONTROL_DK="):
        assert anahtar in metin
    assert "YOUTUBE_TOKEN=" not in metin


def test_force_sifirla_tek_kullanim_tuketir(tmp_path: Path) -> None:
    yol = tmp_path / "ayarlar.json"
    assert ad.force_sifirla(yol) is False, "0 iken tüketim yok"
    ad.kaydet({"force": "1"}, yol)
    assert ad.force_sifirla(yol) is True
    degerler, _ = ad.yukle(yol)
    assert degerler["force"] == "0"


def test_bekleyenleri_al_bozuk_dosyada_none_doner(tmp_path: Path) -> None:
    yol = tmp_path / "bekleyen.json"
    yol.write_text("{bozuk", encoding="utf-8")
    assert ad.bekleyenleri_al(yol) is None


def test_ayarlar_json_baslangic_dosyasi_gecerli() -> None:
    """Repoya eklenen ilk state dosyası şemaya uygun olmalı (sur=1)."""
    yol = REPO_KOK / "bobi_tv" / "state" / "ayarlar.json"
    veri = json.loads(yol.read_text(encoding="utf-8"))
    assert veri["sur"] == 1
    assert isinstance(veri["ayarlar"], dict)
    degerler, uyarilar = ad.yukle(yol)
    assert degerler["GUNLUK_MAKS"] == "6"
    assert uyarilar == []
