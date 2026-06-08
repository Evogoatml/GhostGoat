#!/bin/bash
# GhostGoat Bot Launcher
cd /home/popic/GhostGoat
exec > /tmp/ghostgoat_daemon.log 2>&1
while true; do
    echo "Starting bot at $(date)"
    python3 -u bots/simple_bot.py &
    BOT_PID=$!
    echo "Bot PID: $BOT_PID"
    while kill -0 $BOT_PID 2>/dev/null; do sleep 5; done
    echo "Bot died at $(date), restarting in 5s..."
    sleep 5
done
