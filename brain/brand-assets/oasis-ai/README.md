# OASIS AI — Brand Assets

This directory is the **canonical home** for everything that defines how OASIS AI looks, sounds, and feels in public.

## Files in here

```
brand-assets/oasis-ai/
├── README.md                  ← you are here (the wiring map)
├── BRAND_SYSTEM.md            ← source of truth (colors, fonts, voice, banned words)
├── logos/                     ← logo source files
│   └── oasis-ai-primary-square.jpg
├── colors/                    ← (palette swatch files, when added)
├── typography/                ← (font specimens / license docs, when added)
└── templates/                 ← pre-rendered branded clips ready to use
    ├── oasis-intro-card-v2.mp4
    ├── oasis-outro-card-v2.mp4
    ├── preview-intro-v2.png
    └── preview-outro-v2.png
```

## How everything connects

```
                    ┌──────────────────────────────────┐
                    │   CMO-Agent/CLAUDE.md            │  loads on every session
                    │   (entry point)                  │
                    └──────────────┬───────────────────┘
                                   │ points to
                    ┌──────────────▼───────────────────┐
                    │   BRAND_SYSTEM.md (this dir)     │  source of truth
                    │   • colors                       │
                    │   • typography                   │
                    │   • voice / banned words         │
                    │   • animation language           │
                    └──────────────┬───────────────────┘
                                   │ enforced by
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
   ┌──────────────────┐ ┌────────────────────┐ ┌───────────────────────┐
   │ Remotion         │ │ Pre-rendered       │ │ playbooks/            │
   │ compositions     │ │ templates/         │ │ youtube_video_pipeline│
   │ (.tsx)           │ │ (.mp4)             │ │ .md                   │
   │                  │ │                    │ │                       │
   │ Source code →    │ │ Output files →     │ │ Step-by-step runbook  │
   │ ad-engine/src/   │ │ drop into any cut  │ │ for end-to-end YT     │
   │ compositions/    │ │ without re-render  │ │ video → live URL      │
   └──────────────────┘ └────────────────────┘ └───────────────────────┘
                                   │
                                   │ logo also mirrored at
                                   ▼
                    ┌──────────────────────────────────┐
                    │ ad-engine/public/                │
                    │   oasis-ai-logo.jpg              │  Remotion staticFile()
                    └──────────────────────────────────┘

Memory pointers (auto-loaded every session):
  • reference_oasis_brand_system.md  → BRAND_SYSTEM.md (this dir)
  • reference_oasis_canonical_links.md → domain/booking/email
  • reference_late_api_large_uploads.md → R2 presign flow
  • feedback_late_account_verify.md  → check Late YouTube channel
  • feedback_just_post_dont_handoff.md → execute, don't hand off
```

## When to update what

| If you change... | Also update... |
|---|---|
| Brand color hex | `BRAND_SYSTEM.md` palette table → both Remotion compositions (`OasisIntroCard.tsx` and `OasisOutroCard.tsx`) → re-render templates → memory pointer summary |
| Logo file | Replace `logos/oasis-ai-primary-square.jpg` AND `ad-engine/public/oasis-ai-logo.jpg` (Remotion needs the mirror) → re-render outro template |
| Tagline / voice | `BRAND_SYSTEM.md` voice section → memory pointer summary if it's a major shift |
| Booking link or domain | `BRAND_SYSTEM.md` canonical links section → `memory/reference_oasis_canonical_links.md` → `Business-Empire-Agent/brain/USER.md` (mirror) → existing video descriptions if live |
| Pipeline workflow | `brain/playbooks/youtube_video_pipeline.md` |
| New brand asset (font, color, logo variant) | Drop in the right subfolder → add a row to `BRAND_SYSTEM.md` → mention in the memory pointer if it's load-bearing |

## When to read what (for an agent picking up the work)

1. Open `CMO-Agent/CLAUDE.md` → see the OASIS BRAND section.
2. Open `BRAND_SYSTEM.md` → load colors, fonts, voice into working memory.
3. If the task is a YouTube video: open `brain/playbooks/youtube_video_pipeline.md` and follow it step-by-step.
4. Before any final delivery: run the 7-point checklist at the bottom of `BRAND_SYSTEM.md`.
