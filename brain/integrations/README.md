# Integrations — External Tools Wired Into Maven

> Third-party repos and skills that extend Maven's capabilities. Each entry below has a dedicated `.md` file in this folder with install commands, when-to-use rules, and pipeline integration notes.

| Tool | Role | Doc | Owner |
|---|---|---|---|
| **claude-video** | Video understanding (frames + transcript → Claude reads) for QA / research | [claude-video.md](claude-video.md) | Maven |
| **open-design** | Claude-Design alternative — HTML/PDF/PPTX/MP4 artifacts via skills + design systems | [open-design.md](open-design.md) | Maven |
| **graphify** | Knowledge graph generator (Obsidian vault export from any folder) | [graphify.md](graphify.md) | Bravo (Maven reads for cross-agent awareness) |

## Why integrations live here (not in `brain/playbooks/`)

`playbooks/` = end-to-end runbooks Maven executes (YouTube video pipeline, campaign launch, etc.). `integrations/` = reference docs for individual external tools. A playbook may *cite* an integration, but the integration doc is the source of truth for that tool's install/use.

## When to update

If a tool's API or install path changes, update its `.md` here AND any playbook that references it. The playbook is the consumer; the integration doc is the producer.
