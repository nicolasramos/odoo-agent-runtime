# Runtime release checklist

This checklist is mandatory for every public runtime release. Do not describe a
platform or integration as **E2E-proven** until its box is checked with a link
to or reference for the real-environment evidence. Unchecked items remain
**supported, not E2E-proven**.

## Repository

- [ ] No local absolute paths in docs.
- [ ] `.env` ignored and `.env.example` tracked.
- [ ] `.codebase-memory/` ignored.
- [ ] README install URLs point to the final public repository.
- [ ] License file exists.

## Validation

- [ ] `python3 -m py_compile daemon.py scripts/smoke.py`
- [ ] `python3 scripts/smoke.py`
- [ ] `python3 -m unittest tests.test_daemon`
- [ ] `bash -n install.sh`
- [ ] PowerShell syntax check for `install.ps1`
- [ ] Workflow YAML parses and the quality workflow runs static checks and `tests.test_daemon`.
- [ ] No legacy installer URL remains in release-facing files.

## Platforms

- [ ] Linux manual mode.
- [ ] Linux systemd mode.
- [ ] macOS manual mode.
- [ ] macOS launchd mode.
- [ ] Windows manual mode.
- [ ] Windows Scheduled Task mode.

## Mandatory end-to-end evidence

- [ ] **Real multi-DB:** select the intended database, retain its session, and complete one execution without sending the API key in the login request.
- [ ] **OpenCode:** complete a real queued execution with logs and a final result.
- [ ] **Hermes:** complete a real queued execution with logs and a final result.
- [ ] **Custom skill:** complete a real queued execution that requires the configured custom skill.
- [ ] **MCP stdio:** complete a real queued execution through a configured stdio MCP server.
- [ ] **MCP HTTP:** complete a real queued execution through a configured HTTP MCP server, including its required authentication.
- [ ] **Linux:** verify manual mode and systemd mode on a real host.
- [ ] **macOS:** verify manual mode and launchd mode on a real host.
- [ ] **Windows:** verify manual mode and Scheduled Task mode on a real host.
- [ ] For every E2E scenario above, heartbeat reaches Odoo, poll receives the queued execution, start and logs are reported, and completion, failure, and cancellation acknowledgement are verified where applicable.
