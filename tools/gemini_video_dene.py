"""Gemini web çerezi VİDEO üretebiliyor mu? — ölçüm probu.

NİÇİN: Kullanıcı (2026-11-13) "motoru çöpe at, promptu Gemini'ye at video üretsin"
dedi. Mevcut `modules/gemini_web.py` yalnız `gorsel_uret()` (görsel) ve
`metin_uret()` (metin) biliyor. Video üretimi var mı YOK MU, tahminle değil
ölçümle belirlenmeli.

NASIL: Aynı StreamGenerate RPC'sine video istemi gönderilir; dönen ham yanıt
olduğu gibi diske yazılır. Sonra yanıttaki TÜM URL'ler ve MIME ipuçları
ayıklanır. Böylece "Gemini video döndürdü mü" sorusu kanıtla cevaplanır.

ÇIKTI: docs/GEMINI_VIDEO_DENEY.md — ham yanıt boyu, URL listesi, hüküm.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules import gemini_web  # noqa: E402

#: Video istemi. Türkçe; Gemini web arayüzünde video üretimi isteği.
ISTEM = (
    "Bana 8 saniyelik dikey (9:16) bir video üret. "
    "İçerik: gece gökyüzünde yıldızlar yavaşça kayıyor, altın renkli bir teleskop "
    "silüeti, sinematik ışık. Ses olmasın. Videoyu dosya olarak ver."
)

#: Video servislerinin bilinen URL kalıpları.
VIDEO_IZLERI = (
    "contribution.usercontent.google.com",
    "video",
    "mp4",
    "webm",
    ".m3u8",
)

#: MIME tipi izleri (JSON içinde geçerse video dönmüş demektir).
MIME_IZLERI = (
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "veo",
    "Veo",
)


def _url_ayikla(yanit: str) -> list[str]:
    ham = re.findall(r"https?://[^\s\"'\\<>\]]{20,400}", yanit)
    gorulen, cikti = set(), []
    for u in ham:
        u = u.rstrip(".,);")
        if u in gorulen:
            continue
        gorulen.add(u)
        cikti.append(u)
    return cikti


def main() -> int:
    durum = gemini_web.durum()
    print(f"[prob] durum: {durum}", flush=True)

    rapor = {
        "cerez_var": durum.get("cerez_var"),
        "istem": ISTEM,
        "metin_yaniti": None,
        "ham_uzunluk": 0,
        "url_sayisi": 0,
        "url_video_izi": [],
        "url_diger": [],
        "mime_izi": [],
        "gorsel_denemesi": None,
        "hukum": "",
    }

    # --- 1) METİN kanalından dene: video ürettiğini iddia ediyor mu? --------
    metin = gemini_web.metin_uret(ISTEM, sure=240)
    if metin:
        rapor["metin_yaniti"] = metin[:3000]
        rapor["ham_uzunluk"] = len(metin)
        urls = _url_ayikla(metin)
        rapor["url_sayisi"] = len(urls)
        for u in urls:
            if any(i in u.lower() for i in VIDEO_IZLERI):
                rapor["url_video_izi"].append(u)
            else:
                rapor["url_diger"].append(u)
        rapor["mime_izi"] = [m for m in MIME_IZLERI if m in metin]
        print(f"[prob] metin yanıtı: {len(metin)} karakter, {len(urls)} URL", flush=True)
    else:
        rapor["metin_yaniti"] = f"HATA: {gemini_web.durum().get('hata')}"
        print("[prob] metin kanalı boş döndü", flush=True)

    # --- 2) GÖRSEL kanalını video istemiyle dene --------------------------
    #     Bazı sürümlerde görsel ucu video da döndürebiliyor (çıktı uzantısı
    #     .jpg/.png dışındaysa video demektir).
    cikis = Path("out/gemini_video_prob")
    cikis.mkdir(parents=True, exist_ok=True)
    gorsel = gemini_web.gorsel_uret(ISTEM, str(cikis / "deneme.png"), sure=240)
    rapor["gorsel_denemesi"] = gorsel or f"HATA: {gemini_web.durum().get('hata')}"
    print(f"[prob] görsel kanalı: {rapor['gorsel_denemesi']}", flush=True)

    # --- 3) Hüküm ---------------------------------------------------------
    if rapor["url_video_izi"] or rapor["mime_izi"]:
        rapor["hukum"] = "VIDEO_VAR — Gemini web video döndürdü"
    elif "http" in (rapor["metin_yaniti"] or "") and metin:
        rapor["hukum"] = "BELIRSIZ — bağlantı döndü ama video izi yok (elle bakılmalı)"
    elif metin:
        rapor["hukum"] = "VIDEO_YOK — yalnız metin döndü, video üretmedi"
    else:
        rapor["hukum"] = "ERISIM_YOK — çerez/jeton sorunu, ölçüm yapılamadı"
    print(f"[prob] HÜKÜM: {rapor['hukum']}", flush=True)

    Path("docs").mkdir(exist_ok=True)
    Path("docs/GEMINI_VIDEO_DENEY.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = ["# Gemini web VİDEO üretebiliyor mu? — ölçüm", ""]
    md.append(f"**Hüküm:** {rapor['hukum']}")
    md.append(f"**Çerez:** {rapor['cerez_var']} · **Yanıt boyu:** {rapor['ham_uzunluk']} karakter")
    md.append("")
    md.append("## İstem")
    md.append("```")
    md.append(ISTEM)
    md.append("```")
    md.append("")
    md.append(f"## Bulunan URL'ler ({rapor['url_sayisi']})")
    if rapor["url_video_izi"]:
        md.append("### Video izi taşıyanlar")
        md += [f"- `{u}`" for u in rapor["url_video_izi"]]
    else:
        md.append("_Video izi taşıyan URL YOK._")
    if rapor["url_diger"]:
        md.append("")
        md.append("### Diğer")
        md += [f"- `{u}`" for u in rapor["url_diger"]]
    md.append("")
    md.append("## MIME izleri")
    md.append(f"`{rapor['mime_izi']}`" if rapor["mime_izi"] else "_YOK_")
    md.append("")
    md.append("## Görsel kanalı denemesi")
    md.append(f"`{rapor['gorsel_denemesi']}`")
    md.append("")
    md.append("## Ham metin yanıtı (ilk 3000 karakter)")
    md.append("```")
    md.append(rapor["metin_yaniti"] or "")
    md.append("```")
    Path("docs/GEMINI_VIDEO_DENEY.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("[prob] docs/GEMINI_VIDEO_DENEY.md yazıldı", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
