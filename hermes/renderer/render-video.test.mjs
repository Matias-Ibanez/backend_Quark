import assert from 'node:assert/strict';
import test from 'node:test';
import {spring, interpolate} from 'remotion';
import {dimensions, render, reviewFrames} from './render-video.mjs';

test('confirmed duration and format are imposed independently of generated markup', () => {
  assert.deepEqual(dimensions(1080, 1920, 30, 2), {width: 1080, height: 1920, durationInFrames: 900, fps: 30});
  for (const invalid of [[1081, 1920, 30, 2], [1080, 100, 30, 2], [1080, 1920, 181, 2], [1080, 1920, 30, 8]]) {
    assert.throws(() => dimensions(...invalid));
  }
});

test('external files are rejected before executing generated code', async () => {
  await assert.rejects(render(['/etc/passwd', '/tmp/test.mp4', '320', '320', '5']), /inside \/workspace\/hermes/);
});

test('preview sampling is bounded and covers opening, development and closing', () => {
  assert.deepEqual(reviewFrames(300), [24,75,126,174,225,276]);
  assert.deepEqual(reviewFrames(300,'10,80,180,280'),[10,80,180,280]);
  for (const frames of ['0,1,2','1,1,2,3','0,1,2,300','0,1,2,NaN','0,1,2,3,4,5,6']) assert.throws(() => reviewFrames(300,frames));
});

test('local skill spring recipe matches the installed runtime including delayed scenes', () => {
  assert.throws(() => spring(10, 30, {damping:200}), /Argument missing for parameter "frame"/);
  for (const frame of [-12, 0, 15, 300]) {
    const value = spring({frame, fps:30, config:{damping:200, stiffness:120}});
    assert.ok(Number.isFinite(value));
    assert.ok(Number.isFinite(interpolate(value,[0,1],[40,0])));
  }
});
