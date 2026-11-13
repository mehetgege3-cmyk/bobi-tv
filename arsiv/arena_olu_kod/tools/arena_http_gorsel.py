"""Arena'nın ÜRETTİĞİ görseli tarayıcısız indirir (yeni veri yolu).

KULLANIM (yerel/GitHub Actions):
    ARENA_COOKIES_JSON=... GH_PAT=... PREVIEW_URL=<actions önizleme URL> \
        python3 tools/arena_http_gorsel.py --cikti kanit/arena_kapak.png

İKİ KAYNAK, tek amaç:
  1. PREVIEW_URL verilirse: `sandbox:` köprüsüyle kullanıcının tarayıcısında
     `fetch()` çalıştırılıp yanıt base64 olarak alınır (tarayıcı zaten Arena
     oturumunda). Cevap sonrası kullanıcıya "çalıştır" denen tek satırlık komut
     üretilir.
  2. `--chat-id` + çerez verilirse: `modules.arena_http` ile SSE akışı okunur,
     görselin hash'i bulunup `/api/chat/workspace/cas/user/{hash}` üzerinden
     indirilir.

Bu araç ASLA görsel uydurmaz: indirilen dosya yoksa hata verir.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import arena_http  # noqa: E402


def chat_id_ile(chat_id: str, cikti: str, cerez: str) -> int:
    print(f"🔎 Akış okunuyor: {chat_id}", flush=True)
    akis = arena_http.akisi_oku(chat_id, cerez)
    print(f"   cevap: {(akis['metin'] or '(yok)')[:160]}", flush=True)
    print(f"   görsel yolu: {akis['gorsel_yolu']}", flush=True)
    print(f"   hash: {akis['hash']}", flush=True)
    if not akis["hash"]:
        print("❌ Akışta görsel hash'i YOK — üretim olmamış.", flush=True)
        return 2
    indi = arena_http.gorsel_indir(akis["hash"], cikti, cerez)
    if not indi:
        print("❌ Görsel indirilemedi.", flush=True)
        return 3
    _dogrula(indi)
    return 0


def _dogrula(yol: str) -> None:
    try:
        from PIL import Image

        with Image.open(yol) as im:
            print(f"✅ DOĞRULANDI: {yol} · {im.size[0]}×{im.size[1]} · {im.mode}", flush=True)
    except Exception as e:
        print(f"⚠️ Boyut okunamadı: {str(e)[:80]}", flush=True)


# --------------------------------------------------------------------------- #
# Yol 2: kullanıcının tarayıcısında çalışacak köprü komutu
# --------------------------------------------------------------------------- #
KOPRU_JS = """await (async () => {
  const r = await fetch("/api/chat/{chat}/events", {headers: {"accept": "text/event-stream"}});
  const t = await r.text();
  let hash = null, metin = "";
  for (const satir of t.split("\\n")) {
    if (!satir.startsWith("data: ")) continue;
    let p; try { p = JSON.parse(satir.slice(6)); } catch (e) { continue; }
    for (const k of (p.records || [])) {
      let b; try { b = JSON.parse(k.body); } catch (e) { continue; }
      const d = b.data || {};
      if (d.type === "text-delta") metin += (d.delta || "");
      if (d.type === "tool-output-available" && d.output && d.output.hash) hash = d.output.hash;
    }
  }
  if (!hash) return "GÖRSEL YOK. Cevap: " + metin.slice(0, 300);
  const g = await fetch("/api/chat/workspace/cas/user/" + hash + "?w=1024");
  const blob = await g.blob();
  const b64 = await new Promise(ok => { const f = new FileReader(); f.onload = () => ok(f.result); f.readAsDataURL(blob); });
  return JSON.stringify({hash, metin: metin.slice(0, 500), boyut: blob.size, veri: b64});
})()"""


def kopru_komutu_uret(chat_id: str, preview_url: str) -> str:
    js = KOPRU_JS.format(chat=chat_id)
    return (
        "fetch(" + json.dumps(preview_url.rstrip("/") + "/sandbox") + ", {\n"
        '  method: "POST", headers: {"content-type": "application/json"},\n'
        "  body: JSON.stringify({command: " + json.dumps("python3 -c 'pass'") + ", code: "
        + json.dumps(js) + "})\n"
        "}).then(r => r.json()).then(j => console.log(j));"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Arena görselini tarayıcısız indir")
    ap.add_argument("--chat-id", default=os.environ.get("ARENA_CHAT_ID", ""))
    ap.add_argument("--cikti", default="kanit/arena_gorsel.png")
    ap.add_argument("--son-sohbet", action="store_true", help="son sohbeti kullan")
    ap.add_argument("--kopru-komutu", action="store_true",
                    help="tarayıcıda çalıştırılacak fetch komutunu yazdır")
    ap.add_argument("--preview-url", default=os.environ.get("PREVIEW_URL", ""))
    args = ap.parse_args()

    cerez = arena_http._cerez_basligi()
    if not cerez:
        print("❌ ARENA_COOKIES_JSON yok.", flush=True)
        return 4

    chat_id = args.chat_id
    if not chat_id and args.son_sohbet:
        sohbetler = arena_http.son_sohbetler(cerez, limit=1)
        if not sohbetler:
            print("❌ Sohbet listesi boş (oturum ölü olabilir).", flush=True)
            return 5
        chat_id = sohbetler[0]["id"]
        print(f"ℹ️ Son sohbet: {chat_id}", flush=True)

    if not chat_id:
        print("❌ --chat-id ya da --son-sohbet gerekli.", flush=True)
        return 6

    if args.kopru_komutu:
        if not args.preview_url:
            print("❌ --preview-url gerekli.", flush=True)
            return 7
        print(kopru_komutu_uret(chat_id, args.preview_url))
        return 0

    return chat_id_ile(chat_id, args.cikti, cerez)


if __name__ == "__main__":
    raise SystemExit(main())
