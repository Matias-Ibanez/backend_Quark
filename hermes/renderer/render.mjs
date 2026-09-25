import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright-core';

const [sourceArg, outputArg, widthArg = '1080', heightArg = '1350'] = process.argv.slice(2);
const workspace = '/workspace/hermes';

function usage(message) {
  console.error(message);
  console.error('Usage: node /opt/quark-renderer/render.mjs SOURCE.html OUTPUT.png [width height]');
  process.exit(2);
}

if (!sourceArg || !outputArg) usage('Source and output paths are required.');
const source = path.resolve(sourceArg);
const output = path.resolve(outputArg);
const width = Number(widthArg);
const height = Number(heightArg);
if (!Number.isInteger(width) || !Number.isInteger(height) || width < 320 || height < 320 || width > 2160 || height > 2160) {
  usage('Width and height must be integers between 320 and 2160.');
}
if ((!source.endsWith('.html') && !source.endsWith('.svg')) || !output.endsWith('.png')) usage('Expected an HTML or SVG source and PNG output.');
if (!fs.existsSync(source)) usage('HTML source does not exist.');
const root = fs.realpathSync(workspace);
const resolvedSource = fs.realpathSync(source);
const outputParent = fs.realpathSync(path.dirname(output));
for (const file of [resolvedSource, outputParent]) {
  if (file !== root && !file.startsWith(root + path.sep)) usage('Source and output must be inside /workspace/hermes.');
}

const browser = await chromium.launch({
  executablePath: process.env.QUARK_CHROMIUM_PATH || '/usr/bin/chromium',
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--allow-file-access-from-files'],
});

try {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  const blocked = [];
  await page.route('**/*', async route => {
    const url = route.request().url();
    if (/^https?:/i.test(url)) {
      blocked.push(url);
      await route.abort();
    } else {
      await route.continue();
    }
  });
  await page.goto(pathToFileURL(resolvedSource).href, { waitUntil: 'load', timeout: 30000 });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...(document.images || [])].map(image => image.complete ? undefined : new Promise(resolve => {
      image.addEventListener('load', resolve, { once: true });
      image.addEventListener('error', resolve, { once: true });
    })));
  });
  const issues = await page.evaluate(({ width, height }) => {
    const problems = [];
    const body = (document.body || document.documentElement).getBoundingClientRect();
    if (Math.abs(body.width - width) > 1 || Math.abs(body.height - height) > 1) {
      problems.push(`Canvas size mismatch: HTML ${Math.round(body.width)}x${Math.round(body.height)}, requested ${width}x${height}`);
    }
    for (const image of document.images || []) {
      if (!image.naturalWidth || !image.naturalHeight) problems.push(`Missing image: ${image.getAttribute('src')}`);
    }
    for (const element of document.querySelectorAll('[data-check]')) {
      const name = element.getAttribute('data-check') || element.tagName.toLowerCase();
      const rect = element.getBoundingClientRect();
      if (rect.left < -1 || rect.top < -1 || rect.right > width + 1 || rect.bottom > height + 1) {
        problems.push(`Out of canvas: ${name}`);
      }
      const style = getComputedStyle(element);
      const clipsX = ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX);
      const clipsY = ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY);
      if ((clipsX && element.scrollWidth > element.clientWidth + 2) ||
          (clipsY && element.scrollHeight > element.clientHeight + 2)) {
        problems.push(`Text or content clipped: ${name}`);
      }
    }
    return problems;
  }, { width, height });
  issues.push(...blocked.map(url => `Remote request blocked: ${url}`));
  if (issues.length) {
    console.error(JSON.stringify({ ok: false, issues }, null, 2));
    process.exitCode = 1;
  } else {
    await page.screenshot({ path: output, type: 'png', animations: 'disabled' });
    console.log(JSON.stringify({ ok: true, width, height, bytes: fs.statSync(output).size }));
  }
  await page.close();
} finally {
  await browser.close();
}
