# Compatibility

Odoo Agent Runtime is released independently from the Odoo addon repository.

Runtime code lives here:

```text
odoo-agent-runtime
```

Odoo modules live separately:

```text
odoo-addons
└── odoo_agent
```

## Version matrix

| Runtime version | Addon version | Status |
| --- | --- | --- |
| `0.1.x` | `18.0.1.4.x` | First public execution baseline. |
| `0.2.x` | `18.0.1.5.x`‑`18.0.1.6.x` | Chat executions and Odoo bus notifications. |
| `0.3.x` | `18.0.1.7.x` | Public release. Task-context Agent Communications UI on top of chat executions. |

## Compatibility rules

- Runtime releases use semantic versioning.
- Odoo addon releases use Odoo-style versioning.
- Runtime `0.3.x` expects the addon execution API introduced in `18.0.1.4.x`.
- The runtime still attempts legacy task endpoints as fallback, but new deployments should use execution endpoints.

## API expectations

The Odoo addon must provide:

- `POST /api/agent/runtime/heartbeat`
- `GET/POST /api/agent/runtime/poll`
- `GET/POST /api/agent/runtime/capabilities`
- `POST /api/agent/execution/{id}/start`
- `POST /api/agent/execution/{id}/log`
- `POST /api/agent/execution/{id}/complete`
- `POST /api/agent/execution/{id}/fail`
- `POST /api/agent/execution/{id}/cancel/ack`
- `POST /api/agent/execution/{id}/message`

## Operational compatibility

A compatible Odoo agent configuration should send:

- execution prompt;
- engine;
- CLI command;
- instructions;
- skills;
- MCP server configuration;
- timeout and execution limits.


## Chat execution support

Runtime `0.3.x` accepts execution payloads with optional chat fields:

- `source`;
- `chat_message_id`;
- `conversation`.

For `source=chat`, the runtime includes the current user message and conversation context in the instruction sent to the configured CLI. The Project task title is not prepended as the primary task, which prevents short chat messages from being redirected toward the task title.
