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
 *   Opsiyonel (Oturum Yenileme İçin):
 *      SAVE_UPDATED_COOKIES=/tmp/updated-cookies.json
 *      -> Sayfa açıldığında Supabase token yenilediyse yeni çerezleri buraya yazar;
 *         GitHub Actions sonunda `gh secret set ARENA_COOKIES_JSON < /tmp/updated-cookies.json` ile secret güncellenebilir.
 */

import { chromium } from 'playwright';
import fs from 'fs';

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
  // Base64 decode
  const decoded = Buffer.from(combinedRaw, 'base64').toString('utf-8');
  // Kontrol karakterlerini temizle (JSON içinde geçersiz olan 0x00-0x1F arası)
  const cleanDecoded = decoded.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '');
  const sessionObj = JSON.parse(cleanDecoded);

  const minimalSession = {
    access_token: sessionObj.access_token,
    token_type: sessionObj.token_type || 'bearer',
    expires_in: sessionObj.expires_in || 3600,
    expires_at: sessionObj.expires_at,
    refresh_token: sessionObj.refresh_token,
    user: {
      id: sessionObj.user?.id,
      email: sessionObj.user?.email,
    },
  };

  return `base64-${Buffer.from(JSON.stringify(minimalSession)).toString('base64')}`;
}

export function extractCleanAnswer(fullBody, promptText) {
  const lastPromptIdx = fullBody.lastIndexOf(promptText);
  let slice = lastPromptIdx !== -1
    ? fullBody.slice(lastPromptIdx + promptText.length).trim()
    : fullBody;

  for (const marker of ['\nWas this task successful?', '\nWorkspace\n', '\nConnectors\n']) {
    const idx = slice.indexOf(marker);
    if (idx !== -1) slice = slice.slice(0, idx).trim();
  }

  return slice.replace(/\n\d+s\s*\|\s*just now[\s\S]*$/i, '').trim();
}

export async function askArenaAgent({
  cleanAuthCookie,
  promptText,
  screenshotPath = 'arena-cevap.png',
  saveUpdatedCookiesPath = process.env.SAVE_UPDATED_COOKIES,
}) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1024 } });

  await context.addCookies([
    { name: 'arena-auth-prod-v1.0', value: cleanAuthCookie, domain: 'arena.ai', path: '/' },
    { name: 'arena_build_bucket', value: 'stable', domain: 'arena.ai', path: '/' },
    { name: 'user_country_code', value: 'TR', domain: 'arena.ai', path: '/' },
  ]);

  const page = await context.newPage();
  await page.goto('https://arena.ai/agent/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  // Sayfanın tam yüklenmesi için bekle
  await page.waitForTimeout(3000);

  const editor = page.locator('div.tiptap[contenteditable="true"]');
  await editor.waitFor({ state: 'visible', timeout: 15000 });
  await editor.click();
  await page.waitForTimeout(500);
  await page.keyboard.type(promptText, { delay: 15 });
  await page.waitForTimeout(1000);

  const sendBtn = page.locator('button[aria-label="Send message"]');
  // Buton hidden olsa bile force ile tıkla
  await page.waitForTimeout(500);
  await sendBtn.click({ force: true });

  for (let i = 0; i < 15; i++) {
    await page.waitForTimeout(1000);
    if (page.url() !== 'https://arena.ai/agent/') break;
  }

  let lastText = '';
  let stableTicks = 0;
  for (let i = 0; i < 45; i++) {
    await page.waitForTimeout(2000);
    const currentText = await page.locator('body').innerText().catch(() => '');
    const isThinking = currentText.includes('orchestrating..');

    if (currentText.length !== lastText.length || isThinking) {
      lastText = currentText;
      stableTicks = 0;
    } else {
      stableTicks++;
      if (stableTicks >= 4 && currentText.length > promptText.length + 120) {
        break;
      }
    }
  }

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true });
  }

  // "Was this task successful?" diyaloğunu kapat
  try {
    const escBtn = page.locator('button:has-text("Esc"), [aria-label="Esc"], button.close').first();
    if (await escBtn.isVisible({ timeout: 2000 })) {
      await escBtn.click({ force: true });
      await page.waitForTimeout(300);
    }
  } catch(e) {}
  // ESC tuşu ile de kapat
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // Eğer Supabase oturumu yenilediyse güncel arena-auth çerezlerini kaydet
  if (saveUpdatedCookiesPath) {
    const latestCookies = await context.cookies('https://arena.ai');
    const authOnly = latestCookies.filter(c => c.name.startsWith('arena-auth-prod-v1'));
    if (authOnly.length > 0) {
      fs.writeFileSync(saveUpdatedCookiesPath, JSON.stringify(authOnly, null, 2), { mode: 0o600 });
    }
  }

  const fullBody = await page.locator('body').innerText();
  const chatUrl = page.url();

  // Cevabı daha doğru çıkar — AI mesaj bloğunu direkt al
  let answer = '';
  try {
    // Arena AI cevap mesajları genellikle kullanıcı mesajından sonra gelen paragraflar
    const msgBlocks = await page.locator('[data-message-role="assistant"], .assistant-message, .prose').allInnerTexts();
    if (msgBlocks.length > 0) {
      answer = msgBlocks[msgBlocks.length - 1].trim();
    }
  } catch(e) {}

  // Fallback: extractCleanAnswer
  if (!answer) {
    answer = extractCleanAnswer(fullBody, promptText);
  }

  await browser.close();

  return {
    chatUrl,
    answer,
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
