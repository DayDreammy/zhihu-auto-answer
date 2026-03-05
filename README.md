# zhihu-auto-answer

Codex skill + Python automation project for processing Zhihu invitations and saving generated answers to drafts.

## What This Repo Is

- A runnable automation project (`main.py`, `zhihu_bot.py`)
- A Codex skill (`SKILL.md`, `agents/openai.yaml`)
- A reusable scheduler setup (`scripts/*.ps1`)

## Quick Start

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

First-time login:

```powershell
python main.py --login --user-data-dir .playwright-profile/zhihu
```

Run once:

```powershell
python main.py --headless --max-questions 10
```

## Config

- Main config: `config.yaml`
- Optional env: copy `.env.example` to `.env` and fill values.
- See [`references/config-reference.md`](references/config-reference.md) for fields.

## Codex Skill Usage

This repo is directly usable as a skill source.

- Skill name: `zhihu-auto-answer`
- Trigger intent: Zhihu auto-answer workflow, login/debug/scheduling for this bot.
- Skill instructions: [`SKILL.md`](SKILL.md)

## Open Source Notes

- Sensitive files are git-ignored: cookies, artifacts, profile dirs, `.env`.
- Do not commit real webhook URLs or tokens.
- Review Zhihu platform policies before running automation.

## License

MIT License. See [`LICENSE`](LICENSE).
