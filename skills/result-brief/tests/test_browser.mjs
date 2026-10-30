#!/usr/bin/env node
// Optional integration suite. Same environment overrides as check_browser.mjs.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
const { chromium } = await import(process.env.REVIEW_BRIEF_PLAYWRIGHT || 'playwright');
const skill = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const fixture = mkdtempSync(join(tmpdir(), 'review-brief-browser-'));
const run = (cmd, args, cwd = fixture) => execFileSync(cmd, args, { cwd, encoding: 'utf8' });
let browser;
try {
  run('git', ['init','-q']); run('git',['config','user.name','Test']); run('git',['config','user.email','test@example.invalid']);
  writeFileSync(join(fixture,'seed.txt'),'before\n'); run('git',['add','.']); run('git',['commit','-qm','fixture']);
  writeFileSync(join(fixture,'.git/info/exclude'), '/artifacts/\n');
  run('python3',['-c', 'from pathlib import Path; Path("artifacts").mkdir(); Path("a").mkdir(); Path("b").mkdir()']);
  writeFileSync(join(fixture,'seed.txt'),'after'); // no trailing LF exercises EOF rendering
  writeFileSync(join(fixture,'a/same.txt'),'first\n'); writeFileSync(join(fixture,'b/same.txt'),'second\n');
  writeFileSync(join(fixture,'binary.bin'),Buffer.from([0,255,1]));
  run('chmod',['+x','seed.txt']);
  writeFileSync(join(fixture,'artifacts/plan.json'),JSON.stringify({commits:[{message:'Fixture change',files:['seed.txt','a/same.txt','b/same.txt','binary.bin']}]}));
  const body = (embed) => `<div class="tab-page" data-tab="overview"><header class="hero"><h1>Browser fixture</h1></header>${["changes","requirements","review-focus","verification","merge-checklist"].map(id=>`<section id="${id}">Fixture evidence</section>`).join("")}<section id="intro" data-toc="Result"><h2>검증 결과</h2><div id="commit-map"></div></section></div>
<div class="tab-page" data-commit="1"><section id="focus" data-toc="Diff"><h2>핵심 변경</h2>${embed}</section></div>
<div class="tab-page" data-tab="device" data-label="수동 검증"><section id="manual"><ul class="device" id="checks"><li><label><input type="checkbox" data-check-id="fixture">Check behavior</label></li></ul><div data-progress-for="checks"></div></section></div>
<div class="tab-page" data-tab="all"><section id="all-files"><div id="file-browser"></div></section></div>`;
  const build = (name, embed) => {
    writeFileSync(join(fixture,`artifacts/${name}.html`),body(embed));
    run('python3',['-B',join(skill,'scripts/build.py'),`artifacts/${name}.html`,`artifacts/${name}-report.html`,'--plan','artifacts/plan.json']);
    return pathToFileURL(join(fixture,`artifacts/${name}-report.html`)).href;
  };
  const good = build('good','<div class="diff-embed" data-file="seed.txt" data-match="after"></div><div class="diff-embed" data-file="a/same.txt"></div>');
  const bad = build('bad','<div class="diff-embed" data-file="same.txt"></div><div class="diff-embed" data-file="seed.txt" data-match="["></div><div class="diff-embed" data-file="seed.txt" data-match="nomatch"></div><div class="diff-embed" data-file="seed.txt" data-hunks="9"></div>');
  browser = await chromium.launch({headless:true,...(process.env.REVIEW_BRIEF_BROWSER ? {executablePath:process.env.REVIEW_BRIEF_BROWSER}: {})});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors = []; page.on('pageerror',e=>errors.push(e.message));
  await page.goto(good); await page.waitForFunction(()=>window.reviewBriefValidation?.ready);
  assert.deepEqual(await page.evaluate(()=>window.reviewBriefValidation.errors),[]);
  assert.equal(await page.locator('.diff-embed').count(),0);
  for (const tab of ['overview','c1','device','all']) {
    await page.evaluate(tab=>{location.hash=tab;},tab);
    await page.waitForFunction(tab=>document.querySelector('.tab-page.active')?.dataset.tab===tab,tab);
  }
  assert.ok((await page.locator('#main').textContent()).includes('100644 → 100755'));
  assert.ok((await page.locator('#main').textContent()).includes('바이너리/비 UTF-8'));
  assert.ok((await page.locator('#main').textContent()).includes('No newline at end of file'));
  await page.locator('#theme-btn').click(); assert.ok(await page.locator('html').getAttribute('data-theme'));
  await page.locator('#wrap-btn').click(); assert.equal(await page.locator('#wrap-btn').getAttribute('aria-pressed'),'true');
  const search=page.locator('#file-browser input[type=search]'); await search.fill('binary');
  assert.equal(await page.locator('#file-browser .diff:visible').count(),1);
  await page.evaluate(()=>{location.hash='device';}); await page.locator('[data-check-id="fixture"]').check();
  await page.reload(); await page.waitForFunction(()=>window.reviewBriefValidation?.ready);
  assert.equal(await page.locator('[data-check-id="fixture"]').isChecked(),true);
  const reportPath=join(fixture,'artifacts/good-report.html');
  const before=readFileSync(reportPath,'utf8');
  writeFileSync(join(fixture,'seed.txt'),'changed after checks');
  run('python3',['-B',join(skill,'scripts/build.py'),'artifacts/good.html','artifacts/good-report.html','--plan','artifacts/plan.json']);
  assert.notEqual(readFileSync(reportPath,'utf8'),before);
  // Updated matching selector must be regenerated together with the code.
  writeFileSync(join(fixture,'artifacts/good.html'),body('<div class="diff-embed" data-file="seed.txt" data-match="changed"></div>'));
  run('python3',['-B',join(skill,'scripts/build.py'),'artifacts/good.html','artifacts/good-report.html','--plan','artifacts/plan.json']);
  await page.reload(); await page.waitForFunction(()=>window.reviewBriefValidation?.ready);
  assert.equal(await page.locator('[data-check-id="fixture"]').isChecked(),false);
  assert.deepEqual(await page.evaluate(()=>window.reviewBriefValidation.errors),[]);
  if (process.env.REVIEW_BRIEF_SCREENSHOTS) {
    run('python3',['-c','from pathlib import Path; import sys; Path(sys.argv[1]).mkdir(parents=True,exist_ok=True)',process.env.REVIEW_BRIEF_SCREENSHOTS]);
    for(const tab of ['overview','c1']) {
      await page.evaluate(tab=>{location.hash=tab;},tab);
      await page.waitForFunction(tab=>document.querySelector('.tab-page.active')?.dataset.tab===tab,tab);
      await page.screenshot({path:join(process.env.REVIEW_BRIEF_SCREENSHOTS,`${tab}.png`),fullPage:true});
    }
  }
  await page.goto(bad); await page.waitForFunction(()=>window.reviewBriefValidation?.ready);
  assert.equal((await page.evaluate(()=>window.reviewBriefValidation.errors)).length,4);
  assert.equal(await page.locator('[data-validation-error]').count(),4);
  await page.evaluate(()=>{location.hash='all';}); await page.waitForFunction(()=>document.querySelector('.tab-page.active')?.dataset.tab==='all');
  assert.deepEqual(errors,[]);
  run('node',[join(skill,'scripts/check_browser.mjs'),reportPath]);
  let rejected=false;
  try { execFileSync('node',[join(skill,'scripts/check_browser.mjs'),join(fixture,'artifacts/bad-report.html')],{stdio:'pipe'}); } catch {rejected=true;}
  assert.equal(rejected,true);
  console.log('Browser integration passed: tabs, embeds, error isolation, mode/binary/EOF, theme, wrap, search, persisted/reset checks, validator exit codes.');
} finally {
  await browser?.close(); rmSync(fixture,{recursive:true,force:true});
}
