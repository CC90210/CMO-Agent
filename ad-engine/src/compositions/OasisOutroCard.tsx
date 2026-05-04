// OASIS AI — YouTube outro card.
// Source of truth for colors / fonts / voice: brain/brand-assets/oasis-ai/BRAND_SYSTEM.md
// Production runbook: brain/playbooks/youtube_video_pipeline.md
// Logo file: public/oasis-ai-logo.jpg (mirror of brand-assets/oasis-ai/logos/oasis-ai-primary-square.jpg).
// Edit this file ONLY with BRAND_SYSTEM.md open. Hex values + font choices are not arbitrary.
import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as loadFraunces } from "@remotion/google-fonts/Fraunces";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { z } from "zod";

const { fontFamily: fraunces } = loadFraunces("normal", { weights: ["300", "400", "600"] });
const { fontFamily: fraunces_italic } = loadFraunces("italic", { weights: ["300", "400"] });
const { fontFamily: inter } = loadInter("normal", { weights: ["200", "300", "400", "500"] });

export const OasisOutroCardSchema = z.object({
  tagline: z.string(),
  cta: z.string().optional(),
  bookingUrl: z.string().optional(),
});

type Props = z.infer<typeof OasisOutroCardSchema>;

const FPS = 30;

const BRAND = {
  BG_DEEP: "#050B12",
  BG_PRIMARY: "#0A1525",
  CYAN_PRIMARY: "#1FE3F0",
  CYAN_SOFT: "#7AE8F0",
  OFF_WHITE: "#F0F4F8",
  BODY_GRAY: "#A8B5C2",
  STAR_DUST: "#3A4A5C",
};

const rand = (seed: number) => {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};

const PARTICLE_COUNT = 100;

const Starfield: React.FC<{
  width: number;
  height: number;
  opacity: number;
  pullToCenter: number;
}> = ({ width, height, opacity, pullToCenter }) => {
  const frame = useCurrentFrame();
  const cx = width / 2;
  const cy = height * 0.42;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: PARTICLE_COUNT }).map((_, i) => {
        const baseX = rand(i + 1) * width;
        const baseY = rand(i + 100) * height;
        const drift = 0.06 + rand(i + 200) * 0.16;
        const angle = rand(i + 300) * Math.PI * 2;
        const size = 0.8 + rand(i + 400) * 2.0;
        const twinkleSpeed = 0.025 + rand(i + 500) * 0.04;
        const twinklePhase = rand(i + 600) * Math.PI * 2;
        const isCyan = rand(i + 700) > 0.65;
        const driftX = ((baseX + Math.cos(angle) * frame * drift) % width + width) % width;
        const driftY = ((baseY + Math.sin(angle) * frame * drift) % height + height) % height;
        // Pull toward center
        const dx = cx - driftX;
        const dy = cy - driftY;
        const pullStrength = pullToCenter * (0.2 + rand(i + 800) * 0.7);
        const fx = driftX + dx * pullStrength;
        const fy = driftY + dy * pullStrength;
        const twinkle = 0.25 + (Math.sin(frame * twinkleSpeed + twinklePhase) + 1) * 0.4;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: fx,
              top: fy,
              width: size,
              height: size,
              borderRadius: "50%",
              background: isCyan ? BRAND.CYAN_PRIMARY : BRAND.OFF_WHITE,
              opacity: twinkle * opacity * (1 - pullToCenter * 0.5) * (isCyan ? 0.75 : 0.55),
              boxShadow: isCyan
                ? `0 0 ${size * 7}px ${BRAND.CYAN_PRIMARY}90`
                : `0 0 ${size * 4}px rgba(240,244,248,0.5)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

export const OasisOutroCard: React.FC<Props> = ({ tagline, cta, bookingUrl }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // Stage timing (fps 30, 240 frames = 8 sec):
  // 0-30:    starfield fades in
  // 30-90:   logo materializes (bloom-up)
  // 60-130:  particle pull toward center
  // 100-160: tagline reveals word by word
  // 160-200: CTA reveals
  // 200-240: hold + final fade out

  const starOpacity = interpolate(frame, [0, 30, 200, 240], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const particlePull = interpolate(frame, [60, 130], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const logoProgress = spring({
    frame: frame - 30,
    fps: FPS,
    config: { damping: 16, stiffness: 70, mass: 1.2 },
    from: 0,
    to: 1,
  });
  const logoScale = 0.7 + logoProgress * 0.3;
  const logoBlur = (1 - logoProgress) * 18;
  const logoOpacity = logoProgress;

  // Glow oscillation behind logo after it forms
  const logoGlowBase = interpolate(frame, [70, 130, 200], [0, 1, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const logoGlowPulse = logoGlowBase * (0.6 + Math.sin(frame * 0.045) * 0.4);

  // Breath
  const breath = 1 + Math.sin(frame * 0.035) * 0.008;

  // Vignette pulse
  const vignettePulse = 0.5 + Math.sin(frame * 0.022) * 0.08;

  // Final fade + slight scale-up
  const finalScale = interpolate(frame, [200, 240], [1, 1.04], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const finalFade = interpolate(frame, [210, 240], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const taglineWords = tagline.split(" ");

  const logoSize = 360;
  const logoCenterY = height * 0.42;

  return (
    <AbsoluteFill
      style={{
        background: BRAND.BG_PRIMARY,
        overflow: "hidden",
        transform: `scale(${finalScale})`,
        opacity: finalFade,
      }}
    >
      <Starfield width={width} height={height} opacity={starOpacity} pullToCenter={particlePull} />

      {/* Cyan glow halo behind logo */}
      <div
        style={{
          position: "absolute",
          left: width / 2 - 250,
          top: logoCenterY - 250,
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${BRAND.CYAN_PRIMARY}30 0%, transparent 70%)`,
          opacity: logoGlowPulse,
          pointerEvents: "none",
          filter: "blur(20px)",
        }}
      />

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 90% 70% at 50% 50%, transparent 0%, ${BRAND.BG_DEEP}E5 100%)`,
          opacity: vignettePulse,
          pointerEvents: "none",
        }}
      />

      {/* Logo */}
      <div
        style={{
          position: "absolute",
          left: width / 2 - logoSize / 2,
          top: logoCenterY - logoSize / 2,
          width: logoSize,
          height: logoSize,
          opacity: logoOpacity,
          transform: `scale(${logoScale * breath})`,
          filter: `blur(${logoBlur}px) drop-shadow(0 0 ${30 + logoGlowPulse * 40}px ${BRAND.CYAN_PRIMARY}80)`,
        }}
      >
        <Img
          src={staticFile("oasis-ai-logo.jpg")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            mixBlendMode: "screen",
          }}
        />
      </div>

      {/* Tagline — Fraunces italic, word by word */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: logoCenterY + logoSize / 2 + 30,
          textAlign: "center",
          fontFamily: fraunces_italic,
          fontStyle: "italic",
          fontSize: 38,
          fontWeight: 300,
          color: BRAND.CYAN_SOFT,
          letterSpacing: "-0.005em",
          textShadow: `0 0 30px ${BRAND.CYAN_PRIMARY}40`,
          padding: "0 100px",
        }}
      >
        {taglineWords.map((word, i) => {
          const wordDelay = 100 + i * 5;
          const p = spring({
            frame: frame - wordDelay,
            fps: FPS,
            config: { damping: 18, stiffness: 90, mass: 1 },
            from: 0,
            to: 1,
          });
          const yOff = (1 - p) * 12;
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                opacity: p,
                transform: `translateY(${yOff}px)`,
                marginRight: "0.3em",
              }}
            >
              {word}
            </span>
          );
        })}
      </div>

      {/* CTA / booking line */}
      {(cta || bookingUrl) && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 90,
            textAlign: "center",
            opacity: interpolate(frame, [165, 200], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            transform: `translateY(${interpolate(frame, [165, 200], [10, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
          }}
        >
          {cta && (
            <div
              style={{
                fontFamily: inter,
                fontSize: 18,
                fontWeight: 400,
                color: BRAND.BODY_GRAY,
                letterSpacing: "0.04em",
                marginBottom: 10,
              }}
            >
              {cta}
            </div>
          )}
          {bookingUrl && (
            <div
              style={{
                fontFamily: inter,
                fontSize: 22,
                fontWeight: 500,
                color: BRAND.CYAN_PRIMARY,
                letterSpacing: "0.02em",
                textShadow: `0 0 20px ${BRAND.CYAN_PRIMARY}66`,
              }}
            >
              {bookingUrl}
            </div>
          )}
        </div>
      )}

      {/* Domain footer — very subtle */}
      <div
        style={{
          position: "absolute",
          bottom: 30,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: inter,
          fontSize: 13,
          fontWeight: 300,
          color: BRAND.STAR_DUST,
          letterSpacing: "0.4em",
          textTransform: "uppercase",
          opacity: interpolate(frame, [180, 210], [0, 0.6], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        OASISAI.WORK
      </div>
    </AbsoluteFill>
  );
};
