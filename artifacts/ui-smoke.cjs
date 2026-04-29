const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  const response = await page.goto('http://127.0.0.1:8017/', { waitUntil: 'networkidle' });
  const title = await page.locator('h1').innerText();
  const hasTune = await page.locator('#proposalsTable').count();
  const hasMetrics = await page.locator('#metricsGrid').count();
  await page.screenshot({ path: 'artifacts/ui-smoke.png', fullPage: true });
  await browser.close();
  if (!response || !response.ok()) throw new Error('page response failed');
  if (!title.includes('Mutation Lab')) throw new Error('missing hero title: ' + title);
  if (hasTune !== 1 || hasMetrics !== 1) throw new Error('missing required panels');
  if (errors.length) throw new Error(errors.join('\n'));
  console.log(JSON.stringify({ ok: true, title, screenshot: 'artifacts/ui-smoke.png' }));
})();
