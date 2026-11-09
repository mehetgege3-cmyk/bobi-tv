#!/usr/bin/env node
/**
 * BOBİ TV — Arena AI Senaryo Üretim Entegrasyonu v2
 * arena-ask.mjs'nin CLI modunu kullanır (daha güvenilir).
 */
import { spawnSync } from 'child_process';
import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const KATEGORILER = [
    "kurumsal_hayat", "pazartesi_sendromu", "ik_toplantisi", "mesai_sonu",
    "bar_fikrasi", "diyet_kavrami", "google_sorusu", "trafik_kavgasi",
    "wifi_kavgasi", "saglik_sorunu", "kahve_hayati", "evlilik_hayati",
    "yapay_zeka", "sabah_alarmi", "sigara_kavgasi", "sok_diyalog",
    "hastane_korkusu", "egitim_sistemi", "sosyal_medya", "spor_hayati", "sok_hayati"
];

function senaryo_prompt(kategori) {
    return `Türkçe absürt kısa Shorts senaryosu yaz. Kategori: ${kategori}. 4 diyalog, kısa. Sadece JSON: {"kategori":"${kategori}","hook_metni":"KISA HOOK","hook_suresi":1.0,"diyaloglar":[{"karakter":"AD","metin":"metin","ses":"normal","sure":1.0}],"punchline_efekt":"zoom_in","loop_baslangic":"AD","etkilesim":"soru","sabit_yorum":"yorum fikri"}`;
}

async function main() {
    const kategori = process.argv[2] || KATEGORILER[Math.floor(Math.random() * KATEGORILER.length)];
    const prompt = senaryo_prompt(kategori);

    console.error(`[Arena] Kategori: ${kategori}`);
    console.error(`[Arena] Prompt gönderiliyor...`);

    // arena-ask.mjs'yi child process olarak çalıştır
    const env = { ...process.env };
    const result = spawnSync('node', [join(__dirname, 'arena-ask.mjs'), prompt], {
        env,
        timeout: 90000,
        maxBuffer: 1024 * 1024
    });

    if (result.status !== 0) {
        const err = result.stderr?.toString() || result.error?.message || 'Bilinmeyen hata';
        console.error(`[Arena] Hata: ${err.substring(0, 300)}`);
        process.exit(1);
    }

    const output = result.stdout?.toString() || '';
    console.error(`[Arena] Cevap alındı (${output.length} char)`);

    // JSON çıkar
    let answer = output.trim();

    // Markdown kod bloğu temizle
    if (answer.includes('```json')) {
        answer = answer.split('```json')[1].split('```')[0].trim();
    } else if (answer.includes('```')) {
        answer = answer.split('```')[1].split('```')[0].trim();
    }

    // Son JSON bloğunu al
    const lastBrace = answer.lastIndexOf('}');
    const firstBrace = answer.indexOf('{');
    if (firstBrace !== -1 && lastBrace !== -1) {
        answer = answer.substring(firstBrace, lastBrace + 1);
    }

    try {
        const senaryo = JSON.parse(answer);
        console.log(JSON.stringify(senaryo, null, 2));
        console.error(`[Arena] Senaryo başarıyla üretildi`);
    } catch(e) {
        console.error(`[Arena] JSON parse hatası: ${e.message}`);
        console.error(`[Arena] Cevap: ${answer.substring(0, 300)}`);
        process.exit(1);
    }
}

main().catch(e => {
    console.error(`[Arena] Beklenmeyen hata: ${e.message}`);
    process.exit(1);
});
