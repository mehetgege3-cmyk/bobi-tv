"""NotebookLM'i Playwright ile gerçek tarayıcıda sürmeyi dene.

NİÇİN: `batchexecute` RPC'leri elle çağrıldığında `wrb.fr` yükü `null` dönüyor.
HAR'dan çıkan şey şu: not defteri AÇMA ve NOT EKLEME adımlarının RPC'leri
HAR'da YOK (kayıt 16:32:35'te başladı, defter 16:31:18'de açılmıştı).
Yani o iki adımı bilmiyoruz. Tahminle uç yazmak yerine **gerçek tarayıcı**
kullanıyoruz: çerezleri yükle, kullanıcı gibi tıkla, her adımda ekran görüntüsü al.

Akış (her adımda screenshot):
  0. Çerezleri yükle → notebook.google.com → giriş kontrolü
  1. Yeni not defteri oluştur
  2. Kaynak/not ekle (Gemini metni)
  3. Studio → Video Özeti → Kısa → Oluştur
  4. Üretimi bekle, indirme bağlantısını yakala

ÇIKTI: docs/pw/<adim>.png + docs/pw/rapor.md
Sır yazılmaz: çerez değerleri maskelenir, screenshot'larda oturum bilgisi yok.
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

#: Gemini'den geldiği varsayılan örnek metin. Kullanıcının promptuyla üretilmiş
#: formatta: başlık + soru + cevap + şaşırtıcı gerçek.
ORNEK_METIN = """**Kategori:** İnsan Vücudu 🧬

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

BASLIK = "Parmaklarımız Neden Buruşur?"


def _cerezler() -> list[dict]:
    """NOTEBOOK_GOOGLE → Playwright cookie listesi."""
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
    """Google çerezlerini hem .google.com hem notebook.google.com için yaz."""
    out = []
    for c in ham:
        ad, deger = str(c["name"]), str(c.get("value", ""))
        for alan in (".google.com", "notebook.google.com"):
            out.append({
                "name": ad, "value": deger, "domain": alan,
                "path": "/", "secure": True, "httpOnly": False,
                "sameSite": "None",
            })
    return out


def main() -> int:
    from playwright.sync_api import sync_playwright

    rapor: list[str] = []
    d = rapor.append
    d("# NotebookLM Playwright Denemesi")
    d("")

    cerez_ham = _cerezler()
    d(f"- Çerez sayısı: **{len(cerez_ham)}**")
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
        # otomasyon izini azalt
        baglam.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        baglam.add_cookies(_pw_cerezleri(cerez_ham))
        sayfa = baglam.new_page()

        def ss(ad: str) -> None:
            try:
                sayfa.screenshot(path=str(CIKTI / f"{ad}.png"), full_page=False)
                d(f"- 📷 `{ad}.png`")
            except Exception as e:
                d(f"- ⚠️ screenshot `{ad}` alınamadı: {e}")

        # ---------- 0. GİRİŞ ----------
        d("## 0. Giriş")
        d("")
        try:
            sayfa.goto(TABAN + "/", wait_until="domcontentloaded", timeout=60000)
            sayfa.wait_for_timeout(4000)
            url = sayfa.url
            baslik = sayfa.title()
            d(f"- Adres: `{url[:90]}`")
            d(f"- Sayfa başlığı: `{baslik[:80]}`")
            ss("00_giris")
            giris_yok = ("accounts.google.com" in url
                         or "Sign in" in baslik or "Oturum" in baslik)
            d(f"- Giriş durumu: **{'❌ GİRİŞ YOK' if giris_yok else '✅ GİRİŞ VAR'}**")
            if giris_yok:
                d("")
                d("**DURDURULDU:** çerezler tarayıcıda oturum açmadı.")
                (CIKTI / "rapor.md").write_text("\n".join(rapor) + "\n",
                                                encoding="utf-8")
                print("\n".join(rapor))
                tarayici.close()
                return 1
        except Exception as e:
            d(f"- ❌ Açılamadı: {e}")
            (CIKTI / "rapor.md").write_text("\n".join(rapor) + "\n",
                                            encoding="utf-8")
            print("\n".join(rapor))
            tarayici.close()
            return 1
        d("")

        # ---------- 1. YENİ NOT DEFTERİ ----------
        d("## 1. Yeni not defteri")
        d("")
        try:
            # "Oluştur" / "Yeni not defteri" düğmesini ara
            adaylar = [
                'button:has-text("Oluştur")',
                'button:has-text("Yeni not defteri")',
                'a:has-text("Yeni not defteri")',
                '[aria-label*="Oluştur"]',
                'button:has-text("Create")',
                'button:has-text("Create new")',
            ]
            bulundu = None
            for sec in adaylar:
                try:
                    if sayfa.locator(sec).first.is_visible(timeout=1500):
                        bulundu = sec
                        break
                except Exception:
                    continue
            if bulundu:
                d(f"- Düğme bulundu: `{bulundu}`")
                sayfa.locator(bulundu).first.click()
                sayfa.wait_for_timeout(3000)
                ss("01_defter_olustur")
                d(f"- Yeni adres: `{sayfa.url[:90]}`")
                m = re.search(r"/notebook/([0-9a-f-]{36})", sayfa.url)
                if m:
                    d(f"- ✅ **Yeni defter ID: `{m.group(1)}`**")
            else:
                d("- ❌ Oluştur düğmesi bulunamadı. Ekrandaki düğmeler:")
                for t in sayfa.locator("button").all_text_contents()[:25]:
                    if t.strip():
                        d(f"    - `{t.strip()[:50]}`")
        except Exception as e:
            d(f"- ⚠️ Hata: {e}")
            ss("01_hata")
        d("")

        # ---------- 2. İÇERİK EKLE ----------
        d("## 2. İçerik ekleme alanı")
        d("")
        try:
            alanlar = [
                'textarea', '[contenteditable="true"]',
                'input[type="text"]',
            ]
            for sel in alanlar:
                n = sayfa.locator(sel).count()
                if n:
                    d(f"- `{sel}` → {n} adet")
            ss("02_icerik_alani")

            # "Kopyala yapıştır" / "Metin" seçeneği
            for metin in ["Kopyalanan metin", "Metin", "Paste text",
                          "Copy text", "Not ekle"]:
                loc = sayfa.locator(f':text("{metin}")').first
                try:
                    if loc.is_visible(timeout=1200):
                        d(f"- Seçenek göründü: `{metin}`")
                        break
                except Exception:
                    continue
        except Exception as e:
            d(f"- ⚠️ Hata: {e}")
        d("")

        # ---------- 3. STUDIO / VİDEO ----------
        d("## 3. Studio paneli")
        d("")
        try:
            # Studio düğmesi
            for sel in ['button:has-text("Studio")',
                        ':text("Studio")']:
                try:
                    if sayfa.locator(sel).first.is_visible(timeout=1500):
                        sayfa.locator(sel).first.click()
                        sayfa.wait_for_timeout(2500)
                        d(f"- Studio açıldı: `{sel}`")
                        break
                except Exception:
                    continue
            ss("03_studio")
            # Video Özeti var mı
            for kw in ["Video Özeti", "Video Overview", "Video",
                       "Sesli Özet", "Audio Overview"]:
                sayfa_metni = sayfa.inner_text("body")[:20000]
                d(f"- Metinde `{kw}`: {'✅ var' if kw in sayfa_metni else '— yok'}")
        except Exception as e:
            d(f"- ⚠️ Hata: {e}")
        d("")

        # ---------- ÖZET ----------
        d("## Ekrandaki tüm düğmeler")
        d("")
        try:
            for i, t in enumerate(sayfa.locator("button").all_text_contents()):
                t = " ".join(t.split())
                if t:
                    d(f"{i}. `{t[:60]}`")
        except Exception:
            pass

        (CIKTI / "rapor.md").write_text("\n".join(rapor) + "\n", encoding="utf-8")
        print("\n".join(rapor))
        tarayici.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
