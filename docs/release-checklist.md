# Runtime release checklist

## Repository

- [ ] No local absolute paths in docs.
- [ ] `.env` ignored and `.env.example` tracked.
- [ ] `.codebase-memory/` ignored.
- [ ] README install URLs point to the final public repository.
- [ ] License file exists.

## Validation

- [ ] `python3 -m py_compile daemon.py scripts/smoke.py`
- [ ] `python3 scripts/smoke.py`
- [ ] `bash -n install.sh`
- [ ] PowerShell syntax check for `install.ps1`

## Platforms

- [ ] Linux manual mode.
- [ ] Linux systemd mode.
- [ ] macOS manual mode.
- [ ] macOS launchd mode.
- [ ] Windows manual mode.
- [ ] Windows Scheduled Task mode.

## End-to-end

- [ ] Heartbeat reaches Odoo.
- [ ] Poll receives queued execution.
- [ ] Start is reported.
- [ ] Logs are streamed.
- [ ] Completion is reported.
- [ ] Failure is reported.
- [ ] Cancellation is acknowledged.
