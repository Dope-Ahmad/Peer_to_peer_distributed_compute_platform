# ComputeLend

A distributed compute lending platform — submit Python jobs, have them executed
in sandboxed Docker containers across a pool of worker machines.

## Status: Week 1, Day 1 — early scaffolding

## Running locally
\`\`\`bash
docker compose up -d
source venv/bin/activate
uvicorn coordinator.main:app --reload --port 8000
\`\`\`

Visit http://localhost:8000/docs for the interactive API.