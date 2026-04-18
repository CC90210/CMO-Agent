# REMOTION_RULES — Remotion 4.0.436 Rules and Gotchas

> These rules prevent the most common rendering failures. Violating them causes black frames,
> crashes, or non-deterministic output that breaks batch renders.

---

## Rule 1: ALL Animations via Frame Math Only

**NEVER** use:
- CSS `transition`
- CSS `animation`
- CSS `@keyframes`
- `setTimeout` / `setInterval`
- `requestAnimationFrame`
- React state that changes over time

**ALWAYS** use:
```typescript
const frame = useCurrentFrame();
const { fps } = useVideoConfig();

// Smooth spring
const scale = spring({ frame, fps, from: 0, to: 1, config: { damping: 14, stiffness: 120 } });

// Linear/eased interpolation
const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

// Periodic / looping
const bounce = interpolate(frame % 20, [0, 10, 20], [0, -8, 0]);
const pulse = Math.sin(frame / 30) * 0.1 + 1;
```

Remotion renders each frame in isolation — side effects don't carry between frames.

---

## Rule 2: Font Loading at Module Scope

`loadFont()` from `@remotion/google-fonts/*` MUST be called outside any component or hook.

```typescript
// CORRECT — module scope
import { loadFont } from "@remotion/google-fonts/Inter";
const { fontFamily } = loadFont();

export const MyComp: React.FC = () => {
  return <div style={{ fontFamily }}>...</div>;
};
```

```typescript
// WRONG — inside component
export const MyComp: React.FC = () => {
  const { fontFamily } = loadFont(); // Will cause errors
  return <div style={{ fontFamily }}>...</div>;
};
```

---

## Rule 3: Font Weight Limits

Not every font supports every weight. Using an unsupported weight falls back to the browser default and breaks your design.

| Font | Supported Weights |
|------|------------------|
| **Inter** | 100, 200, 300, 400, 500, 600, 700, 800, 900 |
| **Space Grotesk** | 300, 400, 500, 600, 700 only |

When loading Space Grotesk with weight overrides:
```typescript
const { fontFamily } = loadFont("normal", { weights: ["400", "600", "700"] });
// Do NOT include "800" or "900" — not supported by Space Grotesk
```

---

## Rule 4: Static Assets via staticFile()

All assets in `public/` must be referenced via `staticFile()`, not relative paths.

```typescript
import { Img, staticFile } from "remotion";

// CORRECT
<Img src={staticFile("products/earbuds.jpg")} />

// WRONG — breaks in renders
<img src="/products/earbuds.jpg" />
<img src="./products/earbuds.jpg" />
```

Use `<Img>` from remotion (not `<img>`). It handles preloading and prevents black frames.

---

## Rule 5: Deterministic Rendering — No Math.random()

Remotion may render the same frame multiple times (preview, export, seeking). `Math.random()` returns different values each call — particles will flicker, positions will jump.

```typescript
// CORRECT — seeded pseudo-random, same output every render
function seededRandom(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// OR use sin/cos with unique multipliers
const x = Math.sin(i * 73.19) * 0.5 + 0.5;
const y = Math.cos(i * 47.31) * 0.5 + 0.5;

// WRONG
const x = Math.random() * 100; // Different each frame
```

---

## Rule 6: No premountFor Prop

The `premountFor` prop was removed in Remotion 4.x. Do not add it to `<Sequence>`.

```typescript
// WRONG — prop doesn't exist in 4.0.436
<Sequence from={30} durationInFrames={60} premountFor={30}>

// CORRECT
<Sequence from={30} durationInFrames={60}>
```

---

## Rule 7: extrapolateLeft/Right Clamp on interpolate

Without clamp, `interpolate` extrapolates beyond your input range and produces values you don't expect (negative opacity, scale > 1 when you don't want it).

```typescript
// CORRECT — values stay within [0, 1] outside the input range
const opacity = interpolate(frame, [20, 50], [0, 1], {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
});

// RISKY — will produce values < 0 before frame 20 and > 1 after frame 50
const opacity = interpolate(frame, [20, 50], [0, 1]);
```

Use `extrapolateLeft: "clamp"` unless you explicitly want the extrapolated behavior.

---

## Rule 8: spring() from/to for Initial State

If you use `spring()` without `from`/`to`, the default is 0→1. Always be explicit.

```typescript
// Clear intent
const scale = spring({
  frame,
  fps,
  from: 0,
  to: 1,
  config: { damping: 14, stiffness: 120, mass: 0.8 },
});

// For staggered entrance: offset by scene start
const enter = spring({
  frame: frame - sceneStartFrame,  // local frame within scene
  fps,
  from: 0,
  to: 1,
  config: { damping: 16, stiffness: 140 },
});
```

---

## Rule 9: Zod Schema Required for All Compositions

Every composition registered in `Root.tsx` must have a co-located Zod schema passed to `schema={}`. This enables type-safe props editing in Remotion Studio.

```typescript
// In Root.tsx
import { MyTemplate, MyTemplateSchema } from "./compositions/MyTemplate";

<Composition
  id="MyTemplate"
  component={MyTemplate}
  schema={MyTemplateSchema}   // required
  durationInFrames={450}
  fps={30}
  width={1080}
  height={1920}
  defaultProps={{ ... }}      // must satisfy schema
/>
```

---

## Rule 10: Scene Timing with Sequence

Use `<Sequence>` to scope content to frame ranges. `useCurrentFrame()` inside a `<Sequence>` returns the frame relative to the sequence start.

```typescript
// frame inside HookScene counts from 0 (even though Sequence starts at 70)
<Sequence from={70} durationInFrames={120}>
  <HookScene />
</Sequence>
```

If you need the global frame inside a Sequence-wrapped component, pass it as a prop:

```typescript
<Sequence from={70} durationInFrames={120}>
  <HookScene globalFrame={frame} />
</Sequence>
```

---

## Debugging Tips

| Symptom | Likely Cause |
|---------|-------------|
| Black frame at start | `spring()` with `from: 0` — scale or opacity is 0 at frame 0 |
| Font renders as serif | `loadFont()` called inside component, or unsupported weight |
| Image missing in render | Used `<img>` instead of `<Img>`, or relative path instead of `staticFile()` |
| Particles flicker | `Math.random()` used instead of seeded math |
| Animation stops mid-ad | `extrapolateRight` not clamped, value went to 0 unexpectedly |
| Studio works, render fails | Environment variable missing, or `staticFile()` path wrong |
| `premountFor` error | Remove the prop — doesn't exist in 4.0.436 |
