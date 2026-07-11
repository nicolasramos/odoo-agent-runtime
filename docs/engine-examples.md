# Engine CLI Examples

The runtime uses `agent.cli_command` from Odoo when present. Keep commands explicit so the runtime does not need to guess from agent names.

## Support boundary

These are supported command templates, not E2E-proven engine certifications.
The runtime invokes the configured executable and reports its output; the
runtime does not install, configure, or validate the external CLI. Before a
release is described as E2E-proven, record real-host evidence for OpenCode,
Hermes, the selected custom skill, and both MCP stdio and HTTP paths in the
mandatory release checklist.

## Placeholders

| Placeholder | Meaning |
| --- | --- |
| `{instruction}` | Full instruction built from execution prompt, agent instructions, skills, and MCP config. |
| `{task_name}` | Execution name. |
| `{task_id}` | Execution ID. |
| `{model}` | Agent model value. |

## Examples

```text
opencode run {instruction}
hermes run --context {instruction}
openclaw agent --task {task_name} --context {instruction}
claude --print {instruction}
```

## Rules

- If the CLI is missing, the runtime fails the execution.
- Do not place secrets inside `cli_command`.
- Prefer environment variables or runtime-side secret stores for credentials.
- Test each command manually on the runtime host before assigning production tasks.
