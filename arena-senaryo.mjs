#!/usr/bin/env node
/**
 * BOBİ TV — Arena AI Senaryo Üretim Entegrasyonu v3
 * spawn (async) kullanır — timeout yok, cevap gelene kadar bekler.
 */
import { spawn } from 'child_process';
import { readFileSync } from 'fs';
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

function runArena(prompt) {
    return new Promise((resolve, reject) => {
        const child = spawn('node', [join(__dirname, 'arena-ask.mjs'), prompt], {
            env: process.env,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (d) => { stdout += d.toString(); });
        child.stderr.on('data', (d) => { stderr += d.toString(); process.stderr.write(d); });

        child.on('close', (code) => {
            if (code === 0) {
                resolve(stdout);
            } else {
                reject(new Error(stderr.substring(0, 300) || `exit code ${code}`));
            }
        });

        child.on('error', reject);
    });
}

async function main() {
    const kategori = process.argv[2] || KATEGORILER[Math.floor(Math.random() * KATEGORILER.length)];
    const prompt = senaryo_prompt(kategori);

    console.error(`[Arena] Kategori: ${kategori}`);
    console.error(`[Arena] Prompt gönderiliyor, cevap bekleniyor...`);

    let output;
    try {
        output = await runArena(prompt);
        console.error(`[Arena] Cevap alındı (${output.length} char)`);
    } catch(e) {
        console.error(`[Arena] Hata: ${e.message}`);
        process.exit(1);
    }

    // JSON çıkar — son JSON bloğunu al
    let answer = output.trim();
    if (answer.includes('```json')) {
        answer = answer.split('```json')[1].split('```')[0].trim();
    } else if (answer.includes('```')) {
        answer = answer.split('```')[1].split('```')[0].trim();
    }
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
        console.error(`[Arena] Cevap: ${answer.substring(0, 500)}`);
        process.exit(1);
    }
}

main().catch(e => {
    console.error(`[Arena] Beklenmeyen hata: ${e.message}`);
    process.exit(1);
});
