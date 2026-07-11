# Odoo Agent Runtime

Odoo Agent Runtime is the cross-platform daemon that executes Odoo AI Agent System work on real machines. It connects to Odoo, polls queued executions, runs the configured local agent CLI, streams logs, and reports the final result.

## Release confidence

**Supported** means the runtime exposes an implementation path and documented
operator guidance. **E2E-proven** means that behavior has been exercised in a
real release environment. Platform, engine, skill, and MCP combinations remain
supported only until they are checked off in the mandatory release checklist.

The runtime supports Linux, macOS, and Windows. See
[`docs/release-checklist.md`](docs/release-checklist.md) for the required
cross-platform and integration evidence before claiming a release is E2E-proven.

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
3. Enter Odoo URL, optional database name, API key, runtime name, and poll interval.
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
curl -fsSL https://raw.githubusercontent.com/nicolasramos/odoo-agent-runtime/main/install.sh | bash
```

The installer asks for:

- Odoo URL;
- optional Odoo database name for multi-database instances;
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
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/nicolasramos/odoo-agent-runtime/main/install.ps1'))
```

Choose manual mode for a first test. Choose scheduled task mode only after the manual daemon connects successfully.

## Configuration

The runtime reads `.env` and accepts CLI flags.

| Variable | Flag | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `ODOO_URL` | `--odoo-url` | No | `http://localhost:8069` | Odoo base URL. |
| `ODOO_DATABASE` | `--odoo-database` | No | empty | Database name for a multi-database Odoo instance. When set, the runtime follows `/web/login?db=<URL-encoded database>` before runtime API calls and retains the selected database's session cookie. Omit or leave blank to preserve single-database behavior. |
| `API_KEY` | `--api-key` | Yes | empty | Runtime API key generated in Odoo. |
| `RUNTIME_NAME` | `--name` | No | host name | Display name shown in Odoo. |
| `POLL_INTERVAL` | `--poll-interval` | No | `10` | Seconds between polling cycles. |

Example:

```bash
python3 daemon.py \
  --odoo-url https://odoo.example.com \
  --odoo-database "customer-production" \
  --api-key "YOUR_RUNTIME_KEY" \
  --name "agent-worker-01" \
  --poll-interval 5
```

`ODOO_DATABASE` is optional. Use it only when the Odoo server hosts multiple databases. The database selection request follows redirects and keeps the resulting session cookie for subsequent runtime API calls. Do not put API keys in URLs; configure `API_KEY` through `.env` or `--api-key`.

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

See [`docs/engine-examples.md`](docs/engine-examples.md) for supported command
shapes for Codex, Hermes, OpenCode, OpenClaw, Claude Code, and custom CLIs.
Examples are not an E2E compatibility certification; release evidence is
required for the combinations listed in the release checklist. See
[`docs/compatibility.md`](docs/compatibility.md),
[`docs/configuration.md`](docs/configuration.md),
[`docs/security.md`](docs/security.md), and
[`docs/troubleshooting.md`](docs/troubleshooting.md) for operations guidance.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `API key is required` | Set `API_KEY` in `.env` or pass `--api-key`. |
| Runtime does not appear online | Check `ODOO_URL`, API key, firewall, and Odoo logs. |
| Runtime stops before API calls on a multi-database server | Verify `ODOO_DATABASE` matches the database name and that `ODOO_URL` can reach its login page. Leave `ODOO_DATABASE` blank for a single-database server. |
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

LGPL-3.0-or-later. See [`LICENSE`](LICENSE).


## Chat executions

When Odoo sends an execution with `source=chat`, the runtime treats the current prompt as a user message and includes the recent conversation in the final instruction. It does not prepend the Project task title as the primary `Task`, so short messages such as "hello" remain conversational instead of being interpreted as a request to work on the task title.

The final CLI output is reported as the execution result; Odoo turns that result into the agent chat reply.

The runtime can also send intermediate messages through `POST /api/agent/execution/{id}/message`.
