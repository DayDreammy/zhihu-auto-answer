---
name: zhihu-auto-answer
description: Automate Zhihu invitation processing with Playwright, including login, invitation fetch, answer generation (command/deep_research), and draft saving. Use when users ask for Zhihu auto-answer workflows, scheduled runs, or troubleshooting this repo.
---

# Zhihu Auto Answer

## Overview

This skill runs a Zhihu invitation-to-draft workflow:
- log in (QR code or persistent profile)
- fetch invitations
- generate answers (local command or deep_research API)
- save answers to Zhihu drafts
- send optional notifications

Primary entrypoint: `python main.py`

## When To Use

Use this skill when the user asks to:
- run or debug Zhihu auto-answer automation
- set up login and persistent browser profile
- configure answer generation command/API
- schedule recurring runs (Windows Task Scheduler scripts)
- inspect run artifacts and logs

## Quick Start

1. Install dependencies.

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

2. Configure `config.yaml` and optional `.env`.

3. First-time login (interactive QR code):

```powershell
python main.py --login --user-data-dir .playwright-profile/zhihu
```

4. Run once:

```powershell
python main.py --headless --max-questions 10
```

5. Deep-research mode (if configured):

```powershell
python main.py --headless --answer-type deep_research --max-questions 10 --flush-drafts-every 5
```

## Run Modes

- `--login`: login only, then persist auth/cookies.
- default run: process invitations and save drafts.
- `--answer-type command`: run `answer_generator.command` from config.
- `--answer-type deep_research`: call configured deep_research API.
- `--no-persistent-profile`: disable persistent profile and use cookie backup only.

## Scheduling (Windows)

- Create a daily scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_schtask_daily_4am.ps1 -TaskName ZhihuAutoAnswerDaily -StartTime 04:00
```

- Manual scheduled runner:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_daily_zhihu.ps1 -MaxQuestions 10 -FlushDraftsEvery 5
```

## Key Files

- `main.py`: unified CLI entrypoint.
- `zhihu_bot.py`: core bot implementation.
- `config.yaml`: runtime config.
- `references/config-reference.md`: config field reference.
- `scripts/create_schtask_daily_4am.ps1`: task registration.
- `scripts/run_daily_zhihu.ps1`: scheduled run wrapper.
- `logs/`: runtime logs.
- `artifacts/`: exported per-run artifacts.

## Safety Rules

- Never commit `zhihu_cookies.json`, `.env`, or `.playwright-profile/`.
- Keep webhook/token values in environment variables.
- Respect Zhihu platform rules and rate limits.
- Validate generated answers before publication.

## Troubleshooting

- Not logged in: run `python main.py --login`.
- Browser/profile issues: remove local `.playwright-profile/zhihu` and re-login.
- API timeout in deep_research: increase `timeout_seconds` in `config.yaml`.
- Empty invitation list: verify account has pending invitations and session is valid.
