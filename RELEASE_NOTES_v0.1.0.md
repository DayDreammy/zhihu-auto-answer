# v0.1.0

Release date: 2026-03-05

## Highlights

- Converted the repository into a Codex skill source.
- Added `SKILL.md` and `agents/openai.yaml`.
- Added MIT `LICENSE`.
- Added `.env.example`.
- Added `references/config-reference.md`.
- Refreshed `README.md` for skill-first usage.
- Cleaned historical debug/screenshot/archive files from version control.

## Migration Notes

- Entry point remains `python main.py`.
- `config.yaml` deep_research endpoint now defaults to `http://127.0.0.1:9026/api/deep_research`.
- Skill installation from GitHub works with:

```powershell
python C:\Users\admin\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py `
  --repo DayDreammy/zhihu-auto-answer `
  --path . `
  --name zhihu-auto-answer
```
