# Config Reference

`config.yaml` controls runtime behavior.

## `zhihu`

- `cookie_file`: local cookie backup file path.

## `check`

- `interval_hours`: schedule hint only; real scheduling is done outside Python (Task Scheduler / cron).

## `answer_generator`

- `type`: `command` or `deep_research`.
- `command`: shell command template for command mode.
  - placeholders: `{title}`, `{content}`.

### `answer_generator.deep_research`

- `endpoint`: API endpoint URL.
- `token_env`: env var name containing auth token.
- `timeout_seconds`: request timeout.
- `concurrency`: API concurrency.

## `notification`

- `feishu_webhook`: optional Feishu incoming webhook URL.

## Environment Variables

- `CABINET_API_TOKEN`: token used by deep_research mode.
- `FEISHU_WEBHOOK_URL`: optional webhook fallback.
