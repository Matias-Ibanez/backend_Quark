// Execute inside the Hermes image: node /opt/quark-tests/remotion-smoke.mjs.
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {render} from '/opt/quark-renderer/render-video.mjs';

const folder = await fs.mkdtemp('/workspace/hermes/remotion-runtime-tests/smoke-');
await fs.mkdir(path.join(folder, 'public'));
await fs.writeFile(path.join(folder, 'public/logo.svg'), '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><circle cx="40" cy="40" r="38" fill="#c75139"/></svg>');
execFileSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5', '-y', path.join(folder, 'public/voice.wav')]);
const source = path.join(folder, 'Video.tsx');
const component = (color) => `import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, interpolate} from 'remotion';
import {Audio} from '@remotion/media';
export default function Video() {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{background:'${color}',padding:32,fontFamily:'DejaVu Sans',color:'#f6eddf'}}>
    <Audio src={staticFile('voice.wav')} />
    <Img src={staticFile('logo.svg')} style={{width:50,height:50}} />
    <div style={{marginTop:30,fontSize:38,fontWeight:700,opacity:interpolate(f,[0,20],[0,1],{extrapolateRight:'clamp'})}}>Tu pausa,<br/>tu café.</div>
    <div style={{marginTop:24,fontSize:18}}>Una idea. Una animación.</div>
  </AbsoluteFill>;
}`;
const output = path.join(folder, 'final.mp4');
await fs.writeFile(source, component('#263f32'));
await render([source, output, '320', '320', '5']);
let info = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,duration', '-of', 'json', output]));
assert(Math.abs(Number(info.format.duration) - 5) < 0.1, 'AAC padding must stay bounded.');
assert(info.streams.some(s => s.codec_type === 'video' && s.width === 320 && s.height === 320 && Number(s.duration) === 5));
assert(info.streams.some(s => s.codec_type === 'audio'));
const initial = await fs.readFile(output);
await fs.writeFile(source, component('#542334'));
await render([source, output, '320', '320', '5']);
assert(!(await fs.readFile(output)).equals(initial), 'A source revision must replace the output.');
await render([source, path.join(folder, 'review.png'), '320', '320', '5', '75']);
const latest = await fs.readFile(output);
await fs.writeFile(source, 'export default function Video() { throw new Error("Broken revision"); }');
await assert.rejects(render([source, output, '320', '320', '5']), /Broken revision/);
assert((await fs.readFile(output)).equals(latest), 'A failed revision must preserve the previous complete output.');
await fs.writeFile(path.join(folder, 'outside.tsx'), component('#000000'));
await fs.symlink('/etc/passwd', path.join(folder, 'escape.tsx'));
await assert.rejects(render([path.join(folder, 'escape.tsx'), output, '320', '320', '5']), /inside \/workspace\/hermes/);
console.log(JSON.stringify({ok:true, folder, cases:['canvas-duration', 'local-image', 'audio', 'revision', 'frame-preview', 'failed-revision-preserves-output', 'symlink-boundary']}));
