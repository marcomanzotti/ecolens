'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const BASE = 'https://ecolens-earth.vercel.app';
const W = 1920, H = 1080;
const marks = {};
let t0;
const mark = (k) => { marks[k] = (Date.now() - t0) / 1000; console.log('mark', k, marks[k].toFixed(2)); };
const wait = (p, ms) => p.waitForTimeout(ms);

async function overlays(page) {
  await page.evaluate(() => {
    if (document.getElementById('demo-cap')) return;
    const heading = getComputedStyle(document.querySelector('h1') || document.body).fontFamily;
    const body = getComputedStyle(document.body).fontFamily;
    const css = document.createElement('style');
    css.textContent = `
      #demo-cap{position:fixed;left:50%;bottom:56px;transform:translateX(-50%);z-index:999998;max-width:1500px;
        padding:18px 34px;border-radius:14px;background:rgba(7,23,63,.92);border:1px solid rgba(234,254,7,.55);
        color:#fff;font:600 34px/1.25 ${body};letter-spacing:.2px;text-align:center;opacity:0;transition:opacity .35s;pointer-events:none;
        box-shadow:0 10px 40px rgba(0,0,0,.45)}
      #demo-card{position:fixed;inset:0;z-index:999999;display:flex;flex-direction:column;justify-content:center;padding:0 160px;
        background:linear-gradient(135deg,#1B45B4 0%,#07173F 70%);color:#fff;opacity:0;transition:opacity .5s;pointer-events:none}
      #demo-card .k{font:800 26px/1.2 ${heading};letter-spacing:3px;text-transform:uppercase;color:#EAFE07;margin-bottom:26px}
      #demo-card h1{font:900 168px/0.95 ${heading};margin:0 0 30px}
      #demo-card .t{font:700 50px/1.2 ${heading};margin-bottom:56px} #demo-card .t span{color:#EAFE07}
      #demo-card .m{font:500 34px/1.5 ${body};color:#dfe6ff} #demo-card .m b{color:#fff}
      #demo-card .u{font:800 60px/1.2 ${heading};margin-bottom:18px}
      #demo-card .s{font:400 24px/1.4 ${body};color:#b9c4e6;margin-top:48px}
      #demo-cursor{position:fixed;z-index:999997;pointer-events:none;width:30px;height:30px;transition:left .1s,top .1s;filter:drop-shadow(1px 1px 2px rgba(0,0,0,.4))}`;
    document.head.appendChild(css);
    const cap = document.createElement('div'); cap.id = 'demo-cap'; document.body.appendChild(cap);
    const card = document.createElement('div'); card.id = 'demo-card'; document.body.appendChild(card);
    const cur = document.createElement('div'); cur.id = 'demo-cursor';
    cur.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M5 3L19 12L12 13L9 20L5 3Z" fill="white" stroke="black" stroke-width="1.5" stroke-linejoin="round"/></svg>';
    cur.style.left = '-50px'; cur.style.top = '-50px'; document.body.appendChild(cur);
    document.addEventListener('mousemove', (e) => { cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px'; });
  });
}
const caption = (p, text) => p.evaluate((t) => {
  const c = document.getElementById('demo-cap');
  if (t) { c.textContent = t; c.style.opacity = '1'; } else c.style.opacity = '0';
}, text);
const card = (p, html) => p.evaluate((h) => {
  const c = document.getElementById('demo-card');
  if (h) { c.innerHTML = h; c.style.transition = 'none'; c.style.opacity = '1'; }
  else { c.style.transition = 'opacity .5s'; c.style.opacity = '0'; }
}, html);

async function click(page, locator, label) {
  const el = locator.first();
  if (!(await el.isVisible().catch(() => false))) throw new Error(`not visible: ${label}`);
  const b = await el.boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 12 });
  await wait(page, 300);
  await el.click();
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, recordVideo: { dir: 'raw', size: { width: W, height: H } } });
  const page = await ctx.newPage();
  t0 = Date.now();
  try {
    // A + B: title card over the home page, then the time-lapse
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    await overlays(page);
    await card(page, `<div class="k">NASA Space Apps Challenge 2026</div><h1>EcoLens</h1>
      <div class="t">The tool finds the trends. <span>You investigate them.</span></div>
      <div class="m">Team <b>project_nasa</b> · Marco Manzotti, Dario Bottari, Miles McCrudden</div>`);
    await page.waitForLoadState('networkidle');
    await page.mouse.move(W - 40, H / 2);
    mark('titleStart'); await wait(page, 3200);
    await card(page, null); mark('homeStart');
    await caption(page, 'Challenge: Be An Earth System Trend Detective!');
    const yearIs = (y) => page.evaluate((y) => new RegExp(`\\b${y}\\b\\s*\\n?\\s*Significant`).test(document.body.innerText), y);
    for (let i = 0; i < 200 && !(await yearIs('2012')); i++) await wait(page, 150);
    await caption(page, 'EcoLens tests NASA data for trends, year by year');
    for (let i = 0; i < 200 && !(await yearIs('2025')); i++) await wait(page, 150);
    mark('home2025'); await wait(page, 2500); mark('homeEnd');

    // C: guided tour (Delhi)
    await page.goto(BASE + '/tour', { waitUntil: 'networkidle' });
    await overlays(page);
    await page.getByRole('button', { name: 'Pause the tour' }).click();
    await page.mouse.move(W - 40, H / 2);
    const next = page.getByRole('button', { name: 'Next step' });
    const beats = [
      ['place', 'Pick any place on Earth: 34,216 cities, coordinates or a click'],
      ['evidence', '31 NASA POWER variables, 1981–2025 · two tests must agree'],
      ['verdict', 'Delhi: sunlight reaching the ground −0.61 MJ/m²/day per decade · p < 0.001'],
      ['twin', 'A short way off, the trend flips: one cell rising, one falling, 455 km apart'],
    ];
    for (const [k, text] of beats) {
      await caption(page, null);
      await click(page, next, 'Next step');
      await page.mouse.move(W - 40, H / 2, { steps: 6 });
      await wait(page, 1200); await caption(page, text);
      mark(k); await wait(page, 4800);
    }
    mark('tourEnd');

    // D: 2050 projections
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    await overlays(page);
    await wait(page, 1500);
    mark('futureStart');
    await click(page, page.getByText('2050', { exact: true }).last(), '2050 tab');
    await wait(page, 1800);
    await caption(page, 'CMIP6 climate models, 2041–2060: scenarios, not forecasts');
    mark('future'); await wait(page, 4200);

    // E: end card
    await caption(page, null);
    await card(page, `<h1 style="font-size:130px">EcoLens</h1>
      <div class="t">The tool finds the trends. <span>You investigate them.</span></div>
      <div class="u">ecolens-earth.vercel.app</div>
      <div class="m">Open source: github.com/marcomanzotti/ecolens · Team project_nasa</div>
      <div class="s">Data: NASA POWER, NASA GISS GISTEMP v4, MODIS via NASA GIBS, CMIP6 (WCRP). Not endorsed by NASA.<br>Built with the help of an AI coding assistant; the app itself uses no AI.</div>`);
    mark('end'); await wait(page, 3500); mark('endEnd');
  } catch (e) {
    console.error('DEMO ERROR:', e.message);
    process.exitCode = 1;
  } finally {
    await ctx.close();
    const src = await page.video().path();
    fs.copyFileSync(src, 'raw.webm');
    fs.writeFileSync('marks.json', JSON.stringify(marks, null, 1));
    console.log('saved raw.webm');
    await browser.close();
  }
})();
