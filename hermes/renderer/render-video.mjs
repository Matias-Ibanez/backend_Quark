import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';

const runtime = path.dirname(fileURLToPath(import.meta.url));

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
  const [sourceArg, outputArg, widthArg, heightArg, secondsArg, frameArg] = args;
  if (args.length < 5 || args.length > 6) throw new Error('Usage: render-video.mjs Video.tsx output.mp4 WIDTH HEIGHT SECONDS; or output.png WIDTH HEIGHT SECONDS FRAME');
  const concurrency = Number(process.env.QUARK_REMOTION_CONCURRENCY || 2);
  const config = dimensions(Number(widthArg), Number(heightArg), Number(secondsArg), concurrency);
  const source = await workspacePath(sourceArg);
  if (!/\.(?:tsx|jsx)$/.test(source)) throw new Error('Export a default React component in a .tsx or .jsx file.');
  const output = path.resolve(outputArg);
  await workspacePath(path.dirname(output));
  const still = output.endsWith('.png');
  const frame = Number(frameArg);
  if (still ? (!Number.isInteger(frame) || frame < 0 || frame >= config.durationInFrames) : (!output.endsWith('.mp4') || frameArg !== undefined)) {
    throw new Error('MP4 takes no frame; PNG requires a frame within the composition.');
  }
  const unlock = await acquireLock();
  let scratch;
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
    const composition = await selectComposition({serveUrl, id: 'QuarkVideo', chromiumOptions});
    const staged = path.join(scratch, still ? 'result.png' : 'result.mp4');
    if (still) {
      await renderStill({serveUrl, composition, output: staged, frame, imageFormat: 'png', chromiumOptions});
    } else {
      await renderMedia({serveUrl, composition, outputLocation: staged, codec: 'h264',
        pixelFormat: 'yuv420p', concurrency, crf: 20, chromiumOptions});
    }
    await fs.rename(staged, output);
    console.log(JSON.stringify({ok: true, ...config, concurrency, still, bytes: (await fs.stat(output)).size,
      elapsedSeconds: Math.round((performance.now() - started) / 10) / 100}));
  } finally {
    if (scratch) await fs.rm(scratch, {recursive: true, force: true});
    await unlock();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  render(process.argv.slice(2)).catch(error => {console.error(error.message); process.exitCode = 1;});
}
