/**
 * arena-dom.mjs — Arena.ai etkileşiminin TEK KAYNAĞI (single source of truth).
 *
 * Tüm Playwright tabanlı Arena scriptleri (arena-ask.mjs, arena-selftest.mjs,
 * arena-self-repair.mjs) seçici ve gönderim doğrulama mantığını buradan alır.
 *
 * Kanıtlanmış bulgular (handoff):
 *  - Composer <textarea> DEĞİLDİR; div.tiptap[contenteditable="true"] (ProseMirror).
 *    textarea seçicisi her zaman boşa gider.
 *  - Hydration yavaştır (30-45 sn makul); domcontentloaded + waitForSelector şart.
 *  - Terms of Use duvarı gönderimi engeller: modal açılır, mesaj composer'da kalır.
 *    Eski kod bu durumu "cevap" sanıyordu. ACCEPT_TOS=1 yokken Agree'ye BASILMAZ.
 *  - page.keyboard.press('Enter') HATA FIRLATMAZ; gönderim başarısı ancak
 *    composer boşalması VEYA URL değişimiyle doğrulanır.
 *  - Cloudflare bot doğrulamasında composer hiç render olmaz; oturum hatasıyla
 *    karıştırılmamalı (ayrı exit kodu).
 *
 * Seçici listelerinin Python karşılığı modules/arena_api.py içindeki
 * ARENA_EDITOR_FALLBACKS / ARENA_SEND_SELECTORS / ARENA_CONSENT_BUTTON_LABELS
 * sabitleridir. Ayrışma olursa tests/test_arena_selector_parity.py kırılır.
 */

// --- Birincil seçiciler -------------------------------------------------------

export const EDITOR_SELECTOR = 'div.tiptap[contenteditable="true"]';

// Sıra ÖNEMLİ: birincil (tiptap) tam timeout alır; geri kalanlar yedek.
export const EDITOR_FALLBACKS = [
  EDITOR_SELECTOR,
  'div[contenteditable="true"][role="textbox"]',
  'div[contenteditable="true"]',
  'textarea',
];

export const SEND_SELECTORS = [
  'button[aria-label="Send message"]',
  'button[aria-label="Send Message"]',
  'button[data-testid="send-button"]',
  'button[type="submit"]',
];

// Buton VARLIĞI esas sinyaldir. Metin taraması sadece raporlamadır (footer'da
// "Privacy Policy" geçer, metne güvenilmez).
export const CONSENT_BUTTON_LABELS = ['Agree', 'Kabul et', 'Accept'];

const CONSENT_TEXT_HINTS = [
  'terms of use',
  'kullanım koşulları',
  'kullanim kosullari',
  'terms and conditions',
];

const VERIFY_WINDOW_MS = 5000; // Her gönderim denemesinden sonraki doğrulama penceresi
const VERIFY_POLL_MS = 400;

// --- ToS / onay duvarı -------------------------------------------------------

/**
 * Consent/ToS butonu var mı? Buton varlığı esas sinyaldir.
 * Gövde metni taraması yalnızca raporlama amaçlıdır (footer gürültüsü nedeniyle
 * güvenilir değildir).
 * @returns {Promise<{present:boolean, label:string|null, selector:string|null, textHints:string[]}>}
 */
export async function detectConsent(page) {
  const textHints = [];
  try {
    const bodyText = (await page.locator('body').innerText().catch(() => '')) || '';
    const lower = bodyText.toLowerCase();
    for (const hint of CONSENT_TEXT_HINTS) {
      if (lower.includes(hint)) textHints.push(hint);
    }
  } catch (_) {
    /* metin alınamazsa raporlama boş kalır */
  }

  for (const label of CONSENT_BUTTON_LABELS) {
    // Rol/erişilebilir ad ile buton aranır; metin eşleşmesi hassastır.
    const candidates = [
      page.getByRole('button', { name: label, exact: false }),
      page.locator(`button:has-text("${label}")`),
    ];
    for (const cand of candidates) {
      try {
        const count = await cand.count();
        for (let i = 0; i < count; i++) {
          const el = cand.nth(i);
          if (await el.isVisible().catch(() => false)) {
            return { present: true, label, selector: null, textHints };
          }
        }
      } catch (_) {
        /* devam */
      }
    }
  }
  return { present: false, label: null, selector: null, textHints };
}

/**
 * ToS onay butonuna tıklar. YALNIZCA ACCEPT_TOS=1 iken çağrılmalıdır.
 * Fallback: odaklanılan butona Enter.
 * @returns {Promise<{clicked:boolean, method:string}>}
 */
export async function acceptConsent(page) {
  for (const label of CONSENT_BUTTON_LABELS) {
    const btn = page.getByRole('button', { name: label, exact: false });
    if ((await btn.count().catch(() => 0)) > 0 && (await btn.first().isVisible().catch(() => false))) {
      try {
        await btn.first().click({ timeout: 3000 });
        return { clicked: true, method: `click:${label}` };
      } catch (_) {
        try {
          await btn.first().focus();
          await page.keyboard.press('Enter');
          return { clicked: true, method: `enter:${label}` };
        } catch (_) {
          /* sonraki etikete geç */
        }
      }
    }
  }
  // Son çare: sayfada Enter (odak Buton'daysa çalışır).
  try {
    await page.keyboard.press('Enter');
    return { clicked: true, method: 'enter-fallback' };
  } catch (_) {
    return { clicked: false, method: 'none' };
  }
}

// --- Editör / composer -------------------------------------------------------

/**
 * Editörü bekler. Fallbackler sırayla denenir; tiptap'a (birincil) TAM timeout
 * ayrılır, sonraki fallbacklere kalan süreden dilim düşer.
 * @returns {Promise<import('playwright').Locator|null>}
 */
export async function waitForEditor(page, timeoutMs = 30000) {
  const perFallback = Math.max(3000, Math.floor(timeoutMs / EDITOR_FALLBACKS.length));
  for (let i = 0; i < EDITOR_FALLBACKS.length; i++) {
    const selector = EDITOR_FALLBACKS[i];
    const budget = i === 0 ? timeoutMs : perFallback; // tiptap tam timeout alır
    const loc = page.locator(selector).first();
    try {
      await loc.waitFor({ state: 'visible', timeout: budget });
      if (await loc.isEditable().catch(() => true)) {
        return loc;
      }
    } catch (_) {
      /* sonraki fallback */
    }
  }
  return null;
}

/**
 * Composer'ın şu anki metnini döndür. Boşsa '' döner (hata fırlatmaz).
 */
export async function composerText(page) {
  for (const selector of EDITOR_FALLBACKS) {
    const loc = page.locator(selector).first();
    if ((await loc.count().catch(() => 0)) === 0) continue;
    const txt = await loc.innerText().catch(async () => loc.inputValue().catch(() => ''));
    if (typeof txt === 'string') return txt;
  }
  return '';
}

// --- Gönderim ve DOĞRULAMA ---------------------------------------------------

async function _verifySend(page, startUrl, startLen) {
  const deadline = Date.now() + VERIFY_WINDOW_MS;
  while (Date.now() < deadline) {
    if (page.url() !== startUrl) return true; // URL değişti → gönderildi
    const remaining = await composerText(page);
    // Composer belirgin şekilde boşaldıysa gönderildi sayılır.
    if (remaining.trim().length === 0 || remaining.length < Math.max(1, startLen * 0.3)) {
      return true;
    }
    await page.waitForTimeout(VERIFY_POLL_MS);
  }
  return false;
}

/**
 * Mesajı göndermeyi dener ve DOĞRULAR. "Tıkladım" yetmez: doğrulama =
 * composer boşaldı VEYA URL değişti.
 * Sıra: Enter → Enter (tekrar) → bilinen gönder butonları.
 * Her denemeden sonra 5 sn doğrulama penceresi.
 * @returns {Promise<{clicked:boolean, verified:boolean, method:string, remainingComposerText:string}>}
 */
export async function attemptSend(page) {
  const startUrl = page.url();
  const startText = await composerText(page);
  const startLen = startText.length;

  const attempts = [
    { method: 'keyboard-enter-1', run: async () => { await page.keyboard.press('Enter'); } },
    { method: 'keyboard-enter-2', run: async () => { await page.keyboard.press('Enter'); } },
  ];
  for (const sel of SEND_SELECTORS) {
    attempts.push({
      method: `button:${sel}`,
      run: async () => {
        const btn = page.locator(sel).first();
        if ((await btn.count().catch(() => 0)) === 0) throw new Error('no-button');
        await btn.click({ timeout: 3000 }).catch(async () => {
          await btn.click({ force: true, timeout: 3000 });
        });
      },
    });
  }

  let clicked = false;
  let lastMethod = 'none';
  for (const att of attempts) {
    lastMethod = att.method;
    try {
      await att.run();
      clicked = true;
    } catch (_) {
      // Bu deneme çalışmadı (örn. buton yok); doğrulamayı yine de dene, sonra devam.
    }
    if (await _verifySend(page, startUrl, startLen)) {
      return {
        clicked: true,
        verified: true,
        method: att.method,
        remainingComposerText: await composerText(page),
      };
    }
  }
  return {
    clicked,
    verified: false,
    method: lastMethod,
    remainingComposerText: await composerText(page),
  };
}
