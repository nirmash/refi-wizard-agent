#!/bin/bash
# Embr startup script — writes .env and starts gunicorn

cat > .env << 'ENVEOF'
AZURE_AI_API_KEY=EgsUnoGDlo559BTgvPPTq1fLdzmaR7O5A1qK0C5T4GERuSDO2y4OJQQJ99ALACHYHv6XJ3w3AAAAACOGEymi
AGENT_VERSION=5
OTEL_EXPORTER_OTLP_ENDPOINT=https://production-otlp-2fa05823.app.embr.azure
ENVEOF

# Clear stale DB so seed data refreshes on code changes
rm -f homes.db

exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 app:app
