#!/usr/bin/env node
/**
 * arena-selftest.mjs — Arena.ai oturum/arayüz tanılama scripti.
 *
 * Çıkış kodları (report.json içindeki "verdict" ile eşleşir):
 *   0 basarili               — uçtan uca çalıştı (gönderildi + cevap büyüdü)
 *   1 cookie-yapilandirma-hatasi / ag-hatasi — secret eksik ya da ağ hatası
 *   2 oturum-gecersiz         — giriş ekranı; çerez süresi dolmuş
 *   3 selector-bulunamadi     — composer yok, giriş ekranı da yok → arayüz değişmiş
 *   4 gonderim-basarisiz      — composer hâlâ dolu (gönderim doğrulanamadı)
 *   5 cevap-algilamadi        — gönderildi ama gövde büyümedi
 *   6 tos-onayi-bekliyor      — Terms of Use duvarı, ACCEPT_TOS=1 verilmedi
 *   7 bot-korumasi            — Cloudflare doğrulama ekranı
 *
 * Ortam değişkenleri:
 *   PROMPT            (gönderilecek metin; varsayılan kısa ping)
 *   ARENA_URL         (varsayılan https://arena.ai/agent/)
 *   OUT_DIR           (varsayılan arena-diagnostics)
 *   EDITOR_TIMEOUT    (ms, varsayılan 30000)
 *   ANSWER_TIMEOUT    (ms, varsayılan 120000)
 *   ACCEPT_TOS        (varsayılan 0; 1 ise ToS onay butonuna basılır)
 *   ARENA_COOKIES_JSON / ARENA_AUTH_COOKIE / COOKIES_FILE — oturum çerezi
 *
 * Gizlilik: çerez DEĞERİ hiçbir dosyaya yazılmaz. Raporda yalnız çerez
 * ADI + UZUNLUK geçer.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {
  waitForEditor,
  attemptSend,
  detectConsent,
  acceptConsent,
  composerText,
} from './arena-dom.mjs';
import { buildCleanArenaCookie, sanitizeCookieJsonText } from './arena-ask.mjs';

const PROMPT = process.env.PROMPT || "Merhaba, lütfen sadece 'pong' yanıtını ver.";
const ARENA_URL = process.env.ARENA_URL || 'https://arena.ai/agent/';
const OUT_DIR = process.env.OUT_DIR || 'arena-diagnostics';
const EDITOR_TIMEOUT = Number(process.env.EDITOR_TIMEOUT || 30000);
const ANSWER_TIMEOUT = Number(process.env.ANSWER_TIMEOUT || 120000);
const ACCEPT_TOS = process.env.ACCEPT_TOS === '1';

const report = {
  startedAt: new Date().toISOString(),
  arenaUrl: ARENA_URL,
  acceptTos: ACCEPT_TOS,
  editorTimeoutMs: EDITOR_TIMEOUT,
  answerTimeoutMs: ANSWER_TIMEOUT,
  promptLength: PROMPT.length,
  exitCode: null,
  verdict: null,
  note: '',
  cookies: [], // yalnız ad + uzunluk
  steps: [],
};

function log(msg) {
  process.stderr.write(`[selftest] ${msg}\n`);
}

async function snapshot(page, name, note = '') {
  try {
    const png = path.join(OUT_DIR, `${name}.png`);
    const dom = path.join(OUT_DIR, `${name}.html`);
    await page.screenshot({ path: png, fullPage: true }).catch(() => {});
    const html = await page.content().catch(() => '');
    fs.writeFileSync(dom, html, 'utf8');
    report.steps.push({ name, ts: new Date().toISOString(), screenshot: `${name}.png`, dom: `${name}.html`, note });
  } catch (e) {
    report.steps.push({ name, ts: new Date().toISOString(), note: `snapshot failed: ${e.message}` });
  }
}

function finish(code, verdict, note = '') {
  report.exitCode = code;
  report.verdict = verdict;
  report.note = note;
  report.finishedAt = new Date().toISOString();
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, 'report.json'), JSON.stringify(report, null, 2), 'utf8');
  log(`VERDICT: ${verdict} (exit ${code}) — ${note || 'no detail'}`);
  process.exit(code);
}

function prepareCleanCookie() {
  if (process.env.ARENA_AUTH_COOKIE) {
    report.cookies.push({ name: 'ARENA_AUTH_COOKIE (env)', length: process.env.ARENA_AUTH_COOKIE.length });
    return process.env.ARENA_AUTH_COOKIE;
  }
  let raw = process.env.ARENA_COOKIES_JSON || '';
  let source = 'ARENA_COOKIES_JSON (env)';
  if (!raw && process.env.COOKIES_FILE) {
    raw = fs.readFileSync(process.env.COOKIES_FILE, 'utf8');
    source = `COOKIES_FILE (${process.env.COOKIES_FILE})`;
  }
  if (!raw) {
    return null;
  }
  let parsed;
  try {
    parsed = JSON.parse(sanitizeCookieJsonText(raw));
  } catch (e) {
    finish(1, 'cookie-yapilandirma-hatasi', `Çerez JSON ayrıştırılamadı: ${e.message}`);
  }
  if (!Array.isArray(parsed) || parsed.length === 0) {
    finish(1, 'cookie-yapilandirma-hatasi', 'Çerez listesi boş veya dizi değil.');
  }
  for (const c of parsed) {
    if (c && typeof c.name === 'string') {
      report.cookies.push({ name: c.name, length: String(c.value || '').length, source });
    }
  }
  try {
    return buildCleanArenaCookie(parsed);
  } catch (e) {
    finish(1, 'cookie-yapilandirma-hatasi', `Temiz çerez üretilemedi: ${e.message}`);
  }
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const cleanAuthCookie = prepareCleanCookie();
  if (!cleanAuthCookie) {
    finish(1, 'cookie-yapilandirma-hatasi', 'ARENA_COOKIES_JSON / ARENA_AUTH_COOKIE / COOKIES_FILE tanımlı değil.');
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  await context.addCookies([
    { name: 'arena-auth-prod-v1.0', value: cleanAuthCookie, domain: 'arena.ai', path: '/' },
    { name: 'arena_build_bucket', value: 'stable', domain: 'arena.ai', path: '/' },
    { name: 'user_country_code', value: 'TR', domain: 'arena.ai', path: '/' },
  ]);
  const page = await context.newPage();

  // 1) Sayfayı aç — ağ hatası → exit 1
  try {
    await page.goto(ARENA_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  } catch (e) {
    await snapshot(page, '01-goto-hata', String(e.message));
    finish(1, 'ag-hatasi', `Sayfa açılamadı: ${e.message}`);
  }
  await page.waitForTimeout(2000);
  await snapshot(page, '02-goto-sonrasi');

  let bodyText = '';
  try {
    bodyText = (await page.locator('body').innerText().catch(() => '')) || '';
  } catch (_) {
    bodyText = '';
  }
  const lower = bodyText.toLowerCase();

  // 2) Cloudflare bot koruması → exit 7
  const title = await page.title().catch(() => '');
  if (
    /just a moment|checking your browser|attention required|cloudflare/i.test(title) ||
    /cf-chl|challenge-platform|just a moment|doğrulanıyor|bot doğrulaması/i.test(lower)
  ) {
    await snapshot(page, '03-cloudflare', title);
    finish(7, 'bot-korumasi', `Cloudflare doğrulama ekranı (title="${title}"). Composer hiç render olmaz; oturum hatasıyla karıştırılmamalı.`);
  }

  // 3) Giriş ekranı → oturum süresi dolmuş → exit 2
  const loginHints = ['sign in', 'continue with google', 'log in', 'giriş yap', 'giris yap', 'oturum aç'];
  const sawLogin = loginHints.some(h => lower.includes(h));
  if (sawLogin) {
    await snapshot(page, '04-login-ekrani', loginHints.filter(h => lower.includes(h)).join(','));
    finish(2, 'oturum-gecersiz', 'Giriş ekranı algılandı — çerez süresi dolmuş. Elle yenilemeniz gerekir.');
  }

  // 4) ToS / onay duvarı → exit 6 (ACCEPT_TOS=1 değilse)
  const consent = await detectConsent(page);
  if (consent.present) {
    if (!ACCEPT_TOS) {
      await snapshot(page, '05-tos-duvari', `label=${consent.label}; hints=${consent.textHints.join(',')}`);
      finish(6, 'tos-onayi-bekliyor', `Terms of Use duvarı (buton: ${consent.label}). ACCEPT_TOS=1 verilmeden Agree'ye BASILMAZ.`);
    }
    const res = await acceptConsent(page);
    log(`ToS onaylandı: ${res.method}`);
    await page.waitForTimeout(2000);
    await snapshot(page, '05b-tos-kabul-edildi', res.method);
  }

  // 5) Editörü bekle → yoksa exit 3
  const editor = await waitForEditor(page, EDITOR_TIMEOUT);
  if (!editor) {
    await snapshot(page, '06-editor-bulunamadi');
    finish(3, 'selector-bulunamadi', 'Composer (tiptap/fallback) render olmadı ve giriş ekranı da yok — arayüz değişmiş olabilir.');
  }
  await snapshot(page, '06-editor-hazir');

  // 6) Prompt'u yaz
  try {
    await editor.click();
    await page.waitForTimeout(200);
    await page.keyboard.insertText(PROMPT);
    await page.waitForTimeout(400);
  } catch (e) {
    await snapshot(page, '07-prompt-yazilamadi', e.message);
    finish(3, 'selector-bulunamadi', `Editör odaklanamadı/yazılamadı: ${e.message}`);
  }
  const beforeSend = await composerText(page);
  await snapshot(page, '07-composer-dolu', `composerLength=${beforeSend.length}`);

  // 7) Gönder + doğrula → doğrulanamazsa exit 4
  const sendResult = await attemptSend(page);
  report.sendResult = sendResult;
  await snapshot(page, '08-gonderim-sonrasi', JSON.stringify(sendResult));
  if (!sendResult.verified) {
    finish(4, 'gonderim-basarisiz', `Gönderim doğrulanamadı (method=${sendResult.method}, clicked=${sendResult.clicked}, composer hâlâ ${sendResult.remainingComposerText.length} karakter).`);
  }

  // 8) Cevap büyümesini bekle → büyümezse exit 5
  const baseline = (await page.locator('body').innerText().catch(() => '')).length;
  let lastLen = baseline;
  let stableTicks = 0;
  let sawGrowth = false;
  const deadline = Date.now() + ANSWER_TIMEOUT;
  while (Date.now() < deadline) {
    await page.waitForTimeout(1500);
    const body = await page.locator('body').innerText().catch(() => '');
    const isThinking = /orchestrating|thinking|düşünüyor|dusunuyor/i.test(body);
    const bitti = body.includes('Was this task successful?');
    if (body.length > lastLen) {
      sawGrowth = true;
      lastLen = body.length;
      stableTicks = 0;
    } else if (!isThinking) {
      stableTicks += 1;
    } else {
      stableTicks = 0;
    }
    if (sawGrowth && stableTicks >= 4) {
      await snapshot(page, '09-cevap-alindi', `growth=${body.length - baseline} chars`);
      finish(0, 'basarili', `Uçtan uca çalıştı; gövde ${body.length - baseline} karakter büyüdü.`);
    }
    if (bitti && body.length > baseline + 40) {
      sawGrowth = true;
      await snapshot(page, '09-cevap-alindi-bitti-isareti', `growth=${body.length - baseline} chars`);
      finish(0, 'basarili', "Uçtan uca çalıştı; 'Was this task successful?' işareti görüldü.");
    }
  }
  await snapshot(page, '09-cevap-boyutu-sabit', `sawGrowth=${sawGrowth}, growth=${lastLen - baseline}`);
  finish(5, 'cevap-algilamadi', `Gönderildi ama ${ANSWER_TIMEOUT}ms içinde gövde belirgin şekilde büyümedi (sawGrowth=${sawGrowth}).`);
}

main().catch((e) => {
  try {
    fs.mkdirSync(OUT_DIR, { recursive: true });
    report.exitCode = 1;
    report.verdict = 'tanilama-hata';
    report.note = `Beklenmeyen hata: ${e && e.message ? e.message : String(e)}`;
    report.finishedAt = new Date().toISOString();
    fs.writeFileSync(path.join(OUT_DIR, 'report.json'), JSON.stringify(report, null, 2), 'utf8');
  } catch (_) { /* rapor yazılamazsa sessiz */ }
  log(`Beklenmeyen hata: ${e && e.message ? e.message : e}`);
  process.exit(1);
});
