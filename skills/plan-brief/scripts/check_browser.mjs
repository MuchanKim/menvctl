#!/usr/bin/env node
// Optional browser QA. Uses an existing Playwright installation; installs nothing.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { mkdir } from 'node:fs/promises';

const [file, screenshots] = process.argv.slice(2);
if (!file) { console.error('Usage: node check_browser.mjs report.html [screenshots-dir]'); process.exit(2); }
let chromium;
try {
  ({ chromium } = await import(process.env.REVIEW_BRIEF_PLAYWRIGHT || 'playwright'));
} catch {
  console.error('Playwright 미설치: 기존 설치 경로를 REVIEW_BRIEF_PLAYWRIGHT로 지정하거나 브라우저 검증을 미실행으로 기록하세요.');
  process.exit(2);
}
let browser;
try {
  browser = await chromium.launch({ headless: true, ...(process.env.REVIEW_BRIEF_BROWSER ? { executablePath: process.env.REVIEW_BRIEF_BROWSER } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.route(/^https?:/, (route) => { errors.push(`외부 요청: ${route.request().url()}`); return route.abort(); });
  await page.goto(pathToFileURL(resolve(file)).href);
  await page.waitForFunction(() => window.reviewBriefValidation?.ready, null, { timeout: 10000 });
  const result = await page.evaluate(() => ({
    errors: window.reviewBriefValidation.errors,
    unresolved: document.querySelectorAll('.diff-embed').length,
    draft: JSON.parse(document.querySelector('#diff-data').textContent).draft,
    tabs: Array.from(document.querySelectorAll('.tab-page')).map((p) => p.dataset.tab),
  }));
  errors.push(...result.errors);
  if (result.draft) errors.push('초안 모드 출력');
  if (result.unresolved) errors.push(`미해결 diff-embed: ${result.unresolved}`);
  if (screenshots) await mkdir(resolve(screenshots), { recursive: true });
  for (const tab of result.tabs) {
    await page.evaluate((tab) => { location.hash = tab; }, tab);
    await page.waitForFunction((tab) => document.querySelector('.tab-page.active')?.dataset.tab === tab, tab);
    if (screenshots && (tab === 'overview' || tab === 'c1')) {
      await page.screenshot({ path: resolve(screenshots, `${tab}.png`), fullPage: true });
    }
  }
  if (errors.length) throw new Error(errors.join('\n'));
  console.log(`브라우저 검증 통과: ${result.tabs.length}개 탭, diff 연결/console/외부 요청 확인`);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally { await browser?.close(); }
