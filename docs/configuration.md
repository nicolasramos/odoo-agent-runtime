# Runtime configuration

The runtime can be configured through `.env` or command-line flags.

## Environment variables

```env
ODOO_URL=https://odoo.example.com
API_KEY=your-runtime-api-key
# Optional: select this Odoo database before runtime API calls.
ODOO_DATABASE=production
RUNTIME_NAME=agent-worker-01
POLL_INTERVAL=10
```

## CLI flags

```bash
python3 daemon.py \
  --odoo-url https://odoo.example.com \
  --api-key your-runtime-api-key \
  --odoo-database production \
  --name agent-worker-01 \
  --poll-interval 10
```

## Multi-database Odoo

`ODOO_DATABASE` (or `--odoo-database`) is optional. Configure it only when the
Odoo server hosts more than one database and the runtime must use a specific
one. Leaving it unset or blank preserves the existing single-database behavior.

Before making runtime API calls, the runtime selects the configured database by
requesting `/web/login?db=<URL-encoded database>` and following redirects. The
resulting session cookie is retained and used for subsequent runtime API calls.

This is supported multi-database behavior. A release may claim it is E2E-proven
only after it passes the real multi-database scenario in the release checklist.

Keep the Odoo URL free of credentials and API keys. Set `API_KEY` through the
environment variable or `--api-key` flag; never put API keys in a URL.

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

Passing skills and MCP server configuration into the final instruction is
supported. Successful execution against a custom skill or a concrete MCP stdio
or HTTP server requires release-specific E2E evidence.

Supported placeholders:

| Placeholder | Value |
| --- | --- |
| `{instruction}` | Full instruction text. |
| `{task_name}` | Execution name. |
| `{task_id}` | Execution ID. |
| `{model}` | Agent model. |

Example:

```text
opencode run {instruction}
```
