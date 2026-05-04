// OASIS AI — YouTube intro card.
// Source of truth for colors / fonts / voice: brain/brand-assets/oasis-ai/BRAND_SYSTEM.md
// Production runbook: brain/playbooks/youtube_video_pipeline.md
// Edit this file ONLY with BRAND_SYSTEM.md open. Hex values + font choices are not arbitrary.
import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as loadFraunces } from "@remotion/google-fonts/Fraunces";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { z } from "zod";

const { fontFamily: fraunces } = loadFraunces("normal", { weights: ["300", "400", "600"] });
const { fontFamily: fraunces_italic } = loadFraunces("italic", { weights: ["300", "400", "600"] });
const { fontFamily: inter } = loadInter("normal", { weights: ["300", "400", "500"] });

export const OasisIntroCardSchema = z.object({
  line1: z.string(),
  line2: z.string(),
});

type Props = z.infer<typeof OasisIntroCardSchema>;

const FPS = 30;

const BRAND = {
  BG_DEEP: "#050B12",
  BG_PRIMARY: "#0A1525",
  CYAN_PRIMARY: "#1FE3F0",
  CYAN_SOFT: "#7AE8F0",
  OFF_WHITE: "#F0F4F8",
  STAR_DUST: "#3A4A5C",
};

const rand = (seed: number) => {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};

const PARTICLE_COUNT = 75;

const Starfield: React.FC<{ width: number; height: number; opacity: number }> = ({
  width,
  height,
  opacity,
}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: PARTICLE_COUNT }).map((_, i) => {
        const baseX = rand(i + 1) * width;
        const baseY = rand(i + 100) * height;
        const drift = 0.08 + rand(i + 200) * 0.18;
        const angle = rand(i + 300) * Math.PI * 2;
        const size = 1.0 + rand(i + 400) * 1.8;
        const twinkleSpeed = 0.03 + rand(i + 500) * 0.04;
        const twinklePhase = rand(i + 600) * Math.PI * 2;
        const isCyan = rand(i + 700) > 0.7;
        const x = ((baseX + Math.cos(angle) * frame * drift) % width + width) % width;
        const y = ((baseY + Math.sin(angle) * frame * drift) % height + height) % height;
        const twinkle = 0.25 + (Math.sin(frame * twinkleSpeed + twinklePhase) + 1) * 0.35;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background: isCyan ? BRAND.CYAN_PRIMARY : BRAND.OFF_WHITE,
              opacity: twinkle * opacity * (isCyan ? 0.7 : 0.55),
              boxShadow: isCyan
                ? `0 0 ${size * 6}px ${BRAND.CYAN_PRIMARY}80`
                : `0 0 ${size * 4}px rgba(240,244,248,0.5)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

export const OasisIntroCard: React.FC<Props> = ({ line1, line2 }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const line1Chars = line1.split("");
  const line2Chars = line2.split("");

  const starOpacity = interpolate(
    frame,
    [0, 25, 110, 150],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const breath = 1 + Math.sin(frame * 0.04) * 0.012;

  const cyanGlowIntensity = interpolate(
    frame,
    [60, 100, 130, 150],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const glowPulse = 0.5 + Math.sin(frame * 0.05) * 0.3;
  const glowSize = 30 + cyanGlowIntensity * glowPulse * 40;

  const textFadeOut = interpolate(frame, [115, 145], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textDisperse = interpolate(frame, [110, 150], [0, 24], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const vignetteIntensity = 0.45 + Math.sin(frame * 0.025) * 0.08;

  return (
    <AbsoluteFill style={{ background: BRAND.BG_PRIMARY, overflow: "hidden" }}>
      <Starfield width={width} height={height} opacity={starOpacity} />

      {/* Soft cyan radial glow behind text */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 50% 30% at 50% 50%, ${BRAND.CYAN_PRIMARY}10 0%, transparent 70%)`,
          opacity: cyanGlowIntensity * 0.8,
          pointerEvents: "none",
        }}
      />

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 90% 70% at 50% 50%, transparent 0%, ${BRAND.BG_DEEP}E0 100%)`,
          opacity: vignetteIntensity,
          pointerEvents: "none",
        }}
      />

      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 12,
          transform: `scale(${breath})`,
        }}
      >
        {/* Line 1 — primary serif (off-white) */}
        <div
          style={{
            fontFamily: fraunces,
            fontSize: 76,
            fontWeight: 400,
            color: BRAND.OFF_WHITE,
            letterSpacing: "-0.01em",
            display: "flex",
            opacity: textFadeOut,
            textShadow: `0 0 ${glowSize}px rgba(240,244,248,${0.1 + cyanGlowIntensity * 0.15})`,
          }}
        >
          {line1Chars.map((ch, i) => {
            const charDelay = 18 + i * 1.6;
            const p = spring({
              frame: frame - charDelay,
              fps: FPS,
              config: { damping: 18, stiffness: 90, mass: 1 },
              from: 0,
              to: 1,
            });
            const blur = (1 - p) * 14;
            const yOff = (1 - p) * 14;
            const dx = (rand(i + 700) - 0.5) * textDisperse;
            const dy = (rand(i + 800) - 0.5) * textDisperse;
            return (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  whiteSpace: "pre",
                  opacity: p,
                  transform: `translate(${dx}px, ${yOff + dy}px)`,
                  filter: `blur(${blur}px)`,
                }}
              >
                {ch === " " ? " " : ch}
              </span>
            );
          })}
        </div>

        {/* Line 2 — italic serif (cyan soft) */}
        <div
          style={{
            fontFamily: fraunces_italic,
            fontStyle: "italic",
            fontSize: 76,
            fontWeight: 400,
            color: BRAND.CYAN_SOFT,
            letterSpacing: "-0.01em",
            display: "flex",
            opacity: textFadeOut,
            textShadow: `0 0 ${glowSize * 1.2}px ${BRAND.CYAN_PRIMARY}${Math.round(cyanGlowIntensity * 0.6 * 255).toString(16).padStart(2, "0")}`,
          }}
        >
          {line2Chars.map((ch, i) => {
            const charDelay = 60 + i * 1.6;
            const p = spring({
              frame: frame - charDelay,
              fps: FPS,
              config: { damping: 18, stiffness: 90, mass: 1 },
              from: 0,
              to: 1,
            });
            const blur = (1 - p) * 14;
            const yOff = (1 - p) * 14;
            const dx = (rand(i + 1700) - 0.5) * textDisperse;
            const dy = (rand(i + 1800) - 0.5) * textDisperse;
            return (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  whiteSpace: "pre",
                  opacity: p,
                  transform: `translate(${dx}px, ${yOff + dy}px)`,
                  filter: `blur(${blur}px)`,
                }}
              >
                {ch === " " ? " " : ch}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* Thin cyan accent line — draws across slowly */}
      <div
        style={{
          position: "absolute",
          top: height * 0.5 + 100,
          left: width * 0.5,
          width: interpolate(frame, [50, 110], [0, 320], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          height: 1,
          background: `linear-gradient(90deg, transparent 0%, ${BRAND.CYAN_PRIMARY}99 50%, transparent 100%)`,
          transform: "translateX(-50%)",
          opacity: textFadeOut,
          boxShadow: `0 0 8px ${BRAND.CYAN_PRIMARY}66`,
        }}
      />

      {/* Tiny brand byline — bottom corner, very subtle */}
      <div
        style={{
          position: "absolute",
          bottom: 50,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: inter,
          fontSize: 14,
          fontWeight: 300,
          color: BRAND.STAR_DUST,
          letterSpacing: "0.32em",
          textTransform: "uppercase",
          opacity: interpolate(frame, [80, 110, 130, 150], [0, 0.5, 0.5, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        OASIS AI
      </div>
    </AbsoluteFill>
  );
};
