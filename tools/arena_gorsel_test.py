"""Arena AI GERÇEKTEN görsel üretiyor mu? — kanıt toplayıcı (2026-11-12).

Kullanıcı haklı olarak "ürettiği görseli göster, ortada yalan var" dedi.
Bu script iddiayı ÖLÇER: Arena'ya gerçek kapak promptunu gönderir, sayfada kaç
<img>/<canvas> olduğunu, kaynakların data:/blob:/http dağılımını ve indirilen
görsellerin boyutunu yazar. Görsel gelmezse "GÖRSEL GELMEDİ" der — uydurmaz.

Kullanım: ARENA_COOKIES_JSON=... python tools/arena_gorsel_test.py
Çıktı: kanit/arena_test_*.png + kanit/arena_test_rapor.json
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from modules import arena_api, kapak_gorsel

CIKIS = Path(os.environ.get("KANIT_DIZINI", "kanit"))

SAYFA_DURUMU = """() => {
    const img = [...document.querySelectorAll('img')].map(i => i.currentSrc || i.src || '');
    return {
        img_sayisi: img.length,
        canvas: document.querySelectorAll('canvas').length,
        data_url: img.filter(s => s.startsWith('data:image')).length,
        blob: img.filter(s => s.startsWith('blob:')).length,
        http: img.filter(s => s.startsWith('http')).length,
        metin_uzunluk: (document.body.innerText || '').length,
        ornekler: img.slice(-5).map(s => s.slice(0, 70))
    };
}"""


async def main() -> int:
    CIKIS.mkdir(parents=True, exist_ok=True)
    cookies_raw = os.environ.get("ARENA_COOKIES_JSON", "").strip()
    if not cookies_raw:
        print("❌ ARENA_COOKIES_JSON yok")
        return 1

    ornek_paket = {
        "dosya_adi": "test",
        "baslik": "Yuttuğun Sakız Gerçekten 7 Yıl Kalır mı? #shorts",
        "senaryo": {
            "tam_metin": (
                "🧠 Günün Merak Uyandıran Sorusu\n"
                "Yuttuğun sakız gerçekten yedi yıl midede kalır mı?\n\n"
                "🔍 Cevabı Biliyor Muydun?\n"
                "Hayır. Sakızın sindirilemeyen kısmı mide asidinde çözünmez ama yedi yıl "
                "da kalmaz; sindirim sistemi onu birkaç gün içinde atar. Mide asidi sakız "
                "tabanını parçalayamaz, bu yüzden bağırsaklar onu kasılmadan iter."
            )
        },
    }
    prompt = kapak_gorsel.gorsel_promptu(ornek_paket)
    print(f"📤 Prompt uzunluğu: {len(prompt)} karakter")

    from playwright.async_api import async_playwright

    rapor: dict = {"tarih": datetime.now().isoformat(), "gorsel_bulundu": False, "adaylar": []}
    async with async_playwright() as p:
        browser = await arena_api._tarayici_ac(p.chromium.launch, headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})
        clean = arena_api._arena_sayfasi_hazirla(cookies_raw)
        await context.add_cookies(
            [
                {"name": "arena-auth-prod-v1.0", "value": clean, "domain": "arena.ai", "path": "/"},
                {"name": "arena_build_bucket", "value": "stable", "domain": "arena.ai", "path": "/"},
                {"name": "user_country_code", "value": "TR", "domain": "arena.ai", "path": "/"},
            ]
        )
        page = await context.new_page()
        await page.goto("https://arena.ai/agent/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        await arena_api._arena_riza_modalini_kapat(page)
        await arena_api._promptu_gonder(page, prompt)

        # 8 dakika boyunca her 10 sn'de sayfayı yokla
        for tur in range(48):
            await page.wait_for_timeout(10000)
            durum = await page.evaluate(SAYFA_DURUMU)
            rapor["son_durum"] = durum
            print(
                f"[{tur * 10 + 10:3d}sn] img={durum['img_sayisi']} canvas={durum['canvas']} "
                f"data={durum['data_url']} blob={durum['blob']} http={durum['http']} "
                f"metin={durum['metin_uzunluk']}",
                flush=True,
            )

            if durum["img_sayisi"] or durum["canvas"]:
                ham = CIKIS / f"arena_test_ham_{tur}.png"
                indirilen = await kapak_gorsel._sayfadaki_gorseli_indir(page, ham)
                if indirilen:
                    rapor["gorsel_bulundu"] = True
                    rapor["adaylar"].append(str(indirilen))
                    print(f"✅ GÖRSEL İNDİRİLDİ: {indirilen} ({indirilen.stat().st_size} bayt)")
                    break

            body = await page.locator("body").inner_text()
            if "Sign in to continue" in body or "Continue with Google" in body:
                rapor["sebep"] = "oturum_dusmus"
                print("⛔ OTURUM DÜŞMÜŞ (login modalı) — ARENA_COOKIES_JSON yenilenmeli")
                break

        ekran = CIKIS / "arena_test_ekran.png"
        try:
            await page.screenshot(path=str(ekran), full_page=True)
            rapor["ekran_goruntusu"] = str(ekran)
            print(f"🖼️ Sayfa ekran görüntüsü: {ekran}")
        except Exception as e:
            print(f"ekran görüntüsü hatası: {str(e)[:100]}")

        await arena_api._tarayiciyi_kapat(browser)

    (CIKIS / "arena_test_rapor.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("=" * 60)
    print("SONUÇ: " + ("GÖRSEL ÜRETİLDİ ✅" if rapor["gorsel_bulundu"] else "GÖRSEL GELMEDİ ❌"))
    print("=" * 60)
    return 0 if rapor["gorsel_bulundu"] else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
