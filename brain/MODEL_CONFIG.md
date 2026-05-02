version: 1
defaults:
  provider: claude
  model: claude-sonnet-4-6
  fallbacks:
  - provider: claude
    model: claude-haiku-4-5
  - provider: openrouter
    model: anthropic/claude-3.5-sonnet
agents:
  maven:
    provider: claude
    model: claude-sonnet-4-6
    fallbacks:
    - provider: claude
      model: claude-haiku-4-5
    - provider: openrouter
      model: anthropic/claude-3.5-sonnet
task_types:
  caption_writing:
    provider: claude
    model: claude-sonnet-4-6
  hook_generation:
    provider: claude
    model: claude-haiku-4-5
  script_writing:
    provider: claude
    model: claude-opus-4-7
  ad_copy:
    provider: claude
    model: claude-sonnet-4-6
