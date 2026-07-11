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
| `0.2.x` | `18.0.1.5.x` | Chat executions and Odoo bus notifications. |

## Compatibility rules

- Runtime releases use semantic versioning.
- Odoo addon releases use Odoo-style versioning.
- Runtime `0.2.x` expects the addon execution API introduced in `18.0.1.4.x`.
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

## Support status

The runtime supports the documented payload and command interfaces below.
"Supported" is an implementation and documentation claim, not a certification
that every external CLI, operating system, or MCP transport has completed a
real-environment test. Only checklist entries marked with release evidence are
E2E-proven for that release.

## Operational compatibility

A compatible Odoo agent configuration should send:

- execution prompt;
- engine;
- CLI command;
- instructions;
- skills;
- MCP server configuration;
- timeout and execution limits.

MCP server configuration is passed through as instruction context. It does not
by itself prove that a particular stdio or HTTP server can authenticate, start,
or complete an end-to-end execution. Validate each production integration in
the release checklist.


## Chat execution support

Runtime `0.2.x` accepts execution payloads with optional chat fields:

- `source`;
- `chat_message_id`;
- `conversation`.

For `source=chat`, the runtime includes the current user message and conversation context in the instruction sent to the configured CLI. The Project task title is not prepended as the primary task, which prevents short chat messages from being redirected toward the task title.
