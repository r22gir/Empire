#!/bin/bash
cd /home/rg/empire-repo-v10/backend
source /home/rg/empire-repo/backend/venv/bin/activate
exec python3 -m app.services.max.orchestrator