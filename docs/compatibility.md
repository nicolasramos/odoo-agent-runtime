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
| `0.1.x` | `18.0.1.4.x` | First public baseline. |

## Compatibility rules

- Runtime releases use semantic versioning.
- Odoo addon releases use Odoo-style versioning.
- Runtime `0.1.x` expects the addon execution API introduced in `18.0.1.4.x`.
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

## Operational compatibility

A compatible Odoo agent configuration should send:

- execution prompt;
- engine;
- CLI command;
- instructions;
- skills;
- MCP server configuration;
- timeout and execution limits.
