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

export async function askArenaAgent({
  cleanAuthCookie,
  promptText,
  screenshotPath = 'arena-cevap.png',
  saveUpdatedCookiesPath = process.env.SAVE_UPDATED_COOKIES,
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

  const editor = page.locator('div.tiptap[contenteditable="true"]');
  await editor.waitFor({ state: 'visible', timeout: 15000 });
  await editor.fill(promptText);
  await page.waitForTimeout(300);

  const sendBtn = page.locator('button[aria-label="Send message"]');
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
