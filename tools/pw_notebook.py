"""NotebookLM tam akış — Playwright ile gerçek kullanıcı gibi.

NİÇİN: `batchexecute` elle çağrıldığında `wrb.fr` yükü `null` dönüyor.
Defter açma ve not ekleme RPC'leri HAR'da yok. Bu yüzden gerçek tarayıcı:
çerezleri yükle, kullanıcı gibi tıkla, her adımda ekran görüntüsü al.

Doğrulanmış çalışma koşulu (2026-11-15):
  HAR'daki TAM çerez seti (20 çerez, SID+HSID+APISID dahil) gerekiyor.
  Eksik sette Google `CookieMismatch` verip anonim `/trynow` sayfasına atıyor.
  Ayrıca `__Secure-` çerezlerinde `httpOnly: True` şart.

AKIŞ:
  0. Giriş kontrolü  → "Yeni not defteri" görünmeli
  1. Yeni not defteri oluştur
  2. Metni "not" olarak ekle (kaynak değil — kullanıcı akışı böyle)
  3. Studio → Video Özeti → Kısa → Oluştur
  4. Üretimi bekle, indirme bağlantısını yakala

ÇIKTI: docs/pw/<adim>.png + docs/pw/rapor.md
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

CIKTI = Path("docs/pw")
CIKTI.mkdir(parents=True, exist_ok=True)
TABAN = "https://notebook.google.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)

BASLIK = "Parmaklarımız Neden Buruşur?"
METIN = """**Kategori:** İnsan Vücudu 🧬

**Sudan Çıkmış Balığa Dönen Parmaklarımızın Sırrı!** 🛁

Uzun süre banyoda, havuzda veya denizde kaldığınızda parmak uçlarınızın neden
buruş buruş olduğunu hiç düşündünüz mü? Cevabın, suyun derimize nüfuz edip onu
sünger gibi şişirmesi olduğunu sanıyorsanız, sıkı durun; tamamen yanılıyorsunuz!

Yıllarca bilim insanları bile bu durumun basit bir suyu emme (osmoz) olayı
olduğunu düşündü. Ancak bilimsel gerçek, vücudumuzun adeta yüksek teknolojili
bir sensör gibi çalışan muazzam tasarımında gizli!

Bu buruşma işlemi, tamamen sinir sistemimizin kontrolünde gerçekleşen otomatik
bir reflekstir. Suyun içinde uzun süre kaldığınızda, otonom sinir sisteminiz
parmak uçlarınızdaki kılcal damarlara "hemen daralın!" komutunu verir. Damarlar
hızla daraldığında derinin alt kısmındaki hacim azalır, üstteki deri ise adeta
sönmüş bir balon gibi içeri doğru çökerek o meşhur buruşuk şekli alır.

İşin en kesin kanıtı şudur: Sinirleri zedelenmiş veya kopmuş bir parmağı ne
kadar suda bekletirseniz bekletin, o parmak asla buruşmaz!

Peki vücudumuz neden durup dururken parmaklarımızı ıslak birer kuru üzüme
çevirmek istesin? Evrimsel biyologlara göre bu durum, atalarımızdan bize miras
kalan kusursuz bir hayatta kalma mekanizmasıdır. Buruşuk parmaklarımız, tıpkı
Formula 1 araçlarındaki yağmur lastikleri gibi çalışır. Kırışıklıklar suyu
aralardan dışarı atarak ıslak nesneleri kavrama gücümüzü artırır.

💡 **Şaşırtıcı Gerçek:** Derimiz kendini o kadar hızlı yeniler ki, ortalama bir
insan hayatı boyunca yaklaşık 35 kilogram ağırlığında ölü deri hücresi döker!"""


def _cerezler() -> list[dict]:
    ham = (os.environ.get("NOTEBOOK_GOOGLE") or "").strip()
    if not ham:
        raise SystemExit("HATA: NOTEBOOK_GOOGLE boş.")
    if ham.startswith("[") or ham.startswith("{"):
        veri = json.loads(ham)
        if isinstance(veri, dict) and "cookies" in veri:
            veri = veri["cookies"]
        if isinstance(veri, list):
            return [c for c in veri if isinstance(c, dict) and c.get("name")]
        return [{"name": k, "value": v} for k, v in veri.items()]
    out = []
    for parca in ham.split(";"):
        if "=" in parca:
            k, v = parca.strip().split("=", 1)
            out.append({"name": k, "value": v})
    return out


def _pw_cerezleri(ham: list[dict]) -> list[dict]:
    """Google `CookieMismatch` hatasını önleyen dönüşüm.

    Kural: `__Secure-` önekli çerezler `httpOnly: True` + `secure: True`
    olmadan yazılırsa Google oturumu tanımıyor. Ayrıca çerez TEK domain'e
    yazılır — aynı çerezi iki domain'e koymak da tutarsızlık sayılıyor.
    """
    out = []
    for c in ham:
        ad = str(c["name"])
        deger = str(c.get("value", ""))
        if not deger:
            continue
        domain = c.get("domain") or ".google.com"
        if not domain.startswith("."):
            domain = "." + domain.lstrip(".")
        kayit = {
            "name": ad, "value": deger, "domain": domain,
            "path": c.get("path") or "/", "secure": True,
            "httpOnly": True, "sameSite": "None",
        }
        if isinstance(c.get("expires"), (int, float)) and c["expires"] > 0:
            kayit["expires"] = c["expires"]
        out.append(kayit)
    return out


def main() -> int:
    from playwright.sync_api import sync_playwright

    rapor: list[str] = []
    d = rapor.append
    d("# NotebookLM Tam Akış — Playwright")
    d("")

    cerez = _cerezler()
    adlar = {c["name"] for c in cerez}
    imza = ["SID", "HSID", "SSID", "APISID", "SAPISID"]
    eksik = [a for a in imza if a not in adlar]
    d(f"- Çerez: **{len(cerez)}**")
    d(f"- İmza çerezleri: {'✅ tam' if not eksik else '❌ EKSİK ' + str(eksik)}")
    d("")

    with sync_playwright() as p:
        tarayici = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        baglam = tarayici.new_context(
            user_agent=UA, viewport={"width": 1440, "height": 900},
            locale="tr-TR", timezone_id="Europe/Istanbul",
        )
        baglam.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        baglam.add_cookies(_pw_cerezleri(cerez))
        sayfa = baglam.new_page()
        sayfa.set_default_timeout(20000)

        def ss(ad: str) -> None:
            try:
                sayfa.screenshot(path=str(CIKTI / f"{ad}.png"))
                d(f"- 📷 `{ad}.png`")
            except Exception as e:
                d(f"- ⚠️ `{ad}` alınamadı: {e}")

        def metin() -> str:
            try:
                return " ".join(sayfa.inner_text("body").split())
            except Exception:
                return ""

        # ================= 0. GİRİŞ =================
        d("## 0. Giriş")
        d("")
        sayfa.goto(TABAN + "/", wait_until="domcontentloaded", timeout=60000)
        sayfa.wait_for_timeout(6000)
        girdi = "Yeni not defteri" in metin() or "Not defterlerim" in metin()
        d(f"- Adres: `{sayfa.url[:80]}`")
        d(f"- Giriş: **{'✅ VAR' if girdi else '❌ YOK'}**")
        ss("00_giris")
        if not girdi:
            d("")
            d("**DURDURULDU:** oturum açılmadı. Çerez seti eksik veya süresi geçmiş.")
            (CIKTI / "rapor.md").write_text("\n".join(rapor) + "\n", encoding="utf-8")
            print("\n".join(rapor))
            tarayici.close()
            return 1
        d("")

        # ================= 1. YENİ NOT DEFTERİ =================
        d("## 1. Yeni not defteri")
        d("")
        yeni_id = None
        try:
            dugme = sayfa.get_by_role("button", name=re.compile("Yeni not defteri", re.I))
            dugme.first.click()
            sayfa.wait_for_timeout(4000)
            ss("01a_defter_olustur")
            d(f"- Tıkladıktan sonra adres: `{sayfa.url[:80]}`")
            m = re.search(r"/notebook/([0-9a-f-]{36})", sayfa.url)
            if m:
                yeni_id = m.group(1)
                d(f"- ✅ **Defter ID: `{yeni_id}`**")
            else:
                d("- Defter sayfasına geçilmedi, ekrandaki metin:")
                d(f"  `{metin()[:300]}`")
        except Exception as e:
            d(f"- ❌ {type(e).__name__}: {e}")
            ss("01_hata")
        d("")

        # ================= 2. İÇERİK EKLE =================
        d("## 2. İçerik ekle")
        d("")
        if yeni_id:
            try:
                s = metin()
                d(f"- Sayfadaki metin (ilk 300): `{s[:300]}`")
                ss("02a_defter_bos")

                # "Kaynak ekle" / "Not ekle" düğmesi
                ekle = None
                for ad in ["Kaynak ekle", "Not ekle", "Kaynak veya not ekle",
                           "Metin ekle", "Ekle"]:
                    try:
                        loc = sayfa.get_by_role("button", name=re.compile(ad, re.I))
                        if loc.first.is_visible(timeout=1500):
                            ekle = ad
                            break
                    except Exception:
                        continue
                d(f"- Ekle düğmesi: `{ekle or 'BULUNAMADI'}`")
                if ekle:
                    sayfa.get_by_role("button", name=re.compile(ekle, re.I)).first.click()
                    sayfa.wait_for_timeout(2500)
                    ss("02b_ekle_menusu")
                    d(f"- Menü sonrası metin: `{metin()[:250]}`")

                    # "Kopyalanan metin" seçeneği
                    for sec in ["Kopyalanan metin", "Metin", "Panodan"]:
                        try:
                            loc = sayfa.get_by_text(re.compile(sec, re.I))
                            if loc.first.is_visible(timeout=1500):
                                loc.first.click()
                                sayfa.wait_for_timeout(2000)
                                d(f"- Seçildi: `{sec}`")
                                break
                        except Exception:
                            continue
                    ss("02c_metin_secildi")

                    # Metni yaz
                    for sel in ['textarea', '[contenteditable="true"]']:
                        try:
                            alan = sayfa.locator(sel).first
                            if alan.is_visible(timeout=2000):
                                alan.fill(METIN)
                                d(f"- Metin yazıldı (`{sel}`, {len(METIN)} krkt)")
                                ss("02d_metin_yazildi")
                                break
                        except Exception:
                            continue

                    # Gönder / Kaydet
                    for ad in ["Ekle", "Kaydet", "Gönder", "Tamam", "Oluştur"]:
                        try:
                            b = sayfa.get_by_role("button", name=re.compile(f"^{ad}$", re.I))
                            if b.first.is_visible(timeout=1200):
                                b.first.click()
                                d(f"- Gönderildi: `{ad}`")
                                sayfa.wait_for_timeout(6000)
                                break
                        except Exception:
                            continue
                    ss("02e_eklendi")
            except Exception as e:
                d(f"- ⚠️ {type(e).__name__}: {e}")
                ss("02_hata")
        else:
            d("- Atlanıyor: defter açılmadı.")
        d("")

        # ================= 3. STUDIO / VİDEO =================
        d("## 3. Studio → Video Özeti")
        d("")
        if yeni_id:
            try:
                s = metin()
                for kw in ["Video Özeti", "Video", "Sesli Özet", "Studio"]:
                    d(f"- Metinde `{kw}`: {'✅' if kw in s else '—'}")
                ss("03a_studio")

                # Studio panelini aç
                for ad in ["Studio", "Studio paneli"]:
                    try:
                        b = sayfa.get_by_role("button", name=re.compile(ad, re.I))
                        if b.first.is_visible(timeout=1500):
                            b.first.click()
                            sayfa.wait_for_timeout(2500)
                            d(f"- Studio açıldı: `{ad}`")
                            break
                    except Exception:
                        continue
                ss("03b_studio_acik")

                # Video Özeti kartını bul
                for sec in ["Video Özeti", "Video", "Videolu Özet"]:
                    try:
                        loc = sayfa.get_by_text(re.compile(sec, re.I))
                        if loc.first.is_visible(timeout=1500):
                            loc.first.click()
                            sayfa.wait_for_timeout(2500)
                            d(f"- Video kartı: `{sec}`")
                            break
                    except Exception:
                        continue
                ss("03c_video_karti")

                # Kısa seçeneği
                for sec in ["Kısa", "Kısa video"]:
                    try:
                        loc = sayfa.get_by_text(re.compile(f"^{sec}$", re.I))
                        if loc.first.is_visible(timeout=1500):
                            loc.first.click()
                            d(f"- Format: `{sec}`")
                            break
                    except Exception:
                        continue
                ss("03d_kisa_secildi")

                # Oluştur
                for ad in ["Oluştur", "Hemen oluştur", "Üret"]:
                    try:
                        b = sayfa.get_by_role("button", name=re.compile(ad, re.I))
                        if b.first.is_visible(timeout=1500):
                            b.first.click()
                            d(f"- ✅ **Oluştur tıklandı: `{ad}`**")
                            break
                    except Exception:
                        continue
                ss("03e_olusturuldu")

                # Üretimi bekle
                d("")
                d("### Üretim bekleniyor")
                d("")
                for tur in range(20):
                    sayfa.wait_for_timeout(30000)
                    s = metin()
                    hazir = any(k in s for k in ["indir", "İndir", "hazır"])
                    d(f"- {tur + 1}. tur ({(tur + 1) * 30} sn): "
                      f"{'✅ hazır' if hazir else '⏳ üretiliyor'}")
                    if tur == 0 or hazir:
                        ss(f"04_bekleme_{tur + 1}")
                    if hazir:
                        break
            except Exception as e:
                d(f"- ⚠️ {type(e).__name__}: {e}")
                ss("03_hata")
        d("")

        # ================= ÖZET =================
        d("## Sayfadaki düğmeler")
        d("")
        try:
            gorulen = set()
            for t in sayfa.locator("button").all_text_contents():
                t = " ".join(t.split())
                if t and t not in gorulen:
                    gorulen.add(t)
                    d(f"- `{t[:60]}`")
        except Exception:
            pass

        (CIKTI / "rapor.md").write_text("\n".join(rapor) + "\n", encoding="utf-8")
        print("\n".join(rapor))
        tarayici.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
