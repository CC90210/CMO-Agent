import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  Img,
  staticFile,
  Sequence,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { z } from "zod";

// Load Inter at module scope — required by @remotion/google-fonts
const { fontFamily } = loadFont("normal", { weights: ["700"] });

export const ProductShowcaseSchema = z.object({
  productName: z.string(),
  productImage: z.string(),
  price: z.string(),
  originalPrice: z.string(),
  discount: z.string(),
  features: z.array(z.string()),
  ctaText: z.string(),
  brandColor: z.string(),
  accentColor: z.string(),
});

type ProductShowcaseProps = z.infer<typeof ProductShowcaseSchema>;

// ─── Deterministic helpers ────────────────────────────────────────────────────

function seededRandom(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// Darken a hex color by a given ratio (0–1)
function darkenHex(hex: string, ratio: number): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  const dr = Math.round(r * (1 - ratio))
    .toString(16)
    .padStart(2, "0");
  const dg = Math.round(g * (1 - ratio))
    .toString(16)
    .padStart(2, "0");
  const db = Math.round(b * (1 - ratio))
    .toString(16)
    .padStart(2, "0");
  return `#${dr}${dg}${db}`;
}

// ─── Floating accent shapes (Scene 4) ────────────────────────────────────────

type ShapeConfig = {
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
  drift: number;
};

const SHAPES: ShapeConfig[] = Array.from({ length: 10 }, (_, i) => ({
  x: seededRandom(i * 5) * 100,
  y: seededRandom(i * 5 + 1) * 100,
  size: seededRandom(i * 5 + 2) * 60 + 20,
  speed: seededRandom(i * 5 + 3) * 0.02 + 0.005,
  opacity: seededRandom(i * 5 + 4) * 0.12 + 0.04,
  drift: seededRandom(i * 7) * 20 - 10,
}));

const FloatingShapes: React.FC<{ frame: number; brandColor: string }> = ({
  frame,
  brandColor,
}) => (
  <>
    {SHAPES.map((s, i) => {
      const yOffset = ((s.y + frame * s.speed * 10) % 110) - 5;
      const xOffset = s.x + Math.sin(frame * 0.02 + i) * (s.drift * 0.5);
      return (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${xOffset}%`,
            top: `${yOffset}%`,
            width: s.size,
            height: s.size,
            borderRadius: "50%",
            border: `2px solid ${brandColor}`,
            opacity: s.opacity,
            pointerEvents: "none",
          }}
        />
      );
    })}
  </>
);

// ─── Scene 1: The Anchor ──────────────────────────────────────────────────────
// frames 0-90 (3s at 30fps)
// Off-white bg, competitor price slams in heavy

const AnchorScene: React.FC<{
  frame: number;
  originalPrice: string;
  fps: number;
  width: number;
}> = ({ frame, originalPrice, fps, width }) => {
  // "Others charge" label fades in first
  const labelOpacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const labelY = interpolate(frame, [0, 18], [-12, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Competitor price SLAMS in — heavy spring with overshoot
  const priceScale = spring({
    frame: Math.max(0, frame - 15),
    fps,
    from: 3.2,
    to: 1,
    config: { damping: 6, stiffness: 80, mass: 1.4 },
  });

  const priceOpacity = interpolate(frame, [15, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtle paper texture lines via repeating gradient
  const isBig = width >= 1080;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        fontFamily,
        // Paper/linen texture via repeating gradient
        backgroundImage:
          "repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(0,0,0,0.025) 40px)",
      }}
    >
      {/* "Others charge" label */}
      <div
        style={{
          opacity: labelOpacity,
          transform: `translateY(${labelY}px)`,
          fontSize: isBig ? 28 : 22,
          fontWeight: 700,
          color: "#999990",
          letterSpacing: "4px",
          textTransform: "uppercase",
        }}
      >
        Others charge
      </div>

      {/* Competitor price — the anchor */}
      <div
        style={{
          transform: `scale(${priceScale})`,
          opacity: priceOpacity,
          fontSize: isBig ? 148 : 118,
          fontWeight: 700,
          color: "#1A1A1A",
          lineHeight: 1,
          letterSpacing: "-6px",
        }}
      >
        {originalPrice}
      </div>
    </div>
  );
};

// ─── Scene 2: The Rejection ───────────────────────────────────────────────────
// frames 90-150 (2s at 30fps)
// Red strikethrough, shake, "NOT TODAY" stamp

const RejectionScene: React.FC<{
  frame: number;            // global frame
  localFrame: number;       // frame relative to scene start (90)
  originalPrice: string;
  brandColor: string;
  fps: number;
  width: number;
  height: number;
  bgTransitionProgress: number; // 0→1 for off-white→brand color
}> = ({ localFrame, originalPrice, fps, width, height, bgTransitionProgress }) => {
  const isBig = width >= 1080;

  // Red strike draws from left to right (corner to corner diagonally)
  // Line goes from top-left to bottom-right of the price block
  const strikeProgress = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Price shakes — 3 oscillations on frames 22-46
  const shakeFrame = localFrame - 20;
  const shakeX =
    shakeFrame >= 0 && shakeFrame <= 28
      ? interpolate(
          shakeFrame,
          [0, 4, 8, 13, 18, 23, 28],
          [0, -14, 14, -12, 10, -6, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        )
      : 0;

  // "NOT TODAY" stamp — scale from 0 with heavy bounce
  const stampScale = spring({
    frame: Math.max(0, localFrame - 30),
    fps,
    from: 0,
    to: 1,
    config: { damping: 7, stiffness: 150, mass: 0.8 },
  });
  const stampOpacity = interpolate(localFrame, [30, 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const priceFontSize = isBig ? 148 : 118;
  // Price block approximate dimensions for strike line
  const priceBlockW = isBig ? 440 : 350;
  const priceBlockH = isBig ? 160 : 130;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        fontFamily,
        backgroundImage:
          "repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(0,0,0,0.025) 40px)",
      }}
    >
      {/* "Others charge" label — stays visible */}
      <div
        style={{
          fontSize: isBig ? 28 : 22,
          fontWeight: 700,
          color: "#999990",
          letterSpacing: "4px",
          textTransform: "uppercase",
        }}
      >
        Others charge
      </div>

      {/* Price with shake + diagonal strike overlay */}
      <div
        style={{
          position: "relative",
          transform: `translateX(${shakeX}px)`,
          display: "inline-block",
        }}
      >
        {/* The price number */}
        <div
          style={{
            fontSize: priceFontSize,
            fontWeight: 700,
            color: "#1A1A1A",
            lineHeight: 1,
            letterSpacing: "-6px",
            position: "relative",
          }}
        >
          {originalPrice}
        </div>

        {/* Diagonal red strike — clips via overflow hidden on a rotated container */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: -12,
            width: priceBlockW,
            height: 8,
            background: "#E8192C",
            borderRadius: 4,
            transformOrigin: "left center",
            transform: `translateY(-50%) rotate(-8deg) scaleX(${strikeProgress})`,
          }}
        />
      </div>

      {/* "NOT TODAY" stamp */}
      <div
        style={{
          opacity: stampOpacity,
          transform: `scale(${stampScale}) rotate(-3deg)`,
          fontSize: isBig ? 64 : 52,
          fontWeight: 700,
          color: "#E8192C",
          letterSpacing: "3px",
          textTransform: "uppercase",
          border: "6px solid #E8192C",
          paddingLeft: 24,
          paddingRight: 24,
          paddingTop: 10,
          paddingBottom: 10,
          lineHeight: 1.1,
        }}
      >
        NOT TODAY
      </div>
    </div>
  );
};

// ─── Hard wipe transition ─────────────────────────────────────────────────────
// Renders as a solid panel that sweeps left-to-right to reveal the next scene

const HardWipe: React.FC<{
  frame: number;        // global frame
  startFrame: number;
  endFrame: number;
  color: string;
}> = ({ frame, startFrame, endFrame, color }) => {
  // The wipe "sword" sweeps from x=-100% to x=+100%
  // Phase 1: solid panel moves right, revealing brand bg underneath
  // Phase 2: panel continues off-screen right
  const wipeX = interpolate(
    frame,
    [startFrame, endFrame],
    [-100, 100],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: `${wipeX}%`,
          width: "100%",
          height: "100%",
          background: color,
        }}
      />
    </div>
  );
};

// ─── Scene 3: Your Price Reveal ───────────────────────────────────────────────
// frames 150-300 (5s at 30fps)
// Product name + image + YOUR price + savings badge + feature pills

const FeaturePill: React.FC<{
  text: string;
  index: number;
  localFrame: number;
  brandColor: string;
  fps: number;
  isBig: boolean;
}> = ({ text, index, localFrame, brandColor, fps, isBig }) => {
  const delay = 100 + index * 14;
  const pillFrame = Math.max(0, localFrame - delay);

  const slideX = spring({
    frame: pillFrame,
    fps,
    from: -60,
    to: 0,
    config: { damping: 14, stiffness: 180, mass: 0.7 },
  });

  const opacity = interpolate(pillFrame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        transform: `translateX(${slideX}px)`,
        opacity,
        display: "flex",
        alignItems: "center",
        gap: 10,
        background: "#FFFFFF",
        borderRadius: 50,
        paddingLeft: 20,
        paddingRight: 20,
        paddingTop: isBig ? 12 : 10,
        paddingBottom: isBig ? 12 : 10,
        fontSize: isBig ? 24 : 20,
        fontWeight: 700,
        color: brandColor,
        fontFamily,
      }}
    >
      <span style={{ fontSize: isBig ? 18 : 15, lineHeight: 1 }}>✓</span>
      {text}
    </div>
  );
};

const PriceRevealScene: React.FC<{
  localFrame: number;
  productName: string;
  productImage: string;
  price: string;
  originalPrice: string;
  discount: string;
  features: string[];
  brandColor: string;
  fps: number;
  width: number;
  height: number;
}> = ({
  localFrame,
  productName,
  productImage,
  price,
  originalPrice,
  discount,
  features,
  brandColor,
  fps,
  width,
}) => {
  const isBig = width >= 1080;

  // Product name slides in from left
  const nameSlide = spring({
    frame: Math.max(0, localFrame - 5),
    fps,
    from: -80,
    to: 0,
    config: { damping: 14, stiffness: 160, mass: 0.8 },
  });
  const nameOpacity = interpolate(localFrame, [5, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Product image scales from center — snappy spring
  const imgScale = spring({
    frame: Math.max(0, localFrame - 20),
    fps,
    from: 0,
    to: 1,
    config: { damping: 12, stiffness: 140, mass: 1.0 },
  });
  const imgOpacity = interpolate(localFrame, [20, 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // YOUR price bounces in — 0 → 1.2 → 1.0
  const rawPriceSpring = spring({
    frame: Math.max(0, localFrame - 60),
    fps,
    from: 0,
    to: 1,
    config: { damping: 6, stiffness: 120, mass: 0.9 },
  });
  // Clamp overshoot to max 1.25 so it doesn't go wild
  const priceScale = Math.min(rawPriceSpring, 1.25);
  const priceOpacity = interpolate(localFrame, [60, 72], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "SAVE" badge bounces in after price
  const badgeScale = spring({
    frame: Math.max(0, localFrame - 82),
    fps,
    from: 0,
    to: 1,
    config: { damping: 7, stiffness: 180, mass: 0.6 },
  });
  const badgeOpacity = interpolate(localFrame, [82, 94], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const imgSize = isBig ? 340 : 280;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        paddingLeft: 48,
        paddingRight: 48,
        fontFamily,
      }}
    >
      {/* Product name */}
      <div
        style={{
          transform: `translateX(${nameSlide}px)`,
          opacity: nameOpacity,
          fontSize: isBig ? 40 : 32,
          fontWeight: 700,
          color: "#FFFFFF",
          letterSpacing: "-0.5px",
          textAlign: "center",
          lineHeight: 1.15,
        }}
      >
        {productName}
      </div>

      {/* Product image */}
      <div
        style={{
          transform: `scale(${imgScale})`,
          opacity: imgOpacity,
          width: imgSize,
          height: imgSize,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Img
          src={staticFile(productImage)}
          style={{
            width: imgSize,
            height: imgSize,
            objectFit: "contain",
            filter: "drop-shadow(0 20px 40px rgba(0,0,0,0.35))",
          }}
        />
      </div>

      {/* YOUR price — the money shot */}
      <div
        style={{
          transform: `scale(${priceScale})`,
          opacity: priceOpacity,
          fontSize: isBig ? 128 : 104,
          fontWeight: 700,
          color: "#FFFFFF",
          lineHeight: 1,
          letterSpacing: "-5px",
        }}
      >
        {price}
      </div>

      {/* Original price + SAVE badge row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          opacity: badgeOpacity,
          transform: `scale(${badgeScale})`,
        }}
      >
        {/* Strikethrough original price */}
        <div
          style={{
            position: "relative",
            fontSize: isBig ? 34 : 28,
            fontWeight: 600,
            color: "rgba(255,255,255,0.55)",
          }}
        >
          {originalPrice}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: -2,
              right: -2,
              height: 3,
              background: "rgba(255,255,255,0.65)",
              borderRadius: 2,
              transform: "translateY(-50%)",
            }}
          />
        </div>

        {/* SAVE badge */}
        <div
          style={{
            background: "#FFFFFF",
            borderRadius: 50,
            paddingLeft: 18,
            paddingRight: 18,
            paddingTop: 8,
            paddingBottom: 8,
            fontSize: isBig ? 22 : 18,
            fontWeight: 700,
            color: brandColor,
            letterSpacing: "0.5px",
          }}
        >
          SAVE {discount}
        </div>
      </div>

      {/* Feature pills */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          alignItems: "flex-start",
          width: "100%",
          maxWidth: 480,
        }}
      >
        {features.slice(0, 3).map((feat, i) => (
          <FeaturePill
            key={i}
            text={feat}
            index={i}
            localFrame={localFrame}
            brandColor={brandColor}
            fps={fps}
            isBig={isBig}
          />
        ))}
      </div>
    </div>
  );
};

// ─── Scene 4: CTA ─────────────────────────────────────────────────────────────
// frames 300-450 (5s at 30fps)
// Gradient bg, CTA button, reviews, floating shapes, "Limited time" pulse

const CTAScene: React.FC<{
  localFrame: number;
  ctaText: string;
  brandColor: string;
  accentColor: string;
  productName: string;
  fps: number;
  width: number;
  height: number;
}> = ({ localFrame, ctaText, brandColor, accentColor, productName, fps, width }) => {
  const isBig = width >= 1080;
  const darkBrand = darkenHex(brandColor.replace("#", "").length === 6 ? brandColor : "#5B4FE8", 0.22);

  // All previous content slides UP slightly as CTA enters
  const contentSlideUp = interpolate(localFrame, [0, 30], [0, -18], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // CTA button springs in from below
  const ctaSlide = spring({
    frame: Math.max(0, localFrame - 10),
    fps,
    from: 80,
    to: 0,
    config: { damping: 14, stiffness: 130, mass: 0.9 },
  });
  const ctaOpacity = interpolate(localFrame, [10, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Reviews fade in below CTA
  const reviewsOpacity = interpolate(localFrame, [40, 62], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const reviewsY = interpolate(localFrame, [40, 62], [14, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "Limited time" gentle opacity pulse
  const limitedPulse = interpolate(
    localFrame % 36,
    [0, 18, 36],
    [0.6, 1.0, 0.6],
    { extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 28,
        paddingLeft: 48,
        paddingRight: 48,
        fontFamily,
      }}
    >
      {/* Floating accent shapes in background */}
      <FloatingShapes frame={localFrame} brandColor="#FFFFFF" />

      {/* Content wrapper — slides up */}
      <div
        style={{
          transform: `translateY(${contentSlideUp}px)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
          width: "100%",
        }}
      >
        {/* "Limited time" pulse */}
        <div
          style={{
            opacity: limitedPulse,
            fontSize: isBig ? 22 : 18,
            fontWeight: 700,
            color: "rgba(255,255,255,0.9)",
            letterSpacing: "4px",
            textTransform: "uppercase",
          }}
        >
          ⏳ Limited time offer
        </div>

        {/* CTA button */}
        <div
          style={{
            transform: `translateY(${ctaSlide}px)`,
            opacity: ctaOpacity,
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: 16,
              paddingLeft: isBig ? 72 : 56,
              paddingRight: isBig ? 72 : 56,
              paddingTop: isBig ? 30 : 24,
              paddingBottom: isBig ? 30 : 24,
              fontSize: isBig ? 38 : 30,
              fontWeight: 700,
              color: brandColor,
              letterSpacing: "-0.25px",
              whiteSpace: "nowrap",
            }}
          >
            {ctaText} →
          </div>
        </div>

        {/* Star reviews */}
        <div
          style={{
            opacity: reviewsOpacity,
            transform: `translateY(${reviewsY}px)`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 6,
          }}
        >
          <div
            style={{
              fontSize: isBig ? 32 : 26,
              color: "#FFD700",
              letterSpacing: 4,
              lineHeight: 1,
            }}
          >
            ★★★★★
          </div>
          <div
            style={{
              fontSize: isBig ? 22 : 18,
              fontWeight: 600,
              color: "rgba(255,255,255,0.8)",
            }}
          >
            2,847+ verified reviews
          </div>
        </div>

        {/* Product name reminder — subtle */}
        <div
          style={{
            opacity: reviewsOpacity * 0.55,
            fontSize: isBig ? 18 : 15,
            fontWeight: 500,
            color: "rgba(255,255,255,0.6)",
            textAlign: "center",
            letterSpacing: "0.5px",
          }}
        >
          {productName}
        </div>
      </div>
    </div>
  );
};

// ─── Backgrounds ───────────────────────────────────────────────────────────────

// Scene 1 & 2 background: premium off-white
const OffWhiteBackground: React.FC = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: "#F5F5F0",
    }}
  />
);

// Scene 3 & 4: solid brand color
const BrandBackground: React.FC<{
  brandColor: string;
  accentColor: string;
  isScene4?: boolean;
}> = ({ brandColor, accentColor, isScene4 }) => {
  const darkBrand = darkenHex(
    brandColor.replace("#", "").length === 6 ? brandColor : "#5B4FE8",
    0.22
  );
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: isScene4
          ? `linear-gradient(160deg, ${brandColor} 0%, ${darkBrand} 100%)`
          : brandColor,
      }}
    />
  );
};

// ─── Root Composition ─────────────────────────────────────────────────────────

export const ProductShowcase: React.FC<ProductShowcaseProps> = (props) => {
  const {
    productName,
    productImage,
    price,
    originalPrice,
    discount,
    features,
    ctaText,
    brandColor,
    accentColor,
  } = props;

  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Scene boundary constants
  const S1_START = 0;
  const S1_END = 90;
  const S2_START = 90;
  const S2_END = 150;
  const S3_START = 150;
  const S3_END = 300;
  const S4_START = 300;
  const S4_END = 450;

  // Hard wipe fires from frame 148-162 (covers S2→S3 boundary)
  const WIPE_START = 148;
  const WIPE_END = 164;

  // Scene 2 bg color cross-blend: off-white gradually warms toward brand color
  // starts at frame 90, completes at 150
  const bgTransitionProgress = interpolate(frame, [S2_START, S2_END], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Scene 1 opacity fade-out (cross-dissolve into Scene 2 is seamless since bg matches)
  const s1Opacity = interpolate(frame, [S1_END - 8, S1_END], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ fontFamily, overflow: "hidden" }}>

      {/* ── Backgrounds layer ── */}

      {/* Off-white for scenes 1 & 2 */}
      <Sequence from={S1_START} durationInFrames={S2_END - S1_START}>
        <OffWhiteBackground />
      </Sequence>

      {/* Brand color from scene 3 onward */}
      <Sequence from={S3_START} durationInFrames={S4_END - S3_START}>
        <BrandBackground
          brandColor={brandColor}
          accentColor={accentColor}
          isScene4={false}
        />
      </Sequence>

      {/* Scene 4 gradient override */}
      <Sequence from={S4_START} durationInFrames={S4_END - S4_START}>
        <BrandBackground
          brandColor={brandColor}
          accentColor={accentColor}
          isScene4={true}
        />
      </Sequence>

      {/* ── Scene 1: The Anchor ── */}
      <Sequence from={S1_START} durationInFrames={S1_END - S1_START + 8}>
        <AbsoluteFill>
          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: s1Opacity,
            }}
          >
            <AnchorScene
              frame={frame}
              originalPrice={originalPrice}
              fps={fps}
              width={width}
            />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ── Scene 2: The Rejection ── */}
      <Sequence from={S2_START} durationInFrames={S2_END - S2_START}>
        <AbsoluteFill>
          <RejectionScene
            frame={frame}
            localFrame={frame - S2_START}
            originalPrice={originalPrice}
            brandColor={brandColor}
            fps={fps}
            width={width}
            height={height}
            bgTransitionProgress={bgTransitionProgress}
          />
        </AbsoluteFill>
      </Sequence>

      {/* ── Hard wipe: covers S2→S3 boundary ── */}
      <HardWipe
        frame={frame}
        startFrame={WIPE_START}
        endFrame={WIPE_END}
        color={brandColor}
      />

      {/* ── Scene 3: Price Reveal ── */}
      <Sequence from={S3_START} durationInFrames={S4_END - S3_START}>
        <AbsoluteFill>
          <div
            style={{
              position: "absolute",
              inset: 0,
              // Fade out as Scene 4 takes over
              opacity: interpolate(
                frame,
                [S4_START - 10, S4_START + 6],
                [1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <PriceRevealScene
              localFrame={frame - S3_START}
              productName={productName}
              productImage={productImage}
              price={price}
              originalPrice={originalPrice}
              discount={discount}
              features={features}
              brandColor={brandColor}
              fps={fps}
              width={width}
              height={height}
            />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ── Scene 4: CTA ── */}
      <Sequence from={S4_START} durationInFrames={S4_END - S4_START}>
        <AbsoluteFill>
          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: interpolate(frame, [S4_START, S4_START + 12], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            <CTAScene
              localFrame={frame - S4_START}
              ctaText={ctaText}
              brandColor={brandColor}
              accentColor={accentColor}
              productName={productName}
              fps={fps}
              width={width}
              height={height}
            />
          </div>
        </AbsoluteFill>
      </Sequence>

    </AbsoluteFill>
  );
};
