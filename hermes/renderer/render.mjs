import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { randomUUID } from 'node:crypto';
import { chromium } from 'playwright-core';

const workspace = '/workspace/hermes';

function validate(job) {
  const {source: sourceArg, output: outputArg, width = 1080, height = 1350} = job;
  if (typeof sourceArg !== 'string' || typeof outputArg !== 'string') throw new Error('Source and output paths are required.');
  const source = path.resolve(sourceArg), output = path.resolve(outputArg);
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 320 || height < 320 || width > 2160 || height > 2160) {
    throw new Error('Width and height must be integers between 320 and 2160.');
  }
  if ((!source.endsWith('.html') && !source.endsWith('.svg')) || !output.endsWith('.png')) throw new Error('Expected HTML or SVG source and PNG output.');
  const root = fs.realpathSync(workspace), resolvedSource = fs.realpathSync(source), parent = fs.realpathSync(path.dirname(output));
  for (const file of [resolvedSource, parent]) {
    if (file !== root && !file.startsWith(root + path.sep)) throw new Error('Source and output must be inside /workspace/hermes.');
  }
  return {source: resolvedSource, output: path.join(parent, path.basename(output)), width, height};
}

export async function render(jobs) {
  if (!Array.isArray(jobs) || jobs.length < 1 || jobs.length > 10) throw new Error('Expected 1–10 render jobs.');
  const checked = jobs.map(validate); // Reject the entire manifest before touching outputs.
  if (new Set(checked.map(job => job.output)).size !== checked.length) throw new Error('Output paths must be distinct.');
  const started = performance.now();
  const results = [];
  const browser = await chromium.launch({
    executablePath: process.env.QUARK_CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--allow-file-access-from-files'],
  });

  try {
    for (const {source, output, width, height} of checked) {
      const jobStarted = performance.now();
      const staged = path.join(path.dirname(output), `.render-${randomUUID()}.png`);
      const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
      try {
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
        await page.goto(pathToFileURL(source).href, { waitUntil: 'load', timeout: 30000 });
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
          results.push({ok: false, issues, width, height});
        } else {
          await page.screenshot({ path: staged, type: 'png', animations: 'disabled' });
          fs.renameSync(staged, output);
          results.push({ok: true, width, height, bytes: fs.statSync(output).size});
        }
      } finally {
        fs.rmSync(staged, {force: true});
        await page.close();
      }
      results.at(-1).renderSeconds = Number(((performance.now() - jobStarted) / 1000).toFixed(3));
    }
  } finally {
    await browser.close();
  }

  return {ok: results.every(result => result.ok), results, totalSeconds: Number(((performance.now() - started) / 1000).toFixed(3))};
}

async function main(args) {
  let jobs;
  if (args[0] === '--batch') {
    if (args.length !== 2) throw new Error('Usage: render.mjs --batch manifest.json');
    const manifest = fs.realpathSync(path.resolve(args[1])), root = fs.realpathSync(workspace);
    if (!manifest.startsWith(root + path.sep) || fs.statSync(manifest).size > 32768) throw new Error('Manifest must be inside /workspace/hermes and at most 32KB.');
    jobs = JSON.parse(fs.readFileSync(manifest, 'utf8'));
  } else {
    if (args.length < 2 || args.length > 4) throw new Error('Usage: render.mjs SOURCE.svg OUTPUT.png [width height]');
    jobs = [{source: args[0], output: args[1], width: Number(args[2] || 1080), height: Number(args[3] || 1350)}];
  }
  const result = await render(jobs);
  // Keep the single-job CLI's original ok/width/height/bytes contract.
  console.log(JSON.stringify(jobs.length === 1 ? {...result.results[0], totalSeconds: result.totalSeconds} : result));
  if (!result.ok) process.exitCode = 1;
}
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  main(process.argv.slice(2)).catch(error => {console.error(error.message); process.exitCode = 1;});
}
