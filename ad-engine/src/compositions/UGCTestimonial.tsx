import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  staticFile,
  Sequence,
} from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

// ─── Font — module scope, required by @remotion/google-fonts ─────────────────

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
});

// ─── Schema ───────────────────────────────────────────────────────────────────

export const UGCTestimonialSchema = z.object({
  hookText: z.string(),
  testimonialLines: z.array(z.string()),
  productName: z.string(),
  productImage: z.string(),
  rating: z.number(),
  reviewerName: z.string(),
  ctaText: z.string(),
  brandColor: z.string(),
});

type UGCTestimonialProps = z.infer<typeof UGCTestimonialSchema>;

// ─── Scene timing ─────────────────────────────────────────────────────────────

const SCENE_1_START = 0;   // Product reveal         frames 0–75
const SCENE_2_START = 75;  // First notification     frames 75–135
const SCENE_3_START = 135; // Cascade                frames 135–300
const SCENE_4_START = 300; // CTA convergence        frames 300–450
const TOTAL_FRAMES = 450;

// ─── Notification data — hardcoded social proof ───────────────────────────────

type NotificationEntry = {
  id: number;
  type: "purchase" | "review" | "stock" | "aggregate";
  avatar: string;
  name: string;
  city: string;
  text: string;
  time: string;
  accentColor: string;
};

const NOTIFICATIONS: NotificationEntry[] = [
  {
    id: 0,
    type: "purchase",
    avatar: "S",
    name: "Sarah K.",
    city: "Austin, TX",
    text: "Sarah K. from Austin, TX just purchased this",
    time: "2 min ago",
    accentColor: "#F97316",
  },
  {
    id: 1,
    type: "review",
    avatar: "M",
    name: "Marcus T.",
    city: "Chicago, IL",
    text: "★★★★★  'This changed everything!' — Marcus T.",
    time: "5 min ago",
    accentColor: "#FBBF24",
  },
  {
    id: 2,
    type: "purchase",
    avatar: "J",
    name: "Jenna R.",
    city: "Portland, OR",
    text: "Jenna R. from Portland, OR just bought this",
    time: "7 min ago",
    accentColor: "#34D399",
  },
  {
    id: 3,
    type: "stock",
    avatar: "!",
    name: "",
    city: "",
    text: "Only 7 left in stock — selling fast",
    time: "live",
    accentColor: "#F87171",
  },
  {
    id: 4,
    type: "review",
    avatar: "A",
    name: "Aisha N.",
    city: "Miami, FL",
    text: "★★★★★  'Worth every penny' — Aisha N.",
    time: "11 min ago",
    accentColor: "#A78BFA",
  },
  {
    id: 5,
    type: "purchase",
    avatar: "D",
    name: "Dylan P.",
    city: "Denver, CO",
    text: "Dylan P. from Denver, CO just purchased this",
    time: "14 min ago",
    accentColor: "#38BDF8",
  },
  {
    id: 6,
    type: "aggregate",
    avatar: "★",
    name: "",
    city: "",
    text: "4.9 / 5  from 2,847 verified reviews",
    time: "updated today",
    accentColor: "#FBBF24",
  },
  {
    id: 7,
    type: "purchase",
    avatar: "C",
    name: "Camila V.",
    city: "Los Angeles, CA",
    text: "Camila V. from Los Angeles, CA just bought this",
    time: "18 min ago",
    accentColor: "#F472B6",
  },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

// Seeded pseudo-random for deterministic confetti — no Math.random() at render time
function seededRandom(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ─── Warm background gradient ─────────────────────────────────────────────────

const WarmBackground: React.FC<{ warmth: number }> = ({ warmth }) => {
  // warmth 0→1: creamy beige to deeper peach
  const topR = Math.round(interpolate(warmth, [0, 1], [253, 255]));
  const topG = Math.round(interpolate(warmth, [0, 1], [248, 235]));
  const topB = Math.round(interpolate(warmth, [0, 1], [240, 210]));
  const botR = Math.round(interpolate(warmth, [0, 1], [255, 255]));
  const botG = Math.round(interpolate(warmth, [0, 1], [240, 210]));
  const botB = Math.round(interpolate(warmth, [0, 1], [230, 185]));

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(165deg, rgb(${topR},${topG},${topB}) 0%, rgb(${botR},${botG},${botB}) 100%)`,
      }}
    />
  );
};

// ─── Single notification toast ────────────────────────────────────────────────

const Toast: React.FC<{
  entry: NotificationEntry;
  slideProgress: number; // 0→1 spring
  stackOffsetY: number;  // px shift upward as new toasts arrive
  opacity: number;
}> = ({ entry, slideProgress, stackOffsetY, opacity }) => {
  const translateX = interpolate(slideProgress, [0, 1], [620, 40]);
  const translateY = -stackOffsetY;

  return (
    <div
      style={{
        position: "absolute",
        right: 0,
        bottom: 0,
        transform: `translateX(${translateX}px) translateY(${translateY}px)`,
        opacity,
        width: 680,
        pointerEvents: "none",
      }}
    >
      {/* Card body — frosted appearance via layering */}
      <div
        style={{
          background: "rgba(255, 255, 255, 0.88)",
          borderRadius: 20,
          padding: "18px 20px",
          display: "flex",
          alignItems: "center",
          gap: 16,
          boxShadow:
            "0 8px 32px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06)",
          borderLeft: `5px solid ${entry.accentColor}`,
          // Inner white layer to approximate frosted glass on warm background
          borderTop: "1px solid rgba(255,255,255,0.9)",
          borderRight: "1px solid rgba(255,255,255,0.9)",
          borderBottom: "1px solid rgba(255,255,255,0.9)",
        }}
      >
        {/* Avatar circle */}
        <div
          style={{
            width: 52,
            height: 52,
            borderRadius: "50%",
            background: `${entry.accentColor}22`,
            border: `2px solid ${entry.accentColor}55`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <span
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 22,
              color: entry.accentColor,
              lineHeight: 1,
            }}
          >
            {entry.avatar}
          </span>
        </div>

        {/* Text block */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 26,
              color: "#1C1410",
              lineHeight: 1.3,
              letterSpacing: -0.3,
            }}
          >
            {entry.text}
          </div>
          <div
            style={{
              fontFamily,
              fontWeight: 400,
              fontSize: 20,
              color: "#9B8E85",
              marginTop: 4,
              letterSpacing: 0.1,
            }}
          >
            {entry.time}
          </div>
        </div>

        {/* App icon dot — iOS notification feel */}
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: entry.accentColor,
            flexShrink: 0,
            alignSelf: "flex-start",
            marginTop: 6,
          }}
        />
      </div>
    </div>
  );
};

// ─── Scene 1: Product reveal ──────────────────────────────────────────────────

const ProductRevealScene: React.FC<{
  productImage: string;
  productName: string;
  rating: number;
  sceneFrame: number;
}> = ({ productImage, productName, rating, sceneFrame }) => {
  const { fps } = useVideoConfig();

  const imageEnter = spring({
    frame: sceneFrame,
    fps,
    config: { damping: 18, stiffness: 120, mass: 1.1 },
  });

  const nameEnter = spring({
    frame: sceneFrame - 18,
    fps,
    config: { damping: 16, stiffness: 150 },
  });

  const ratingEnter = spring({
    frame: sceneFrame - 32,
    fps,
    config: { damping: 14, stiffness: 130 },
  });

  const imageScale = interpolate(imageEnter, [0, 1], [0.75, 1]);
  const imageOpacity = interpolate(imageEnter, [0, 0.4, 1], [0, 0.9, 1]);

  // Subtle vertical float
  const floatY = Math.sin(sceneFrame * 0.06) * 6;

  const filledStars = Math.round(Math.min(5, Math.max(0, rating)));

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 0,
      }}
    >
      {/* Product on pedestal */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 36,
          transform: `translateY(${floatY}px)`,
        }}
      >
        {/* Circular shadow pedestal */}
        <div style={{ position: "relative" }}>
          <div
            style={{
              position: "absolute",
              bottom: -20,
              left: "50%",
              transform: "translateX(-50%)",
              width: 360,
              height: 60,
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse, rgba(180,120,60,0.22) 0%, transparent 70%)",
              opacity: imageEnter,
            }}
          />
          <div
            style={{
              width: 420,
              height: 420,
              borderRadius: "50%",
              overflow: "hidden",
              boxShadow:
                "0 30px 80px rgba(180,100,40,0.18), 0 8px 24px rgba(0,0,0,0.08)",
              transform: `scale(${imageScale})`,
              opacity: imageOpacity,
              border: "4px solid rgba(255,255,255,0.85)",
            }}
          >
            <Img
              src={staticFile(productImage)}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </div>
        </div>

        {/* Product name */}
        <div
          style={{
            textAlign: "center",
            transform: `translateY(${interpolate(nameEnter, [0, 1], [20, 0])}px)`,
            opacity: nameEnter,
          }}
        >
          <span
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 52,
              color: "#2D1E0F",
              letterSpacing: -1,
              lineHeight: 1,
            }}
          >
            {productName}
          </span>
        </div>

        {/* Star rating */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            transform: `scale(${interpolate(ratingEnter, [0, 1], [0.7, 1])})`,
            opacity: ratingEnter,
          }}
        >
          <div style={{ display: "flex", gap: 4 }}>
            {Array.from({ length: 5 }, (_, i) => (
              <span
                key={i}
                style={{
                  fontSize: 38,
                  color: i < filledStars ? "#F59E0B" : "#E5D5C5",
                  lineHeight: 1,
                  filter:
                    i < filledStars
                      ? "drop-shadow(0 1px 4px rgba(245,158,11,0.45))"
                      : "none",
                }}
              >
                ★
              </span>
            ))}
          </div>
          <span
            style={{
              fontFamily,
              fontWeight: 400,
              fontSize: 28,
              color: "#8A6F5A",
              letterSpacing: 0.2,
            }}
          >
            {rating.toFixed(1)}
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Scene 2 + 3: Notification cascade ───────────────────────────────────────
// Handles both first notification (Scene 2) and full cascade (Scene 3)
// cascadeFrame is relative to SCENE_2_START

const CascadeScene: React.FC<{
  productImage: string;
  productName: string;
  cascadeFrame: number;
}> = ({ productImage, productName, cascadeFrame }) => {
  const { fps } = useVideoConfig();

  // Each notification slides in 25 frames after the previous
  const TOAST_INTERVAL = 25;
  // First toast starts at cascadeFrame 0 (which is SCENE_2_START)
  // Rest follow every 25 frames from SCENE_3_START (= cascadeFrame 60)
  const toastStartFrames = [
    0,   // Scene 2: first
    60,  // Scene 3 opens
    85,
    110,
    135,
    160,
    185,
    210,
  ];

  // Product scales down into corner as notifications accumulate
  const productShrink = spring({
    frame: cascadeFrame - 60,
    fps,
    config: { damping: 20, stiffness: 80 },
  });
  const productScale = interpolate(productShrink, [0, 1], [1, 0.55]);
  const productY = interpolate(productShrink, [0, 1], [0, -340]);
  const productX = interpolate(productShrink, [0, 1], [0, 0]);

  // Background warmth increases with density
  const warmthRamp = interpolate(cascadeFrame, [60, 200], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      {/* Warm overlay that builds up */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(165deg, rgba(255,230,180,${warmthRamp * 0.25}) 0%, rgba(255,200,140,${warmthRamp * 0.18}) 100%)`,
          pointerEvents: "none",
        }}
      />

      {/* Product image — shrinks to top as toasts accumulate */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, calc(-50% + ${productY}px)) scale(${productScale})`,
          width: 420,
          height: 420,
          borderRadius: "50%",
          overflow: "hidden",
          boxShadow:
            "0 30px 80px rgba(180,100,40,0.18), 0 8px 24px rgba(0,0,0,0.08)",
          border: "4px solid rgba(255,255,255,0.85)",
        }}
      >
        <Img
          src={staticFile(productImage)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>

      {/* Product label — fades as product shrinks */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, calc(230px + ${productY}px)) scale(${productScale})`,
          opacity: interpolate(productShrink, [0, 0.6], [1, 0], {
            extrapolateRight: "clamp",
          }),
          whiteSpace: "nowrap",
        }}
      >
        <span
          style={{
            fontFamily,
            fontWeight: 700,
            fontSize: 52,
            color: "#2D1E0F",
            letterSpacing: -1,
          }}
        >
          {productName}
        </span>
      </div>

      {/* Toast stack — positioned at bottom right, each pushed up by later ones */}
      <div
        style={{
          position: "absolute",
          right: 40,
          bottom: 200,
          width: 680,
        }}
      >
        {toastStartFrames.map((startFrame, index) => {
          const notif = NOTIFICATIONS[index];
          if (!notif) return null;

          const relFrame = cascadeFrame - startFrame;

          const slideProgress = spring({
            frame: relFrame,
            fps,
            config: { damping: 12, stiffness: 180, mass: 0.85 },
          });

          // Each toast visible from when it enters
          const isVisible = cascadeFrame >= startFrame - 5;
          if (!isVisible) return null;

          // How many toasts came after this one (push it upward)
          const toastsAfter = toastStartFrames.filter(
            (f) => f > startFrame && cascadeFrame >= f
          ).length;

          // Each toast card is ~100px tall including gap
          const TOAST_HEIGHT = 108;
          const stackOffsetY = toastsAfter * TOAST_HEIGHT;

          // Older toasts fade slightly for depth
          const ageFade = interpolate(toastsAfter, [0, 4, 7], [1, 0.75, 0.45], {
            extrapolateRight: "clamp",
          });

          return (
            <Toast
              key={notif.id}
              entry={notif}
              slideProgress={slideProgress}
              stackOffsetY={stackOffsetY}
              opacity={ageFade}
            />
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ─── Scene 4: CTA convergence ─────────────────────────────────────────────────

const CTAScene: React.FC<{
  productImage: string;
  productName: string;
  ctaText: string;
  brandColor: string;
  sceneFrame: number;
}> = ({ productImage, productName, ctaText, brandColor, sceneFrame }) => {
  const { fps } = useVideoConfig();

  // Trust bar slides down from top
  const trustBarEnter = spring({
    frame: sceneFrame,
    fps,
    config: { damping: 18, stiffness: 160 },
  });

  // Product surges back to prominence
  const productEnter = spring({
    frame: sceneFrame - 10,
    fps,
    config: { damping: 10, stiffness: 120, mass: 1.2 },
  });

  // Price + CTA rise from bottom
  const ctaEnter = spring({
    frame: sceneFrame - 30,
    fps,
    config: { damping: 12, stiffness: 150 },
  });

  // Sub-CTA text
  const subEnter = spring({
    frame: sceneFrame - 50,
    fps,
    config: { damping: 14, stiffness: 130 },
  });

  const trustBarY = interpolate(trustBarEnter, [0, 1], [-80, 0]);
  const productScale = interpolate(productEnter, [0, 1], [0.4, 1]);
  const ctaY = interpolate(ctaEnter, [0, 1], [60, 0]);

  // Confetti dots — deterministic positions seeded per index
  const CONFETTI_COUNT = 28;
  const confettiColors = [
    "#F97316", "#FBBF24", "#34D399", "#F87171",
    "#A78BFA", "#38BDF8", "#F472B6", "#FB923C",
  ];
  const confettiProgress = interpolate(sceneFrame, [40, 90], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        flexDirection: "column",
      }}
    >
      {/* Confetti dots drifting down */}
      {Array.from({ length: CONFETTI_COUNT }, (_, i) => {
        const startX = seededRandom(i * 7) * 1080;
        const drift = (seededRandom(i * 13) - 0.5) * 120;
        const speed = 0.6 + seededRandom(i * 3) * 0.8;
        const size = 8 + seededRandom(i * 17) * 14;
        const dotColor = confettiColors[i % confettiColors.length];
        const delay = seededRandom(i * 5) * 60; // frame delay
        const dotProgress = interpolate(
          sceneFrame,
          [delay, delay + 80],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        const dotY = dotProgress * 1000 * speed;
        const dotX = startX + drift * dotProgress;
        const dotOpacity = interpolate(
          dotProgress,
          [0, 0.1, 0.8, 1],
          [0, 0.8, 0.7, 0]
        );

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: -20,
              left: dotX,
              width: size,
              height: size,
              borderRadius: "50%",
              background: dotColor,
              transform: `translateY(${dotY}px)`,
              opacity: dotOpacity * confettiProgress,
              pointerEvents: "none",
            }}
          />
        );
      })}

      {/* Trust bar — slides in from top */}
      <div
        style={{
          width: "100%",
          paddingTop: 72,
          paddingBottom: 24,
          paddingLeft: 40,
          paddingRight: 40,
          transform: `translateY(${trustBarY}px)`,
          opacity: trustBarEnter,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            background: "rgba(255,255,255,0.82)",
            borderRadius: 60,
            paddingTop: 18,
            paddingBottom: 18,
            paddingLeft: 40,
            paddingRight: 40,
            display: "flex",
            alignItems: "center",
            gap: 24,
            boxShadow:
              "0 4px 24px rgba(180,100,40,0.12), 0 1px 4px rgba(0,0,0,0.06)",
            border: "1.5px solid rgba(255,255,255,0.9)",
          }}
        >
          <span style={{ fontFamily, fontWeight: 700, fontSize: 26, color: "#F59E0B" }}>
            ★ 4.9
          </span>
          <div
            style={{
              width: 1,
              height: 28,
              background: "rgba(180,140,100,0.3)",
            }}
          />
          <span style={{ fontFamily, fontWeight: 400, fontSize: 24, color: "#6B5140" }}>
            2,847 reviews
          </span>
          <div
            style={{
              width: 1,
              height: 28,
              background: "rgba(180,140,100,0.3)",
            }}
          />
          <span
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 22,
              color: "#EF4444",
              letterSpacing: 0.5,
              textTransform: "uppercase" as const,
            }}
          >
            Trending
          </span>
        </div>
      </div>

      {/* Product image — surges to center */}
      <div
        style={{
          width: 460,
          height: 460,
          borderRadius: "50%",
          overflow: "hidden",
          boxShadow:
            "0 40px 100px rgba(180,100,40,0.22), 0 10px 30px rgba(0,0,0,0.10)",
          transform: `scale(${productScale})`,
          opacity: productEnter,
          border: "5px solid rgba(255,255,255,0.9)",
          marginTop: 24,
        }}
      >
        <Img
          src={staticFile(productImage)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>

      {/* Product name */}
      <div
        style={{
          marginTop: 28,
          opacity: interpolate(productEnter, [0, 0.6], [0, 1], {
            extrapolateRight: "clamp",
          }),
          transform: `translateY(${interpolate(productEnter, [0, 1], [16, 0])}px)`,
        }}
      >
        <span
          style={{
            fontFamily,
            fontWeight: 700,
            fontSize: 46,
            color: "#2D1E0F",
            letterSpacing: -1,
          }}
        >
          {productName}
        </span>
      </div>

      {/* CTA button */}
      <div
        style={{
          marginTop: 44,
          transform: `translateY(${ctaY}px)`,
          opacity: ctaEnter,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
        }}
      >
        <div
          style={{
            background: brandColor,
            borderRadius: 72,
            paddingTop: 28,
            paddingBottom: 28,
            paddingLeft: 80,
            paddingRight: 80,
            boxShadow: `0 20px 56px ${brandColor}55`,
          }}
        >
          <span
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 38,
              color: "#FFFFFF",
              letterSpacing: 0.3,
            }}
          >
            {ctaText}
          </span>
        </div>

        {/* Social proof sub-line */}
        <div
          style={{
            transform: `translateY(${interpolate(subEnter, [0, 1], [16, 0])}px)`,
            opacity: subEnter,
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontFamily,
              fontWeight: 400,
              fontSize: 24,
              color: "#9B8070",
              letterSpacing: 0.2,
            }}
          >
            Join 12,847+ happy customers
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────

export const UGCTestimonial: React.FC<UGCTestimonialProps> = ({
  productName,
  productImage,
  rating,
  ctaText,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Background warmth drives through the whole video ────────────────────────
  // Scene 1: neutral creamy. Scene 3+: deeper peach as social proof density builds.

  const warmth = interpolate(
    frame,
    [SCENE_1_START, SCENE_3_START, SCENE_3_START + 100, SCENE_4_START],
    [0, 0, 0.7, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // ── Scene-local frame counters ───────────────────────────────────────────────

  const scene1Frame = frame - SCENE_1_START;
  const scene2Frame = frame - SCENE_2_START; // cascade scene uses this too
  const scene4Frame = frame - SCENE_4_START;

  // ── Fade between scenes ──────────────────────────────────────────────────────

  // Scene 1 fades out as scene 2 opens
  const scene1Opacity = interpolate(frame, [SCENE_2_START - 8, SCENE_2_START + 8], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Scene 2+3 (cascade) fades out as CTA opens
  const cascadeOpacity = interpolate(
    frame,
    [SCENE_4_START - 15, SCENE_4_START + 10],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Scene 4 fades in
  const scene4Opacity = interpolate(
    frame,
    [SCENE_4_START - 5, SCENE_4_START + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ fontFamily, overflow: "hidden" }}>
      {/* ── Warm background — always present ────────────────────── */}
      <WarmBackground warmth={warmth} />

      {/* ── Scene 1: Product reveal ──────────────────────────────── */}
      {frame < SCENE_2_START + 8 && (
        <AbsoluteFill style={{ opacity: scene1Opacity }}>
          <ProductRevealScene
            productImage={productImage}
            productName={productName}
            rating={rating}
            sceneFrame={scene1Frame}
          />
        </AbsoluteFill>
      )}

      {/* ── Scenes 2+3: Notification cascade ────────────────────── */}
      {frame >= SCENE_2_START - 5 && frame < SCENE_4_START + 10 && (
        <AbsoluteFill style={{ opacity: cascadeOpacity }}>
          <CascadeScene
            productImage={productImage}
            productName={productName}
            cascadeFrame={scene2Frame}
          />
        </AbsoluteFill>
      )}

      {/* ── Scene 4: CTA convergence ─────────────────────────────── */}
      {frame >= SCENE_4_START - 5 && (
        <AbsoluteFill style={{ opacity: scene4Opacity }}>
          <CTAScene
            productImage={productImage}
            productName={productName}
            ctaText={ctaText}
            brandColor={brandColor}
            sceneFrame={scene4Frame}
          />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
