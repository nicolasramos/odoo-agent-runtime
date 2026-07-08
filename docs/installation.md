# Runtime installation

Install the runtime daemon on every machine that should execute Odoo agent work.

## Quick path

1. Create a runtime record in Odoo.
2. Generate and copy its API key.
3. Clone this repository on the execution machine.
4. Run the installer.
5. Choose manual mode first.
6. Confirm heartbeat in Odoo.
7. Switch to service/daemon mode only after the manual run works.

## Linux

```bash
git clone https://github.com/nicolasramos-es/odoo-agent-runtime.git
cd odoo-agent-runtime
bash install.sh
```

Manual run:

```bash
python3 daemon.py
```

Systemd mode is available from the installer when selected.

## macOS

```bash
git clone https://github.com/nicolasramos-es/odoo-agent-runtime.git
cd odoo-agent-runtime
bash install.sh
```

Launchd mode is available from the installer when selected.

## Windows

```powershell
git clone https://github.com/nicolasramos-es/odoo-agent-runtime.git
cd odoo-agent-runtime
.\install.ps1
```

Scheduled Task mode is available from the installer when selected.

## Required values

| Value | Example |
| --- | --- |
| Odoo URL | `https://odoo.example.com` |
| Runtime API key | `odoo_rt_xxx` |
| Runtime name | `agent-worker-01` |
| Poll interval | `10` |

## Existing `.env`

The installer does not silently overwrite `.env`. If `.env` exists, it asks before replacing it. If you decline, it writes `.env.new` and does not install/start a background service with stale settings.

## First validation

After starting the daemon:

1. Open Odoo.
2. Go to **AI Agents → Runtimes**.
3. Confirm `Last Seen` updates.
4. Send a simple task to an agent assigned to that runtime.
5. Confirm logs and final status.
