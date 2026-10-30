# mod-multibot-bridge agent instructions

- For module work, use `.agents/skills/multibot-bridge-project/SKILL.md` and inspect the relevant code and `docs/project-context.md`.
- Follow AzerothCore style and preserve authorization, validation, protocol limits, session lifetime, and thread-safety invariants. Do not change Core, Playerbots, or the external addon unless requested.
- Choose checks proportional to the change. Build a compatible worldserver when needed; verify protocol changes across both sides when feasible. Distinguish build, tests, and live behavior in the result.
- Do not execute mutating SQL without prior user permission. Preserve unrelated changes and never commit secrets.
