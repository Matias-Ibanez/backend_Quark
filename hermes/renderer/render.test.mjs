import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {test} from 'node:test';
import {render} from './render.mjs';

test('batch renders exact canvases with one browser and preserves previews on validation failure', async () => {
  const dir = fs.mkdtempSync('/workspace/hermes/static-render-tests/case-');
  try {
    const source = path.join(dir, 'source.svg'), other = path.join(dir, 'other.svg');
    const output = path.join(dir, 'final.png'), second = path.join(dir, 'second.png');
    fs.writeFileSync(source, '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><rect width="320" height="320" fill="#542334"/></svg>');
    fs.writeFileSync(other, '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><rect width="320" height="320" fill="#F6EDDF"/></svg>');
    const result = await render([{source, output, width:320, height:320}, {source:other, output:second, width:320, height:320}]);
    assert.equal(result.ok, true);
    assert.equal(result.results.length, 2);
    assert.ok(result.totalSeconds > 0);
    assert.ok(fs.statSync(output).size > 100);
    assert.ok(fs.statSync(second).size > 100);
    assert.notDeepEqual(fs.readFileSync(output), fs.readFileSync(second));
    const before = fs.readFileSync(output);
    fs.writeFileSync(source, '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="320"/>');
    const rejected = await render([{source, output, width:320, height:320}]);
    assert.equal(rejected.ok, false);
    assert.match(rejected.results[0].issues[0], /Canvas size mismatch/);
    assert.deepEqual(fs.readFileSync(output), before);
    fs.writeFileSync(source, '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><text x="10" y="350" font-size="30">CTA recortado</text></svg>');
    const clipped = await render([{source, output, width:320, height:320}]);
    assert.equal(clipped.ok, false);
    assert.match(clipped.results[0].issues.join(' '), /Out of canvas: CTA recortado/);
    assert.deepEqual(fs.readFileSync(output), before);
    fs.writeFileSync(source, '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><text x="20" y="314" font-size="20">CTA al borde</text></svg>');
    const unsafe = await render([{source, output, width:320, height:320}]);
    assert.equal(unsafe.ok, false);
    assert.match(unsafe.results[0].issues.join(' '), /3% safe margin: CTA al borde/);
    assert.deepEqual(fs.readFileSync(output), before);
    assert.equal(fs.readdirSync(dir).some(name => name.startsWith('.render-')), false);
  } finally { fs.rmSync(dir, {recursive:true, force:true}); }
});

test('whole batch is validated before writing and paths cannot escape workspace', async () => {
  const dir = fs.mkdtempSync('/workspace/hermes/static-render-tests/case-');
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'quark-static-outside-'));
  try {
    const source = path.join(dir, 'source.svg'), output = path.join(dir, 'final.png');
    fs.writeFileSync(source, '<svg/>');
    const job = {source, output, width:320, height:320};
    await assert.rejects(render([]), /1–10/);
    await assert.rejects(render(Array(11).fill(job)), /1–10/);
    await assert.rejects(render([job, {...job, output:path.join(dir,'other.png'), width:0}]), /320 and 2160/);
    await assert.rejects(render([job, job]), /distinct/);
    await assert.rejects(render([{...job, output:path.join(outside,'final.png')}]), /inside/);
    fs.writeFileSync(path.join(outside,'source.svg'), '<svg/>');
    fs.symlinkSync(path.join(outside,'source.svg'), path.join(dir,'linked.svg'));
    await assert.rejects(render([{...job, source:path.join(dir,'linked.svg')}]), /inside/);
    assert.equal(fs.existsSync(output), false);
  } finally {
    fs.rmSync(dir, {recursive:true, force:true});
    fs.rmSync(outside, {recursive:true, force:true});
  }
});
