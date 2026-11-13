"""MOTOR YAZICI — Gemini'ye video motorunu kendisi yazdırır.

KULLANICI TALEBİ (2026-11-13):
  "Mevcut motorları gemini kendisi yazsın. İçerikleri detaylıca vermeden yüzeysel
   ne istediğini söyle, o gerekli py dosyalarını kodlasın. Böylece daha farklı
   içerik üretir. Çok detay verme, sadece short videosu ve konular. Diğer basit
   şeyler."

TASARIM KARARI — az detay:
  Brief KISA. Format/sınıf/fonksiyon dayatmıyoruz. Tek zorunluluk: arayüz.
  Gemini kendi yapısını kursun ki içerik de farklı olsun.

NASIL ÇALIŞIR:
  1. Brief yazılır (docs/motor_istemi/BRIEF.md — kısa).
  2. Gemini web'e 2 istek: (a) plan, (b) dosya dosya kod.
     ⚠️ Uzun yanıt tek istekte kesilir; bu yüzden PLAN sonra KOD.
  3. Dönen yanıttan ```python blokları ayıklanır → modules/yeni_motor/.
  4. Sözdizimi + import testi koşar. Geçmezse Gemini'ye hata geri gönderilir
     (1 onarım turu).
  5. Rapor docs/MOTOR_URETIMI.md'ye yazılır.

ÇIKTI: modules/yeni_motor/*.py + docs/MOTOR_URETIMI.md
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules import gemini_web  # noqa: E402

HEDEF = Path("modules/yeni_motor")
RAPOR_JSON = Path("docs/MOTOR_URETIMI.json")
RAPOR_MD = Path("docs/MOTOR_URETIMI.md")

# ---------------------------------------------------------------------------
# BRIEF — bilerek KISA. Gemini'nin kendi yapısını kurmasını istiyoruz.
# ---------------------------------------------------------------------------
BRIEF = """\
Sen BOBİ TV adlı Türkçe YouTube Shorts kanalının yazılım motorunu yazacaksın.

İSTENEN: Konu al, video üret, YouTube'a yükle. Hepsi bu.

KURALLAR:
- Video dikey 1080x1920, sesli, 15-60 saniye.
- Konular: ilginç bilgiler, şaşırtıcı gerçekler, günlük hayat detayları.
  Türkçe, sade, "sen" dili.
- Video üretimi için: Gemini görsel üretimi + ffmpeg + edge-tts kullan.
  (Gemini video üretmiyor, görsel üretiyor.)
- YouTube yükleme: mevcut `modules/youtube_upload.py` içindeki
  `video_yukle(paket)` fonksiyonunu kullan. Paket sözleşmesi:
  {"final_video": "<mp4 yolu>", "baslik": "...", "aciklama": "...", "etiketler": [...]}
- Arayüz: `modules/yeni_motor/motor.py` içinde `video_uret(video_no: int) -> dict`
  fonksiyonu olacak. main_pipeline bu fonksiyonu çağıracak.

ORTAM (bunlar tasarım değil, gerçekler — uymak zorunlu):
- Gemini API ANAHTARI YOK, `google-genai` kullanılamaz. Görsel üretimi için
  `from modules.gemini_web import gorsel_uret` kullan (çerez tabanlı, çalışıyor).
  İmza: `gorsel_uret(prompt: str, hedef_yol: str) -> str | None`
- `video_yukle(paket)` şu alanları ZORUNLU ister:
  {"dosya_adi": "<uzantısız ad>", "baslik": "...", "aciklama": "...",
   "final_video": "<mp4 yolu>", "etiketler": [...]}
- ffmpeg ve edge-tts workflow'da kurulu. PIL kurulu.

Yapı, sınıf, dosya sayısı, algoritma — SENİN kararın. Yaratıcı ol.
Kısa ve çalışan kod yaz. Uzun soyutlama katmanları kurma.
"""

PLAN_ISTEM = BRIEF + """

Şimdi PLAN yaz. Sadece plan — kod yazma.
- Kaç dosya olacak, adları ne?
- Her dosya ne yapacak (1-2 cümle)?
- Video tam olarak nasıl oluşacak (adım adım, kısa)?
- Hangi kütüphaneler?

Kısa tut. En fazla 40 satır.
"""

KOD_ISTEM = BRIEF + """

Şimdi KODU yaz. Plan:

{plan}

ÇIKTI KURALI (ÇOK ÖNEMLİ):
- Her dosyayı ayrı bir ```python bloğunda ver.
- Her bloktan ÖNCE şu satır olsun: `# DOSYA: modules/yeni_motor/<ad>.py`
- Blok dışında kod yazma. Açıklama en fazla 1 satır.
- `motor.py` MUTLAKA olsun ve içinde `video_uret(video_no: int) -> dict` bulunsun.
- stdlib + ffmpeg + edge_tts + requests dışında bağımlılık kullanma.
- `main_pipeline.py`'ı değiştirme; sadece motoru yaz.

Hemen kodu ver, önsöz yazma.
"""


def _python_bloklari(yanit: str) -> dict[str, str]:
    """```python bloklarını dosya adlarıyla ayıklar."""
    dosyalar: dict[str, str] = {}
    # Blok öncesi "# DOSYA: path" işaretini yakala
    desen = re.compile(
        r"#\s*DOSYA:\s*(\S+)\s*[\r\n]+```(?:python|py)?\s*\n(.*?)```",
        re.DOTALL,
    )
    for m in desen.finditer(yanit):
        ad = m.group(1).strip().strip("`")
        kod = m.group(2)
        dosyalar[ad] = kod

    # İşaret yoksa: blokları sırayla "dosya_1.py" diye kaydet (fallback)
    if not dosyalar:
        for i, m in enumerate(
            re.finditer(r"```(?:python|py)?\s*\n(.*?)```", yanit, re.DOTALL), 1
        ):
            dosyalar[f"modules/yeni_motor/uretilen_{i}.py"] = m.group(1)
    return dosyalar


def _temizle(kod: str) -> str:
    """Yanıttan gelen kod kirliliğini sil (markdown, kaçış)."""
    kod = kod.replace("\\n", "\n") if "\\n" in kod and "\n" not in kod else kod
    kod = re.sub(r"^\s*```\w*\s*", "", kod)
    kod = re.sub(r"\s*```\s*$", "", kod)
    return kod.strip() + "\n"


def _sozdizimi(kod: str) -> str | None:
    try:
        ast.parse(kod)
        return None
    except SyntaxError as e:
        return f"satır {e.lineno}: {e.msg}"


def _yaz(dosyalar: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    """Dosyaları yazar. (yazılanlar, hatalar) döner."""
    HEDEF.mkdir(parents=True, exist_ok=True)
    yazilan, hatalar = [], {}
    for ad, kod in dosyalar.items():
        kod = _temizle(kod)
        hata = _sozdizimi(kod)
        if hata:
            hatalar[ad] = f"SÖZDİZİMİ — {hata}"
            continue
        hedef = Path(ad if ad.startswith("modules/") else f"modules/yeni_motor/{Path(ad).name}")
        if ".." in str(hedef) or hedef.is_absolute():
            hatalar[ad] = "GEÇERSİZ YOL"
            continue
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(kod, encoding="utf-8")
        yazilan.append(str(hedef))
    return yazilan, hatalar


def _arayuz_var_mi() -> str | None:
    """motor.py'de video_uret var mı?"""
    motor = HEDEF / "motor.py"
    if not motor.exists():
        return "motor.py YOK"
    try:
        agac = ast.parse(motor.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return f"motor.py sözdizimi: {e.msg}"
    adlar = {n.name for n in ast.walk(agac) if isinstance(n, ast.FunctionDef)}
    if "video_uret" not in adlar:
        return f"motor.py'de video_uret yok (var: {sorted(adlar)[:8]})"
    return None


def _dogrula() -> dict:
    """tools/motor_dogrula.py'yi koşar, JSON raporunu okur."""
    import subprocess

    try:
        subprocess.run(
            [sys.executable, "tools/motor_dogrula.py"],
            capture_output=True, text=True, timeout=900,
        )
    except Exception as e:
        return {"gecti": False, "hata": f"doğrulama koşulamadı: {type(e).__name__}: {e}"}
    try:
        return json.loads(Path("docs/MOTOR_DOGRULAMA.json").read_text(encoding="utf-8"))
    except Exception as e:
        return {"gecti": False, "hata": f"doğrulama raporu okunamadı: {e}"}


def _dosyalari_oku() -> dict[str, str]:
    if not HEDEF.exists():
        return {}
    return {
        str(f.relative_to(Path.cwd())): f.read_text(encoding="utf-8")
        for f in HEDEF.rglob("*.py")
    }


def main() -> int:
    rapor: dict = {"plan": None, "dosyalar": [], "hatalar": {}, "arayuz": None, "turlar": []}

    print("[motor] 1/2 plan isteniyor...", flush=True)
    plan = gemini_web.metin_uret(PLAN_ISTEM, sure=240)
    if not plan:
        print(f"[motor] ❌ plan alınamadı: {gemini_web.durum().get('hata')}", flush=True)
        return 1
    rapor["plan"] = plan
    print(f"[motor] plan: {len(plan)} karakter", flush=True)

    print("[motor] 2/2 kod isteniyor...", flush=True)
    # NOT: .format() KULLANMA — BRIEF içinde {"final_video": ...} var ve süslü
    # parantez format alanı sanılıp KeyError veriyordu (koşu 43417743423).
    yanit = gemini_web.metin_uret(KOD_ISTEM.replace("{plan}", plan), sure=300)
    if not yanit:
        print(f"[motor] ❌ kod alınamadı: {gemini_web.durum().get('hata')}", flush=True)
        return 1
    print(f"[motor] kod yanıtı: {len(yanit)} karakter", flush=True)

    dosyalar = _python_bloklari(yanit)
    print(f"[motor] ayıklanan dosya: {len(dosyalar)} → {list(dosyalar)}", flush=True)
    yazilan, hatalar = _yaz(dosyalar)
    rapor["dosyalar"] = yazilan
    rapor["hatalar"] = hatalar
    rapor["turlar"].append({"tur": 1, "yanit_boyu": len(yanit), "yazilan": len(yazilan)})

    # --- onarım turu: sözdizimi/arayüz hatası varsa Gemini'ye geri gönder ---
    arayuz = _arayuz_var_mi()
    if hatalar or arayuz:
        print(f"[motor] onarım turu — hatalar: {hatalar or arayuz}", flush=True)
        onarim = (
            BRIEF
            + f"\n\nÖnceki denemen şu hatalarla geldi:\n{json.dumps(hatalar or {'arayuz': arayuz}, ensure_ascii=False, indent=1)}\n"
            + "Yalnız HATALI dosyaları yeniden yaz, tam ve çalışır kod ver."
            + "\nHer bloktan önce `# DOSYA: modules/yeni_motor/<ad>.py` satırı olsun."
        )
        yanit2 = gemini_web.metin_uret(onarim, sure=300)
        if yanit2:
            d2 = _python_bloklari(yanit2)
            y2, h2 = _yaz(d2)
            rapor["dosyalar"] = sorted(set(yazilan) | set(y2))
            rapor["hatalar"] = h2
            rapor["turlar"].append({"tur": 2, "yanit_boyu": len(yanit2), "yazilan": len(y2)})
            arayuz = _arayuz_var_mi()

    rapor["arayuz"] = arayuz or "TAMAM — video_uret mevcut"
    print(f"[motor] arayüz: {rapor['arayuz']}", flush=True)

    # --- GERÇEK ÇALIŞTIRMA: sözdizimi geçen kod çalışan kod değildir -------
    dogrulama = _dogrula()
    rapor["dogrulama"] = dogrulama
    print(f"[motor] doğrulama: {dogrulama.get('gecti')} {dogrulama.get('hata') or ''}", flush=True)

    # Başarısızsa Gemini'ye HATAYI göster, kendisi düzeltsin (en fazla 2 tur)
    tur = 0
    while not dogrulama.get("gecti") and tur < 2:
        tur += 1
        print(f"[motor] onarım turu {tur} — Gemini'ye hata gösteriliyor", flush=True)
        mevcut = _dosyalari_oku()
        istek = (
            BRIEF
            + f"\n\nMOTORUN ÇALIŞTIRILDI ve ŞU HATAYI VERDİ:\n\n"
            + f"{dogrulama.get('hata')}\n\n```\n{(dogrulama.get('traceback') or '')[-1200:]}\n```\n\n"
            + "Mevcut dosyalar:\n"
            + "\n".join(f"### {ad}\n```python\n{kod}\n```" for ad, kod in mevcut.items())
            + "\n\nHatayı düzelt. TÜM dosyaları eksiksiz yeniden yaz. "
            + "Her bloktan önce `# DOSYA: modules/yeni_motor/<ad>.py` satırı olsun."
        )
        d = gemini_web.metin_uret(istek, sure=300)
        if not d:
            print("[motor] onarım yanıtı alınamadı", flush=True)
            break
        y, _h = _yaz(_python_bloklari(d))
        rapor["turlar"].append({"tur": f"onarim-{tur}", "yanit_boyu": len(d), "yazilan": len(y)})
        dogrulama = _dogrula()
        rapor["dogrulama"] = dogrulama
        print(f"[motor] onarım {tur} sonucu: {dogrulama.get('gecti')} "
              f"{dogrulama.get('hata') or ''}", flush=True)

    # --- rapor ---
    RAPOR_JSON.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# GEMİNİ'NİN YAZDIĞI MOTOR", "", f"**Arayüz:** {rapor['arayuz']}", ""]
    dg = rapor.get("dogrulama") or {}
    md.append(f"**Uçtan uca doğrulama:** {'✅ GEÇTİ' if dg.get('gecti') else '❌ BAŞARISIZ'}")
    if dg.get("olcum"):
        md.append(f"`{dg['olcum']}`")
    if dg.get("hata"):
        md.append(f"\n**Hata:** `{dg['hata']}`")
    md.append("")
    md.append("## Üretilen dosyalar")
    md += [f"- `{d}`" for d in rapor["dosyalar"]] or ["_YOK_"]
    if rapor["hatalar"]:
        md.append("")
        md.append("## Hatalar")
        md += [f"- `{k}`: {v}" for k, v in rapor["hatalar"].items()]
    md.append("")
    md.append("## Gemini'nin planı")
    md.append("```")
    md.append(rapor["plan"] or "")
    md.append("```")
    RAPOR_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("[motor] docs/MOTOR_URETIMI.md yazıldı", flush=True)
    gecti = bool((rapor.get("dogrulama") or {}).get("gecti"))
    return 0 if gecti else 1


if __name__ == "__main__":
    raise SystemExit(main())
