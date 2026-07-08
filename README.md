# Odoo Agent Runtime

Odoo Agent Runtime is the cross-platform daemon that executes Odoo AI Agent System work on real machines. It connects to Odoo, polls queued executions, runs the configured local agent CLI, streams logs, and reports the final result.

It supports Linux, macOS, and Windows.

## What it does

1. Authenticates against Odoo with a runtime API key.
2. Sends heartbeat and host capabilities.
3. Polls queued executions assigned to this runtime.
4. Builds the final instruction from task, agent, skills, and MCP configuration.
5. Executes the configured CLI command.
6. Streams logs back to Odoo.
7. Sends optional intermediate chat messages.
8. Completes, fails, or acknowledges cancellation.

## Quick path

1. Create a runtime in Odoo and generate its API key.
2. Install this runtime on the machine that will execute agent CLIs.
3. Enter Odoo URL, API key, runtime name, and poll interval.
4. Choose manual mode or background service mode.
5. Confirm the runtime appears online in Odoo.
6. Assign agents to this runtime and send Project tasks to them.

## Requirements

- Python 3.8 or newer.
- Network access from the runtime host to Odoo.
- A valid Odoo runtime API key.
- The agent CLI tools you configure in Odoo, installed on this host.

## Linux and macOS install

```bash
curl -fsSL https://raw.githubusercontent.com/nicolasramos-es/odoo-agent-runtime/main/install.sh | bash
```

The installer asks for:

- Odoo URL;
- runtime API key;
- runtime display name;
- polling interval;
- install mode: manual or service/daemon.

Manual run:

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 daemon.py
```

## Windows install

Open PowerShell. Use Administrator only if your environment requires it for Scheduled Tasks.

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/nicolasramos-es/odoo-agent-runtime/main/install.ps1'))
```

Choose manual mode for a first test. Choose scheduled task mode only after the manual daemon connects successfully.

## Configuration

The runtime reads `.env` and accepts CLI flags.

| Variable | Flag | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `ODOO_URL` | `--odoo-url` | No | `http://localhost:8069` | Odoo base URL. |
| `API_KEY` | `--api-key` | Yes | empty | Runtime API key generated in Odoo. |
| `RUNTIME_NAME` | `--name` | No | host name | Display name shown in Odoo. |
| `POLL_INTERVAL` | `--poll-interval` | No | `10` | Seconds between polling cycles. |

Example:

```bash
python3 daemon.py \
  --odoo-url https://odoo.example.com \
  --api-key "YOUR_RUNTIME_KEY" \
  --name "agent-worker-01" \
  --poll-interval 5
```

## Command placeholders

Odoo sends each agent's `cli_command`. The runtime replaces these placeholders:

| Placeholder | Value |
| --- | --- |
| `{instruction}` | Full instruction text built from execution and agent config. |
| `{task_name}` | Execution name. |
| `{task_id}` | Execution ID. |
| `{model}` | Agent model value, when configured. |

If a command does not include `{instruction}` or `{task_name}`, the runtime appends the instruction as the final argument.

## Runtime API contract

The runtime uses these Odoo endpoints:

| Action | Endpoint |
| --- | --- |
| Heartbeat | `POST /api/agent/runtime/heartbeat` |
| Poll | `GET/POST /api/agent/runtime/poll` |
| Capabilities | `GET/POST /api/agent/runtime/capabilities` |
| Start | `POST /api/agent/execution/{id}/start` |
| Log | `POST /api/agent/execution/{id}/log` |
| Complete | `POST /api/agent/execution/{id}/complete` |
| Fail | `POST /api/agent/execution/{id}/fail` |
| Acknowledge cancellation | `POST /api/agent/execution/{id}/cancel/ack` |

Legacy `/api/agent/task/{id}/...` endpoints are still used as fallback for older Odoo installations.

## Service management

See [`docs/service-management.md`](docs/service-management.md) for systemd, launchd, and Windows Scheduled Task commands. See [`docs/installation.md`](docs/installation.md) for the full installation path.

## Engine examples

See [`docs/engine-examples.md`](docs/engine-examples.md) for Codex, Hermes, OpenCode, OpenClaw, Claude Code, and Custom CLI examples. See [`docs/compatibility.md`](docs/compatibility.md), [`docs/configuration.md`](docs/configuration.md), [`docs/security.md`](docs/security.md), and [`docs/troubleshooting.md`](docs/troubleshooting.md) for operations guidance.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `API key is required` | Set `API_KEY` in `.env` or pass `--api-key`. |
| Runtime does not appear online | Check `ODOO_URL`, API key, firewall, and Odoo logs. |
| Execution remains queued | Confirm the agent is assigned to this runtime and the daemon is running. |
| Execution fails with CLI not found | Install the CLI on this host or fix the agent `cli_command` in Odoo. |
| Service does not start | Run the daemon manually first, then inspect system logs. |
| Windows task does not run | Check Task Scheduler history, user permissions, and working directory. |

## Validation

```bash
python3 -m py_compile daemon.py scripts/smoke.py
python3 scripts/smoke.py
bash -n install.sh
```

If PowerShell is available:

```powershell
$errors = $null
[System.Management.Automation.PSParser]::Tokenize((Get-Content .\install.ps1 -Raw), [ref]$errors) | Out-Null
$errors
```

## Public release note

Before publishing, create the public repository, push `main`, and verify the raw GitHub URLs for `install.sh` and `install.ps1`.

## License

LGPL-3.


## Chat executions

When Odoo sends an execution with `source=chat`, the runtime includes the recent conversation in the final instruction. The final CLI output is reported as the execution result; Odoo turns that result into the agent chat reply.

The runtime can also send intermediate messages through `POST /api/agent/execution/{id}/message`.
