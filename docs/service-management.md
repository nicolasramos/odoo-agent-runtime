# Runtime Service Management

Use this guide after the interactive installer has created a background service/task.

## Linux systemd

```bash
sudo systemctl status odoo-agent-runtime
sudo systemctl restart odoo-agent-runtime
sudo systemctl stop odoo-agent-runtime
journalctl -u odoo-agent-runtime -f
```

Uninstall:

```bash
sudo systemctl stop odoo-agent-runtime || true
sudo systemctl disable odoo-agent-runtime || true
sudo rm -f /etc/systemd/system/odoo-agent-runtime.service
sudo systemctl daemon-reload
```

## macOS launchd

```bash
launchctl list | grep odoo-agent-runtime
launchctl unload ~/Library/LaunchAgents/com.odoo.odoo-agent-runtime.plist
launchctl load ~/Library/LaunchAgents/com.odoo.odoo-agent-runtime.plist
```

Logs are written under the runtime install directory, usually:

```text
~/odoo-agent-runtime/logs/stdout.log
~/odoo-agent-runtime/logs/stderr.log
```

Uninstall:

```bash
launchctl unload ~/Library/LaunchAgents/com.odoo.odoo-agent-runtime.plist || true
rm -f ~/Library/LaunchAgents/com.odoo.odoo-agent-runtime.plist
```

## Windows Scheduled Task

Open **Task Scheduler** and look for `OdooAgentRuntime`.

PowerShell commands:

```powershell
Get-ScheduledTask -TaskName OdooAgentRuntime
Start-ScheduledTask -TaskName OdooAgentRuntime
Stop-ScheduledTask -TaskName OdooAgentRuntime
Unregister-ScheduledTask -TaskName OdooAgentRuntime -Confirm:$false
```

## Manual mode

Manual mode does not install a service/task. Run:

```bash
python3 daemon.py
```

or on Windows:

```powershell
python .\daemon.py
```
