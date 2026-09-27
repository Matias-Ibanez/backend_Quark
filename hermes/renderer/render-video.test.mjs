import assert from 'node:assert/strict';
import test from 'node:test';
import {dimensions, render} from './render-video.mjs';

test('confirmed duration and format are imposed independently of generated markup', () => {
  assert.deepEqual(dimensions(1080, 1920, 30, 2), {width: 1080, height: 1920, durationInFrames: 900, fps: 30});
  for (const invalid of [[1081, 1920, 30, 2], [1080, 100, 30, 2], [1080, 1920, 181, 2], [1080, 1920, 30, 8]]) {
    assert.throws(() => dimensions(...invalid));
  }
});

test('external files are rejected before executing generated code', async () => {
  await assert.rejects(render(['/etc/passwd', '/tmp/test.mp4', '320', '320', '5']), /inside \/workspace\/hermes/);
});
