# Runtime security

The runtime executes local commands. Treat it as privileged automation infrastructure.

## Core rules

- Use one API key per runtime host.
- Do not commit `.env`.
- Run under a dedicated OS user when possible.
- Install only required CLIs.
- Keep secrets out of prompts and logs.
- Do not execute unreviewed shell pipelines.
- Restrict file and network permissions according to the workload.

## API key handling

The API key authenticates the runtime to Odoo. Store it in `.env` or an OS secret mechanism.

Rotate it if:

- the machine is decommissioned;
- the key appears in logs;
- the key is shared accidentally;
- a team member with access leaves.

## Command execution

The runtime executes agent `cli_command` values configured in Odoo. Review those commands before production use.

Prefer direct executable invocation:

```text
opencode run --instruction {instruction}
```

Avoid commands that download and execute remote scripts.

## Logs

Logs are sent back to Odoo. Avoid logging credentials, private tokens, or sensitive customer data.
