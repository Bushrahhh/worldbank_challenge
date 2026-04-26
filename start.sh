#!/bin/bash
set -e

PORT="${PORT:-8000}"
export API_BASE_URL="http://localhost:${PORT}"

echo "Starting UNMAPPED API on port ${PORT}..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}" &
API_PID=$!

echo "Starting UNMAPPED Telegram Bot (API_BASE_URL=${API_BASE_URL})..."
python telegram_bot/bot.py &
BOT_PID=$!

wait -n $API_PID $BOT_PID
EXIT_CODE=$?

echo "A process exited with code $EXIT_CODE — shutting down."
kill $API_PID $BOT_PID 2>/dev/null || true
exit $EXIT_CODE
