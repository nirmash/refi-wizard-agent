# Embr Platform — OTEL Telemetry Support

## Overview

Embr supports exporting telemetry from your running sandboxes to external OTLP-compatible endpoints (e.g., Prometheus, Grafana Cloud, Azure Monitor). This is configured at the **project level** (with optional **environment-level overrides**) via the Embr API.

## How It Works

When telemetry is configured, the Embr deployment pipeline passes your OTLP endpoint config to the underlying ADC (Azure Dev Compute) sandboxes at creation time. The sandbox runtime then routes the specified data kinds to your endpoints.

**Telemetry is applied at deployment time** — changes require a redeployment to take effect on running instances.

## Configuration

### Data Model

```json
{
  "settings": {
    "telemetry": {
      "endpoints": [
        {
          "endpoint": "https://your-otlp-receiver.example.com/api/v1/otlp",
          "protocol": "Http",
          "data": ["Metrics", "ContainerOtel"],
          "auth": {
            "headerName": "Authorization",
            "secretVariableKey": "OTLP_AUTH_TOKEN"
          }
        }
      ]
    }
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `endpoint` | string | Yes | OTLP receiver URL |
| `protocol` | `Http` \| `Grpc` | No (default: `Http`) | OTLP transport protocol |
| `data` | string[] | Yes | Data kinds to export (see below) |
| `auth` | object | No | Authentication header config |
| `auth.headerName` | string | Yes (if auth) | HTTP header name (e.g., `Authorization`) |
| `auth.secretVariableKey` | string | Yes (if auth) | Embr variable key containing the secret value |

### Data Kinds

| Kind | Description |
|------|-------------|
| `Metrics` | Platform-level container metrics |
| `ContainerOtel` | OTEL traces/metrics emitted by the app itself (via OTEL SDK) |
| `ContainerStdoutStderr` | Container stdout/stderr logs |

## API Usage

### Set telemetry on a project

```bash
curl -X PATCH "https://api.embr.azure/projects/{projectId}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "telemetry": {
        "endpoints": [{
          "endpoint": "https://your-prometheus.app.embr.azure/api/v1/otlp",
          "protocol": "Http",
          "data": ["Metrics", "ContainerOtel"]
        }]
      }
    }
  }'
```

### Clear telemetry (disable)

```bash
curl -X PATCH "https://api.embr.azure/projects/{projectId}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"settings": {"telemetry": {"endpoints": []}}}'
```

### View current config

```bash
embr projects get {projectId} --json
# → settings.telemetry shows current endpoints
```

## App-Level OTEL Instrumentation

For your app to emit its own traces/metrics (routed via `ContainerOtel`), add OpenTelemetry SDK instrumentation. Example for Python/Flask:

```
# requirements.txt
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-flask>=0.41b0
opentelemetry-exporter-otlp-proto-http>=1.20.0
```

The `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable can be set to point at your collector. When `ContainerOtel` is enabled in the project telemetry config, the platform will also route app-emitted OTEL data to the configured endpoints.

## Environment Overrides

Environment-level telemetry overrides follow the same shape and are set via the environment update API:

```bash
curl -X PATCH "https://api.embr.azure/projects/{projectId}/environments/{envId}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "settingsOverrides": {
      "telemetry": {
        "endpoints": [{
          "endpoint": "https://staging-prometheus.example.com/api/v1/otlp",
          "protocol": "Http",
          "data": ["Metrics"]
        }]
      }
    }
  }'
```

## Key Files in Embr Repo

| File | Purpose |
|------|---------|
| `src/Embr.Contracts/Global/Models/ProjectSettings.cs` | Telemetry data model (`EmbrTelemetryConfig`, `EmbrTelemetryEndpoint`) |
| `src/Embr.Global.Api/Services/Deployment/TelemetryConfigResolver.cs` | Resolves config + auth secrets at deploy time |
| `src/Embr.Global.Api/Services/Deployment/DeploymentExecutionService.cs` | Passes telemetry to sandbox creation |
| `docs/arch/EmbrTelemetryExport.md` | Architecture documentation |

## CLI Support (Coming Soon)

A `embr telemetry` command group is being developed to manage telemetry config from the CLI:
- `embr telemetry show` — view current endpoints
- `embr telemetry add` — add an OTLP endpoint
- `embr telemetry remove` — remove an endpoint
- `embr telemetry clear` — disable telemetry
