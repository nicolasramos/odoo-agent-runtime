# Runtime configuration

The runtime can be configured through `.env` or command-line flags.

## Environment variables

```env
ODOO_URL=https://odoo.example.com
API_KEY=your-runtime-api-key
RUNTIME_NAME=agent-worker-01
POLL_INTERVAL=10
```

## CLI flags

```bash
python3 daemon.py \
  --odoo-url https://odoo.example.com \
  --api-key your-runtime-api-key \
  --name agent-worker-01 \
  --poll-interval 10
```

## Poll interval

Start with `10` seconds. Lower values feel more responsive but increase traffic. Higher values reduce traffic but make queues feel slower.

## Runtime name

Use stable names that identify the machine or workload:

- `linux-ci-agent-01`
- `mac-mini-design-01`
- `windows-qa-agent-01`

## API key rotation

1. Stop the daemon.
2. Generate a new API key in Odoo.
3. Update `.env`.
4. Start the daemon.
5. Confirm heartbeat.
6. Revoke or discard the old key.

## Agent CLI commands

The runtime executes the command configured on each Odoo agent.

Supported placeholders:

| Placeholder | Value |
| --- | --- |
| `{instruction}` | Full instruction text. |
| `{task_name}` | Execution name. |
| `{task_id}` | Execution ID. |
| `{model}` | Agent model. |

Example:

```text
opencode run --instruction {instruction}
```
