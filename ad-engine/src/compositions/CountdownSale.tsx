import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  staticFile,
  Img,
  Sequence,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { z } from "zod";

const { fontFamily } = loadFont("normal", { weights: ["400", "700"] });

export const CountdownSaleSchema = z.object({
  productName: z.string(),
  productImage: z.string(),
  originalPrice: z.string(),
  salePrice: z.string(),
  discount: z.string(),
  urgencyText: z.string(),
  hoursLeft: z.number(),
  minutesLeft: z.number(),
  ctaText: z.string(),
  brandColor: z.string(),
  accentColor: z.string(),
});

type CountdownSaleProps = z.infer<typeof CountdownSaleSchema>;

// ─── Scene 1: The Hook Words (frames 0–90) ────────────────────────────────────
// Words SLAM in filling 80% of the screen. Background does HARD color cuts on
// each word impact. No fades, no gradients — pure kinetic energy.

const SceneHookWords: React.FC<{
  frame: number;
  fps: number;
  urgencyText: string;
  brandColor: string;
}> = ({ frame, fps, urgencyText, brandColor }) => {
  // Split urgencyText into two words. If only one word, duplicate it.
  const words = urgencyText.toUpperCase().split(/\s+/).slice(0, 2);
  const word1 = words[0] ?? "FLASH";
  const word2 = words[1] ?? "SALE";

  // Word 1: slams in from TOP at frame 0 (translateY from -900 to 0)
  // Low damping = heavy bounce
  const w1Spring = spring({ frame, fps, config: { damping: 6, stiffness: 220 } });
  const w1Y = interpolate(w1Spring, [0, 1], [-900, 0]);

  // Word 2: crashes in from RIGHT at frame 28
  const w2Spring = spring({
    frame: frame - 28,
    fps,
    config: { damping: 6, stiffness: 220 },
  });
  const w2X = interpolate(w2Spring, [0, 1], [1200, 0]);

  // Background color: electric yellow → hot coral at word1 impact (frame ~8)
  // → brand color at word2 impact (frame ~36)
  // HARD cuts driven by integer frame comparisons — no interpolation
  let bgColor = "#FFE135";
  if (frame >= 8) bgColor = "#FF6B6B";
  if (frame >= 36) bgColor = brandColor;

  // Word 2 opacity: invisible until it starts moving
  const w2Opacity = interpolate(frame, [27, 30], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: bgColor }}>
      {/* Word 1 — fills ~80% of 1080px width → fontSize ~220 */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `translateY(${w1Y}px)`,
          // Offset upward so both words stack nicely
          marginTop: -260,
        }}
      >
        <span
          style={{
            fontFamily,
            fontWeight: 700,
            fontSize: 220,
            color: "#000000",
            textAlign: "center",
            lineHeight: 0.9,
            letterSpacing: -8,
            textTransform: "uppercase",
            // Viewport-width clamping via inline style
            maxWidth: 1040,
            display: "block",
          }}
        >
          {word1}
        </span>
      </AbsoluteFill>

      {/* Word 2 — crashes in from right */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `translateX(${w2X}px)`,
          opacity: w2Opacity,
          marginTop: 260,
        }}
      >
        <span
          style={{
            fontFamily,
            fontWeight: 700,
            fontSize: 220,
            color: "#ffffff",
            textAlign: "center",
            lineHeight: 0.9,
            letterSpacing: -8,
            textTransform: "uppercase",
            maxWidth: 1040,
            display: "block",
          }}
        >
          {word2}
        </span>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─── Scene 2: The Product Drop (frames 90–180) ────────────────────────────────
// Solid brand color background. Previous text wipes LEFT. Product DROPS from
// above. On landing: circular shockwave. Product name + separator line appear.

const SceneProductDrop: React.FC<{
  frame: number;
  fps: number;
  productImage: string;
  productName: string;
  brandColor: string;
}> = ({ frame, fps, productImage, productName, brandColor }) => {
  const relFrame = frame - 90;

  // Text wipe exit: slides everything left and off screen
  const wipeX = interpolate(relFrame, [0, 18], [0, -1200], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Product drops from -800px. Spring with damping 8 = bouncy landing
  const dropSpring = spring({
    frame: relFrame - 10,
    fps,
    config: { damping: 8, stiffness: 180 },
  });
  const dropY = interpolate(dropSpring, [0, 1], [-800, 0]);
  const productOpacity = interpolate(relFrame, [9, 14], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Shockwave: starts on "impact" at ~relFrame 32 (when spring settles ~80%)
  // Expands from scale 0 to 3, opacity 0.7 to 0
  const shockScale = interpolate(relFrame, [32, 65], [0, 3], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const shockOpacity = interpolate(relFrame, [32, 65], [0.7, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Product name slides up from below after impact
  const nameSpring = spring({
    frame: relFrame - 40,
    fps,
    config: { damping: 10, stiffness: 200 },
  });
  const nameY = interpolate(nameSpring, [0, 1], [80, 0]);
  const nameOpacity = interpolate(relFrame, [39, 48], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Separator line expands left+right from center
  const lineProgress = spring({
    frame: relFrame - 50,
    fps,
    config: { damping: 12, stiffness: 220 },
  });
  const lineWidth = interpolate(lineProgress, [0, 1], [0, 600]);
  const lineOpacity = interpolate(relFrame, [49, 56], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: brandColor }}>
      {/* Wipe container — slides previous scene elements off LEFT */}
      {relFrame < 18 && (
        <AbsoluteFill
          style={{
            transform: `translateX(${wipeX}px)`,
            background: brandColor,
          }}
        />
      )}

      {/* Product image drops from top */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            transform: `translateY(${dropY}px)`,
            opacity: productOpacity,
            position: "relative",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          {/* Shockwave ring — centered on product */}
          <div
            style={{
              position: "absolute",
              width: 480,
              height: 480,
              borderRadius: "50%",
              border: `12px solid #ffffff`,
              transform: `scale(${shockScale})`,
              opacity: shockOpacity,
              top: 0,
              left: 0,
            }}
          />

          <Img
            src={staticFile(productImage)}
            style={{
              width: 480,
              height: 480,
              objectFit: "contain",
            }}
          />
        </div>

        {/* Separator line — expands from center */}
        <div
          style={{
            opacity: lineOpacity,
            marginTop: 32,
            display: "flex",
            justifyContent: "center",
            width: "100%",
          }}
        >
          <div
            style={{
              height: 6,
              width: lineWidth,
              background: "#000000",
              borderRadius: 3,
            }}
          />
        </div>

        {/* Product name */}
        <div
          style={{
            transform: `translateY(${nameY}px)`,
            opacity: nameOpacity,
            marginTop: 28,
          }}
        >
          <span
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 64,
              color: "#ffffff",
              textAlign: "center",
              letterSpacing: -1,
              textTransform: "uppercase",
              display: "block",
            }}
          >
            {productName}
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─── Scene 3: The Price Assault (frames 180–330) ──────────────────────────────
// Deep navy background. Prices assault the eye. Diagonal slash. Countdown
// digits slam in one-by-one. "ENDS TONIGHT" in staccato entrance.

const DiagonalSlash: React.FC<{ frame: number; fps: number }> = ({
  frame,
  fps,
}) => {
  // A thick red bar rotated ~-15deg, animates its scaleX from 0 to 1
  const slashProgress = spring({
    frame: frame - 210,
    fps,
    config: { damping: 14, stiffness: 260 },
  });
  const scaleX = interpolate(slashProgress, [0, 1], [0, 1]);

  return (
    <div
      style={{
        position: "absolute",
        // Center on the originalPrice text area
        top: "50%",
        left: "50%",
        width: 560,
        height: 14,
        background: "#FF2020",
        transform: `translate(-50%, -50%) rotate(-8deg) scaleX(${scaleX})`,
        transformOrigin: "left center",
        borderRadius: 4,
        zIndex: 10,
      }}
    />
  );
};

const CountdownBlock: React.FC<{
  value: string;
  label: string;
  frame: number;
  fps: number;
  enterFrame: number;
  blockColor: string;
}> = ({ value, label, frame, fps, enterFrame, blockColor }) => {
  // Each digit block slams in from a different direction
  const blockSpring = spring({
    frame: frame - enterFrame,
    fps,
    config: { damping: 7, stiffness: 280 },
  });
  const blockScale = interpolate(blockSpring, [0, 1], [0, 1]);
  const blockOpacity = interpolate(frame, [enterFrame, enterFrame + 6], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Blink-based colon separator is handled separately
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        transform: `scale(${blockScale})`,
        opacity: blockOpacity,
      }}
    >
      <div
        style={{
          background: blockColor,
          width: 200,
          height: 200,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 0,
        }}
      >
        <span
          style={{
            fontFamily,
            fontWeight: 700,
            fontSize: 120,
            color: "#ffffff",
            lineHeight: 1,
            letterSpacing: -4,
          }}
        >
          {value}
        </span>
      </div>
      <span
        style={{
          fontFamily,
          fontWeight: 700,
          fontSize: 24,
          color: "rgba(255,255,255,0.5)",
          letterSpacing: 4,
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
    </div>
  );
};

const ScenePriceAssault: React.FC<{
  frame: number;
  fps: number;
  originalPrice: string;
  salePrice: string;
  discount: string;
  hoursLeft: number;
  minutesLeft: number;
  brandColor: string;
  accentColor: string;
}> = ({
  frame,
  fps,
  originalPrice,
  salePrice,
  discount,
  hoursLeft,
  minutesLeft,
  brandColor,
  accentColor,
}) => {
  const relFrame = frame - 180;

  // Background is deep navy #1A1A3E — hard cut from brand color
  // Original price fades in at relFrame 0
  const origOpacity = interpolate(relFrame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Sale price EXPLODES: scale 0 → 1.3 → 1.0 (overshoot then settle)
  const salePriceSpring = spring({
    frame: relFrame - 30,
    fps,
    config: { damping: 5, stiffness: 300 },
  });
  const salePriceScale = interpolate(salePriceSpring, [0, 0.7, 1], [0, 1.3, 1.0]);
  const salePriceOpacity = interpolate(relFrame, [29, 36], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Discount badge SPINS in: rotate 360 → -5 degrees
  const badgeSpring = spring({
    frame: relFrame - 48,
    fps,
    config: { damping: 8, stiffness: 200 },
  });
  const badgeRotate = interpolate(badgeSpring, [0, 1], [360, -5]);
  const badgeScale = interpolate(badgeSpring, [0, 1], [0, 1]);
  const badgeOpacity = interpolate(relFrame, [47, 54], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Countdown timer — each block slams in staggered
  const totalSecondsAtStart = hoursLeft * 3600 + minutesLeft * 60;
  const elapsed = Math.floor(frame / fps);
  const remaining = Math.max(0, totalSecondsAtStart - elapsed);
  const h = Math.floor(remaining / 3600);
  const m = Math.floor((remaining % 3600) / 60);
  const s = remaining % 60;
  const pad = (n: number) => String(n).padStart(2, "0");

  // Colon blink — derived from frame
  const colonOpacity = Math.floor(frame / (fps / 2)) % 2 === 0 ? 1 : 0.2;

  // "ENDS TONIGHT" — each word slams from a different direction, staggered
  const endsWords = ["ENDS", "TONIGHT"];
  const wordDirections: [number, number][] = [
    [-400, 0],  // ENDS: from left
    [400, 0],   // TONIGHT: from right
  ];

  // Slightly different block colors (brand hue variations using opacity)
  const blockColors = [brandColor, accentColor, brandColor];

  return (
    <AbsoluteFill style={{ background: "#1A1A3E" }}>
      {/* Original price — large, gray, already defeated */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          paddingTop: 80,
          gap: 0,
        }}
      >
        {/* Price zone */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
            marginTop: -320,
          }}
        >
          {/* Original price + slash */}
          <div
            style={{
              position: "relative",
              opacity: origOpacity,
              display: "inline-block",
            }}
          >
            <span
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 96,
                color: "rgba(255,255,255,0.35)",
                letterSpacing: -2,
              }}
            >
              {originalPrice}
            </span>
            <DiagonalSlash frame={frame} fps={fps} />
          </div>

          {/* Sale price EXPLODES */}
          <div
            style={{
              transform: `scale(${salePriceScale})`,
              opacity: salePriceOpacity,
            }}
          >
            <span
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 180,
                color: brandColor,
                letterSpacing: -6,
                lineHeight: 0.9,
                display: "block",
                textAlign: "center",
              }}
            >
              {salePrice}
            </span>
          </div>

          {/* Discount badge SPINS in */}
          <div
            style={{
              position: "absolute",
              top: 60,
              right: 40,
              transform: `rotate(${badgeRotate}deg) scale(${badgeScale})`,
              opacity: badgeOpacity,
              background: accentColor,
              width: 160,
              height: 160,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 52,
                color: "#000000",
                textAlign: "center",
                lineHeight: 1,
              }}
            >
              {discount}
            </span>
          </div>
        </div>

        {/* Countdown digit blocks — slam in staggered */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "flex-start",
            gap: 0,
            marginTop: 60,
          }}
        >
          <CountdownBlock
            value={pad(h)}
            label="HRS"
            frame={frame}
            fps={fps}
            enterFrame={180 + 60}
            blockColor={blockColors[0]}
          />
          {/* Colon separator */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 40,
              height: 200,
              opacity: colonOpacity,
            }}
          >
            <span
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 80,
                color: "#ffffff",
                lineHeight: 1,
              }}
            >
              :
            </span>
          </div>
          <CountdownBlock
            value={pad(m)}
            label="MIN"
            frame={frame}
            fps={fps}
            enterFrame={180 + 72}
            blockColor={blockColors[1]}
          />
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 40,
              height: 200,
              opacity: colonOpacity,
            }}
          >
            <span
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 80,
                color: "#ffffff",
                lineHeight: 1,
              }}
            >
              :
            </span>
          </div>
          <CountdownBlock
            value={pad(s)}
            label="SEC"
            frame={frame}
            fps={fps}
            enterFrame={180 + 84}
            blockColor={blockColors[2]}
          />
        </div>

        {/* "ENDS TONIGHT" — staccato word-by-word, each from different direction */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            gap: 24,
            marginTop: 40,
          }}
        >
          {endsWords.map((word, i) => {
            const wordEnterFrame = 180 + 100 + i * 12;
            const wordSpring = spring({
              frame: frame - wordEnterFrame,
              fps,
              config: { damping: 9, stiffness: 260 },
            });
            const [dxBase] = wordDirections[i];
            const wordX = interpolate(wordSpring, [0, 1], [dxBase, 0]);
            const wordOpacity = interpolate(
              frame,
              [wordEnterFrame, wordEnterFrame + 8],
              [0, 1],
              { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
            );
            return (
              <span
                key={word}
                style={{
                  fontFamily,
                  fontWeight: 700,
                  fontSize: 72,
                  color: "#ffffff",
                  letterSpacing: -2,
                  transform: `translateX(${wordX}px)`,
                  opacity: wordOpacity,
                  display: "block",
                  textTransform: "uppercase",
                }}
              >
                {word}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─── Scene 4: CTA Slam (frames 330–450) ──────────────────────────────────────
// Everything compresses upward. CTA fills bottom half. Huge button PULSES once.
// Two thick color bars frame top + bottom of screen.

const SceneCTASlam: React.FC<{
  frame: number;
  fps: number;
  ctaText: string;
  brandColor: string;
  accentColor: string;
}> = ({ frame, fps, ctaText, brandColor, accentColor }) => {
  const relFrame = frame - 330;

  // Top color bar — slams DOWN from off-screen top
  const topBarSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 10, stiffness: 280 },
  });
  const topBarY = interpolate(topBarSpring, [0, 1], [-60, 0]);

  // Bottom color bar — slams UP from off-screen bottom
  const bottomBarSpring = spring({
    frame: relFrame - 6,
    fps,
    config: { damping: 10, stiffness: 280 },
  });
  const bottomBarY = interpolate(bottomBarSpring, [0, 1], [60, 0]);

  // Background solid: brand color but lighter — use white for max contrast
  // with brand-colored button

  // CTA headline: fills bottom half of screen
  const headlineSpring = spring({
    frame: relFrame - 12,
    fps,
    config: { damping: 8, stiffness: 240 },
  });
  const headlineY = interpolate(headlineSpring, [0, 1], [600, 0]);
  const headlineOpacity = interpolate(relFrame, [11, 20], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // CTA button PULSES once on entrance: scale 1.0 → 1.05 → 1.0
  // Driven entirely by spring overshoot
  const buttonSpring = spring({
    frame: relFrame - 22,
    fps,
    config: { damping: 5, stiffness: 400 },
  });
  // Overshoot: maps 0→0, peaks at ~1.05, settles at 1.0
  const buttonScale = interpolate(buttonSpring, [0, 0.6, 1], [0.6, 1.05, 1.0]);
  const buttonOpacity = interpolate(relFrame, [21, 28], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // "Don't miss out" — gentle fade below button
  const missOutOpacity = interpolate(relFrame, [45, 65], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      {/* Top accent bar — brand color */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 24,
          background: brandColor,
          transform: `translateY(${topBarY}px)`,
          zIndex: 20,
        }}
      />

      {/* Bottom accent bar — accent color */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 24,
          background: accentColor,
          transform: `translateY(${bottomBarY}px)`,
          zIndex: 20,
        }}
      />

      {/* Main content — centered */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          paddingLeft: 48,
          paddingRight: 48,
          gap: 40,
        }}
      >
        {/* CTA Headline — fills top portion */}
        <div
          style={{
            transform: `translateY(${headlineY}px)`,
            opacity: headlineOpacity,
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 160,
              color: "#000000",
              lineHeight: 0.88,
              letterSpacing: -8,
              textTransform: "uppercase",
              display: "block",
            }}
          >
            DON&apos;T
            <br />
            MISS
            <br />
            OUT.
          </span>
        </div>

        {/* CTA Button — 60% of 1080px = 648px wide */}
        <div
          style={{
            transform: `scale(${buttonScale})`,
            opacity: buttonOpacity,
            width: 648,
          }}
        >
          <div
            style={{
              background: brandColor,
              padding: "44px 48px",
              textAlign: "center",
              borderRadius: 0,
            }}
          >
            <span
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 72,
                color: "#ffffff",
                letterSpacing: -2,
                textTransform: "uppercase",
                display: "block",
                lineHeight: 1,
              }}
            >
              {ctaText}
            </span>
          </div>
        </div>

        {/* "Don't miss out" — small text, gentle fade */}
        <div style={{ opacity: missOutOpacity }}>
          <span
            style={{
              fontFamily,
              fontWeight: 400,
              fontSize: 36,
              color: "rgba(0,0,0,0.45)",
              letterSpacing: 1,
              textAlign: "center",
            }}
          >
            Limited time only.
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─── Main Composition ─────────────────────────────────────────────────────────

export const CountdownSale: React.FC<CountdownSaleProps> = ({
  productName,
  productImage,
  originalPrice,
  salePrice,
  discount,
  urgencyText,
  hoursLeft,
  minutesLeft,
  ctaText,
  brandColor,
  accentColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ fontFamily, overflow: "hidden" }}>
      {/* Scene 1: Hook Words (0–90) — solid colors, hard cuts */}
      <Sequence from={0} durationInFrames={90}>
        <SceneHookWords
          frame={frame}
          fps={fps}
          urgencyText={urgencyText}
          brandColor={brandColor}
        />
      </Sequence>

      {/* Scene 2: Product Drop (90–180) — solid brand color */}
      <Sequence from={90} durationInFrames={90}>
        <SceneProductDrop
          frame={frame}
          fps={fps}
          productImage={productImage}
          productName={productName}
          brandColor={brandColor}
        />
      </Sequence>

      {/* Scene 3: Price Assault (180–330) — deep navy */}
      <Sequence from={180} durationInFrames={150}>
        <ScenePriceAssault
          frame={frame}
          fps={fps}
          originalPrice={originalPrice}
          salePrice={salePrice}
          discount={discount}
          hoursLeft={hoursLeft}
          minutesLeft={minutesLeft}
          brandColor={brandColor}
          accentColor={accentColor}
        />
      </Sequence>

      {/* Scene 4: CTA Slam (330–450) — white background, max contrast */}
      <Sequence from={330} durationInFrames={120}>
        <SceneCTASlam
          frame={frame}
          fps={fps}
          ctaText={ctaText}
          brandColor={brandColor}
          accentColor={accentColor}
        />
      </Sequence>
    </AbsoluteFill>
  );
};
