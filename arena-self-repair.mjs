#!/usr/bin/env node
/** Send a sanitized Actions failure prompt to Arena and emit its proposed patch. */

import fs from 'node:fs';
import {
  askArenaAgent,
  buildCleanArenaCookie,
  sanitizeCookieJsonText,
} from './arena-ask.mjs';

const promptPath = process.env.ARENA_PROMPT_FILE;
const cookieText = process.env.ARENA_COOKIES_JSON;
if (!promptPath || !cookieText) {
  console.error('ARENA_PROMPT_FILE and ARENA_COOKIES_JSON are required.');
  process.exit(2);
}

let cookies;
try {
  cookies = JSON.parse(sanitizeCookieJsonText(cookieText));
} catch (error) {
  console.error(`Arena cookie JSON could not be parsed: ${error.message}`);
  process.exit(2);
}

try {
  const { answer } = await askArenaAgent({
    cleanAuthCookie: buildCleanArenaCookie(cookies),
    promptText: fs.readFileSync(promptPath, 'utf8'),
    screenshotPath: '',
    saveUpdatedCookiesPath: undefined,
  });
  if (!answer.trim()) {
    throw new Error('Arena returned an empty answer.');
  }
  process.stdout.write(answer);
} catch (error) {
  console.error(`Arena self-repair request failed: ${error.message}`);
  process.exit(1);
}
