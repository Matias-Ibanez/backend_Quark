# QUARK: React API for the installed Remotion runtime

This local compatibility guide takes precedence over retained generic Studio/markup recipes. It is verified against the image's installed `remotion@4.0.529`. Export only a default React component; the application supplies composition, duration, FPS and rendering.

## Animation

`spring` accepts **one object**, never positional arguments. Preserve each scene's local frame and delay:

```tsx
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export default function Video() {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = spring({
    frame: frame - 12,
    fps,
    config: {damping: 200, stiffness: 120},
  });
  const y = interpolate(progress, [0, 1], [40, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', backgroundColor: '#12203C'}}>
    <div style={{color: 'white', fontSize: 64, fontFamily: 'DejaVu Sans', opacity: progress, transform: `translateY(${y}px)`}}>Mensaje confirmado</div>
  </AbsoluteFill>;
}
```

- Incorrect: `spring(t, fps, {damping: 200})`. It throws `Argument missing for parameter "frame"`.
- Correct: `spring({frame: t, fps, config: {damping: 200}})`.
- For easing use `Easing.bezier(...)`, `Easing.linear` or a separate `spring` value. Do not assume newer `Easing.spring`, `interpolate` string arrays, `output` or `posterize` examples apply to this installed runtime. Use numeric interpolation and CSS strings built from the result.
- Keep React hooks unconditional. A scene not yet visible still executes its functions; all spring calls must be valid, including delayed scenes.

API source: https://www.remotion.dev/docs/spring (checked 2026-09-28).

## Reading existing work and repairs

Before rewriting an existing file, read its full current contents with the native file tool. Inspect `Video.tsx`, `plan.md` and `caption.txt` before changing them. Preserve previous pieces and confirmed media. Do not fight overwrite protection by writing unrelated scratch files.

When the application returns a render diagnostic, correct the specific defect in **all occurrences** within `Video.tsx`, preserve timing/voice/text, and stop. Write only inside the project's directory. Do not install packages, scaffold, render or inspect images during a controlled create/repair stage; the application does that next.
