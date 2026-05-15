#!/bin/bash
cd /root/onehubserver

echo "[deploy] Pulling latest code..."
git pull

echo "[deploy] Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt -q

echo "[deploy] Running migrations..."
alembic upgrade head

echo "[deploy] Restarting server..."
kill $(lsof -ti:8000) 2>/dev/null
nohup uvicorn app.main:app --host 172.17.0.1 --port 8000 > /tmp/onehub.log 2>&1 &

echo "[deploy] Done!"
