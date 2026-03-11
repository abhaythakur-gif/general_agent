#!/bin/bash
# ─── Universal Agent Builder Platform — Local Dev Startup ───────────────────
# Run this from the agent_platform/ directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Universal Agent Builder Platform ==="
echo ""

# Check .env exists
if [ ! -f "../.env" ]; then
  echo "ERROR: .env file not found at $(realpath ../.env)"
  echo "Create it with: OPENAI_API_KEY, SERPAPI_KEY, weather_api_key"
  exit 1
fi

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies..."
  pip install -r requirements.txt
fi

echo "Starting FastAPI backend on http://localhost:8000 ..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

sleep 2

echo "Starting Streamlit UI on http://localhost:8501 ..."
cd ui
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
UI_PID=$!

echo ""
echo "✅ Platform is running!"
echo "   API:  http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   UI:   http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop both services."

trap "kill $API_PID $UI_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
