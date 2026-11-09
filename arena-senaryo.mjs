/**
 * BOBİ TV — Arena AI Senaryo Üretim Entegrasyonu
 * Arena.ai'ya bağlanıp Türkçe absürt/ironik senaryo yazar.
 * Mevcut arena-ask.mjs'den import edilir.
 * 
 * Kullanım:
 *   node arena-senaryo.mjs "komedi"  # kategori
 *   node arena-senaryo.mjs "kurumsal" # kategori
 * 
 * Çıktı: JSON formatında senaryo
 */
import { askArenaAgent } from './arena-ask.mjs';

// Senaryo prompt şablonu
const SENARYO_PROMPT = (kategori) => `Sen Türkçe absürt ve ironik mizah yazarısın.
Sana verilen kategori için 5-8 saniyelik YouTube Shorts videosu senaryosu yaz.

Kategori: ${kategori}

Kurallar:
- Maksimum 4-5 kısa diyalog
- Her diyalog 1-2 cümle, çok kısa
- Karakter isimleri TTS tarafından okunmayacak (sadece ekranda yazacak)
- Hook metni: ilk saniyede ekranda büyük harflerle çıkacak (2-4 kelime)
- Punchline: sürpriz ters köşe veya absürt final
- Loop: son diyalog baştaki diyaloga bağlanabilmeli
- Toplam 60-80 kelime
- Türkçe, anlaşılır, absürt

Çıktı formatı (SADECE JSON, başka metin yok):
{
  "kategori": "${kategori}",
  "hook_metni": "KISA HOOK",
  "hook_suresi": 1.0,
  "diyaloglar": [
    {"karakter": "KARAKTER1", "metin": "kısa diyalog", "ses": "normal", "sure": 1.0},
    {"karakter": "KARAKTER2", "metin": "kısa diyalog", "ses": "robotik", "sure": 0.8}
  ],
  "punchline_efekt": "zoom_in",
  "loop_baslangic": "KARAKTER1",
  "etkilesim": "izleyiciye soru",
  "sabit_yorum": "sabit yorum fikri"
}

Ses tipleri: normal, yavas_bikkin, yavas_dramatik, robotik_koro, robotik, enerjik, bikeyn, bikeyn_dramatik, uykulu, dusunceli, derin, derin_dramatik, sinirli, suprized, umutlu, kesin, endiseli, gururlu, ciddi, soğuk, alarm
Punchline efektleri: zoom_in, siyah_beyaz_zoom, karartma
SADECE JSON döndür, başka hiçbir şey yazma.`;

const KATEGORILER = [
    "kurumsal_hayat",
    "pazartesi_sendromu",
    "ik_toplantisi",
    "mesai_sonu",
    "bar_fikrasi",
    "diyet_kavrami",
    "google_sorusu",
    "trafik_kavgasi",
    "wifi_kavgasi",
    "saglik_sorunu",
    "kahve_hayati",
    "evlilik_hayati",
    "yapay_zeka",
    "sabah_alarmi",
    "sigara_kavgasi",
    "sok_diyalog",
    "hastane_korkusu",
    "egitim_sistemi",
    "sosyal_medya",
    "spor_hayati",
    "sok_hayati"
];

async function main() {
    const kategori = process.argv[2] || KATEGORILER[Math.floor(Math.random() * KATEGORILER.length)];
    const prompt = SENARYO_PROMPT(kategori);

    console.error(`[Arena] Kategori: ${kategori}`);
    console.error(`[Arena] Prompt gönderiliyor...`);

    let cleanAuthCookie = process.env.ARENA_AUTH_COOKIE;

    if (!cleanAuthCookie && process.env.ARENA_COOKIES_JSON) {
        const { sanitizeCookieJsonText, buildCleanArenaCookie } = await import('./arena-ask.mjs');
        const parsed = JSON.parse(sanitizeCookieJsonText(process.env.ARENA_COOKIES_JSON));
        cleanAuthCookie = buildCleanArenaCookie(parsed);
    }

    if (!cleanAuthCookie) {
        console.error('Hata: ARENA_COOKIES_JSON veya ARENA_AUTH_COOKIE gerekli.');
        process.exit(1);
    }

    try {
        const result = await askArenaAgent({
            cleanAuthCookie,
            promptText: prompt,
            screenshotPath: null, // screenshot istemiyoruz
        });

        // Cevaptan JSON çıkar
        let answer = result.answer.trim();

        // Markdown kod bloğu varsa temizle
        if (answer.includes('```json')) {
            answer = answer.split('```json')[1].split('```')[0].trim();
        } else if (answer.includes('```')) {
            answer = answer.split('```')[1].split('```')[0].trim();
        }

        // İlk { ile son } arasını al
        const start = answer.indexOf('{');
        const end = answer.lastIndexOf('}');
        if (start !== -1 && end !== -1) {
            answer = answer.substring(start, end + 1);
        }

        // JSON doğrula
        const senaryo = JSON.parse(answer);
        console.log(JSON.stringify(senaryo, null, 2));
    } catch (e) {
        console.error(`[Arena] Hata: ${e.message}`);
        console.error(`[Arena] Cevap: ${result?.answer?.substring(0, 500) || 'boş'}`);
        process.exit(1);
    }
}

main().catch(e => {
    console.error(`[Arena] Beklenmeyen hata: ${e.message}`);
    process.exit(1);
});
