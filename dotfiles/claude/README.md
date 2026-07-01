# dotfiles/claude

The meaningful, secret-free parts of this user's `~/.claude/` config, kept here so they can be
copied onto a fresh machine: `CLAUDE.md`, the `graphify` and `cross-domain-brainstorm` skills,
`settings.json`, and `statusline-command.sh`.

`settings.json` is missing its top-level `env` key on purpose — that key held
`GITHUB_PERSONAL_ACCESS_TOKEN` on the source machine. Set `GITHUB_PERSONAL_ACCESS_TOKEN` (or
any other secret a fresh setup needs) locally in `~/.claude/settings.json` after copying; never
commit secrets into this repo.
