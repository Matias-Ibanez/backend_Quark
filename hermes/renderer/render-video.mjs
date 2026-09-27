import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';

const runtime = path.dirname(fileURLToPath(import.meta.url));
const execute = promisify(execFile);

export function reviewFrames(duration, supplied) {
  const frames = supplied === undefined ? [.08,.25,.42,.58,.75,.92].map(t => Math.floor(t * duration)) : supplied.split(',').map(Number);
  if (frames.length < 4 || frames.length > 6 || new Set(frames).size !== frames.length || frames.some(f => !Number.isInteger(f) || f < 0 || f >= duration)) {
    throw new Error('Preview requires 4–6 distinct frames inside the timeline.');
  }
  return frames;
}

// A component is enough: the wrapper owns the agreed canvas, duration and FPS.
export function dimensions(width, height, seconds, concurrency) {
  for (const value of [width, height]) {
    if (!Number.isInteger(value) || value < 320 || value > 2160 || value % 2) {
      throw new Error('Canvas dimensions must be even integers between 320 and 2160.');
    }
  }
  if (!Number.isInteger(seconds) || seconds < 5 || seconds > 180) throw new Error('Duration must be 5–180 whole seconds.');
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 4) throw new Error('Concurrency must be 1–4.');
  return {width, height, durationInFrames: seconds * 30, fps: 30};
}

async function workspacePath(value) {
  const root = await fs.realpath('/workspace/hermes');
  const resolved = await fs.realpath(value);
  if (!resolved.startsWith(root + path.sep)) throw new Error('Files must be inside /workspace/hermes.');
  return resolved;
}

async function acquireLock() {
  const file = path.join(os.tmpdir(), 'quark-remotion.lock');
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const handle = await fs.open(file, 'wx');
      await handle.writeFile(String(process.pid));
      await handle.close();
      return () => fs.unlink(file);
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      const pid = Number(await fs.readFile(file, 'utf8'));
      try { process.kill(pid, 0); }
      catch (check) {
        if (check.code === 'ESRCH') { await fs.unlink(file); continue; }
        throw check;
      }
      throw new Error('Another Remotion render is running. Wait until it finishes before retrying.');
    }
  }
  throw new Error('Could not acquire render lock.');
}

export async function render(args) {
  const preview = args[0] === '--preview';
  if (preview) args = args.slice(1);
  const [sourceArg, outputArg, widthArg, heightArg, secondsArg, frameArg] = args;
  if (args.length < 5 || args.length > 6) throw new Error('Usage: render-video.mjs Video.tsx output.mp4 WIDTH HEIGHT SECONDS; or output.png WIDTH HEIGHT SECONDS FRAME');
  const concurrency = Number(process.env.QUARK_REMOTION_CONCURRENCY || 2);
  const config = dimensions(Number(widthArg), Number(heightArg), Number(secondsArg), concurrency);
  const source = await workspacePath(sourceArg);
  if (!/\.(?:tsx|jsx)$/.test(source)) throw new Error('Export a default React component in a .tsx or .jsx file.');
  const output = path.resolve(outputArg);
  await workspacePath(path.dirname(output));
  const still = output.endsWith('.png');
  const frame = Number(frameArg), frames = preview ? reviewFrames(config.durationInFrames, frameArg) : null;
  if (preview ? !still : still ? (!Number.isInteger(frame) || frame < 0 || frame >= config.durationInFrames) : (!output.endsWith('.mp4') || frameArg !== undefined)) {
    throw new Error('MP4 takes no frame; PNG requires a frame within the composition.');
  }
  const unlock = await acquireLock();
  let scratch;
  let browser;
  const started = performance.now();
  try {
    scratch = await fs.mkdtemp(path.join(path.dirname(source), '.remotion-'));
    const entry = path.join(scratch, 'index.tsx');
    await fs.writeFile(entry, `import React from 'react';
import {Composition, registerRoot} from 'remotion';
import Video from ${JSON.stringify(source)};
registerRoot(() => <Composition id="QuarkVideo" component={Video} width={${config.width}} height={${config.height}} fps={30} durationInFrames={${config.durationInFrames}} />);
`);
    // Dependencies and Chrome are installed once in the image, never per conversation.
    process.chdir(runtime);
    const serveUrl = await bundle({
      entryPoint: entry,
      rootDir: runtime,
      enableCaching: false,
      outDir: path.join(scratch, 'bundle'),
      publicDir: path.join(path.dirname(source), 'public'),
      webpackOverride: (config) => ({...config, cache: false, resolve: {...config.resolve,
        modules: [path.join(runtime, 'node_modules'), ...(config.resolve?.modules || [])],
      }}),
    });
    const chromiumOptions = {enableMultiProcessOnLinux: true, gl: 'swangle'};
    browser = await openBrowser('chrome', {chromiumOptions});
    const composition = await selectComposition({serveUrl, id: 'QuarkVideo', chromiumOptions, puppeteerInstance: browser});
    const staged = path.join(scratch, still ? 'result.png' : 'result.mp4');
    if (preview) {
      const scale = Math.min(1, 540 / config.width), images = [];
      for (const sample of frames) {
        const image = path.join(scratch, `frame-${sample}.png`);
        await renderStill({serveUrl, composition, output: image, frame: sample, scale, imageFormat: 'png', chromiumOptions, puppeteerInstance: browser});
        images.push(image);
      }
      // Compose one labeled sheet locally, keeping layout/duration at the confirmed canvas.
      await execute('/opt/hermes/.venv/bin/python', ['-c', `
from PIL import Image, ImageDraw, ImageFont
import sys,json
images=[Image.open(p).convert('RGB') for p in sys.argv[3:]]
frames=json.loads(sys.argv[2]); w,h=images[0].size
sheet=Image.new('RGB',(w*3,(h+32)*2),'#202020'); draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
for i,img in enumerate(images):
 x=(i%3)*w; y=(i//3)*(h+32)
 sheet.paste(img,(x,y)); draw.text((x+8,y+h+5),f'{i+1} | {frames[i]/30:.2f}s',font=font,fill='white')
sheet.save(sys.argv[1])
`, staged, JSON.stringify(frames), ...images]);
    } else if (still) {
      await renderStill({serveUrl, composition, output: staged, frame, imageFormat: 'png', chromiumOptions, puppeteerInstance: browser});
    } else {
      await renderMedia({serveUrl, composition, outputLocation: staged, codec: 'h264',
        pixelFormat: 'yuv420p', concurrency, crf: 20, chromiumOptions, puppeteerInstance: browser});
    }
    await fs.rename(staged, output);
    const result = {ok: true, ...config, concurrency, still, preview, frames, bytes: (await fs.stat(output)).size,
      elapsedSeconds: Math.round((performance.now() - started) / 10) / 100};
    console.log(JSON.stringify(result));
    return result;
  } finally {
    if (browser) await browser.close({silent:true});
    if (scratch) await fs.rm(scratch, {recursive: true, force: true});
    await unlock();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  render(process.argv.slice(2)).catch(error => {console.error(error.message); process.exitCode = 1;});
}
