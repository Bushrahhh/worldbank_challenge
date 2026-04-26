#!/bin/bash
set -e

echo "Starting UNMAPPED API..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
API_PID=$!

echo "Starting UNMAPPED Telegram Bot..."
python telegram_bot/bot.py &
BOT_PID=$!

# If either process dies, kill the other and exit
wait -n $API_PID $BOT_PID
EXIT_CODE=$?

echo "A process exited with code $EXIT_CODE — shutting down."
kill $API_PID $BOT_PID 2>/dev/null || true
exit $EXIT_CODE
