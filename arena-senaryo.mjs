#!/usr/bin/env node
/**
 * BOBİ TV — Arena AI Viral Loop Senaryo Üretici v6.0
 * Master Prompt: 0.0sn Hook + Çift Karakter (Erkek/Kadın) + Twist + %100 Kusursuz Döngü (Loop)
 */
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const KATEGORILER = [
  'kurumsal_hayat', 'pazartesi_sendromu', 'ik_toplantisi', 'mesai_sonu',
  'diyet_kavrami', 'trafik_kavgasi', 'wifi_kavgasi', 'saglik_sorunu',
  'kahve_hayati', 'yapay_zeka', 'sosyal_medya', 'spor_hayati'
];

function senaryoPrompt(kategori) {
  return [
    `Sen milyonlar izlenen bir Türkçe YouTube Shorts komedi yönetmenisin. Kategori: "${kategori}".`,
    `Hiçbir araç (bash/search) ÇAĞIRMA, sadece geçerli tek bir JSON nesnesi döndür.`,
    `Kurallar:`,
    `1) Toplam 6 veya 7 kısa, hızlı, doğal Türkçe diyalog cümlesi yaz (her cümle 5-11 kelime).`,
    `2) 2 zıt karakter karşılıklı konuşsun: biri "erkek", diğeri "kadin".`,
    `3) 1. cümle ("İşte tam bu yüzden..." veya "Ve o saniye...") doğrudan olayın en şok edici sonucundan başlasın.`,
    `4) Sondan bir önceki cümle (twist_indeksi: 5) hiç beklenmedik komik bir ters köşe (twist) olsun.`,
    `5) En son cümle yarım kalarak ("...ben de kapıyı çarpıp bağırdım...") videonun başındaki 1. cümleye DİLBİLGİSEL KUSURSUZ DÖNGÜ (loop) ile bağlansın!`,
    `Şu JSON şemasında yanıt ver:`,
    `{"kategori":"${kategori}","ortam_etiketi":"office coffee","ruh_hali":"komedi","hook_ust_bant":"MAKS 4 KELİME ŞOK BAŞLIK!","baslik":"Merak Uyandıran Türkçe Başlık 😱 #shorts","twist_indeksi":5,"diyaloglar":[{"karakter":"MÜDÜR","cinsiyet":"erkek","metin":"İşte tam bu yüzden...","ses":"sinirli","sfx":"whoosh"},{"karakter":"AYŞE","cinsiyet":"kadin","metin":"Ama nasıl olur?","ses":"suprized","sfx":"pop"}],"sabit_yorum":"İzleyiciyi yoruma çekecek tartışmalı/komik soru 👇","etkilesim":"Arkadaşını etiketle çağrısı"}`
  ].join(' ');
}

function runArena(prompt) {
  return new Promise((resolve, reject) => {
    const child = spawn('node', [join(__dirname, 'arena-ask.mjs'), prompt], {
      env: process.env,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', d => { stdout += d.toString(); });
    child.stderr.on('data', d => { stderr += d.toString(); process.stderr.write(d); });
    child.on('close', code => {
      if (code === 0 && stdout.trim()) resolve(stdout);
      else reject(new Error(stderr.substring(0, 350) || `exit code ${code}`));
    });
    child.on('error', reject);
  });
}

function extractScenarioJson(rawOutput) {
  let text = rawOutput.trim();
  if (text.includes('```json')) {
    text = text.split('```json')[1].split('```')[0].trim();
  } else if (text.includes('```')) {
    text = text.split('```')[1].split('```')[0].trim();
  }
  const first = text.indexOf('{');
  const last = text.lastIndexOf('}');
  if (first === -1 || last === -1 || last <= first) {
    throw new Error('Yanıt içinde JSON nesnesi bulunamadı.');
  }
  const parsed = JSON.parse(text.slice(first, last + 1));
  if (!Array.isArray(parsed.diyaloglar) || parsed.diyaloglar.length < 4) {
    throw new Error('diyaloglar dizisi eksik veya çok kısa.');
  }
  return parsed;
}

async function main() {
  const kategori = process.argv[2] || KATEGORILER[Math.floor(Math.random() * KATEGORILER.length)];
  const prompt = senaryoPrompt(kategori);

  console.error(`[Arena v6] Kategori: ${kategori} — Loop senaryo isteniyor...`);
  const output = await runArena(prompt);
  const senaryo = extractScenarioJson(output);
  console.log(JSON.stringify(senaryo, null, 2));
  console.error(`[Arena v6] ✅ Loop senaryo üretildi: ${senaryo.baslik}`);
}

main().catch(err => {
  console.error(`[Arena v6] Hata: ${err.message}`);
  process.exit(1);
});
