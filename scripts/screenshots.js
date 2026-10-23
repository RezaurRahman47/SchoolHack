// Regenerate the README screenshots in docs/images from website/index.html.
//
// Usage:  npm i --no-save playwright && npx playwright install chromium
//         node scripts/screenshots.js
//
// Archify views are opened with deep links: #archify/<tech|biz>/<flow>/<step>/[sim]/<de|en>.
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const PAGE = 'file:///' + path.join(ROOT, 'website', 'index.html').replace(/\\/g, '/');
const OUT = path.join(ROOT, 'docs', 'images');

const SHOTS = [
  // [file, hash, wait ms, viewport width]
  ['archify-tech.png', '#archify/tech/test/2/en', 1800, 1280],
  ['archify-biz.png', '#archify/biz/teacher/1/en', 1800, 1280],
  ['archify-sim-tech.png', '#archify/tech/test/sim/en', 9500, 1280],
  ['archify-sim-biz.png', '#archify/biz/student/sim/en', 11000, 1280],
  ['archify-mobile.png', '#archify/biz/student/3/en', 1800, 390],
  ['login.png', '#en', 800, 1280],
];

(async () => {
  const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
  for (const [file, hash, wait, width] of SHOTS) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: width < 600 ? 2 : 1, locale: 'en-GB' });
    await page.addInitScript(() => localStorage.setItem('sh_lang', '"en"'));
    await page.goto(PAGE + hash);
    await page.waitForTimeout(wait);
    await page.addStyleTag({ content: '.top { position: static !important; }' });  // sticky header would cover the crop
    await page.locator('#app').screenshot({ path: path.join(OUT, file) });
    console.log('wrote', file);
    await page.close();
  }
  await browser.close();
})();
