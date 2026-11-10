#!/usr/bin/env node
/**
 * Arena.ai Headless Playwright Agent Otomasyon Aracı (GitHub Actions Uyumlu)
 *
 * Kullanım Seçenekleri:
 *   1) GitHub Secret (Ham Cookie-Editor JSON):
 *      ARENA_COOKIES_JSON='[{"name":...}]' node scripts/arena-ask.mjs "sorunuz"
 *
 *   2) Dosyadan (Cookie-Editor JSON):
 *      COOKIES_FILE=/tmp/cookies.json node scripts/arena-ask.mjs "sorunuz"
 *
 *   3) Tekil Temiz Çerez Değeri:
 *      ARENA_AUTH_COOKIE="base64-..." node scripts/arena-ask.mjs "sorunuz"
 *
 *   ACCEPT_TOS=1 → Terms of Use onay butonuna otomatik basılır.
 *   Verilmezse ToS duvarında net hata fırlatılır + ekran görüntüsü alınır
 *   (Agree'ye asla kendiliğinden BASILMAZ).
 */
import { chromium } from 'playwright';
import fs from 'fs';
import {
  waitForEditor,
  attemptSend,
  detectConsent,
  acceptConsent,
} from './arena-dom.mjs';

export function sanitizeCookieJsonText(rawText) {
  return rawText.replace(/\[([^\]]+)\]\(https?:\/\/[^)]+\)/g, '$1').trim();
}

export function buildCleanArenaCookie(cookiesArray) {
  const chunks = cookiesArray
    .filter(c => c && typeof c.name === 'string' && c.name.startsWith('arena-auth-prod-v1'))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(c => c.value);
  if (chunks.length === 0) {
    throw new Error('Cookie listesinde "arena-auth-prod-v1.*" bulunamadı.');
  }
  const combinedRaw = chunks.join('').replace(/^base64-/, '');
  let minimalSession = null;
  try {
    const pad = combinedRaw + '='.repeat((4 - (combinedRaw.length % 4)) % 4);
    const sessionObj = JSON.parse(Buffer.from(pad, 'base64').toString('utf-8'));
    if (sessionObj.access_token) {
      minimalSession = {
        access_token: sessionObj.access_token,
        token_type: sessionObj.token_type || 'bearer',
        expires_in: sessionObj.expires_in || 3600,
        expires_at: sessionObj.expires_at,
        refresh_token: sessionObj.refresh_token,
        user: {
          id: sessionObj.user?.id,
          aud: sessionObj.user?.aud || 'authenticated',
          role: sessionObj.user?.role || 'authenticated',
          email: sessionObj.user?.email,
        },
      };
    }
  } catch (_) {
    // Parça sınırında kesilme varsa ilk parçadan regex ile kurtar
  }
  if (!minimalSession) {
    let first = chunks[0].replace(/^base64-/, '');
    first = first.slice(0, first.length - (first.length % 4));
    const text = Buffer.from(first, 'base64').toString('utf-8');
    const at = text.match(/"access_token"\s*:\s*"([^"]+)"/);
    const rt = text.match(/"refresh_token"\s*:\s*"([^"]+)"/);
    const exp = text.match(/"expires_at"\s*:\s*(\d+)/);
    const uid = text.match(/"user"\s*:\s*\{\s*"id"\s*:\s*"([^"]+)"/);
    const em = text.match(/"email"\s*:\s*"([^"]+)"/);
    if (!at) throw new Error('Çerez içinde access_token çözümlenemedi.');
    minimalSession = {
      access_token: at[1],
      token_type: 'bearer',
      expires_in: 3600,
      expires_at: exp ? Number(exp[1]) : 1794150284,
      refresh_token: rt ? rt[1] : '',
      user: {
        id: uid ? uid[1] : '',
        aud: 'authenticated',
        role: 'authenticated',
        email: em ? em[1] : '',
      },
    };
  }
  return `base64-${Buffer.from(JSON.stringify(minimalSession)).toString('base64')}`;
}

export function extractCleanAnswer(fullBody, promptText) {
  const promptLines = promptText.split('\n').map(s => s.trim()).filter(Boolean);
  const lastLine = promptLines[promptLines.length - 1] || promptText;
  let lastPromptIdx = fullBody.lastIndexOf(promptText);
  let slice = '';
  if (lastPromptIdx !== -1) {
    slice = fullBody.slice(lastPromptIdx + promptText.length).trim();
  } else {
    const endIdx = fullBody.lastIndexOf(lastLine);
    slice = endIdx !== -1 ? fullBody.slice(endIdx + lastLine.length).trim() : fullBody;
  }
  for (const marker of ['\nWas this task successful?', '\nWorkspace\n', '\nConnectors\n']) {
    const idx = slice.indexOf(marker);
    if (idx !== -1) slice = slice.slice(0, idx).trim();
  }
  slice = slice.replace(/\n\d+s\s*\|\s*just now[\s\S]*$/i, '').trim();
  // "Thought for X second(s)" başlığını temizle
  const lines = slice.split('\n');
  if (lines.length > 0 && /^Thought for \d+/i.test(lines[0].trim())) {
    lines.shift();
    while (lines.length > 0 && !lines[0].trim()) lines.shift();
    if (lines.length >= 3 && !lines[1].trim() && /^(Kullanıcı|The user)\b/i.test(lines[0].trim())) {
      lines.splice(0, 2);
    }
  }
  return lines.join('\n').trim();
}

const THINKING_PATTERNS = [/orchestrating/i, /thinking/i, /düşünüyor/i, /dusunuyor/i];
function isModelBusy(bodyText) {
  return THINKING_PATTERNS.some(re => re.test(bodyText));
}

export async function askArenaAgent({
  cleanAuthCookie,
  promptText,
  screenshotPath = 'arena-cevap.png',
  acceptTos = process.env.ACCEPT_TOS === '1',
  answerTimeoutMs = 120000,
}) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  await context.addCookies([
    { name: 'arena-auth-prod-v1.0', value: cleanAuthCookie, domain: 'arena.ai', path: '/' },
    { name: 'arena_build_bucket', value: 'stable', domain: 'arena.ai', path: '/' },
    { name: 'user_country_code', value: 'TR', domain: 'arena.ai', path: '/' },
  ]);
  const page = await context.newPage();
  await page.goto('https://arena.ai/agent/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(1500);

  // ToS / onay duvarı: HİÇBİR koşulda sessizce devam etme.
  const consent = await detectConsent(page);
  if (consent.present) {
    if (!acceptTos) {
      const tosShot = screenshotPath ? screenshotPath.replace(/\.png$/, '-tos.png') : 'arena-tos-duvari.png';
      await page.screenshot({ path: tosShot, fullPage: true }).catch(() => {});
      await browser.close();
      throw new Error(
        `Arena Terms of Use duvarı algılandı (buton: ${consent.label}). ` +
        'ACCEPT_TOS=1 verilmeden Agree\'ye BASILMAZ. Lütfen ACCEPT_TOS=1 ile tekrar deneyin ' +
        `veya çerezi elle güncelleyin. Ekran görüntüsü: ${tosShot}`
      );
    }
    await acceptConsent(page);
    await page.waitForTimeout(1500);
  }

  // Editör: tiptap birincil, fallbackler sırayla; 45 sn (hydration yavaş).
  const editor = await waitForEditor(page, 45000);
  if (!editor) {
    if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    await browser.close();
    throw new Error('Arena editörü (tiptap/fallback) 45 sn içinde görünmedi — arayüz değişmiş olabilir.');
  }
  await editor.click();
  await page.waitForTimeout(200);
  await page.keyboard.insertText(promptText);
  await page.waitForTimeout(400);

  // Gönderim DOĞRULANIR (Enter→Enter→butonlar; composer boşaldı VEYA URL değişti).
  const sendResult = await attemptSend(page);
  if (!sendResult.verified) {
    if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    await browser.close();
    throw new Error(
      `Arena gönderimi doğrulanamadı (method=${sendResult.method}, clicked=${sendResult.clicked}, ` +
      `composer hâlâ ${sendResult.remainingComposerText.length} karakter).`
    );
  }

  // Cevap bekleme: sabit sleep yok; metin büyüdü + duruldu + model meşgul değil.
  const baseline = (await page.locator('body').innerText().catch(() => '')).length;
  let lastLen = baseline;
  let stableTicks = 0;
  let sawGrowth = false;
  const deadline = Date.now() + answerTimeoutMs;
  while (Date.now() < deadline) {
    await page.waitForTimeout(1500);
    const currentText = await page.locator('body').innerText().catch(() => '');
    const busy = isModelBusy(currentText);
    const bitti = currentText.includes('Was this task successful?');
    if (currentText.length > lastLen) {
      sawGrowth = true;
      lastLen = currentText.length;
      stableTicks = 0;
    } else if (!busy) {
      stableTicks += 1;
    } else {
      stableTicks = 0;
    }
    // sawGrowth ŞART: metin hiç büyümeden durduysa cevap sayılmaz.
    if (sawGrowth && stableTicks >= 4 && currentText.length > promptText.length + 120) {
      break;
    }
    if (bitti && currentText.length > promptText.length + 120) {
      sawGrowth = true;
      break;
    }
  }
  if (!sawGrowth) {
    if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    await browser.close();
    throw new Error('Arena gönderildi ama cevap gövdesi büyümedi — oturum/arayüz durumunu kontrol edin.');
  }

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
  }
  const fullBody = await page.locator('body').innerText();
  const chatUrl = page.url();
  await browser.close();
  return {
    chatUrl,
    answer: extractCleanAnswer(fullBody, promptText),
    fullBody,
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const promptText = process.argv[2] || 'merhaba kanka bana kendini tanıt.';
  let cleanAuthCookie = process.env.ARENA_AUTH_COOKIE;
  if (!cleanAuthCookie && process.env.ARENA_COOKIES_JSON) {
    const parsed = JSON.parse(sanitizeCookieJsonText(process.env.ARENA_COOKIES_JSON));
    cleanAuthCookie = buildCleanArenaCookie(parsed);
  } else if (!cleanAuthCookie && process.env.COOKIES_FILE) {
    const raw = fs.readFileSync(process.env.COOKIES_FILE, 'utf-8');
    const parsed = JSON.parse(sanitizeCookieJsonText(raw));
    cleanAuthCookie = buildCleanArenaCookie(parsed);
  }
  if (!cleanAuthCookie) {
    console.error('Hata: ARENA_COOKIES_JSON, COOKIES_FILE veya ARENA_AUTH_COOKIE ortam değişkeni gerekli.');
    process.exit(1);
  }
  const result = await askArenaAgent({ cleanAuthCookie, promptText });
  console.log('Chat URL:', result.chatUrl);
  console.log('\n--- CEVAP ---\n');
  console.log(result.answer);
}
