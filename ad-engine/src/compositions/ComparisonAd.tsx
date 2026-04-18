import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { z } from "zod";

// ─── Fonts (module scope — REQUIRED by Remotion) ─────────────────────────────
const { fontFamily } = loadFont("normal", { weights: ["400", "700"] });

// ─── Schema ───────────────────────────────────────────────────────────────────
export const ComparisonAdSchema = z.object({
  headline: z.string(),
  ourProduct: z.string(),
  competitor: z.string(),
  ourPrice: z.string(),
  competitorPrice: z.string(),
  comparisons: z.array(
    z.object({
      feature: z.string(),
      ours: z.string(),
      theirs: z.string(),
    })
  ),
  ctaText: z.string(),
  brandColor: z.string(),
});

type ComparisonAdProps = z.infer<typeof ComparisonAdSchema>;

// ─── Scene timing ─────────────────────────────────────────────────────────────
// Scene 1: frames   0– 90  "WITHOUT" side + mystery right side   (3 s)
// Scene 2: frames  90–180  Wipe reveal                            (3 s)
// Scene 3: frames 180–330  Metric comparison rows                 (5 s)
// Scene 4: frames 330–450  CTA                                    (4 s)

// ─── Colour constants ─────────────────────────────────────────────────────────
const WITHOUT_BG = "#E8E8EC";   // dull gray-blue
const WITHOUT_LABEL = "#8B8B99";
const WITH_BG = "#FFFFFF";
const CHECK_GREEN = "#22C55E";
const CROSS_RED = "#EF4444";
const MYSTERY_BG = "#D0D0D8";
const DIVIDER_WHITE = "#FFFFFF";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function clampedInterpolate(
  frame: number,
  [inStart, inEnd]: [number, number],
  [outStart, outEnd]: [number, number]
): number {
  return interpolate(frame, [inStart, inEnd], [outStart, outEnd], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}

function fadeIn(frame: number, start: number, duration = 18): number {
  return clampedInterpolate(frame, [start, start + duration], [0, 1]);
}

function springIn(
  frame: number,
  start: number,
  fps: number,
  damping = 16,
  stiffness = 140
): number {
  return spring({
    frame: frame - start,
    fps,
    config: { damping, stiffness, mass: 1 },
  });
}

// Gentle pulse: oscillates 0→1→0 on a sine curve for the "?" and divider glow
function pulse(frame: number, period = 45): number {
  return 0.5 + 0.5 * Math.sin((frame / period) * Math.PI * 2);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Red-tinted weakness item that shakes briefly on entrance */
const WeaknessItem: React.FC<{
  text: string;
  frame: number;
  enterFrame: number;
  fps: number;
}> = ({ text, frame, enterFrame, fps }) => {
  const op = fadeIn(frame, enterFrame, 15);
  const slideX = clampedInterpolate(frame, [enterFrame, enterFrame + 20], [-24, 0]);

  // Shake: tiny rapid oscillation during the first 12 frames after entrance
  const shakeProgress = clampedInterpolate(frame, [enterFrame, enterFrame + 12], [0, 1]);
  const shakeX =
    shakeProgress < 1
      ? Math.sin((frame - enterFrame) * 3.2) * 5 * (1 - shakeProgress)
      : 0;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        opacity: op,
        transform: `translateX(${slideX + shakeX}px)`,
        marginBottom: 18,
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: "50%",
          background: "rgba(239,68,68,0.15)",
          border: `2px solid ${CROSS_RED}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily,
            fontSize: 18,
            fontWeight: 700,
            color: CROSS_RED,
            lineHeight: 1,
          }}
        >
          ✗
        </span>
      </div>
      <span
        style={{
          fontFamily,
          fontSize: 30,
          fontWeight: 400,
          color: "#5A5A72",
          lineHeight: 1.2,
        }}
      >
        {text}
      </span>
    </div>
  );
};

/** Green feature item that springs in on the "WITH" side */
const FeatureItem: React.FC<{
  text: string;
  frame: number;
  enterFrame: number;
  fps: number;
}> = ({ text, frame, enterFrame, fps }) => {
  const op = fadeIn(frame, enterFrame, 12);
  const scl = springIn(frame, enterFrame, fps, 14, 200);
  const slideX = clampedInterpolate(frame, [enterFrame, enterFrame + 18], [20, 0]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        opacity: op,
        transform: `translateX(${slideX}px) scale(${interpolate(scl, [0, 1], [0.8, 1])})`,
        marginBottom: 18,
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: "50%",
          background: "rgba(34,197,94,0.18)",
          border: `2px solid ${CHECK_GREEN}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily,
            fontSize: 18,
            fontWeight: 700,
            color: CHECK_GREEN,
            lineHeight: 1,
          }}
        >
          ✓
        </span>
      </div>
      <span
        style={{
          fontFamily,
          fontSize: 30,
          fontWeight: 400,
          color: "#1A1A2E",
          lineHeight: 1.2,
        }}
      >
        {text}
      </span>
    </div>
  );
};

/** A single metric comparison row */
const MetricRow: React.FC<{
  feature: string;
  ours: string;
  theirs: string;
  frame: number;
  enterFrame: number;
  fps: number;
  brandColor: string;
}> = ({ feature, ours, theirs, frame, enterFrame, fps, brandColor }) => {
  const op = fadeIn(frame, enterFrame, 14);
  const slideY = clampedInterpolate(frame, [enterFrame, enterFrame + 22], [30, 0]);
  const scl = springIn(frame, enterFrame, fps, 16, 160);

  return (
    <div
      style={{
        opacity: op,
        transform: `translateY(${slideY}px)`,
        display: "flex",
        flexDirection: "row",
        alignItems: "stretch",
        gap: 8,
        marginBottom: 16,
      }}
    >
      {/* Ours — larger, vibrant */}
      <div
        style={{
          flex: 1,
          background: `${brandColor}18`,
          border: `2px solid ${brandColor}`,
          borderRadius: 20,
          padding: "20px 16px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${interpolate(scl, [0, 1], [0.92, 1])})`,
        }}
      >
        <span
          style={{
            fontFamily,
            fontSize: 18,
            fontWeight: 400,
            color: "#555",
            marginBottom: 6,
            textAlign: "center",
          }}
        >
          {feature}
        </span>
        <span
          style={{
            fontFamily,
            fontSize: 34,
            fontWeight: 700,
            color: brandColor,
            textAlign: "center",
            lineHeight: 1.1,
          }}
        >
          {ours}
        </span>
      </div>

      {/* Connector "vs" */}
      <div
        style={{
          width: 48,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily,
            fontSize: 20,
            fontWeight: 700,
            color: "#BBBBC8",
          }}
        >
          vs
        </span>
      </div>

      {/* Theirs — muted, smaller */}
      <div
        style={{
          flex: 1,
          background: "rgba(0,0,0,0.04)",
          border: "2px solid #DDDDE8",
          borderRadius: 20,
          padding: "20px 16px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          opacity: 0.7,
        }}
      >
        <span
          style={{
            fontFamily,
            fontSize: 18,
            fontWeight: 400,
            color: "#999",
            marginBottom: 6,
            textAlign: "center",
          }}
        >
          {feature}
        </span>
        <span
          style={{
            fontFamily,
            fontSize: 28,
            fontWeight: 700,
            color: "#AAAABC",
            textAlign: "center",
            lineHeight: 1.1,
            textDecoration: "line-through",
          }}
        >
          {theirs}
        </span>
      </div>
    </div>
  );
};

// ─── Main composition ─────────────────────────────────────────────────────────

export const ComparisonAd: React.FC<ComparisonAdProps> = ({
  headline,
  ourProduct,
  competitor,
  ourPrice,
  competitorPrice,
  comparisons,
  ctaText,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // ── Shared layout ──────────────────────────────────────────────────────────
  const PADDING = 40;

  // ── Scene 1 (0–90): WITHOUT side + mystery right ──────────────────────────
  const scene1LabelOp = fadeIn(frame, 8, 20);
  const scene1WeaknessBaseFrame = 22;
  const scene1WeaknessStagger = 14;

  // Right "mystery" side — blurred dark overlay
  const mysteryPulseAmt = pulse(frame, 50);

  // ── Scene 2 (90–180): Wipe reveal ─────────────────────────────────────────
  // The divider line position: starts at 55% (of width), sweeps to 0% over 60 frames
  // clip-path on the WITH side expands from right as the wipe progresses
  const wipeProgress = clampedInterpolate(frame, [90, 150], [0, 1]);
  // Divider X in pixels
  const dividerX = interpolate(wipeProgress, [0, 1], [width * 0.55, 0]);

  // Divider glow — brightest during wipe
  const dividerGlowOpacity = clampedInterpolate(frame, [85, 100], [0, 1]);
  const dividerWipeGlow =
    frame >= 90 && frame <= 160
      ? interpolate(frame, [90, 140, 160], [1, 1, 0.3], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : clampedInterpolate(frame, [80, 95], [0, 0.4]);

  // As wipe moves, the left side desaturates further (CSS filter via opacity layers)
  const leftExtraDim = clampedInterpolate(frame, [90, 165], [0, 0.35]);

  // WITH-side features appear as the wipe passes over them
  // Product label appears at frame 100
  const withLabelOp = fadeIn(frame, 105, 16);
  const withFeatureBaseFrame = 115;
  const withFeatureStagger = 10;

  // ── Scene 3 (180–330): Metric cards ───────────────────────────────────────
  // Split sides shrink to cards at top, then metric rows slide in below
  const CARDS_SHRINK_START = 180;
  const cardsProgress = clampedInterpolate(
    frame,
    [CARDS_SHRINK_START, CARDS_SHRINK_START + 35],
    [0, 1]
  );
  // Cards shrink from full screen to small floating cards
  const cardScale = interpolate(cardsProgress, [0, 1], [1, 0.38]);
  const cardY = interpolate(cardsProgress, [0, 1], [0, 48]); // settle near top

  const METRICS_START = 230;
  const metricStagger = 28;

  // WINNER badge
  const winnerBadgeScale = springIn(frame, METRICS_START + comparisons.length * metricStagger + 10, fps, 9, 220);
  const winnerBadgeOp = fadeIn(frame, METRICS_START + comparisons.length * metricStagger + 10, 12);

  // ── Scene 4 (330–450): CTA ────────────────────────────────────────────────
  // Cards + metrics slide up and compress off screen
  const ctaSlideProgress = clampedInterpolate(frame, [330, 375], [0, 1]);
  const ctaContentY = interpolate(ctaSlideProgress, [0, 1], [height, 0]);

  const productCenterScale = springIn(frame, 355, fps, 10, 140);
  const priceFadeOp = fadeIn(frame, 370, 18);
  const ctaBtnScale = springIn(frame, 385, fps, 12, 180);
  const ctaBtnOp = fadeIn(frame, 385, 14);
  const trustOp = fadeIn(frame, 405, 16);

  // Scene 3 content pushes up during scene 4
  const scene3PushUp = clampedInterpolate(frame, [330, 370], [0, -height * 0.6]);

  // ─── Calculate WITH-side clip (reveals left-to-right as divider sweeps left)
  // clipPath covers the full-height panel: reveals from right side
  // At wipeProgress=0: with panel clip starts at x=55% width, revealing nothing
  // At wipeProgress=1: clip starts at 0, revealing everything
  const withClipLeftPx = interpolate(wipeProgress, [0, 1], [width * 0.55, 0]);

  // In scene 3+, both panels need to be visible fully
  const withClipFinal = frame >= 180 ? 0 : withClipLeftPx;

  // ─── Without-side saturation filter: gets grayer as wipe progresses ────────
  const withoutSaturation = clampedInterpolate(frame, [90, 165], [100, 40]);

  // ─── Scenes 1-3 overall opacity (fades out during scene 4) ─────────────────
  const splitScreenOp = clampedInterpolate(frame, [330, 368], [1, 0]);

  return (
    <AbsoluteFill
      style={{ background: "#F5F5F8", fontFamily, overflow: "hidden" }}
    >
      {/* ════════════════════════════════════════════════════════════════════
          SCENES 1–3: Split screen (fades away in scene 4)
      ════════════════════════════════════════════════════════════════════ */}
      <AbsoluteFill
        style={{ opacity: frame < 330 ? 1 : splitScreenOp, overflow: "hidden" }}
      >
        {/* ── Headline bar at very top ──────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 120,
            background: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 20,
            boxShadow: "0 2px 20px rgba(0,0,0,0.06)",
            opacity: clampedInterpolate(frame, [0, 20], [0, 1]),
            transform: `translateY(${clampedInterpolate(frame, [0, 22], [-30, 0])}px)`,
          }}
        >
          <span
            style={{
              fontFamily,
              fontSize: 38,
              fontWeight: 700,
              color: "#1A1A2E",
              letterSpacing: "-0.01em",
            }}
          >
            {headline}
          </span>
        </div>

        {/* ════════════ Scene 3 wrapper: cards shrink + metric rows ════════ */}
        <AbsoluteFill
          style={{
            top: 120,
            transform: `translateY(${frame >= 330 ? scene3PushUp : 0}px)`,
          }}
        >
          {/* ═══ CARD WRAPPER (both panels live here, shrink during scene 3) ═══ */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              // Full height in scenes 1-2, shrinks to card height in scene 3
              height:
                frame < CARDS_SHRINK_START
                  ? height - 120
                  : interpolate(cardsProgress, [0, 1], [height - 120, 340]),
              display: "flex",
              flexDirection: "row",
              overflow: "hidden",
            }}
          >
            {/* ─── WITHOUT panel (LEFT) ─────────────────────────────────── */}
            <div
              style={{
                flex: 1,
                background: WITHOUT_BG,
                position: "relative",
                overflow: "hidden",
                filter: `saturate(${withoutSaturation}%)`,
              }}
            >
              {/* Extra dim overlay that deepens after wipe */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background: `rgba(100,100,120,${leftExtraDim})`,
                  pointerEvents: "none",
                  zIndex: 2,
                }}
              />

              {/* WITHOUT label */}
              <div
                style={{
                  position: "absolute",
                  top: 28,
                  left: 0,
                  right: 0,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  opacity: scene1LabelOp,
                  zIndex: 3,
                }}
              >
                <span
                  style={{
                    fontFamily,
                    fontSize: 20,
                    fontWeight: 700,
                    color: WITHOUT_LABEL,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                  }}
                >
                  WITHOUT
                </span>
                <span
                  style={{
                    fontFamily,
                    fontSize: 28,
                    fontWeight: 700,
                    color: "#9090A0",
                    marginTop: 4,
                    textAlign: "center",
                    paddingInline: 12,
                  }}
                >
                  {competitor}
                </span>
              </div>

              {/* Weakness list */}
              <div
                style={{
                  position: "absolute",
                  top: 140,
                  left: 24,
                  right: 16,
                  zIndex: 3,
                }}
              >
                {comparisons.map((c, i) => (
                  <WeaknessItem
                    key={c.feature}
                    text={c.theirs}
                    frame={frame}
                    enterFrame={scene1WeaknessBaseFrame + i * scene1WeaknessStagger}
                    fps={fps}
                  />
                ))}
              </div>
            </div>

            {/* ─── WITH panel (RIGHT) — clipped until wipe reveals it ─────── */}
            <div
              style={{
                flex: 1,
                position: "relative",
                overflow: "hidden",
                // Clip from left: reveals as divider sweeps left
                clipPath: `inset(0 0 0 ${withClipFinal}px)`,
              }}
            >
              {/* WITH background */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background: WITH_BG,
                  // Subtle brand color wash
                  backgroundImage: `radial-gradient(ellipse at 60% 40%, ${brandColor}22 0%, transparent 70%)`,
                }}
              />

              {/* Mystery overlay: visible before wipe starts (frame < 90) */}
              {frame < 90 && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: MYSTERY_BG,
                    zIndex: 5,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <div
                    style={{
                      width: 100,
                      height: 100,
                      borderRadius: "50%",
                      background: `rgba(0,0,0,${0.08 + mysteryPulseAmt * 0.06})`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      transform: `scale(${0.92 + mysteryPulseAmt * 0.08})`,
                    }}
                  >
                    <span
                      style={{
                        fontFamily,
                        fontSize: 52,
                        fontWeight: 700,
                        color: "rgba(0,0,0,0.25)",
                      }}
                    >
                      ?
                    </span>
                  </div>
                </div>
              )}

              {/* WITH label */}
              <div
                style={{
                  position: "absolute",
                  top: 28,
                  left: 0,
                  right: 0,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  opacity: withLabelOp,
                  zIndex: 3,
                }}
              >
                <span
                  style={{
                    fontFamily,
                    fontSize: 20,
                    fontWeight: 700,
                    color: brandColor,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                  }}
                >
                  WITH
                </span>
                <span
                  style={{
                    fontFamily,
                    fontSize: 28,
                    fontWeight: 700,
                    color: "#1A1A2E",
                    marginTop: 4,
                    textAlign: "center",
                    paddingInline: 12,
                  }}
                >
                  {ourProduct}
                </span>
              </div>

              {/* Feature list */}
              <div
                style={{
                  position: "absolute",
                  top: 140,
                  left: 16,
                  right: 24,
                  zIndex: 3,
                }}
              >
                {comparisons.map((c, i) => (
                  <FeatureItem
                    key={c.feature}
                    text={c.ours}
                    frame={frame}
                    enterFrame={withFeatureBaseFrame + i * withFeatureStagger}
                    fps={fps}
                  />
                ))}
              </div>
            </div>

            {/* ─── Divider line ─────────────────────────────────────────── */}
            <div
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: dividerX,
                width: 4,
                zIndex: 10,
                background: DIVIDER_WHITE,
                boxShadow:
                  frame >= 85
                    ? `0 0 ${24 + dividerWipeGlow * 28}px ${dividerWipeGlow * 12}px ${brandColor}BB, 0 0 8px 2px ${DIVIDER_WHITE}`
                    : "none",
                opacity:
                  frame >= 90
                    ? dividerGlowOpacity
                    : clampedInterpolate(frame, [0, 18], [0, 1]),
                transition: "none",
              }}
            />
          </div>

          {/* ═══ SCENE 3: Metric rows (below the cards) ═════════════════════ */}
          {frame >= METRICS_START && (
            <div
              style={{
                position: "absolute",
                top: interpolate(cardsProgress, [0, 1], [height - 120, 348]),
                left: PADDING,
                right: PADDING,
                opacity: clampedInterpolate(frame, [METRICS_START - 10, METRICS_START + 10], [0, 1]),
              }}
            >
              {/* Price row first */}
              <MetricRow
                feature="Price"
                ours={ourPrice}
                theirs={competitorPrice}
                frame={frame}
                enterFrame={METRICS_START}
                fps={fps}
                brandColor={brandColor}
              />

              {/* Comparison rows */}
              {comparisons.map((c, i) => (
                <MetricRow
                  key={c.feature}
                  feature={c.feature}
                  ours={c.ours}
                  theirs={c.theirs}
                  frame={frame}
                  enterFrame={METRICS_START + (i + 1) * metricStagger}
                  fps={fps}
                  brandColor={brandColor}
                />
              ))}

              {/* WINNER badge */}
              <div
                style={{
                  marginTop: 20,
                  display: "flex",
                  justifyContent: "center",
                  opacity: winnerBadgeOp,
                  transform: `scale(${interpolate(winnerBadgeScale, [0, 1], [0.6, 1])})`,
                }}
              >
                <div
                  style={{
                    background: brandColor,
                    borderRadius: 60,
                    paddingTop: 16,
                    paddingBottom: 16,
                    paddingLeft: 48,
                    paddingRight: 48,
                    boxShadow: `0 8px 32px ${brandColor}55`,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                  }}
                >
                  <span style={{ fontSize: 32 }}>🏆</span>
                  <span
                    style={{
                      fontFamily,
                      fontSize: 32,
                      fontWeight: 700,
                      color: "#FFFFFF",
                      letterSpacing: "0.04em",
                    }}
                  >
                    {ourProduct} WINS
                  </span>
                </div>
              </div>
            </div>
          )}
        </AbsoluteFill>
      </AbsoluteFill>

      {/* ════════════════════════════════════════════════════════════════════
          SCENE 4: CTA (slides up from bottom, renders above everything)
      ════════════════════════════════════════════════════════════════════ */}
      <AbsoluteFill
        style={{
          transform: `translateY(${ctaContentY}px)`,
          background: "#FFFFFF",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          paddingInline: PADDING,
          gap: 0,
        }}
      >
        {/* Radial brand color wash */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `radial-gradient(ellipse at 50% 40%, ${brandColor}14 0%, transparent 65%)`,
            pointerEvents: "none",
          }}
        />

        {/* Product name */}
        <div
          style={{
            transform: `scale(${interpolate(productCenterScale, [0, 1], [0.88, 1])})`,
            opacity: clampedInterpolate(frame, [355, 372], [0, 1]),
            textAlign: "center",
            marginBottom: 12,
          }}
        >
          <span
            style={{
              fontFamily,
              fontSize: 52,
              fontWeight: 700,
              color: "#1A1A2E",
              letterSpacing: "-0.02em",
              lineHeight: 1.1,
            }}
          >
            {ourProduct}
          </span>
        </div>

        {/* Price block */}
        <div
          style={{
            opacity: priceFadeOp,
            display: "flex",
            flexDirection: "row",
            alignItems: "baseline",
            gap: 16,
            marginBottom: 48,
          }}
        >
          <span
            style={{
              fontFamily,
              fontSize: 72,
              fontWeight: 700,
              color: brandColor,
              letterSpacing: "-0.03em",
            }}
          >
            {ourPrice}
          </span>
          <span
            style={{
              fontFamily,
              fontSize: 38,
              fontWeight: 400,
              color: "#AAAABC",
              textDecoration: "line-through",
            }}
          >
            {competitorPrice}
          </span>
        </div>

        {/* CTA button */}
        <div
          style={{
            opacity: ctaBtnOp,
            transform: `scale(${interpolate(ctaBtnScale, [0, 1], [0.7, 1])})`,
            background: brandColor,
            borderRadius: 60,
            paddingTop: 32,
            paddingBottom: 32,
            paddingLeft: 80,
            paddingRight: 80,
            boxShadow: `0 16px 48px ${brandColor}55, 0 4px 12px rgba(0,0,0,0.1)`,
            marginBottom: 28,
          }}
        >
          <span
            style={{
              fontFamily,
              fontSize: 44,
              fontWeight: 700,
              color: "#FFFFFF",
              letterSpacing: "0.02em",
              textTransform: "uppercase",
            }}
          >
            {ctaText}
          </span>
        </div>

        {/* Make the switch line */}
        <div
          style={{
            opacity: clampedInterpolate(frame, [395, 412], [0, 1]),
            marginBottom: 16,
          }}
        >
          <span
            style={{
              fontFamily,
              fontSize: 32,
              fontWeight: 700,
              color: "#1A1A2E",
            }}
          >
            Make the switch today.
          </span>
        </div>

        {/* Trust line */}
        <div style={{ opacity: trustOp }}>
          <span
            style={{
              fontFamily,
              fontSize: 26,
              fontWeight: 400,
              color: "#9090A8",
            }}
          >
            30-day money back guarantee
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
