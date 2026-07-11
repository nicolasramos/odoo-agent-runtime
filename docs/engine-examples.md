# Engine CLI Examples

The runtime uses `agent.cli_command` from Odoo when present. Keep commands explicit so the runtime does not need to guess from agent names.

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
