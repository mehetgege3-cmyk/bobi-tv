#!/usr/bin/env node
/**
 * BOBİ TV — Arena AI Senaryo Üretici v6.3
 * Konu rotasyonlu, en az 15sn hedefli, kapsayıcı ve ters köşeli Shorts senaryo üretimi.
 */
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const KONU_HAVUZU = {
  kurumsal_hayat: 'özgün işyeri gözlemi; toplantı, e-posta veya iş arkadaşları',
  pazartesi_sendromu: 'alarm, sabah rutini ve pazartesi telaşı',
  ik_toplantisi: 'beklenmedik iş görüşmesi veya işe alım durumu',
  mesai_sonu: 'mesai, tatil veya son dakika iş talebi',
  diyet_kavrami: 'diyet, yemek tercihi ve küçük gündelik çelişkiler',
  trafik_kavgasi: 'trafik, yol tarifi veya navigasyonla yaşanan komik anlaşmazlık',
  wifi_kavgasi: 'ev interneti, modem veya teknolojiye dair absürt durum',
  saglik_sorunu: 'doktor, hasta veya sağlık kurumunda zararsız gündelik komedi',
  kahve_hayati: 'kahve, kafe veya kahve makinesinin tuhaf davranışı',
  yapay_zeka: 'insan ile yapay zekâ arasında komik ve özgün bir diyalog',
  sosyal_medya: 'sosyal medya, aile veya içerik üreticiliği üzerine komedi',
  spor_hayati: 'spor salonu, egzersiz veya motivasyon üzerine kendine dönük mizah',
  bar_fikralari: 'bar, barmen ve müşterinin beklenmedik sohbeti; alkol kullanımını özendirmeden',
  paradoks_hikayeleri: 'zaman döngüsü, gelecekten mesaj veya neden-sonuç paradoksu',
  absurt_komedi: 'gündelik eşya veya kurumun mantıksız biçimde karakter gibi davranması',
  absurt_sakalar: 'kelime oyunu ve beklenmedik mantık sıçraması içeren kısa diyalog şakası',
  cilgin_hikayeler: 'yanlış anlaşılmayla başlayan çılgın ama zararsız kısa macera',
  ters_kose_fikralar: 'beklenti kurup son anda temiz ve komik ters köşe yapan fıkra',
  eglenceli_replikler: 'iki karakter arasında hızlı, akılda kalan neşeli replik düellosu',
  kulturlar_arasi_mizah: 'farklı kültürlerden karakterlerin eşit ve saygılı gündelik yanlış anlaşılması'
};
const KATEGORILER = Object.keys(KONU_HAVUZU);

function senaryoPrompt(kategori) {
  const ornek = {
    kategori,
    ortam_etiketi: KONU_HAVUZU[kategori],
    ruh_hali: 'komedi',
    hook_ust_bant: 'KISA VE MERAK UYANDIRAN BAŞLIK!',
    baslik: 'Özgün ve merak uyandıran Türkçe başlık #shorts',
    twist_indeksi: 5,
    diyaloglar: [
      { karakter: 'MERT', cinsiyet: 'erkek', metin: 'Olayın tuhaf sonucundan başlayan ilk replik burada.', ses: 'enerjik', sfx: 'whoosh' },
      { karakter: 'ECE', cinsiyet: 'kadin', metin: 'Karşı karakterin doğal ve kısa yanıtı burada.', ses: 'normal', sfx: 'pop' }
    ],
    sabit_yorum: 'İzleyiciye hikâyeyle ilgili eğlenceli bir soru 👇',
    etkilesim: 'Bunu gülümseyecek arkadaşına gönder!'
  };
  return [
    `Sen özgün Türkçe YouTube Shorts komedi yazarı ve yönetmenisin. Kategori: ${kategori}. Konu: ${KONU_HAVUZU[kategori]}.`,
    'Hiçbir araç çağırma; yalnızca tek, geçerli JSON nesnesi döndür.',
    'Önceki videolardaki şaka veya olay örgüsünü kopyalama. İstenen kategoriye sadık kal; ofis komedisine sıkışma.',
    '7 veya 8 doğal, hızlı diyalog repliği yaz; toplam en az 45, tercihen 50-65 konuşma kelimesi olsun. Hedef süre 15-30 saniyedir.',
    'İki özgün karakter karşılıklı konuşsun; biri erkek, biri kadın. İlk replikte kanca, sondan önceki ana replikte temiz bir ters köşe olsun; final doğal bir kapanış/loop köprüsü olsun.',
    'Irk, ten rengi veya etnik kökeni hedef alan aşağılayıcı şaka, hakaret veya stereotip yazma. Çok kültürlü karakterleri eşit ve saygılı çiz; komediyi kimlikten değil durumdan çıkar.',
    `Çıktı şeması: ${JSON.stringify(ornek)}`
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

function extractScenarioJson(rawOutput, kategori) {
  let text = rawOutput.trim();
  if (text.includes('```json')) {
    text = text.split('```json')[1].split('```')[0].trim();
  } else if (text.includes('```')) {
    text = text.split('```')[1].split('```')[0].trim();
  }
  const first = text.indexOf('{');
  const last = text.lastIndexOf('}');
  if (first === -1 || last === -1 || last <= first) throw new Error('Yanıt içinde JSON nesnesi bulunamadı.');
  const parsed = JSON.parse(text.slice(first, last + 1));
  if (!Array.isArray(parsed.diyaloglar) || parsed.diyaloglar.length < 6 || parsed.diyaloglar.length > 8) {
    throw new Error('diyaloglar 6-8 replik arasında olmalı.');
  }
  const kelimeSayisi = parsed.diyaloglar.reduce((sum, d) => sum + String(d.metin || '').trim().split(/\s+/).filter(Boolean).length, 0);
  if (kelimeSayisi < 45) throw new Error(`Senaryo çok kısa: ${kelimeSayisi} kelime; en az 45 gerekli.`);
  if (!KATEGORILER.includes(parsed.kategori)) parsed.kategori = kategori;
  return parsed;
}

async function main() {
  const istenen = process.argv[2] || KATEGORILER[Math.floor(Math.random() * KATEGORILER.length)];
  const kategori = KATEGORILER.includes(istenen) ? istenen : null;
  if (!kategori) throw new Error(`Bilinmeyen kategori: ${istenen}`);
  const output = await runArena(senaryoPrompt(kategori));
  const senaryo = extractScenarioJson(output, kategori);
  console.log(JSON.stringify(senaryo, null, 2));
  console.error(`[Arena v6.3] ✅ ${senaryo.kategori}: ${senaryo.baslik}`);
}

main().catch(err => {
  console.error(`[Arena v6.3] Hata: ${err.message}`);
  process.exit(1);
});
