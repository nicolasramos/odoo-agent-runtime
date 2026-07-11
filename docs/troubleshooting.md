# Troubleshooting

Use this guide when the runtime does not connect or executions fail.

## Runtime does not appear online

Check:

- `ODOO_URL` is correct and reachable from the runtime host.
- `API_KEY` matches the runtime record in Odoo.
- Odoo is running and the addon is installed.
- Firewall or reverse proxy allows `/api/agent/runtime/heartbeat`.

Run manually:

```bash
python3 daemon.py
```

## Execution stays queued

Check:

- daemon is running;
- runtime is online;
- agent is assigned to that runtime;
- agent is active;
- runtime API key belongs to the same runtime;
- poll interval is not too high.

## CLI not found

The runtime does not install every agent CLI automatically.

Install the CLI on the runtime host, then verify:

```bash
which opencode
which hermes
which openclaw
```

On Windows:

```powershell
Get-Command opencode
```

## Command fails with quoting issues

Prefer placeholder-based commands:

```text
opencode run {instruction}
```

Avoid shell-specific command strings when possible.

## Service starts but does nothing

Run manually first. If manual mode works, inspect service logs:

- Linux: `journalctl -u odoo-agent-runtime -f`
- macOS: `launchctl list | grep odoo-agent-runtime`
- Windows: Task Scheduler history

## Odoo receives failed execution immediately

Check the execution error message in Odoo. Common causes:

- missing CLI;
- invalid command;
- timeout;
- permission denied;
- runtime host cannot access required files or network resources.
